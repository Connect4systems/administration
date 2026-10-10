import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch


class TestFlatAccommodation(TestCase):
	def setUp(self):
		self.frappe = Mock()
		self.frappe._ = lambda message: message
		self.frappe.throw.side_effect = ValueError
		spec = importlib.util.spec_from_file_location("flat_accommodation_under_test", Path(__file__).with_name("flat_accommodation.py"))
		self.module = importlib.util.module_from_spec(spec)
		with patch.dict("sys.modules", {"frappe": self.frappe}):
			spec.loader.exec_module(self.module)
		self.values = {"request_type": "Private", "employee": "EMP-1", "project": "PROJ-1"}
		self.flat = Mock(employee="EMP-1", project="PROJ-1")
		self.flat.get.side_effect = self.values.get
		self.flat.get_doc_before_save.return_value = None

	def test_private_employee_must_be_active_in_project_and_private(self):
		for status, project, accommodation, allowed in (
			("Active", "PROJ-1", "Private", True),
			("Left", "PROJ-1", "Private", False),
			("Active", "PROJ-2", "Private", False),
			("Active", "PROJ-1", "Share", False),
		):
			with self.subTest(status=status, project=project, accommodation=accommodation):
				self.frappe.db.get_value.return_value = SimpleNamespace(status=status, custom_project=project, custom_accommidation=accommodation)
				if allowed:
					self.module.validate_flat_accommodation(self.flat)
				else:
					with self.assertRaises(ValueError):
						self.module.validate_flat_accommodation(self.flat)

	def test_share_clears_direct_employee(self):
		self.values["request_type"] = "Share"
		self.module.validate_flat_accommodation(self.flat)
		self.assertIsNone(self.flat.employee)
		self.frappe.db.get_value.assert_not_called()

	def test_private_employee_is_optional(self):
		self.values["employee"] = None
		self.module.validate_flat_accommodation(self.flat)
		self.frappe.db.get_value.assert_not_called()

	def test_rooms_and_beds_reject_private_flats(self):
		for request_type in (None, "Share", "Private"):
			with self.subTest(request_type=request_type):
				self.frappe.db.get_value.return_value = request_type
				if request_type == "Private":
					with self.assertRaises(ValueError):
						self.module.ensure_shared_flat("FLAT-1")
				else:
					self.module.ensure_shared_flat("FLAT-1")

	def test_switch_to_private_requires_removing_existing_rooms_and_beds(self):
		self.flat.get_doc_before_save.return_value = {"request_type": "Share"}
		for room, bed in ((True, False), (False, True)):
			with self.subTest(room=room, bed=bed):
				self.frappe.db.exists.side_effect = lambda doctype, filters: room if doctype == "Room" else bed
				with self.assertRaises(ValueError):
					self.module.validate_flat_accommodation(self.flat)
