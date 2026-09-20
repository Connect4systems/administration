from unittest import TestCase
from unittest.mock import Mock, patch

from administration import user_employee


class TestUserEmployee(TestCase):
	def setUp(self):
		self.frappe_patch = patch.object(user_employee, "frappe")
		self.frappe = self.frappe_patch.start()
		self.addCleanup(self.frappe_patch.stop)
		self.employee = {
			"name": "EMP-001",
			"employee_name": "Test Employee",
			"department": "Operations",
			"branch": "Cairo",
			"custom_project": "PROJ-001",
			"designation": "Engineer",
		}

	def test_user_save_replaces_details_from_linked_employee(self):
		self.frappe.get_all.return_value = [self.employee]
		doc = Mock(name="User")
		user_employee.set_user_employee_details(doc)
		doc.update.assert_called_once_with({
			"custom_employee_id": "EMP-001",
			"custom_employee_name": "Test Employee",
			"custom_department": "Operations",
			"custom_branch_location": "Cairo",
			"custom_project": "PROJ-001",
			"custom_position": "Engineer",
		})

	def test_user_without_employee_has_empty_details(self):
		self.frappe.get_all.return_value = []
		doc = Mock()
		user_employee.set_user_employee_details(doc)
		doc.update.assert_called_once_with(dict.fromkeys(user_employee.EMPLOYEE_FIELDS))

	def test_reassignment_refreshes_old_and_new_user(self):
		doc = Mock()
		doc.get.return_value = "new@example.com"
		doc.get_doc_before_save.return_value = {"user_id": "old@example.com"}
		with patch.object(user_employee, "_employee_for_user", side_effect=lambda user: user), patch.object(
			user_employee, "_update_user"
		) as update:
			user_employee.sync_employee_to_user(doc)
			self.assertCountEqual(
				[call.args for call in update.call_args_list],
				[("old@example.com", "old@example.com"), ("new@example.com", "new@example.com")],
			)

	def test_changed_and_removed_values_are_written_and_notified(self):
		self.frappe.db.get_value.return_value = dict.fromkeys(user_employee.EMPLOYEE_FIELDS, "old")
		self.employee["custom_project"] = None
		user_employee._update_user("test@example.com", self.employee)
		self.frappe.db.set_value.assert_called_once_with(
			"User", "test@example.com", user_employee._values(self.employee)
		)
		self.frappe.get_doc.return_value.notify_update.assert_called_once()

	def test_unchanged_details_do_not_write(self):
		self.frappe.db.get_value.return_value = user_employee._values(self.employee)
		user_employee._update_user("test@example.com", self.employee)
		self.frappe.db.set_value.assert_not_called()

	def test_employee_deletion_clears_user_link(self):
		self.frappe.get_all.return_value = ["test@example.com"]
		doc = Mock()
		doc.name = "EMP-001"
		with patch.object(user_employee, "_update_user") as update:
			user_employee.clear_employee_from_user(doc)
			update.assert_called_once_with("test@example.com", None)

	def test_hooks_skip_until_custom_fields_exist(self):
		self.frappe.get_meta.return_value.has_field.return_value = False
		user_employee.set_user_employee_details(Mock())
		user_employee.sync_employee_to_user(Mock())
		self.frappe.get_all.assert_not_called()
