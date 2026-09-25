import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from administration import flat_request_layout as layout


class TestFlatRequestLayout(TestCase):
	def test_repairs_old_order_without_losing_custom_fields(self):
		old = ["workflow_state", "project", "custom_site_note", "document_approval", "employee"]
		order = layout.approval_field_order(old)
		self.assertEqual(order, ["request_details_tab", "workflow_state", "project",
			"custom_site_note", "employee", *layout.APPROVAL_FIELDS])
		self.assertEqual(layout.approval_field_order(order), order)

	def test_migration_repairs_visibility_after_customizations(self):
		module_name = "frappe.custom.doctype.property_setter.property_setter"
		setter = ModuleType(module_name)
		setter.make_property_setter = Mock()
		with patch.dict(sys.modules, {module_name: setter}), patch.object(layout, "frappe") as frappe:
			frappe.get_meta.return_value.fields = [SimpleNamespace(fieldname="project")]
			layout.ensure_approval_layout()
			self.assertEqual([call.args[2] for call in frappe.reload_doc.call_args_list],
				["flat_request_approval", "flat_request"])
			setter.make_property_setter.assert_any_call("Flat Request", "document_approval_tab", "hidden", 0, "Check")
			setter.make_property_setter.assert_any_call("Flat Request", "document_approval", "read_only", 1, "Check")
			setter.make_property_setter.assert_any_call("Flat Request", "document_approval", "permlevel", 0, "Int")
			frappe.clear_cache.assert_any_call(doctype="Flat Request")

	def test_shipped_layout_contains_visible_content_and_all_audit_columns(self):
		root = Path(__file__).parent / "administration"
		schema = json.loads((root / "doctype/flat_request/flat_request.json").read_text())
		custom = json.loads((root / "custom/flat_request.json").read_text())
		order = json.loads(next(row["value"] for row in custom["property_setters"] if row["property"] == "field_order"))
		for fields in (schema["field_order"], order):
			self.assertEqual(fields[-3:], list(layout.APPROVAL_FIELDS))
		child = json.loads((root / "doctype/flat_request_approval/flat_request_approval.json").read_text())
		visible = {row["fieldname"] for row in child["fields"] if row.get("in_list_view")}
		self.assertEqual(visible, {"status", "approved_by_role", "approved_by_user", "user_name", "action_date", "note"})
