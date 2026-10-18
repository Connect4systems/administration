"""Keep subsequent Employee saves from changing administrator-managed access."""

import frappe
from erpnext.setup.doctype.employee.employee import Employee


class AdministrationEmployee(Employee):
    def update_user_permissions(self):
        # Initial permissions are provisioned by the create_user wrapper only.
        return

    def update_user(self):
        # Preserve ERPNext's profile synchronization without its automatic role grant.
        user = frappe.get_doc("User", self.user_id)
        user.flags.ignore_permissions = True
        if self.employee_name and not (user.first_name and user.last_name):
            employee_name = self.employee_name.split(" ")
            if len(employee_name) >= 3:
                user.last_name = " ".join(employee_name[2:])
                user.middle_name = employee_name[1]
            elif len(employee_name) == 2:
                user.last_name = employee_name[1]
            user.first_name = employee_name[0]
        if self.date_of_birth:
            user.birth_date = self.date_of_birth
        if self.gender:
            user.gender = self.gender
        if self.image and not user.user_image:
            user.user_image = self.image
            try:
                frappe.get_doc({
                    "doctype": "File", "file_url": self.image,
                    "attached_to_doctype": "User", "attached_to_name": self.user_id,
                }).insert(ignore_if_duplicate=True)
            except frappe.DuplicateEntryError:
                pass
        user.save()
