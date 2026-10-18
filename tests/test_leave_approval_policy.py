"""Policy regression tests runnable without a Frappe bench."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class Doc(dict):
    def __getattr__(self, key):
        return self.get(key)

    __setattr__ = dict.__setitem__

    def set(self, field, value):
        self[field] = value

    def get_doc_before_save(self):
        return self.get("_old")


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.roles = ["Leave Approver"]
        self.users = {"EMP": "employee", "FIRST": "first", "SECOND": "second"}
        self.frappe = types.ModuleType("frappe")
        self.frappe._ = lambda text: text
        self.frappe.PermissionError = PermissionError
        self.frappe.session = Doc(user="first")
        self.frappe.get_roles = lambda user=None: self.roles
        self.frappe.throw = lambda message, exc=ValueError: self.raise_error(message, exc)
        self.frappe.db = Doc(get_value=self.get_value, escape=lambda value: "'" + value + "'")
        spec = importlib.util.spec_from_file_location("leave_policy_test", Path(__file__).parents[1] / "administration/leave_approval.py")
        self.policy = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"frappe": self.frappe}):
            spec.loader.exec_module(self.policy)

    def raise_error(self, message, exc):
        raise exc(message)

    def get_value(self, dt, name, field):
        return self.users.get(name) if dt == "Employee" else 1

    def document(self, state="Pending Approval", level=None):
        return Doc(name="LEAVE", owner="employee", employee="EMP", workflow_state=state,
            custom_leave_approval_level=level or self.policy.ONE, leave_approver="first",
            custom_second_leave_approver="second", docstatus=0, status="Open")

    def transition(self, old, state, docstatus=0):
        new = Doc(old)
        new.update(_old=old, workflow_state=state, docstatus=docstatus)
        self.policy.validate_leave(new)
        return new

    def test_both_full_routes(self):
        for level in (self.policy.ONE, self.policy.TWO):
            old = self.document(level=level)
            target = "Pending HR Approval" if level == self.policy.ONE else "Pending Management Approval"
            new = self.transition(old, target)
            self.assertEqual(new.docstatus, 0)
            if level == self.policy.TWO:
                self.frappe.session.user = "second"
                new = self.transition(new, "Pending HR Approval")
            self.frappe.session.user = "hr"
            self.roles = ["HR Leave Approver"]
            final = self.transition(new, "Approved", 1)
            self.assertEqual(final.status, "Approved")
            self.roles = ["Leave Approver"]
            self.frappe.session.user = "first"

    def test_rejection_all_stages_and_terminal(self):
        for state, user, role in [("Pending Approval", "first", "Leave Approver"),
                ("Pending Management Approval", "second", "Leave Approver"),
                ("Pending HR Approval", "hr", "HR Leave Approver")]:
            self.frappe.session.user = user
            self.roles = [role]
            rejected = self.transition(self.document(state, self.policy.TWO), "Rejected")
            self.assertEqual((rejected.status, rejected.docstatus), ("Rejected", 0))
            with self.assertRaises(PermissionError):
                self.transition(rejected, "Pending Approval")

    def test_wrong_assignee_and_skipping_hr_denied(self):
        old = self.document()
        self.frappe.session.user = "other"
        with self.assertRaises(PermissionError):
            self.transition(old, "Pending HR Approval")
        self.frappe.session.user = "first"
        with self.assertRaises(PermissionError):
            self.transition(old, "Approved", 1)

    def test_direct_submission_and_snapshot_tampering_denied(self):
        old = self.document()
        with self.assertRaises(ValueError):
            self.transition(old, "Pending Approval", 1)
        new = Doc(old, _old=old, leave_approver="other")
        with self.assertRaises(ValueError):
            self.policy.validate_leave(new)

    def test_employee_mapping_and_invalid_configuration(self):
        employee = Doc(custom_first_approval="FIRST", custom_second_approval="SECOND",
            custom_leave_approval_level=self.policy.TWO)
        self.policy.validate_employee(employee)
        self.assertEqual(employee.leave_approver, "first")
        self.assertEqual(employee.custom_second_leave_approver, "second")
        employee.custom_second_approval = "FIRST"
        with self.assertRaises(ValueError):
            self.policy.validate_employee(employee)
        employee.custom_leave_approval_level = self.policy.ONE
        self.policy.validate_employee(employee)
        self.assertIsNone(employee.custom_second_leave_approver)
        employee.custom_first_approval = "MISSING"
        with self.assertRaises(ValueError):
            self.policy.validate_employee(employee)

    def test_new_application_copies_employee_configuration(self):
        employee = Doc(custom_first_approval="FIRST", custom_leave_approval_level=self.policy.ONE)
        self.frappe.get_doc = lambda dt, name: employee
        doc = self.document("Open")
        doc.leave_approver = "forged"
        self.policy.validate_leave(doc)
        self.assertEqual(doc.leave_approver, "first")
        self.assertIsNone(doc.custom_second_leave_approver)

    def test_no_approval_clears_managers_and_routes_to_hr(self):
        employee = Doc(custom_leave_approval_level=self.policy.NONE,
            custom_first_approval="FIRST", custom_second_approval="SECOND",
            leave_approver="first", custom_second_leave_approver="second")
        self.frappe.get_doc = lambda dt, name: employee
        doc = self.document("Open")
        self.policy.validate_leave(doc)
        for field in ("custom_first_approval", "custom_second_approval", "leave_approver", "custom_second_leave_approver"):
            self.assertIsNone(employee.get(field))
        self.assertEqual(doc.custom_leave_approval_level, self.policy.NONE)
        self.assertIsNone(doc.leave_approver)
        self.assertIsNone(doc.custom_second_leave_approver)
        self.frappe.session.user = "employee"
        for target, status in [("Pending Approval", 0), ("Pending Management Approval", 0), ("Approved", 1)]:
            with self.assertRaises(PermissionError):
                self.transition(doc, target, status)
        pending = self.transition(doc, "Pending HR Approval")
        with self.assertRaises(PermissionError):
            self.transition(pending, "Approved", 1)
        self.frappe.session.user = "hr"
        self.roles = ["HR Leave Approver"]
        self.assertEqual(self.transition(pending, "Approved", 1).status, "Approved")
        self.assertEqual(self.transition(pending, "Rejected").status, "Rejected")

    def test_direct_hr_submission_requires_applicant_and_no_approval_level(self):
        self.frappe.session.user = "other"
        with self.assertRaises(PermissionError):
            self.transition(self.document("Open", self.policy.NONE), "Pending HR Approval")
        self.frappe.session.user = "employee"
        for level in (self.policy.ONE, self.policy.TWO):
            with self.assertRaises(PermissionError):
                self.transition(self.document("Open", level), "Pending HR Approval")
            self.assertEqual(self.transition(self.document("Open", level), "Pending Approval").workflow_state,
                "Pending Approval")

    def test_assignment_reconciliation_and_terminal_cleanup(self):
        calls = []
        module = types.ModuleType("frappe.desk.form.assign_to")
        # Match Frappe v15: the public add accepts only args; _add supports
        # trusted server-side assignment with ignore_permissions.
        module.add = lambda args=None: calls.append(("public_add", args))
        def add_assignment(args=None, *, ignore_permissions=False):
            self.assertTrue(ignore_permissions)
            calls.append(("add", args))
        module._add = add_assignment
        module.set_status = lambda *args, **kw: calls.append(("close", kw["todo"]))
        self.frappe.get_all = lambda *args, **kw: [Doc(name="old", allocated_to="first")]
        self.frappe.has_permission = lambda *args, **kw: False
        def share_document(doctype, name, user, *, read=1, write=0, flags=None):
            self.assertEqual(flags, {"ignore_share_permission": True})
            calls.append(("share", user))
        self.frappe.share = Doc(add_docshare=share_document)
        doc = self.document("Pending Management Approval", self.policy.TWO)
        doc.doctype = "Leave Application"
        with patch.dict(sys.modules, {"frappe.desk.form.assign_to": module}):
            self.policy.sync_assignments(doc)
            self.assertEqual(calls[0], ("close", "old"))
            self.assertEqual(calls[-1][1]["assign_to"], ["second"])
            calls.clear()
            doc.workflow_state = "Rejected"
            self.policy.sync_assignments(doc)
            self.assertEqual(calls, [("close", "old")])
            calls.clear()
            doc.workflow_state = "Pending Approval"
            self.policy.sync_assignments(doc)
            self.assertFalse(any(call[0] == "add" for call in calls))

    def test_pending_scope(self):
        self.assertIn("leave_approver='first'", self.policy.pending_conditions("first"))
        self.assertNotIn("workflow_state='Pending HR Approval'", self.policy.pending_conditions("first"))
        self.roles = []
        self.assertIn("1=0", self.policy.pending_conditions("employee"))


if __name__ == "__main__":
    unittest.main()
