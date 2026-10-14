from unittest import TestCase
from unittest.mock import Mock, patch

from administration.administration.doctype.vehicles import vehicles


class TestVehiclePassengers(TestCase):
	def test_duplicate_assignments_are_blocked_in_both_selectors(self):
		for employee, rows in (("EMP-001", []), (None, [Mock(code="EMP-001")])):
			with self.subTest(employee=employee), patch.object(vehicles, "frappe") as frappe, patch.object(
				vehicles, "find_employee_vehicles", return_value=["PV-ABC-001", "TV-ABC-002"]
			) as lookup:
				frappe.throw.side_effect = ValueError
				doc = Mock(employee=employee)
				doc.name = "TV-ABC-003"
				doc.get.return_value = rows
				with self.assertRaises(ValueError):
					vehicles.Vehicles.validate_employee_assignments(doc)
				lookup.assert_called_once_with("EMP-001", "TV-ABC-003")
				message = frappe.throw.call_args.args[0]
				self.assertIn("PV-ABC-001", message)
				self.assertIn("TV-ABC-002", message)

	def test_employee_without_other_vehicle_is_allowed(self):
		with patch.object(vehicles, "frappe") as frappe, patch.object(
			vehicles, "find_employee_vehicles", return_value=[]
		):
			doc = Mock(employee="EMP-001", name="PV-ABC-001")
			doc.get.return_value = []
			vehicles.Vehicles.validate_employee_assignments(doc)
			frappe.throw.assert_not_called()

	def test_employee_assignments_follow_request_type(self):
		for request_type, employee, clear_table in (
			("Private Vehicle", "EMP-001", True),
			("Private Vehicle", None, True),
			("Transportation", None, False),
			("Transportation and Service", None, False),
			("Site Service", None, True),
		):
			with self.subTest(request_type=request_type, employee=employee):
				doc = Mock(request_type=request_type, employee=employee or "EMP-OLD")
				if request_type == "Private Vehicle":
					doc.employee = employee
				vehicles.Vehicles.validate_employee(doc)
				self.assertEqual(doc.employee, employee)
				if clear_table:
					doc.set.assert_called_once_with("employees", [])
				else:
					doc.set.assert_not_called()

	def test_assigned_private_vehicle_employee_is_valid(self):
		with patch.object(vehicles, "frappe") as frappe:
			vehicles.Vehicles.validate_employee(Mock(request_type="Private Vehicle", employee="EMP-001"))
			frappe.throw.assert_not_called()

	def test_submitted_employee_changes_require_fleet_manager(self):
		for role in ("Fleet Manager", "System Manager", "Administration Manager", "Legal User"):
			for changed in (True, False):
				with self.subTest(role=role, changed=changed), patch.object(vehicles, "frappe") as frappe:
					frappe.get_roles.return_value = [role]
					frappe.PermissionError = PermissionError
					frappe.throw.side_effect = PermissionError
					doc = Mock(request_type="Private Vehicle")
					doc.get.return_value = []
					doc.get_doc_before_save.return_value = {"employees": []}
					doc.has_value_changed.return_value = changed
					if changed and role != "Fleet Manager":
						with self.assertRaises(PermissionError):
							vehicles.Vehicles.before_update_after_submit(doc)
					else:
						vehicles.Vehicles.before_update_after_submit(doc)
						frappe.throw.assert_not_called()
					doc.validate_employee.assert_called_once_with()
					doc.has_value_changed.assert_called_once_with("employee")

	def test_submitted_table_changes_are_allowed_for_all_writers(self):
		row = {"name": "ROW-1", "idx": 1, "code": "EMP-001", "employee": "Employee One"}
		for old, new in (
			([], [row]),
			([row], []),
			([row], [{**row, "code": "EMP-002"}]),
			([row], [{**row, "department": "Operations"}]),
			([row], [row]),
		):
			for role in ("Fleet Manager", "System Manager", "Administration Manager", "Legal User"):
				with self.subTest(role=role, old=old, new=new), patch.object(vehicles, "frappe") as frappe:
					frappe.get_roles.return_value = [role]
					frappe.PermissionError = PermissionError
					frappe.throw.side_effect = PermissionError
					doc = Mock(request_type="Private Vehicle")
					doc.get.return_value = new
					doc.get_doc_before_save.return_value = {"employees": old}
					doc.has_value_changed.return_value = False
					vehicles.Vehicles.before_update_after_submit(doc)
					frappe.throw.assert_not_called()
					doc.validate_employee_assignments.assert_called_once_with()


class TestVehiclesNaming(TestCase):
	def test_name_uses_type_year_and_three_digit_sequence(self):
		for vehicle_type, prefix in (
			("Private Vehicle", "PV"), ("Transportation", "TV"),
			("Site Service", "SV"), ("Transportation and Service", "TSV"),
		):
			with self.subTest(vehicle_type=vehicle_type):
				doc = Mock(request_type=vehicle_type, project="PROJ-001")
				with patch.object(vehicles.frappe, "db") as db, patch.object(vehicles, "make_autoname") as naming:
					naming.return_value = f"{prefix}-26-001"
					vehicles.Vehicles.autoname(doc)
					self.assertEqual(doc.name, f"{prefix}-26-001")
					self.assertEqual(doc.naming_series, f"{prefix}-.YY.-.###")
					naming.assert_called_once_with(f"{prefix}-.YY.-.###", doc=doc)
					db.get_value.assert_not_called()

	def test_legacy_category_uses_the_same_year_series(self):
		doc = Mock(request_type=None, project="PROJ-001")
		doc.get.return_value = "Transportation and Service"
		with patch.object(vehicles, "make_autoname", return_value="TSV-26-001") as naming:
			vehicles.Vehicles.autoname(doc)
			naming.assert_called_once_with("TSV-.YY.-.###", doc=doc)

	def test_missing_naming_inputs_do_not_allocate_a_number(self):
		for vehicle_type, project in (("Unknown", "PROJ-001"), ("Private Vehicle", "")):
			with self.subTest(vehicle_type=vehicle_type, project=project):
				doc = Mock(request_type=vehicle_type, project=project)
				doc.get.return_value = None
				with patch.object(vehicles, "make_autoname") as naming:
					with patch.object(vehicles.frappe, "throw", side_effect=ValueError), self.assertRaises(ValueError):
						vehicles.Vehicles.autoname(doc)
					naming.assert_not_called()
