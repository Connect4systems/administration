from unittest import TestCase
from unittest.mock import Mock, patch

from administration.administration.doctype.vehicles import vehicles


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
