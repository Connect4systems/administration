"""Employee provisioning regression tests runnable without a Frappe bench."""

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch


class EmployeeAccessTests(unittest.TestCase):
    def setUp(self):
        self.frappe = Mock()
        self.frappe.whitelist.return_value = lambda fn: fn
        spec = importlib.util.spec_from_file_location(
            "employee_access_test",
            Path(__file__).parents[1] / "administration/employee_user_permissions.py",
        )
        self.access = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"frappe": self.frappe}):
            spec.loader.exec_module(self.access)

    def employee(self, **values):
        doc = Mock()
        values = {"user_id": "employee@example.com", "custom_project": "HQ",
            "name": "EMP-001", "create_user_permission": 1, "company": "CSCEC", **values}
        doc.get.side_effect = values.get
        for field, value in values.items():
            setattr(doc, field, value)
        return doc

    def test_linked_user_gets_both_roles_project_and_default_employee(self):
        user = self.frappe.get_doc.return_value
        user.get.return_value = [Mock(role="Other Role")]
        with patch.object(self.access, "ensure_permission") as ensure:
            self.access.provision_employee_user_access(self.employee())
        user.add_roles.assert_called_once_with("Employee", "Employee Self Service")
        self.assertTrue(user.flags.ignore_permissions)
        self.assertEqual(ensure.call_args_list[0].args, ("employee@example.com", "Project", "HQ"))
        self.assertEqual(ensure.call_args_list[1].args, ("employee@example.com", "Employee", "EMP-001"))
        self.assertEqual(ensure.call_args_list[1].kwargs, {"is_default": True})
        self.assertEqual(ensure.call_args_list[2].args, ("employee@example.com", "Company", "CSCEC"))
        self.assertEqual(ensure.call_args_list[2].kwargs, {"is_default": True})

    def test_unchecked_employee_permission_still_grants_project(self):
        user = self.frappe.get_doc.return_value
        user.get.return_value = [Mock(role="Employee"), Mock(role="Employee Self Service")]
        with patch.object(self.access, "ensure_permission") as ensure:
            self.access.provision_employee_user_access(self.employee(create_user_permission=0))
        user.add_roles.assert_not_called()
        ensure.assert_called_once_with("employee@example.com", "Project", "HQ")

    def test_missing_project_does_not_create_empty_permission(self):
        self.frappe.get_doc.return_value.get.return_value = []
        with patch.object(self.access, "ensure_permission") as ensure:
            self.access.provision_employee_user_access(self.employee(custom_project=None))
        self.assertEqual([call.args[1] for call in ensure.call_args_list], ["Employee", "Company"])

    def test_missing_company_does_not_create_empty_permission(self):
        self.frappe.get_doc.return_value.get.return_value = []
        with patch.object(self.access, "ensure_permission") as ensure:
            self.access.provision_employee_user_access(self.employee(company=None))
        self.assertEqual([call.args[1] for call in ensure.call_args_list], ["Project", "Employee"])

    def test_unlinked_and_builtin_users_are_skipped(self):
        for user in (None, "Administrator", "Guest"):
            self.access.provision_employee_user_access(self.employee(user_id=user))
        self.frappe.get_doc.assert_not_called()

    def test_default_permission_sync_does_not_reapply_roles_or_project_access(self):
        with patch.object(self.access, "ensure_permission") as ensure:
            self.access.ensure_employee_default_permissions(self.employee())
        self.assertEqual([call.args[1] for call in ensure.call_args_list], ["Employee", "Company"])
        self.assertTrue(all(call.kwargs == {"is_default": True} for call in ensure.call_args_list))
        self.frappe.get_doc.assert_not_called()

    def test_default_permission_sync_respects_opt_out_and_missing_user(self):
        with patch.object(self.access, "ensure_permission") as ensure:
            for values in ({"create_user_permission": 0}, {"user_id": None},
                           {"user_id": "Administrator"}, {"user_id": "Guest"}):
                self.access.ensure_employee_default_permissions(self.employee(**values))
        ensure.assert_not_called()

    def test_permission_creation_applies_to_all_doctypes(self):
        self.frappe.db.exists.return_value = None
        self.access.ensure_permission("user", "Project", "HQ")
        self.frappe.get_doc.assert_called_once_with({"doctype": "User Permission",
            "user": "user", "allow": "Project", "for_value": "HQ",
            "apply_to_all_doctypes": 1, "is_default": 0})
        self.frappe.get_doc.return_value.insert.assert_called_once_with(ignore_permissions=True)

    def test_existing_employee_permission_promoted_and_other_default_cleared(self):
        self.frappe.db.exists.return_value = "own"
        self.frappe.get_all.return_value = ["other"]
        own, other = Mock(is_default=0), Mock(is_default=1)
        self.frappe.get_doc.side_effect = lambda dt, name: own if name == "own" else other
        self.access.ensure_permission("user", "Employee", "EMP-001", is_default=True)
        self.assertEqual(other.is_default, 0)
        other.save.assert_called_once_with(ignore_permissions=True)
        self.assertEqual(own.is_default, 1)
        own.save.assert_called_once_with(ignore_permissions=True)
        own.insert.assert_not_called()

    def test_existing_permissions_are_idempotent(self):
        self.frappe.db.exists.return_value = "own"
        self.frappe.get_all.return_value = ["own"]
        permission = self.frappe.get_doc.return_value
        permission.is_default = 1
        self.access.ensure_permission("user", "Employee", "EMP-001", is_default=True)
        self.access.ensure_permission("user", "Project", "HQ")
        permission.insert.assert_not_called()
        permission.save.assert_not_called()

    def test_created_user_has_only_administration_enabled(self):
        user = Mock(module_profile="Old Profile")
        self.frappe.get_all.return_value = ["Accounts", "Administration", "HR", "Core"]
        self.access.configure_employee_modules(user)
        self.assertIsNone(user.module_profile)
        user.set.assert_called_once_with("block_modules", [
            {"module": "Accounts"}, {"module": "HR"}, {"module": "Core"},
        ])
        user.save.assert_called_once_with(ignore_permissions=True)

    def test_creation_retains_standard_flow_and_configures_new_user(self):
        standard = types.ModuleType("erpnext.setup.doctype.employee.employee")
        standard.create_user = Mock(return_value="new@example.com")
        with patch.dict(sys.modules, {standard.__name__: standard}), patch.object(
            self.access, "configure_employee_modules"
        ) as configure, patch.object(self.access, "provision_employee_user_access") as provision:
            result = self.access.create_user("EMP-001", email="new@example.com")
        standard.create_user.assert_called_once_with("EMP-001", user=None, email="new@example.com")
        self.frappe.get_doc.assert_any_call("User", "new@example.com")
        self.frappe.get_doc.assert_any_call("Employee", "EMP-001")
        provision.assert_called_once_with(self.frappe.get_doc.return_value)
        configure.assert_called_once_with(self.frappe.get_doc.return_value)
        self.assertEqual(result, "new@example.com")

    def test_failed_creation_does_not_configure_modules(self):
        standard = types.ModuleType("erpnext.setup.doctype.employee.employee")
        standard.create_user = Mock(side_effect=PermissionError)
        with patch.dict(sys.modules, {standard.__name__: standard}), patch.object(
            self.access, "configure_employee_modules"
        ) as configure:
            with self.assertRaises(PermissionError):
                self.access.create_user("EMP-001")
        configure.assert_not_called()

    def test_checked_roles_are_added_only_to_new_user(self):
        standard = types.ModuleType("erpnext.setup.doctype.employee.employee")
        standard.create_user = Mock(return_value="new@example.com")
        for flags, expected in [
            ({"leave_approver": "1"}, ("Leave Approver",)),
            ({"expense_approver": 1}, ("Expense Approver",)),
            ({"line_manager": True}, ("Line Manager",)),
            ({"leave_approver": 1, "expense_approver": 1, "line_manager": 1},
                ("Leave Approver", "Expense Approver", "Line Manager")),
            ({"leave_approver": "0", "expense_approver": "0", "line_manager": "0"}, ()),
        ]:
            with self.subTest(flags=flags):
                self.frappe.reset_mock()
                with patch.dict(sys.modules, {standard.__name__: standard}), patch.object(
                    self.access, "provision_employee_user_access"
                ), patch.object(self.access, "configure_employee_modules"):
                    self.access.create_user("EMP-001", **flags)
                user = self.frappe.get_doc.return_value
                if expected:
                    self.frappe.only_for.assert_called_once_with(["User Manager", "System Manager"])
                    user.add_roles.assert_called_once_with(*expected)
                else:
                    self.frappe.only_for.assert_not_called()
                    user.add_roles.assert_not_called()

    def test_unauthorized_role_selection_fails_before_creation(self):
        standard = types.ModuleType("erpnext.setup.doctype.employee.employee")
        standard.create_user = Mock()
        self.frappe.only_for.side_effect = PermissionError
        with patch.dict(sys.modules, {standard.__name__: standard}):
            with self.assertRaises(PermissionError):
                self.access.create_user("EMP-001", line_manager=1)
        standard.create_user.assert_not_called()
        self.frappe.get_doc.assert_not_called()

    def test_user_manager_permissions_setup_is_idempotent(self):
        permissions = types.ModuleType("frappe.permissions")
        permissions.add_permission = Mock()
        permissions.setup_custom_perms = Mock()
        permissions.update_permission_property = Mock()
        self.frappe.db.exists.return_value = True
        with patch.dict(sys.modules, {permissions.__name__: permissions}):
            self.access.setup_user_manager_permissions()
        permissions.add_permission.assert_not_called()
        permissions.update_permission_property.assert_any_call("Employee", "User Manager", 0, "write", 1)
        permissions.update_permission_property.assert_any_call("User", "User Manager", 0, "create", 1)
        self.assertFalse(any(call.args[3] in ("delete", "submit", "cancel")
            for call in permissions.update_permission_property.call_args_list))
        self.frappe.clear_cache.assert_called_once_with()

    def test_user_manager_setup_creates_missing_roles_and_permissions(self):
        permissions = types.ModuleType("frappe.permissions")
        permissions.add_permission = Mock()
        permissions.setup_custom_perms = Mock()
        permissions.update_permission_property = Mock()
        self.frappe.db.exists.return_value = None
        with patch.dict(sys.modules, {permissions.__name__: permissions}):
            self.access.setup_user_manager_permissions()
        self.assertEqual(permissions.add_permission.call_count, 4)
        self.frappe.get_doc.assert_any_call({"doctype": "Role", "role_name": "Line Manager", "desk_access": 1})

    def test_employee_save_has_no_access_provisioning_hook(self):
        hooks = Path(__file__).parents[1] / "administration/hooks.py"
        namespace = {}
        exec(compile(hooks.read_text(), str(hooks), "exec"), namespace)
        employee_hooks = namespace["doc_events"]["Employee"]
        self.assertEqual(employee_hooks["on_update"], ["administration.user_employee.sync_employee_to_user"])
        self.assertEqual(namespace["override_doctype_class"]["Employee"],
            "administration.employee_access.AdministrationEmployee")

    def test_employee_controller_preserves_removed_roles_and_permissions(self):
        standard = types.ModuleType("erpnext.setup.doctype.employee.employee")
        standard.Employee = type("Employee", (), {})
        spec = importlib.util.spec_from_file_location("employee_controller_test",
            Path(__file__).parents[1] / "administration/employee_access.py")
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"frappe": self.frappe, standard.__name__: standard}):
            spec.loader.exec_module(module)
        employee = module.AdministrationEmployee()
        employee.user_id = "user@example.com"
        employee.employee_name = "Test Employee"
        employee.date_of_birth = "1990-01-01"
        employee.gender = "Male"
        employee.image = None
        employee.get_doc_before_save = lambda: {"user_id": employee.user_id}
        user = self.frappe.get_doc.return_value
        user.roles = []
        user.module_profile = "Manager Profile"
        user.block_modules = [{"module": "Administration"}]
        employee.update_user()
        with patch.dict(sys.modules, {"administration.employee_user_permissions": self.access}), patch.object(
            self.access, "ensure_employee_default_permissions"
        ) as defaults:
            employee.update_user_permissions()
        defaults.assert_called_once_with(employee)
        self.assertEqual(user.roles, [])
        self.assertEqual(user.module_profile, "Manager Profile")
        self.assertEqual(user.block_modules, [{"module": "Administration"}])
        user.append_roles.assert_not_called()
        user.add_roles.assert_not_called()
        user.save.assert_called_once_with()
        self.assertEqual(user.birth_date, "1990-01-01")
        self.frappe.db.assert_not_called()
        self.frappe.get_all.assert_not_called()
        self.frappe.get_doc.assert_called_once_with("User", "user@example.com")

        # A new link grants the baseline roles; ordinary later saves do not.
        employee.get_doc_before_save = lambda: {"user_id": None}
        user.get.return_value = []
        employee.update_user()
        self.assertEqual([call.args for call in user.append_roles.call_args_list],
            [("Employee",), ("Employee Self Service",)])
        user.append_roles.reset_mock()
        employee.get_doc_before_save = lambda: {"user_id": employee.user_id}
        employee.update_user()
        user.append_roles.assert_not_called()

        # Reassignment grants only the missing baseline role to the newly linked user.
        employee.get_doc_before_save = lambda: {"user_id": "old@example.com"}
        user.get.return_value = [Mock(role="Employee")]
        employee.update_user()
        user.append_roles.assert_called_once_with("Employee Self Service")


if __name__ == "__main__":
    unittest.main()
