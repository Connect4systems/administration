"""Migration regression: legacy drafts need no employee approval configuration."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch


class SetupTests(unittest.TestCase):
    def test_legacy_draft_migrates_without_loading_employee(self):
        frappe = types.ModuleType("frappe")
        frappe.get_all = Mock(return_value=[types.SimpleNamespace(
            name="TRIP-OLD", docstatus=0, workflow_state=None)])
        frappe.db = types.SimpleNamespace(set_value=Mock(), exists=Mock(return_value=True))
        frappe.clear_cache = Mock()
        frappe.get_doc = Mock(side_effect=AssertionError("Migration must not validate Employee"))
        custom = types.ModuleType("frappe.custom.doctype.custom_field.custom_field")
        custom.create_custom_fields = Mock()
        setters = types.ModuleType("frappe.custom.doctype.property_setter.property_setter")
        setters.make_property_setter = Mock()
        permissions = types.ModuleType("frappe.permissions")
        permissions.add_permission = Mock()
        permissions.setup_custom_perms = Mock()
        permissions.update_permission_property = Mock()
        policy = types.ModuleType("administration.leave_approval")
        policy.permission_query = Mock()
        workflows = types.ModuleType("administration.leave_approval_setup")
        workflows.setup_approval_workflow = Mock()
        path = Path(__file__).parents[1] / "administration/business_trip_setup.py"
        spec = importlib.util.spec_from_file_location("trip_setup_test", path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"frappe": frappe,
                "frappe.custom.doctype.custom_field.custom_field": custom,
                "frappe.custom.doctype.property_setter.property_setter": setters,
                "frappe.permissions": permissions,
                "administration.leave_approval": policy,
                "administration.leave_approval_setup": workflows}):
            spec.loader.exec_module(module)
            module.setup()
        frappe.db.set_value.assert_called_once_with("Business Trip Request", "TRIP-OLD",
            {"workflow_state": "Open", "status": "Open"}, update_modified=False)
        workflows.setup_approval_workflow.assert_called_once_with("Business Trip Request")
        frappe.get_doc.assert_not_called()
