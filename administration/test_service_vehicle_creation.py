from datetime import date
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from administration.test_vehicle_creation import TestVehicleCreation as VehicleCreationFixture


class TestServiceVehicleCreation(TestCase):
	def setUp(self):
		VehicleCreationFixture.setUp(self)
		self.source.name = "SVC-001"
		self.frappe.get_all.return_value = []
		self.row_values = {
			"route": "PRICE-001", "qty": 2, "vehicle_type": "Bus",
			"service_type": "Transportation", "vehicle_route": "Route A",
			"location": "Site A", "passengers": 30, "overtime": 50,
			"extra_km": 10, "allowance": 1, "half_day_allowance": 1,
			"allowance_time": "12:00:00", "rent_cycle": "Monthly",
			"rent_amount": 5000, "check_in": "08:00:00", "check_out": "17:00:00",
		}
		self.row = Mock()
		self.row.name = "ROW-001"
		self.row.get.side_effect = self.row_values.get
		self.values.update({
			"provider_company": "Supplier A", "contract_details": [self.row],
			"contract_start_date": "2026-10-01", "contract_end_date": "2026-10-31",
		})
		self.source.contract_start_date = "2026-10-01"
		self.source.contract_end_date = "2026-10-31"
		self.utils_patch = patch.dict("sys.modules", {
			"frappe.utils": SimpleNamespace(getdate=lambda value: date.fromisoformat(value)),
		})
		self.utils_patch.start()
		self.addCleanup(self.utils_patch.stop)

	def test_service_copies_row_and_contract_and_submits(self):
		self.module.start_service("SVC-001", "ROW-001", "2026-10-03", 1, "REQ-001")
		self.frappe.get_doc.assert_called_once_with("Service Vehicle Contract", "SVC-001", for_update=True)
		self.source.check_permission.assert_called_once_with("read")
		self.assertEqual([call.args for call in self.vehicle.check_permission.call_args_list], [("create",), ("submit",)])
		values = self.vehicle.update.call_args.args[0]
		self.assertEqual(values["rent_start_date"], date(2026, 10, 3))
		self.assertEqual(values["project"], "Project A")
		self.assertEqual(values["vehicle_owner"], "Supplier A")
		self.assertEqual(values["service_contract_row"], "ROW-001")
		self.assertEqual(values["vehical_type"], "Transportation")
		copied = dict(call.args for call in self.vehicle.set.call_args_list)
		self.assertEqual(copied["extra_hour_fees"], 50)
		self.assertEqual(copied["no_of_employee"], 30)
		self.assertEqual(copied["midnight_allowance"], 1)
		self.assertEqual(len(copied), len(self.row_values) - 1)
		self.vehicle.insert.assert_called_once_with()
		self.vehicle.submit.assert_called_once_with()

	def test_service_rejects_invalid_selection_status_and_dates(self):
		for row, start, status in [
			("ROW-001", "2026-10-03", 0), ("ROW-001", "2026-10-03", 2),
			("OTHER-ROW", "2026-10-03", 1), (["ROW-001"], "2026-10-03", 1),
			("ROW-001", None, 1), ("ROW-001", "2026-09-30", 1),
			("ROW-001", "2026-11-01", 1),
		]:
			with self.subTest(row=row, start=start, status=status):
				self.source.docstatus = status
				with self.assertRaises(ValueError):
					self.module.start_service("SVC-001", row, start, 1, "REQ-001")
		self.frappe.new_doc.assert_not_called()

	def test_service_repeat_opens_existing_vehicle(self):
		self.frappe.get_all.return_value = [SimpleNamespace(name="TV-A-001", service_start_request="REQ-001", docstatus=1)]
		self.assertEqual(self.module.start_service("SVC-001", "ROW-001", "2026-10-03", 1, "REQ-001"), ["TV-A-001"])
		self.frappe.new_doc.assert_not_called()

	def test_service_create_permission_failure_prevents_insert(self):
		self.vehicle.check_permission.side_effect = PermissionError()
		with self.assertRaises(PermissionError):
			self.module.start_service("SVC-001", "ROW-001", "2026-10-03", 1, "REQ-001")
		self.vehicle.insert.assert_not_called()

	def test_quantity_creates_and_submits_multiple_vehicles(self):
		self.assertEqual(self.module.start_service("SVC-001", "ROW-001", "2026-10-03", 2, "REQ-001"), ["PV-A-001", "PV-A-001"])
		self.assertEqual(self.vehicle.insert.call_count, 2)
		self.assertEqual(self.vehicle.submit.call_count, 2)
		self.vehicle.set.assert_any_call("qty", 1)

	def test_invalid_or_excess_quantity_is_rejected(self):
		for qty in (0, -1, 1.5, "bad", 3, "NaN", "Infinity"):
			with self.subTest(qty=qty), self.assertRaises(ValueError):
				self.module.start_service("SVC-001", "ROW-001", "2026-10-03", qty, "REQ-001")
		self.vehicle.insert.assert_not_called()

	def test_existing_vehicles_reduce_available_quantity(self):
		self.frappe.get_all.return_value = [SimpleNamespace(name="TV-A-001", service_start_request="OTHER", docstatus=1)]
		with self.assertRaises(ValueError):
			self.module.start_service("SVC-001", "ROW-001", "2026-10-03", 2, "REQ-001")
		self.vehicle.insert.assert_not_called()

	def test_remaining_quantity_after_partial_and_complete_creation(self):
		self.row_values["qty"] = 3
		for created, remaining in ((0, 3), (1, 2), (3, 0), (4, 0)):
			with self.subTest(created=created):
				self.frappe.db.count.return_value = created
				self.assertEqual(self.module.get_service_remaining_qty("SVC-001", "ROW-001"), remaining)
		self.frappe.db.count.assert_called_with("Vehicles", {
			"service_vehicle_contract": "SVC-001", "service_contract_row": "ROW-001",
			"docstatus": ["!=", 2],
		})

	def test_remaining_quantity_checks_permission_and_row(self):
		with self.assertRaises(ValueError):
			self.module.get_service_remaining_qty("SVC-001", "OTHER")
		self.frappe.db.count.assert_not_called()
		self.source.check_permission.side_effect = PermissionError()
		with self.assertRaises(PermissionError):
			self.module.get_service_remaining_qty("SVC-001", "ROW-001")
		self.frappe.db.count.assert_not_called()

	def test_submit_permission_failure_prevents_insert(self):
		self.vehicle.check_permission.side_effect = [None, PermissionError()]
		with self.assertRaises(PermissionError):
			self.module.start_service("SVC-001", "ROW-001", "2026-10-03", 1, "REQ-001")
		self.vehicle.insert.assert_not_called()
