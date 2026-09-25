from datetime import date
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from administration import flat_lifecycle as lifecycle
from administration.administration.doctype.flat import flat as flat_module


class Record(dict):
	__getattr__ = dict.get
	__setattr__ = dict.__setitem__


class Doc(Record):
	def __init__(self, **values):
		super().__init__(values)
		self.flags = Record()
		self.meta = SimpleNamespace(has_field=lambda field: field in self)
		self.previous = None
		self.saved = False

	def set(self, key, value):
		self[key] = value

	def append(self, key, row):
		self.setdefault(key, []).append(Doc(**row))

	def as_dict(self):
		return {k: v for k, v in self.items() if k not in ("flags", "meta", "previous", "saved")}

	def db_set(self, key, value=None, **kwargs):
		self.update(key if isinstance(key, dict) else {key: value})

	def check_permission(self, permission):
		pass

	def get_doc_before_save(self):
		return self.previous

	def save(self, **kwargs):
		flat_module.Flat.validate(self)
		self.saved = True


def rent_row(name="FC-1", start="2026-01-01", end="2026-09-30", contract=False):
	return Doc(rent_contract=None if contract else name, rent_contract_type="Flat Contract",
		add_flat_to_contract=name if contract else None, rent_start_date=start, rent_end_date=end)


class TestCoverage(TestCase):
	def test_expiration_boundary_is_after_end_date(self):
		rows = [rent_row()]
		self.assertEqual(lifecycle.coverage_status(rows, date="2026-09-30")[0], "Active")
		self.assertEqual(lifecycle.coverage_status(rows, date="2026-10-01")[0], "Expired")

	def test_future_renewal_does_not_cover_gap(self):
		rows = [rent_row(), rent_row("FC-2", "2026-11-01", "2027-10-31")]
		self.assertEqual(lifecycle.coverage_status(rows, date="2026-10-15"), ("Expired", date(2027, 10, 31)))
		self.assertEqual(lifecycle.coverage_status(rows, "Expired", "2026-11-01")[0], "Active")

	def test_new_approved_coverage_prevents_expiration(self):
		rows = [rent_row(), rent_row("FC-2", "2026-10-01", "2027-09-30")]
		self.assertEqual(lifecycle.coverage_status(rows, date="2026-10-01")[0], "Active")

	def test_termination_is_not_undone_by_scheduler(self):
		self.assertEqual(lifecycle.coverage_status([rent_row()], "Inactive", "2026-09-26")[0], "Inactive")

	def test_missing_legacy_dates_do_not_invent_expiry(self):
		self.assertEqual(lifecycle.coverage_status([rent_row(start=None, end=None)], "Active", "2026-09-26"), ("Active", None))

	def test_latest_is_based_on_start_date_not_row_position(self):
		latest = rent_row("FC-2", "2027-01-01", "2027-12-31")
		self.assertIs(lifecycle.latest_row([latest, rent_row()]), latest)

	def test_unapproved_cancelled_and_terminated_sources_are_ignored(self):
		with patch.object(lifecycle, "frappe") as frappe:
			frappe.db.get_value.side_effect = [
				Record(docstatus=1, workflow_state="Approved", contract_status="Active"),
				Record(docstatus=0, workflow_state="Draft", contract_status="Active"),
				Record(docstatus=2, workflow_state="Approved", contract_status="Active"),
				Record(docstatus=1, workflow_state="Approved", contract_status="Terminated"),
			]
			flat = Doc(rent_contracts=[rent_row(f"FC-{i}") for i in range(4)])
			self.assertEqual(lifecycle.approved_rows(flat), flat.rent_contracts[:1])


class TestLifecycle(TestCase):
	def setUp(self):
		self.patcher = patch.object(lifecycle, "frappe")
		self.frappe = self.patcher.start()
		self.addCleanup(self.patcher.stop)
		self.frappe.throw.side_effect = ValueError
		self.flat = Doc(name="Flat 1", doctype="Flat", docstatus=1, rent_type="Direct Rent", flat_status="Active",
			flat_title="Flat 1", flat_contract="FC-1", flat_contract_request="FCR-1", rent_contracts=[rent_row()],
			pending_document_type="Flat Request", pending_document="FRQ-2")
		self.frappe.get_doc.return_value = self.flat

	def test_pending_renewal_blocks_a_competing_renewal_or_termination(self):
		for root in (("Flat Request", "FRQ-3"), ("Rent Termination Request", "RTR-1"), (None, None)):
			with self.subTest(root=root), self.assertRaises(ValueError):
				lifecycle.ensure_pending(self.flat, root, allow_empty=True)
		lifecycle.ensure_pending(self.flat, ("Flat Request", "FRQ-2"))

	def test_closed_root_cannot_create_downstream_contract(self):
		self.flat.pending_document = None
		with self.assertRaises(ValueError):
			lifecycle.ensure_pending(self.flat, ("Flat Request", "FRQ-2"))

	def test_same_root_can_continue_through_all_direct_stages(self):
		for dt in ("Flat Request", "Flat Contract Request", "Flat Contract"):
			doc = Doc(doctype=dt, name="FRQ-2" if dt == "Flat Request" else "next", flat_request="FRQ-2")
			lifecycle.ensure_pending(self.flat, lifecycle.root_reference(doc))

	def test_request_approval_keeps_reservation_but_rejection_releases_it(self):
		doc = Doc(doctype="Flat Request", name="FRQ-2", type="Renew", flat=self.flat.name, workflow_state="Approved")
		lifecycle.workflow_updated(doc)
		self.assertEqual(self.flat.pending_document, "FRQ-2")
		doc.workflow_state = "Draft"
		lifecycle.workflow_updated(doc)
		self.assertEqual(self.flat.pending_document, "FRQ-2")
		doc.workflow_state = "Rejected"
		lifecycle.workflow_updated(doc)
		self.assertIsNone(self.flat.pending_document)

	def test_stale_previous_contract_is_rejected(self):
		with patch.object(lifecycle, "latest_for_action", return_value=rent_row("FC-NEW")):
			with self.assertRaises(ValueError):
				lifecycle.validate_latest(Doc(doctype="Flat Contract", last_rent_contract="FC-OLD"), self.flat)

	def test_date_order_is_validated(self):
		for start, end in ((None, "2027-01-01"), ("2027-01-01", None), ("2027-01-01", "2026-01-01")):
			with self.subTest(start=start, end=end), self.assertRaises(ValueError):
				lifecycle.validate_dates(Doc(contract_start_date=start, contract_end_date=end))

	def test_completed_documents_cannot_be_cancelled_or_deleted(self):
		for dt in ("Flat Contract", "Add Flat to Contract", "Rent Termination Request", "Flat Termination"):
			with self.subTest(dt=dt), self.assertRaises(ValueError):
				lifecycle.prevent_cancel_or_delete(Doc(doctype=dt, type="Renew", lifecycle_applied=1))

	def test_flat_status_cannot_be_forged(self):
		self.flat.previous = Doc(flat_status="Active")
		self.flat.flat_status = "Inactive"
		with self.assertRaises(ValueError):
			lifecycle.validate_flat_update(self.flat)

	def test_renewal_preserves_identity_and_history_and_applies_once(self):
		source = Doc(doctype="Flat Contract", name="FC-2", docstatus=1, workflow_state="Approved", type="Renew",
			flat=self.flat.name, flat_request="FRQ-2", flat_contract_request="FCR-2", last_rent_contract="FC-1",
			flat_title="Renewed Flat Title", contract_start_date="2026-10-01", contract_end_date="2027-09-30",
			project="New Project", no_of_rooms=4, no_of_beds=8, monthly_rent=2000, deposit=100,
			payment_cycle="Monthly", flat_owner="SUP-2", second_party_name="New Owner", flat_contents=[])
		with patch.object(lifecycle, "latest_for_action", return_value=self.flat.rent_contracts[0]), \
			patch.object(lifecycle, "approved_rows", side_effect=lambda flat: flat.rent_contracts), \
			patch.object(lifecycle, "today", return_value="2026-10-01"):
			lifecycle.apply_renewal(source)
			lifecycle.apply_renewal(source)
		self.assertTrue(self.flat.saved)
		self.assertEqual(self.flat.flat_title, "Renewed Flat Title")
		self.assertEqual(self.flat.flat_contract, "FC-1")
		self.assertEqual(self.flat.flat_contract_request, "FCR-1")
		self.assertEqual([r.get("rent_contract") for r in self.flat.rent_contracts], ["FC-1", "FC-2"])
		self.assertEqual((self.flat.rent, self.flat.party, self.flat.project), (2000, "SUP-2", "New Project"))
		self.assertEqual(self.flat.flat_status, "Active")
		self.assertIsNone(self.flat.pending_document)
		self.assertEqual(source.created_flat, "Flat 1")
		self.assertFalse(self.flat.flags.get("lifecycle_update"))

	def test_termination_marks_flat_and_target_contract_once(self):
		for dt, root, contract in (("Rent Termination Request", "RTR-1", False), ("Flat Termination", "FT-1", True)):
			self.flat.pending_document_type, self.flat.pending_document = dt, root
			row = rent_row("AFTC-1" if contract else "FC-1", contract=contract)
			doc = Doc(doctype=dt, name=root, flat=self.flat.name, docstatus=1, workflow_state="Approved")
			doc[lifecycle.reference_field(doc)] = lifecycle.row_reference(row)[1]
			with patch.object(lifecycle, "latest_for_action", return_value=row):
				lifecycle.apply_termination(doc)
				lifecycle.apply_termination(doc)
			self.assertEqual(self.flat.flat_status, "Inactive")
			self.frappe.db.set_value.assert_any_call(*lifecycle.row_reference(row), "contract_status", "Terminated")
			self.assertEqual(doc.lifecycle_applied, 1)
		self.assertEqual(self.frappe.db.set_value.call_count, 2)

	def test_unapproved_termination_cannot_be_applied(self):
		self.flat.pending_document_type = "Flat Termination"
		self.flat.pending_document = "FT-1"
		with self.assertRaises(ValueError):
			lifecycle.apply_termination(Doc(doctype="Flat Termination", name="FT-1", flat=self.flat.name,
				docstatus=0, workflow_state="Draft"))

	def test_inactive_flat_action_is_blocked_before_document_creation(self):
		self.flat.flat_status = "Inactive"
		for action in ("Renew", "Terminate"):
			with self.assertRaises(ValueError):
				lifecycle.start_action(self.flat.name, action)
		self.frappe.new_doc.assert_not_called()

	def test_scheduler_locks_each_flat_and_preserves_inactive(self):
		self.flat.flat_status = "Inactive"
		self.frappe.get_all.return_value = [self.flat.name]
		with patch.object(lifecycle, "approved_rows", return_value=[rent_row()]):
			lifecycle.expire_flats()
		self.frappe.get_doc.assert_called_with("Flat", self.flat.name, for_update=True)
		self.assertEqual(self.flat.flat_status, "Inactive")

	def test_contract_renewal_appends_add_flat_reference(self):
		self.flat.rent_type = "Contract"
		self.flat.add_flat_to_contract = "AFTC-1"
		self.flat.flat_contract = None
		self.flat.accommodation_contract = "AC-1"
		self.flat.rent_contracts = [rent_row("AFTC-1", contract=True)]
		self.flat.pending_document_type, self.flat.pending_document = "Add Flat to Contract", "AFTC-2"
		source = Doc(doctype="Add Flat to Contract", name="AFTC-2", docstatus=1, workflow_state="Approved",
			type="Renew", flat=self.flat.name, last_add_flat_to_contract="AFTC-1", flat_title="Flat 1",
			accommodation_contract="AC-2", flat_owner="Owner", no_of_rooms=2, payment_cycle="Monthly",
			monthly_rent=500, contract_start_date="2026-10-01", contract_end_date="2027-09-30")
		with patch.object(lifecycle, "latest_for_action", return_value=self.flat.rent_contracts[0]), \
			patch.object(lifecycle, "approved_rows", side_effect=lambda flat: flat.rent_contracts), \
			patch.object(flat_module, "frappe") as flat_frappe:
			flat_frappe.get_doc.return_value = Doc(name="AC-2", docstatus=1, party="New Supplier")
			lifecycle.apply_renewal(source)
		self.assertEqual([r.get("add_flat_to_contract") for r in self.flat.rent_contracts], ["AFTC-1", "AFTC-2"])
		self.assertEqual(self.flat.add_flat_to_contract, "AFTC-1")
		self.assertEqual(self.flat.accommodation_contract, "AC-2")
		self.assertEqual(self.flat.party, "New Supplier")

	def test_renewal_identity_is_inherited_from_approved_parent(self):
		parent = Doc(doctype="Flat Request", name="FRQ-2", docstatus=1, workflow_state="Approved", type="Renew",
			flat="Flat 1", last_rent_contract="FC-1")
		self.frappe.get_doc.return_value = parent
		self.frappe.db.get_value.return_value = None
		doc = Doc(doctype="Flat Contract Request", name="FCR-2", flat_request="FRQ-2", type="New Flat", flat="forged")
		lifecycle.inherit_renewal(doc)
		self.assertEqual((doc.type, doc.flat, doc.last_rent_contract), ("Renew", "Flat 1", "FC-1"))
		self.frappe.db.get_value.return_value = "existing-successor"
		with self.assertRaises(ValueError):
			lifecycle.inherit_renewal(doc)

	def test_contract_cannot_skip_the_contract_request_stage(self):
		with self.assertRaises(ValueError):
			lifecycle.inherit_renewal(Doc(doctype="Flat Contract", type="Renew", flat_request="FRQ-2", flat="Flat 1"))

	def test_pending_reservation_is_created_once_and_cannot_be_stolen(self):
		self.flat.pending_document = None
		doc = Doc(doctype="Flat Request", name="FRQ-2", type="Renew", flat="Flat 1")
		lifecycle.reserve_request(doc)
		lifecycle.reserve_request(doc)
		self.assertEqual(self.flat.pending_document, "FRQ-2")
		with self.assertRaises(ValueError):
			lifecycle.reserve_request(Doc(doctype="Rent Termination Request", name="RTR-1", flat="Flat 1"))

	def test_action_routes_all_four_paths_and_records_latest_reference(self):
		cases = (("Direct Rent", "Renew", "Flat Request"),
			("Direct Rent", "Terminate", "Rent Termination Request"),
			("Contract", "Renew", "Add Flat to Contract"),
			("Contract", "Terminate", "Flat Termination"))
		for rent_type, action, doctype in cases:
			with self.subTest(rent_type=rent_type, action=action):
				self.flat.rent_type = rent_type
				self.flat.pending_document = None
				self.flat.pending_document_type = None
				row = rent_row("LATEST", contract=rent_type == "Contract")
				doc = Doc(doctype=doctype, name="NEW-1")
				doc.insert = Mock(side_effect=lambda **kwargs: lifecycle.reserve_request(doc))
				self.frappe.new_doc.return_value = doc
				self.frappe.get_roles.return_value = ["Legal User"]
				self.frappe.get_doc.side_effect = [self.flat, Doc(name="LATEST"), self.flat]
				with patch.object(lifecycle, "latest_for_action", return_value=row), patch.object(lifecycle, "snapshot_flat"):
					result = lifecycle.start_action("Flat 1", action)
				self.assertEqual(result, {"doctype": doctype, "name": "NEW-1"})
				self.assertEqual(doc.flat, "Flat 1")
				self.assertEqual(doc.get(lifecycle.reference_field(doc)), "LATEST")
				self.assertEqual(self.flat.pending_document, "NEW-1")
				self.assertEqual(self.flat.pending_document_type, doctype)

	def test_failed_flat_save_clears_trusted_update_flags(self):
		source = Doc(doctype="Flat Contract", name="FC-2", docstatus=1, workflow_state="Approved", type="Renew",
			flat="Flat 1", flat_request="FRQ-2", last_rent_contract="FC-1", flat_title="Flat 1",
			contract_start_date="2026-10-01", contract_end_date="2027-09-30", payment_cycle="Monthly")
		with patch.object(lifecycle, "latest_for_action", return_value=self.flat.rent_contracts[0]), \
			patch.object(lifecycle, "approved_rows", side_effect=lambda flat: flat.rent_contracts), \
			patch.object(Doc, "save", side_effect=RuntimeError("database error")):
			with self.assertRaises(RuntimeError):
				lifecycle.apply_renewal(source)
		self.assertNotIn("lifecycle_update", self.flat.flags)
		self.assertNotIn("ignore_validate_update_after_submit", self.flat.flags)
		self.assertFalse(source.lifecycle_applied)
