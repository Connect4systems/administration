"""Exercise request-local permission expansion without a running bench."""

from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch


class EmployeeSelectionAccessTests(unittest.TestCase):
    def setUp(self):
        self.frappe = Mock()
        self.frappe.whitelist.return_value = lambda function: function
        self.frappe.local = types.SimpleNamespace(form_dict={}, cache={}, request=types.SimpleNamespace(path="/"))
        self.frappe.session.user = "account@example.com"
        self.frappe.get_roles.return_value = ["Accounts User"]
        self.frappe.get_meta.return_value.istable = False
        self.frappe.get_all.return_value = ["EMP-001", "EMP-002"]
        self.frappe._dict.side_effect = lambda **kwargs: kwargs
        self.frappe.cache.make_key.return_value = b"site|user_permissions"
        self.original = {"Employee": [{"doc": "EMP-001", "is_default": 1}],
                         "Company": [{"doc": "Allowed Company"}],
                         "Project": [{"doc": "Allowed Project"}]}
        self.permission_api = Mock()
        self.silent_read = Mock(return_value=False)
        self.permission_api.get_user_permissions.return_value = self.original
        spec = importlib.util.spec_from_file_location(
            "employee_selection_access_test",
            Path(__file__).parents[1] / "administration/employee_selection_access.py",
        )
        self.module = importlib.util.module_from_spec(spec)
        self.patches = patch.dict(sys.modules, {
            "frappe": self.frappe,
            "frappe.core.doctype.user_permission.user_permission": self.permission_api,
            "frappe.client": types.SimpleNamespace(get=Mock(return_value={"standard": True})),
            "frappe.permissions": types.SimpleNamespace(has_permission=self.silent_read),
        })
        self.patches.start()
        self.addCleanup(self.patches.stop)
        spec.loader.exec_module(self.module)

    def run_request(self, command, **kwargs):
        self.frappe.local.form_dict = {"cmd": command, **kwargs}
        self.module.allow_employee_selection()
        return self.frappe.local.cache.get(b"site|user_permissions", {}).get("account@example.com")

    def test_all_document_employee_selectors_receive_active_employees(self):
        before = deepcopy(self.original)
        result = self.run_request("frappe.desk.search.search_link", doctype="Employee",
                                  reference_doctype="Expense Claim", filters={"company": "Allowed Company"})
        self.assertEqual([row["doc"] for row in result["Employee"]], ["EMP-001", "EMP-002"])
        self.assertEqual(self.frappe.local.form_dict["filters"],
                         {"company": "Allowed Company", "status": "Active"})
        self.assertEqual(result["Company"], before["Company"])
        self.assertEqual(result["Project"], before["Project"])
        self.assertEqual(self.original, before)
        self.frappe.cache.hset.assert_not_called()

    def test_balance_lookup_expands_employee_access(self):
        result = self.run_request("erpnext.accounts.utils.get_balance_on", party_type="Employee", party="EMP-002")
        self.assertIn("EMP-002", [row["doc"] for row in result["Employee"]])

    def test_document_saves_and_loads_support_other_employees(self):
        for command in ("frappe.desk.form.save.savedocs", "frappe.client.save"):
            result = self.run_request(command, doc={"doctype": "Journal Entry"})
            self.assertIn("EMP-002", [row["doc"] for row in result["Employee"]])

    def test_employee_master_and_access_configuration_are_never_expanded(self):
        for doctype in ("Employee", "User", "User Permission", "Custom DocPerm"):
            self.assertIsNone(self.run_request("frappe.desk.form.load.getdoc", doctype=doctype))
            self.assertIsNone(self.run_request("frappe.desk.form.save.savedocs", doc={"doctype": doctype}))
        self.frappe.get_all.assert_not_called()

    def test_direct_employee_reads_and_lists_keep_original_permissions(self):
        for command in ("frappe.client.get", "frappe.client.get_value", "frappe.desk.reportview.get"):
            self.assertIsNone(self.run_request(command, doctype="Employee"))
        self.frappe.get_all.assert_not_called()

    def test_other_roles_do_not_receive_expanded_access(self):
        self.frappe.get_roles.return_value = ["Employee"]
        self.assertIsNone(self.run_request("frappe.desk.search.search_link", doctype="Employee"))
        self.frappe.get_all.assert_not_called()

    def test_missing_document_context_does_not_expand_access(self):
        self.assertIsNone(self.run_request("frappe.desk.form.save.savedocs"))
        self.frappe.get_all.assert_not_called()

    def test_non_employee_search_is_unchanged(self):
        self.assertIsNone(self.run_request("frappe.desk.search.search_link", doctype="Supplier"))
        self.frappe.get_all.assert_not_called()

    def test_direct_child_record_updates_keep_parent_restrictions(self):
        self.frappe.get_meta.return_value.istable = True
        self.assertIsNone(self.run_request("frappe.client.save", doc={
            "doctype": "Employee Education", "parenttype": "Employee", "parent": "EMP-002",
        }))
        self.frappe.get_all.assert_not_called()

    def test_browser_balance_rpc_has_no_cmd_before_dispatch(self):
        self.frappe.local.request.path = "/api/method/erpnext.accounts.utils.get_balance_on"
        self.frappe.local.form_dict = {"party_type": "Employee", "party": "EMP-002"}
        self.module.allow_employee_selection()
        cached = self.frappe.local.cache.get(b"site|user_permissions", {}).get("account@example.com")
        self.assertIsNotNone(cached)
        self.assertIn("EMP-002", [row["doc"] for row in cached["Employee"]])

    def test_api_path_overrides_a_conflicting_payload_command(self):
        self.frappe.local.request.path = "/api/method/frappe.client.get"
        self.assertIsNone(self.run_request("erpnext.accounts.utils.get_balance_on", doctype="Employee"))
        self.frappe.get_all.assert_not_called()

    def test_versioned_rpc_search_has_no_cmd_before_dispatch(self):
        self.frappe.local.request.path = "/api/v1/method/frappe.desk.search.search_link"
        self.frappe.local.form_dict = {"doctype": "Employee"}
        self.module.allow_employee_selection()
        self.assertEqual(self.frappe.local.form_dict.get("filters"), {"status": "Active"})

    def employee_document(self, can_read=False, status="Active"):
        values = {"name": "EMP-002", "employee_name": "Other Employee", "company": "Allowed Company",
                  "status": status, "bank_ac_no": "private", "salary": "private"}
        doc = self.frappe.get_doc.return_value
        doc.get.side_effect = values.get
        doc.has_permission.return_value = can_read
        self.silent_read.return_value = can_read
        return doc

    def test_restricted_employee_get_returns_only_selection_fields(self):
        doc = self.employee_document()
        self.frappe.local.cache[b"site|user_permissions"] = {"account@example.com": self.original}
        def check_scope(permission):
            self.assertEqual(permission, "select")
            scoped = self.frappe.local.cache[b"site|user_permissions"]["account@example.com"]
            self.assertNotIn("Employee", scoped)
            self.assertEqual(scoped["Company"], self.original["Company"])
        doc.check_permission.side_effect = check_scope
        result = self.module.get_document("Employee", name="EMP-002")
        self.assertEqual(set(result), {"doctype", "name", "employee_name", "company", "status"})
        self.assertIs(self.frappe.local.cache[b"site|user_permissions"]["account@example.com"], self.original)
        self.silent_read.assert_called_once_with("Employee", "read", doc=doc, raise_exception=False)
        doc.has_permission.assert_not_called()
        sys.modules["frappe.client"].get.assert_not_called()

    def test_identity_lookup_denied_by_other_permissions_restores_cache(self):
        doc = self.employee_document()
        doc.check_permission.side_effect = PermissionError("Company restriction")
        with self.assertRaises(PermissionError):
            self.module.get_document("Employee", name="EMP-002")
        self.assertNotIn("account@example.com", self.frappe.local.cache[b"site|user_permissions"])

    def test_permitted_reads_keep_standard_field_filtering(self):
        self.employee_document(can_read=True)
        self.assertEqual(self.module.get_document("Employee", name="EMP-002"), {"standard": True})

    def test_inactive_employee_reads_are_not_expanded(self):
        self.employee_document(status="Left")
        self.assertEqual(self.module.get_document("Employee", name="EMP-002"), {"standard": True})
        self.permission_api.get_user_permissions.assert_not_called()

    def test_other_roles_and_doctypes_keep_standard_document_reads(self):
        self.frappe.get_roles.return_value = ["Employee"]
        self.assertEqual(self.module.get_document("Employee", name="EMP-002"), {"standard": True})
        self.assertEqual(self.module.get_document("Journal Entry", name="JV-001"), {"standard": True})
        self.frappe.get_doc.assert_not_called()

    def test_each_requested_role_can_select_and_assign_other_employees(self):
        roles = ("Site Admin", "Fleet Manager", "Fleet admin",
                 "Admin supervisor (Accommodation)", "Admin supervisor (Travel)",
                 "Administration Manager", "Accounts User")
        for role in roles:
            with self.subTest(role=role):
                self.frappe.get_roles.return_value = [role]
                self.frappe.local.cache = {}
                selected = self.run_request("frappe.desk.search.search_link", doctype="Employee")
                self.assertIn("EMP-002", [row["doc"] for row in selected["Employee"]])
                for doctype in ("Bed", "Vehicles", "Travel Request"):
                    self.frappe.local.cache = {}
                    saved = self.run_request("frappe.desk.form.save.savedocs", doc={"doctype": doctype})
                    self.assertIn("EMP-002", [row["doc"] for row in saved["Employee"]])
                self.employee_document()
                self.assertEqual(self.module.get_document("Employee", name="EMP-002")["name"], "EMP-002")

    def test_operational_employee_fetches_preserve_other_restrictions(self):
        self.frappe.get_roles.return_value = ["Admin supervisor (Accommodation)"]
        result = self.run_request("frappe.client.get_value", doctype="Employee", filters="EMP-002",
                                  fieldname=["department", "employment_type"])
        self.assertIn("EMP-002", [row["doc"] for row in result["Employee"]])
        self.assertEqual(result["Company"], self.original["Company"])
        self.assertEqual(result["Project"], self.original["Project"])

    def test_link_validation_can_fetch_bed_operational_fields(self):
        self.frappe.get_roles.return_value = ["Fleet admin"]
        result = self.run_request("frappe.client.validate_link", doctype="Employee", docname="EMP-002",
                                  fields=["department", "status", "employment_type"])
        self.assertIn("EMP-002", [row["doc"] for row in result["Employee"]])

    def test_private_fields_and_filter_probes_are_never_expanded(self):
        for field in ("bank_ac_no", "salary", "*", "name as salary"):
            with self.subTest(field=field):
                self.assertIsNone(self.run_request("frappe.client.get_value", doctype="Employee",
                                                  filters="EMP-002", fieldname=[field]))
                self.assertIsNone(self.run_request("frappe.client.validate_link", doctype="Employee",
                                                  docname="EMP-002", fields=[field]))
        self.assertIsNone(self.run_request("frappe.client.get_value", doctype="Employee",
                                          filters={"salary": 1000}, fieldname="name"))

    def test_bed_release_and_vehicle_assignment_helpers_receive_same_access(self):
        for role, command in (
            ("Admin supervisor (Accommodation)", "administration.administration.doctype.bed.bed.employee_left"),
            ("Fleet Manager", "administration.administration.doctype.vehicles.vehicles.get_employee_vehicles"),
        ):
            self.frappe.local.cache = {}
            self.frappe.get_roles.return_value = [role]
            result = self.run_request(command, employee="EMP-002")
            self.assertIn("EMP-002", [row["doc"] for row in result["Employee"]])
