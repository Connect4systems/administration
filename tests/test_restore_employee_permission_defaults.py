"""Regression checks for migration of opted-in Employee defaults."""

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch


class EmployeeDefaultRepairTests(unittest.TestCase):
    def test_repairs_unambiguous_users_and_skips_missing_builtin_and_duplicate_links(self):
        frappe = Mock()
        access = types.ModuleType("administration.employee_user_permissions")
        access.ensure_employee_default_permissions = Mock()
        employee = {"name": "EMP-1", "user_id": "user@example.com", "company": "CSCEC",
                    "create_user_permission": 1}
        frappe.get_all.return_value = [employee,
            {"name": "EMP-2", "user_id": None},
            {"name": "EMP-3", "user_id": "Administrator"},
            {"name": "EMP-4", "user_id": "Guest"},
            {"name": "EMP-5", "user_id": "duplicate@example.com"},
            {"name": "EMP-6", "user_id": "duplicate@example.com"}]
        path = Path(__file__).parents[1] / "administration/patches/restore_employee_permission_defaults.py"
        spec = importlib.util.spec_from_file_location("employee_default_repair_test", path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"frappe": frappe, access.__name__: access}):
            spec.loader.exec_module(module)
            module.execute()
        access.ensure_employee_default_permissions.assert_called_once_with(employee)
        self.assertEqual(frappe.get_all.call_args.kwargs["filters"], {"create_user_permission": 1})
        frappe.logger.return_value.warning.assert_called_once()
