"""Permission boundaries for the accounting-only employee selector."""

import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch


class AccountingEmployeeSelectionTests(unittest.TestCase):
    def setUp(self):
        self.frappe = Mock()
        self.frappe.whitelist.return_value = lambda fn: fn
        self.frappe.PermissionError = PermissionError
        self.frappe.throw.side_effect = lambda message, error: (_ for _ in ()).throw(error(message))
        spec = importlib.util.spec_from_file_location(
            "accounting_selection_test",
            Path(__file__).parents[1] / "administration/accounting_employee_selection.py",
        )
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"frappe": self.frappe, "frappe.utils": Mock(cint=int)}):
            spec.loader.exec_module(self.module)

    def query(self, **overrides):
        args = dict(doctype="Employee", txt="Ali", searchfield="name", start=0,
                    page_len=20, filters={"accounting_context": "Journal Entry"})
        return self.module.employee_query(**(args | overrides))

    def test_lookup_exposes_only_active_employee_identifiers_and_names(self):
        self.query(page_len=999, start=-5)
        self.frappe.only_for.assert_called_once_with("Accounts User")
        self.frappe.has_permission.assert_called_once_with("Journal Entry", "read", throw=True)
        args = self.frappe.get_all.call_args.kwargs
        self.assertEqual(args["filters"], {"status": "Active"})
        self.assertEqual(args["fields"], ["name", "employee_name"])
        self.assertEqual(args["page_length"], 100)
        self.assertEqual(args["start"], 0)

    def test_other_roles_cannot_query(self):
        self.frappe.only_for.side_effect = PermissionError
        with self.assertRaises(PermissionError):
            self.query()
        self.frappe.get_all.assert_not_called()

    def test_unrelated_context_and_doctype_are_rejected(self):
        for args in ({"filters": {"accounting_context": "Employee"}}, {"doctype": "User"}):
            with self.assertRaises(PermissionError):
                self.query(**args)
        self.frappe.get_all.assert_not_called()

    def test_journal_permission_is_required(self):
        self.frappe.has_permission.side_effect = PermissionError
        with self.assertRaises(PermissionError):
            self.query()
        self.frappe.get_all.assert_not_called()

    def test_ledger_checks_report_access_before_lookup(self):
        report_api = Mock()
        with patch.dict(sys.modules, {"frappe.desk.query_report": report_api}):
            self.query(filters={"accounting_context": "General Ledger"})
        report_api.get_report_doc.assert_called_once_with("General Ledger")
        report_api.get_report_doc.return_value.check_permission.assert_called_once_with("read")
        self.frappe.has_permission.assert_called_once_with("GL Entry", "read", throw=True)

    def test_ledger_script_contains_selector_after_standard_definition(self):
        report_api = Mock()
        report_api.get_script.return_value = {"script": "standard_report_script;", "html_format": "test"}
        with patch.dict(sys.modules, {"frappe.desk.query_report": report_api}):
            result = self.module.get_report_script("General Ledger")
        self.assertTrue(result["script"].startswith("standard_report_script;\n"))
        self.assertIn("administration.accounting_employee_selection.employee_query", result["script"])
        self.assertEqual(result["html_format"], "test")

    def test_other_report_scripts_are_unchanged(self):
        report_api = Mock()
        report_api.get_script.return_value = {"script": "other_report_script;"}
        with patch.dict(sys.modules, {"frappe.desk.query_report": report_api}):
            self.assertEqual(self.module.get_report_script("Trial Balance"),
                             {"script": "other_report_script;"})
