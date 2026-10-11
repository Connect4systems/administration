# Copyright (c) 2026, Connect 4 Systems and contributors
# For license information, please see license.txt

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from administration.administration.doctype.flat import flat as module


class Flags(dict):
	__getattr__ = dict.get
	__setattr__ = dict.__setitem__


class DocumentValues(SimpleNamespace):
	def __init__(self, **values):
		values.setdefault("flags", Flags())
		super().__init__(**values)

	def get(self, key):
		return getattr(self, key, None)

	def set(self, key, value):
		setattr(self, key, value)

	def append(self, key, value):
		getattr(self, key).append(value)


class TestFlat(TestCase):
	def setUp(self):
		self.patcher = patch.object(module, "frappe")
		self.frappe = self.patcher.start()
		self.addCleanup(self.patcher.stop)
		self.frappe.throw.side_effect = ValueError
		self.frappe.db.get_value.return_value = None
		self.source = DocumentValues(
			doctype="Flat Contract", name="FC-001", docstatus=1, flat_title="Building A - Flat 12",
			check_permission=Mock(), db_set=Mock(), project="PROJ-1", flat_owner="SUP-1",
			second_party_name="Owner Name", no_of_rooms=3.0, no_of_beds=0,
			monthly_rent=1200, deposit=0, payment_cycle="Yearly",
			contract_start_date="2026-10-01", contract_end_date="2027-09-30",
			flat_contents=[{"item_name": "Bed", "qty": 0, "name": "old-row"}],
		)
		self.frappe.get_doc.return_value = self.source

	def test_creation_requires_exactly_one_source(self):
		for values in ({}, {"flat_contract": "FC-1", "add_flat_to_contract": "AFTC-1"}):
			with self.subTest(values=values), self.assertRaises(ValueError):
				module._get_source(DocumentValues(**values))

	def test_source_must_be_submitted_and_readable(self):
		flat = DocumentValues(flat_contract="FC-001")
		for status in (0, 2):
			self.source.docstatus = status
			with self.assertRaises(ValueError):
				module._get_source(flat)
		self.source.docstatus = 1
		self.source.check_permission.side_effect = PermissionError
		with self.assertRaises(PermissionError):
			module._get_source(flat)

	def test_private_request_type_is_carried_to_created_flat(self):
		self.source.request_type = "Private"
		flat = DocumentValues(flat_contract="FC-001")
		module._set_source_values(flat, self.source)
		self.assertEqual(flat.request_type, "Private")

	def test_request_maps_contract_party_and_contents(self):
		flat = DocumentValues(flat_contract="FC-001")
		flat.flags.creation_action = module._CREATE_FLAT_TOKEN
		module.Flat.before_insert(flat)
		self.assertEqual(flat.flat_title, "Building A - Flat 12")
		self.assertEqual(flat.rent_contracts[0]["rent_contract"], "FC-001")
		self.assertEqual(flat.rent_type, "Direct Rent")
		self.assertEqual(flat.request_type, "Share")
		self.assertEqual(flat.rent_contracts[0]["rent_contract_type"], "Flat Contract")
		self.assertEqual(flat.rent_contracts[0]["rent_start_date"], "2026-10-01")
		self.assertEqual(flat.rent_contracts[0]["rent_end_date"], "2027-09-30")
		self.assertIsNone(flat.get("rent_start_date"))
		self.assertIsNone(flat.accommodation_contract)
		self.assertEqual(flat.party, "SUP-1")
		self.assertEqual(flat.owner_name, "Owner Name")
		self.assertEqual(flat.no_of_room, "3")
		self.assertEqual(flat.payment_schedule, "Annual")
		self.assertEqual(flat.security_deposit, 0)
		self.assertEqual(flat.no_of_beds, 0)
		self.assertEqual(flat.flat_contents[0]["qty"], 0)
		self.assertNotIn("name", flat.flat_contents[0])

	def test_accommodation_maps_contract_party_not_owner_text(self):
		self.source.doctype = "Add Flat to Contract"
		self.source.accommodation_contract = "AC-001"
		self.source.flat_owner = "Free text owner"
		contract = DocumentValues(name="AC-001", party="SUP-2", docstatus=1, check_permission=Mock())
		self.frappe.get_doc.side_effect = [self.source, contract]
		flat = DocumentValues(add_flat_to_contract="AFTC-001", rent_contract="forged")
		flat.flags.creation_action = module._CREATE_FLAT_TOKEN
		module.Flat.before_insert(flat)
		self.assertEqual(flat.accommodation_contract, "AC-001")
		self.assertEqual(flat.flat_title, "Building A - Flat 12")
		self.assertEqual(flat.rent_type, "Contract")
		self.assertEqual(flat.party, "SUP-2")
		self.assertEqual(flat.owner_name, "Free text owner")
		self.assertIsNone(flat.rent_contracts[0]["rent_contract"])
		self.assertEqual(flat.rent_contracts[0]["add_flat_to_contract"], self.source.name)
		contract.check_permission.assert_called_once_with("read")

	def test_accommodation_contract_required_and_not_cancelled(self):
		self.source.doctype = "Add Flat to Contract"
		with self.assertRaises(ValueError):
			module._set_source_values(DocumentValues(), self.source)
		self.source.accommodation_contract = "AC-001"
		self.frappe.get_doc.return_value = DocumentValues(docstatus=2, check_permission=Mock())
		with self.assertRaises(ValueError):
			module._set_source_values(DocumentValues(), self.source)

	def test_existing_legacy_flat_can_still_be_saved(self):
		previous = DocumentValues(rent_contract="FC-001", rent_contract_type="Flat Contract")
		flat = DocumentValues(**vars(previous), get_doc_before_save=lambda: previous)
		module.Flat.validate(flat)

	def test_existing_source_cannot_be_replaced(self):
		previous = DocumentValues(flat_contract="FC-001")
		flat = DocumentValues(flat_contract="FC-002", get_doc_before_save=lambda: previous)
		with self.assertRaises(ValueError):
			module.Flat.validate(flat)

	def test_party_is_refetched_on_save(self):
		flat = DocumentValues(accommodation_contract="AC-001", party="forged", get_doc_before_save=lambda: None)
		self.frappe.db.get_value.return_value = "SUP-2"
		module.Flat.validate(flat)
		self.assertEqual(flat.party, "SUP-2")

	def test_factory_rejects_other_sources_and_checks_create_permission(self):
		with self.assertRaises(ValueError):
			module.make_flat("Flat Contract Request", "FCR-001")
		flat = DocumentValues(check_permission=Mock(side_effect=PermissionError))
		self.frappe.new_doc.return_value = flat
		with self.assertRaises(PermissionError):
			module.make_flat("Flat Contract", "FC-001")
		flat.check_permission.assert_called_once_with("create")

	def test_second_flat_is_blocked_for_either_source_including_cancelled_flats(self):
		for doctype, field in module.SOURCE_FIELDS.items():
			with self.subTest(doctype=doctype):
				self.source.doctype = doctype
				self.frappe.db.get_value.return_value = "Existing Flat"
				with self.assertRaises(ValueError):
					module.Flat.before_insert(DocumentValues(**{field: self.source.name}, flags=Flags(creation_action=module._CREATE_FLAT_TOKEN)))
				self.frappe.get_doc.assert_called_with(doctype, self.source.name, for_update=True)
				# No docstatus filter: a cancelled Flat still consumes this source.
				self.frappe.db.get_value.assert_called_with(
					"Flat", {field: self.source.name}, "name", for_update=True
				)

	def test_repeated_create_opens_existing_flat_with_read_permission(self):
		for doctype in module.SOURCE_FIELDS:
			with self.subTest(doctype=doctype):
				self.source.doctype = doctype
				flat = DocumentValues(check_permission=Mock())
				existing = DocumentValues(name="Existing Flat", flat_title="Existing Title", docstatus=1, check_permission=Mock())
				self.frappe.new_doc.return_value = flat
				self.frappe.get_doc.side_effect = [self.source, existing]
				self.frappe.db.get_value.return_value = existing.name
				self.assertIs(module.make_flat(doctype, self.source.name), existing)
				existing.check_permission.assert_called_once_with("read")
				flat.check_permission.assert_not_called()

	def test_flat_title_is_required_and_source_name_overrides_draft_title(self):
		self.source.flat_title = "   "
		with self.assertRaises(ValueError):
			module._set_source_values(DocumentValues(), self.source)
		self.source.flat_title = "  Chosen Flat Name  "
		flat = DocumentValues(flat_title="Changed draft name")
		module._set_source_values(flat, self.source)
		self.assertEqual(flat.flat_title, "Chosen Flat Name")

	def test_direct_insert_is_blocked_even_with_source_links_and_forged_flags(self):
		for token in (None, True, "creation_action"):
			with self.subTest(token=token), self.assertRaises(ValueError):
				module.Flat.before_insert(DocumentValues(
					flat_contract="FC-001", flags=Flags(creation_action=token)
				))

	def test_action_inserts_submits_and_writes_result_back(self):
		flat = DocumentValues(docstatus=0, check_permission=Mock())
		def insert():
			module.Flat.before_insert(flat)
			flat.name = flat.flat_title
		def submit():
			flat.docstatus = 1
		flat.insert = Mock(side_effect=insert)
		flat.submit = Mock(side_effect=submit)
		self.frappe.new_doc.return_value = flat
		self.assertIs(module.make_flat("Flat Contract", self.source.name), flat)
		flat.insert.assert_called_once_with()
		flat.submit.assert_called_once_with()
		self.assertEqual(flat.docstatus, 1)
		self.assertIsNone(flat.flags.get("creation_action"))
		self.source.db_set.assert_called_once_with({
			"created_flat": "Building A - Flat 12", "flat_title": "Building A - Flat 12"
		})
		self.assertEqual([call.args for call in flat.check_permission.call_args_list], [("create",), ("submit",)])

	def test_submit_permission_denial_does_not_insert(self):
		flat = DocumentValues(check_permission=Mock(side_effect=[None, PermissionError]), insert=Mock())
		self.frappe.new_doc.return_value = flat
		with self.assertRaises(PermissionError):
			module.make_flat("Flat Contract", self.source.name)
		flat.insert.assert_not_called()
		self.source.db_set.assert_not_called()

	def test_submit_failure_does_not_write_source_link(self):
		flat = DocumentValues(docstatus=0, check_permission=Mock(), insert=Mock(), submit=Mock(side_effect=ValueError))
		self.frappe.new_doc.return_value = flat
		with self.assertRaises(ValueError):
			module.make_flat("Flat Contract", self.source.name)
		self.source.db_set.assert_not_called()
		self.assertIsNone(flat.flags.get("creation_action"))

	def test_accommodation_action_creates_submitted_flat_and_backlink(self):
		self.source.doctype = "Add Flat to Contract"
		self.source.accommodation_contract = "AC-001"
		contract = DocumentValues(name="AC-001", party="SUP-2", docstatus=1, check_permission=Mock())
		self.frappe.get_doc.side_effect = [self.source, self.source, contract]
		flat = DocumentValues(docstatus=0, check_permission=Mock())
		def insert():
			module.Flat.before_insert(flat)
			flat.name = flat.flat_title
		flat.insert = Mock(side_effect=insert)
		flat.submit = Mock(side_effect=lambda: flat.set("docstatus", 1))
		self.frappe.new_doc.return_value = flat
		module.make_flat(self.source.doctype, self.source.name)
		self.assertEqual(flat.docstatus, 1)
		self.assertEqual(flat.accommodation_contract, "AC-001")
		self.assertEqual(flat.rent_type, "Contract")
		self.assertEqual(flat.party, "SUP-2")
		self.source.db_set.assert_called_once_with({"created_flat": flat.name, "flat_title": flat.flat_title})

	def test_source_write_permission_is_required(self):
		self.source.check_permission.side_effect = [None, PermissionError]
		flat = DocumentValues(insert=Mock())
		self.frappe.new_doc.return_value = flat
		with self.assertRaises(PermissionError):
			module.make_flat("Flat Contract", self.source.name)
		flat.insert.assert_not_called()


	def test_submission_creates_and_submits_for_both_sources(self):
		for doctype, field in module.SOURCE_FIELDS.items():
			with self.subTest(doctype=doctype):
				self.source.doctype = doctype
				flat = DocumentValues(insert=Mock(), submit=Mock(), name="FLAT-1", flat_title="Flat")
				self.frappe.new_doc.return_value = flat
				module.create_flat_on_submit(self.source)
				self.assertEqual(flat.get(field), self.source.name)
				flat.insert.assert_called_once_with(ignore_permissions=True)
				flat.submit.assert_called_once()
				self.assertNotIn("creation_action", flat.flags)

	def test_renewal_submission_does_not_create_another_flat(self):
		self.source.type = "Renew"
		module.create_flat_on_submit(self.source)
		self.frappe.new_doc.assert_not_called()


class TestUnlinkAndCancel(TestCase):
	def setUp(self):
		self.patcher = patch.object(module, "frappe")
		self.frappe = self.patcher.start()
		self.addCleanup(self.patcher.stop)
		self.frappe.throw.side_effect = ValueError
		self.frappe.get_roles.return_value = ["System Manager"]
		self.source = DocumentValues(doctype="Flat Contract", name="FC-1", docstatus=1,
			created_flat="FLAT-1", check_permission=Mock(), db_set=Mock(), cancel=Mock(),
			meta=SimpleNamespace(has_field=lambda field: True))
		self.row = DocumentValues(rent_contract_type="Flat Contract", rent_contract="FC-1", db_set=Mock())
		self.flat = DocumentValues(name="FLAT-1", docstatus=1, flat_contract="FC-1",
			rent_contracts=[self.row], db_set=Mock(), cancel=Mock())
		self.frappe.get_doc.side_effect = [self.source, self.flat]

	def test_role_required_before_document_access(self):
		self.frappe.get_roles.return_value = ["Legal Manager"]
		with self.assertRaises(ValueError):
			module.unlink_and_cancel("Flat Contract", "FC-1")
		self.frappe.get_doc.assert_not_called()

	def test_cancels_both_and_clears_both_links(self):
		result = module.unlink_and_cancel("Flat Contract", "FC-1")
		self.assertEqual(result, {"source": "FC-1", "flat": "FLAT-1"})
		self.source.db_set.assert_any_call("created_flat", None)
		self.flat.db_set.assert_called_once_with("flat_contract", None)
		self.row.db_set.assert_called_once_with({"rent_contract": None, "add_flat_to_contract": None})
		self.flat.cancel.assert_called_once()
		self.source.cancel.assert_called_once()
		self.frappe.db.commit.assert_not_called()

	def test_failure_at_either_cancel_rolls_back(self):
		for target in (self.flat, self.source):
			with self.subTest(target=target.name):
				self.frappe.get_doc.side_effect = [self.source, self.flat]
				target.cancel.side_effect = RuntimeError("linked document blocks cancellation")
				with self.assertRaises(RuntimeError):
					module.unlink_and_cancel("Flat Contract", "FC-1")
				self.frappe.db.rollback.assert_called_with(save_point="unlink_and_cancel_flat")
				target.cancel.side_effect = None

	def test_mismatched_link_changes_nothing(self):
		self.flat.flat_contract = "OTHER"
		with self.assertRaises(ValueError):
			module.unlink_and_cancel("Flat Contract", "FC-1")
		self.source.db_set.assert_not_called()
		self.flat.cancel.assert_not_called()

	def test_legacy_flat_without_source_backlink(self):
		self.source.created_flat = None
		self.frappe.db.get_value.return_value = self.flat.name
		module.unlink_and_cancel("Flat Contract", "FC-1")
		self.frappe.db.get_value.assert_called_once_with(
			"Flat", {"flat_contract": "FC-1"}, "name", for_update=True)
		self.flat.cancel.assert_called_once()

	def test_add_flat_to_contract_cancellation(self):
		self.source.doctype = "Add Flat to Contract"
		self.flat.flat_contract = None
		self.flat.add_flat_to_contract = self.source.name
		self.row.rent_contract = None
		self.row.add_flat_to_contract = self.source.name
		module.unlink_and_cancel("Add Flat to Contract", self.source.name)
		self.flat.db_set.assert_called_once_with("add_flat_to_contract", None)
		self.source.cancel.assert_called_once()

	def test_renewal_history_blocks_original_cancellation(self):
		self.flat.rent_contracts.append(DocumentValues(rent_contract_type="Flat Contract", rent_contract="FC-2"))
		with self.assertRaises(ValueError):
			module.unlink_and_cancel("Flat Contract", "FC-1")
		self.source.db_set.assert_not_called()


	def test_legacy_rent_table_link_can_cancel(self):
		self.flat.flat_contract = None
		module.unlink_and_cancel("Flat Contract", "FC-1", expected_flat="FLAT-1")
		self.flat.cancel.assert_called_once()

	def test_requested_flat_must_match_source_backlink(self):
		with self.assertRaises(ValueError):
			module.unlink_and_cancel("Flat Contract", "FC-1", expected_flat="OTHER")
		self.source.db_set.assert_not_called()

	def test_flat_endpoint_resolves_legacy_rent_table(self):
		self.flat.flat_contract = None
		self.flat.check_permission = Mock()
		self.frappe.get_doc.side_effect = [self.flat]
		with patch.object(module, "unlink_and_cancel") as cancel:
			module.unlink_and_cancel_flat("FLAT-1")
			cancel.assert_called_once_with("Flat Contract", "FC-1", expected_flat="FLAT-1")

	def test_flat_endpoint_requires_system_manager(self):
		self.frappe.get_roles.return_value = ["Legal User"]
		with self.assertRaises(ValueError):
			module.unlink_and_cancel_flat("FLAT-1")
		self.frappe.get_doc.assert_not_called()
