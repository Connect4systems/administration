import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch


ROOT = Path(__file__).parent / "administration" / "doctype"


class TestSubmittedServiceQuantity(TestCase):
	def load_controller(self, slug):
		frappe = Mock()
		frappe._ = lambda message: message
		frappe.whitelist = lambda: lambda function: function
		frappe.throw.side_effect = ValueError
		workflow = Mock()
		spec = importlib.util.spec_from_file_location(slug + "_under_test", ROOT / slug / f"{slug}.py")
		module = importlib.util.module_from_spec(spec)
		with patch.dict("sys.modules", {
			"frappe": frappe, "frappe.model.document": SimpleNamespace(Document=object),
			"frappe.model.mapper": Mock(), "frappe.model.naming": Mock(), "frappe.utils": Mock(),
			"administration.flat_request_workflow": workflow,
		}):
			spec.loader.exec_module(module)
		return module, workflow

	def row(self, name, qty):
		row = Mock()
		row.name = name
		row.get.side_effect = {"qty": qty}.get
		return row

	def test_request_quantity_edit_keeps_approval_validation(self):
		module, workflow = self.load_controller("service_vehicle_contract_request")
		doc = Mock()
		doc.get_doc_before_save.return_value = {"contract_details": [self.row("ROW-1", 1)]}
		doc.get.return_value = [self.row("ROW-1", 3)]
		module.ServiceVehicleContractRequest.before_update_after_submit(doc)
		workflow.validate_approval_history.assert_called_once_with(doc)
		module.frappe.throw.assert_not_called()

	def test_request_rows_cannot_be_added_removed_or_reordered(self):
		module, _ = self.load_controller("service_vehicle_contract_request")
		for names in (["ROW-1", "ROW-2", "ROW-3"], ["ROW-1"], ["ROW-2", "ROW-1"]):
			with self.subTest(names=names):
				doc = Mock()
				doc.get_doc_before_save.return_value = {"contract_details": [self.row("ROW-1", 1), self.row("ROW-2", 1)]}
				doc.get.return_value = [self.row(name, 1) for name in names]
				with self.assertRaises(ValueError):
					module.ServiceVehicleContractRequest.before_update_after_submit(doc)

	def test_submitted_contract_quantity_remains_locked(self):
		module, _ = self.load_controller("service_vehicle_contract")
		doc = Mock()
		doc.get_doc_before_save.return_value = {"contract_details": [self.row("ROW-1", 1)]}
		doc.get.return_value = [self.row("ROW-1", 2)]
		with self.assertRaises(ValueError):
			module.ServiceVehicleContract.before_update_after_submit(doc)

	def test_schema_allows_quantity_updates(self):
		for slug, fieldname in (("vehicle_route_table", "qty"), ("service_vehicle_contract_request", "contract_details")):
			schema = json.loads((ROOT / slug / f"{slug}.json").read_text(encoding="utf-8"))
			field = next(field for field in schema["fields"] if field["fieldname"] == fieldname)
			self.assertEqual(field["allow_on_submit"], 1)
