import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).parent


class TestVehicleCreation(unittest.TestCase):
	def setUp(self):
		self.frappe = Mock()
		self.frappe._ = lambda message: message
		self.frappe.whitelist = lambda: lambda function: function
		self.frappe.throw.side_effect = ValueError
		self.frappe.db.get_value.return_value = None
		spec = importlib.util.spec_from_file_location("vehicle_creation_under_test", ROOT / "vehicle_creation.py")
		self.module = importlib.util.module_from_spec(spec)
		with patch.dict("sys.modules", {"frappe": self.frappe}):
			spec.loader.exec_module(self.module)
		self.source = Mock(docstatus=1)
		self.source.name = "PVC-001"
		self.values = {
			"project": "Project A", "model": "Truck X", "half_day_allowance": 1,
			"allowance_time": "12:00:00", "request_type": "Private Vehicle",
			"contract_attachment": "/private/files/contract.pdf",
			"naming_series": "PVC-.YY.-.###", "document_approval": [],
		}
		self.source.get.side_effect = self.values.get
		self.source.meta.fields = [
			SimpleNamespace(fieldname=name, fieldtype="Data", no_copy=0)
			for name in self.values
		]
		self.vehicle = Mock()
		self.vehicle.name = "PV-A-001"
		self.frappe.get_doc.return_value = self.source
		self.frappe.new_doc.return_value = self.vehicle

	def test_creates_and_submits_with_business_values(self):
		self.assertEqual(self.module.create_vehicle("PVC-001"), "PV-A-001")
		self.frappe.get_doc.assert_called_once_with("Private Vehicle Contract", "PVC-001", for_update=True)
		self.source.check_permission.assert_called_once_with("read")
		self.assertEqual([call.args for call in self.vehicle.check_permission.call_args_list], [("create",), ("submit",)])
		copied = dict(call.args for call in self.vehicle.set.call_args_list)
		self.assertEqual(copied, {k: v for k, v in self.values.items() if k not in {"naming_series", "document_approval"}})
		self.assertEqual(self.vehicle.private_vehicle_contract, "PVC-001")
		self.assertEqual(self.vehicle.vehical_type, "Private Vehicle")
		self.vehicle.insert.assert_called_once_with()
		self.vehicle.submit.assert_called_once_with()

	def test_rejects_unsubmitted_or_cancelled_contract(self):
		for status in (0, 2):
			self.source.docstatus = status
			with self.assertRaises(ValueError):
				self.module.create_vehicle("PVC-001")
		self.frappe.new_doc.assert_not_called()

	def test_repeat_returns_existing_vehicle(self):
		self.frappe.db.get_value.return_value = "PV-A-001"
		self.assertEqual(self.module.create_vehicle("PVC-001"), "PV-A-001")
		self.frappe.new_doc.assert_not_called()

	def test_submit_permission_failure_prevents_insert(self):
		self.vehicle.check_permission.side_effect = [None, PermissionError()]
		with self.assertRaises(PermissionError):
			self.module.create_vehicle("PVC-001")
		self.vehicle.insert.assert_not_called()

	def test_employee_rows_copy_without_source_row_identity(self):
		field = SimpleNamespace(fieldname="employees", fieldtype="Table", options="Rent Emp", no_copy=0)
		self.source.meta.fields.append(field)
		row = Mock()
		row.meta.fields = [SimpleNamespace(fieldname="code", fieldtype="Link", no_copy=0)]
		row.get.return_value = "EMP-001"
		self.values["employees"] = [row]
		self.vehicle.meta.get_field.return_value = field
		self.module.create_vehicle("PVC-001")
		self.vehicle.append.assert_called_once_with("employees", {"code": "EMP-001"})

	def test_vehicle_schema_locks_every_data_field_except_project(self):
		base = ROOT / "administration/doctype"
		vehicle = json.loads((base / "vehicles/vehicles.json").read_text())
		contract = json.loads((base / "private_vehicle_contract/private_vehicle_contract.json").read_text())
		fields = {field["fieldname"]: field for field in vehicle["fields"]}
		self.assertEqual(len(fields), len(vehicle["fields"]))
		self.assertEqual(set(fields), set(vehicle["field_order"]))
		self.assertEqual(len(fields), len(vehicle["field_order"]))
		for field in fields.values():
			if field["fieldtype"] in self.module.LAYOUT_FIELDS:
				continue
			project = field["fieldname"] == "project"
			self.assertEqual(bool(field.get("read_only")), not project)
			self.assertEqual(bool(field.get("allow_on_submit")), project)
		for field in contract["fields"]:
			if field["fieldtype"] not in self.module.LAYOUT_FIELDS:
				self.assertIn(field["fieldname"], fields)


if __name__ == "__main__":
	unittest.main()
