"""Grant baseline roles on linking, then preserve administrator-managed access."""

import frappe
from erpnext.setup.doctype.employee.employee import Employee


class AdministrationEmployee(Employee):
    def update_user_permissions(self):
        from administration.employee_user_permissions import ensure_employee_default_permissions

        ensure_employee_default_permissions(self)

    def update_user(self):
        # Preserve profile synchronization and grant baseline roles only on a new link.
        user = frappe.get_doc("User", self.user_id)
        user.flags.ignore_permissions = True
        previous = self.get_doc_before_save()
        if self.user_id not in ("Administrator", "Guest") and (
            not previous or previous.get("user_id") != self.user_id
        ):
            existing_roles = {row.role for row in user.get("roles")}
            for role in ("Employee", "Employee Self Service"):
                if role not in existing_roles:
                    user.append_roles(role)
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
