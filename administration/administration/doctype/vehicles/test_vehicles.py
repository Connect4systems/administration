from unittest import TestCase
from unittest.mock import Mock, patch

from administration.administration.doctype.vehicles import vehicles


class TestVehiclePassengers(TestCase):
	def test_private_vehicle_requires_employee(self):
		for request_type in ("Private Vehicle", "Transportation", "Site Service"):
			with self.subTest(request_type=request_type), patch.object(vehicles, "frappe") as frappe:
				frappe.throw.side_effect = ValueError
				doc = Mock(request_type=request_type, employee=None)
				if request_type == "Private Vehicle":
					with self.assertRaises(ValueError):
						vehicles.Vehicles.validate_employee(doc)
				else:
					vehicles.Vehicles.validate_employee(doc)
					frappe.throw.assert_not_called()

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
					doc = Mock()
					doc.has_value_changed.return_value = changed
					if changed and role != "Fleet Manager":
						with self.assertRaises(PermissionError):
							vehicles.Vehicles.before_update_after_submit(doc)
					else:
						vehicles.Vehicles.before_update_after_submit(doc)
						frappe.throw.assert_not_called()
					doc.validate_employee.assert_called_once_with()
					doc.has_value_changed.assert_called_once_with("employee")


class TestVehiclesNaming(TestCase):
	def test_name_uses_type_and_project_abbreviation(self):
		for vehicle_type, prefix in (
			("Private Vehicle", "PV"), ("Transportation", "TV"), ("Site Service", "SV")
		):
			with self.subTest(vehicle_type=vehicle_type):
				doc = Mock(vehical_type=vehicle_type, project="PROJ-001")
				with patch.object(vehicles.frappe, "db") as db, patch.object(vehicles, "getseries") as series:
					db.get_value.return_value = " ABC "
					series.return_value = "001"
					vehicles.Vehicles.autoname(doc)
					self.assertEqual(doc.name, f"{prefix}-ABC-001")
					series.assert_called_once_with(f"{prefix}-ABC-", 3)
					db.get_value.assert_called_once_with("Project", "PROJ-001", "custom_abbreviation")

	def test_missing_naming_inputs_do_not_allocate_a_number(self):
		for vehicle_type, project, abbreviation in (
			("Unknown", "PROJ-001", "ABC"),
			("Private Vehicle", "", "ABC"),
			("Transportation", "PROJ-001", None),
			("Site Service", "PROJ-001", "  "),
		):
			with self.subTest(vehicle_type=vehicle_type, project=project, abbreviation=abbreviation):
				doc = Mock(vehical_type=vehicle_type, project=project)
				with patch.object(vehicles.frappe, "db") as db, patch.object(vehicles, "getseries") as series:
					db.get_value.return_value = abbreviation
					with patch.object(vehicles.frappe, "throw", side_effect=ValueError), self.assertRaises(ValueError):
						vehicles.Vehicles.autoname(doc)
					series.assert_not_called()
