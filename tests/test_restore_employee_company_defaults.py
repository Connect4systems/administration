"""The repair targets Company defaults only, including existing disabled users."""

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch


class CompanyDefaultRepairTests(unittest.TestCase):
    def setUp(self):
        self.frappe = Mock()
        self.access = types.ModuleType("administration.employee_user_permissions")
        self.access.ensure_permission = Mock()
        path = Path(__file__).parents[1] / "administration/patches/restore_employee_company_defaults.py"
        spec = importlib.util.spec_from_file_location("company_default_repair_test", path)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {
            "frappe": self.frappe,
            self.access.__name__: self.access,
        }):
            spec.loader.exec_module(self.module)

    def test_repairs_existing_users_without_reapplying_roles_modules_or_employee_permissions(self):
        self.frappe.get_all.return_value = [
            {"user_id": "existing@example.com", "company": "CSCEC"},
            {"user_id": "existing@example.com", "company": "CSCEC"},
            {"user_id": "disabled@example.com", "company": "Other Company"},
            {"user_id": None, "company": "CSCEC"},
            {"user_id": "missing-company@example.com", "company": ""},
            {"user_id": "Administrator", "company": "CSCEC"},
            {"user_id": "Guest", "company": "CSCEC"},
        ]
        self.module.execute()
        self.assertEqual(self.frappe.get_all.call_args.kwargs["filters"], {"create_user_permission": 1})
        self.assertEqual(self.access.ensure_permission.call_count, 2)
        self.access.ensure_permission.assert_any_call(
            "existing@example.com", "Company", "CSCEC", is_default=True)
        self.access.ensure_permission.assert_any_call(
            "disabled@example.com", "Company", "Other Company", is_default=True)
        self.frappe.get_doc.assert_not_called()

    def test_conflicting_employee_companies_are_logged_and_not_guessed(self):
        self.frappe.get_all.return_value = [
            {"user_id": "user@example.com", "company": "Company A"},
            {"user_id": "user@example.com", "company": "Company B"},
        ]
        self.module.execute()
        self.access.ensure_permission.assert_not_called()
        self.frappe.logger.return_value.warning.assert_called_once()

    def test_registered_as_one_time_patch(self):
        path = Path(__file__).parents[1] / "administration/patches.txt"
        self.assertIn("administration.patches.restore_employee_company_defaults", path.read_text().splitlines())
