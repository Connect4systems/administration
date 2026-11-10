import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch


class MyProfileWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.frappe = Mock()
        spec = importlib.util.spec_from_file_location(
            "my_profile_workspace_test",
            Path(__file__).parents[1] / "administration/my_profile_workspace.py",
        )
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"frappe": self.frappe}):
            spec.loader.exec_module(self.module)

    def test_existing_roles_preserved_and_missing_employee_role_added(self):
        workspace = self.frappe.get_doc.return_value
        workspace.roles = [Mock(role="Employee"), Mock(role="Leave Approver")]
        self.module.setup()
        workspace.append.assert_called_once_with("roles", {"role": "Employee Self Service"})
        workspace.save.assert_called_once_with(ignore_permissions=True)
        self.frappe.db.set_value.assert_called_once_with(
            "Workspace", "My Profile",
            {"module": "", "public": 1, "is_hidden": 0, "for_user": "", "parent_page": ""},
            update_modified=False,
        )
        self.frappe.clear_cache.assert_called_once()

    def test_existing_employee_roles_are_not_duplicated(self):
        workspace = self.frappe.get_doc.return_value
        workspace.roles = [Mock(role="Employee"), Mock(role="Employee Self Service")]
        self.module.setup()
        workspace.append.assert_not_called()
        workspace.save.assert_not_called()
        self.frappe.db.set_value.assert_called_once()

    def test_missing_workspace_is_not_created_empty(self):
        self.frappe.db.exists.return_value = False
        self.module.setup()
        self.frappe.get_doc.assert_not_called()
        self.frappe.db.set_value.assert_not_called()
