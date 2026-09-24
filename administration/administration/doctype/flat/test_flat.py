# Copyright (c) 2026, Connect 4 Systems and contributors
# For license information, please see license.txt

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from administration.administration.doctype.flat import flat as module


class DocumentValues(SimpleNamespace):
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
		self.source = DocumentValues(
			doctype="Flat Contract Request", name="FCR-001", docstatus=1,
			check_permission=Mock(), project="PROJ-1", flat_owner="SUP-1",
			flat_owner_name="Owner Name", no_of_rooms=3.0, no_of_beds=0,
			monthly_rent=1200, deposit=0, payment_cycle="Yearly",
			flat_contents=[{"item_name": "Bed", "qty": 0, "name": "old-row"}],
		)
		self.frappe.get_doc.return_value = self.source

	def test_creation_requires_exactly_one_source(self):
		for values in ({}, {"flat_contract_request": "FCR-1", "add_flat_to_contract": "AFTC-1"}):
			with self.subTest(values=values), self.assertRaises(ValueError):
				module.Flat.before_insert(DocumentValues(**values))

	def test_source_must_be_submitted_and_readable(self):
		flat = DocumentValues(flat_contract_request="FCR-001")
		for status in (0, 2):
			self.source.docstatus = status
			with self.assertRaises(ValueError):
				module._get_source(flat)
		self.source.docstatus = 1
		self.source.check_permission.side_effect = PermissionError
		with self.assertRaises(PermissionError):
			module._get_source(flat)

	def test_request_maps_contract_party_and_contents(self):
		flat = DocumentValues(flat_contract_request="FCR-001")
		module.Flat.before_insert(flat)
		self.assertEqual(flat.rent_contract, "FCR-001")
		self.assertEqual(flat.rent_type, "Direct Rent")
		self.assertEqual(flat.rent_contract_type, "Flat Contract Request")
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
		module.Flat.before_insert(flat)
		self.assertEqual(flat.accommodation_contract, "AC-001")
		self.assertEqual(flat.rent_type, "Contract")
		self.assertEqual(flat.party, "SUP-2")
		self.assertEqual(flat.owner_name, "Free text owner")
		self.assertIsNone(flat.rent_contract)
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
		previous = DocumentValues(flat_contract_request="FCR-001")
		flat = DocumentValues(flat_contract_request="FCR-002", get_doc_before_save=lambda: previous)
		with self.assertRaises(ValueError):
			module.Flat.validate(flat)

	def test_party_is_refetched_on_save(self):
		flat = DocumentValues(accommodation_contract="AC-001", party="forged", get_doc_before_save=lambda: None)
		self.frappe.db.get_value.return_value = "SUP-2"
		module.Flat.validate(flat)
		self.assertEqual(flat.party, "SUP-2")

	def test_factory_rejects_other_sources_and_checks_create_permission(self):
		with self.assertRaises(ValueError):
			module.make_flat("Flat Contract", "FC-001")
		flat = DocumentValues(check_permission=Mock(side_effect=PermissionError))
		self.frappe.new_doc.return_value = flat
		with self.assertRaises(PermissionError):
			module.make_flat("Flat Contract Request", "FCR-001")
		flat.check_permission.assert_called_once_with("create")
