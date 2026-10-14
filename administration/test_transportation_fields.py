import json
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch


ROOT = Path(__file__).parent / "administration" / "doctype"


def fields(slug):
	schema = json.loads((ROOT / slug / f"{slug}.json").read_text(encoding="utf-8"))
	return {field["fieldname"]: field for field in schema["fields"]}


class TestTransportationFields(TestCase):
	def test_migration_retains_site_options_and_only_updates_metadata(self):
		frappe = Mock()
		frappe.get_all.return_value = [
			SimpleNamespace(name="category-options", field_name="request_type", property="options",
				value="Private Vehicle\nTransportation\nSite Service\nLocal Category"),
			SimpleNamespace(name="category-label", field_name="request_type", property="label", value="Request Type"),
		]
		path = Path(__file__).parent / "patches" / "standardize_transportation_fields.py"
		spec = importlib.util.spec_from_file_location("transportation_patch_under_test", path)
		module = importlib.util.module_from_spec(spec)
		with patch.dict("sys.modules", {"frappe": frappe}):
			spec.loader.exec_module(module)
		module.DOCTYPES = ("vehicle_request",)
		module.execute()
		module.execute()
		for call in frappe.db.set_value.call_args_list:
			self.assertEqual(call.args[0], "Property Setter")
			if call.args[1] == "category-options":
				self.assertEqual(call.args[3].splitlines(),
					["Private Vehicle", "Transportation", "Site Service", "Local Category", "Transportation and Service"])
		frappe.reload_doc.assert_called_with("administration", "doctype", "vehicle_request", force=True)
		frappe.clear_cache.assert_called_with(doctype="Vehicle Request")

	def test_request_category_options_survive_the_full_contract_flow(self):
		for slug in ("vehicle_request", "private_vehicle_contract_request", "private_vehicle_contract", "vehicles"):
			with self.subTest(doctype=slug):
				category = fields(slug)["request_type"]
				self.assertEqual(category["label"], "Request Type")
				self.assertEqual(category["options"].splitlines(),
					["Private Vehicle", "Transportation", "Site Service", "Transportation and Service"])

	def test_price_and_contract_terms_keep_separate_catalog_and_category_fetches(self):
		price = fields("transportation_price_list")
		terms = fields("vehicle_route_table")
		for name in ("vehicle_type", "service_type"):
			self.assertEqual(price[name]["label"], "Request Type" if name == "service_type" else "Vehicle Type")
			self.assertEqual(terms[name]["label"], "Request Type" if name == "service_type" else "Vehicle Type")
			self.assertEqual(terms[name]["fetch_from"], f"route.{name}")
		self.assertEqual(terms["vehicle_type"]["options"], "Vehicle Type")
		self.assertEqual(price["service_type"]["options"], terms["service_type"]["options"])
		self.assertIn("Transportation and Service", terms["service_type"]["options"].splitlines())

	def test_passengers_have_matching_tables_throughout_the_flow(self):
		for slug in ("vehicle_request", "private_vehicle_contract_request", "private_vehicle_contract", "vehicles"):
			with self.subTest(doctype=slug):
				table = fields(slug)["employees"]
				self.assertEqual(table["options"], "Rent Emp")
				self.assertIn("'Transportation', 'Transportation and Service'", table["depends_on"])
				self.assertEqual(table["fieldtype"], "Table")
