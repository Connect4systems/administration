"""Set initial access only when creating a User from Employee."""

import frappe


@frappe.whitelist()
def create_user(employee, user=None, email=None):
    from erpnext.setup.doctype.employee.employee import create_user as standard_create_user

    # Retain the standard Employee write check, creation, and linking behavior.
    user_name = standard_create_user(employee, user=user, email=email)
    provision_employee_user_access(frappe.get_doc("Employee", employee))
    configure_employee_modules(frappe.get_doc("User", user_name))
    return user_name


def configure_employee_modules(user_doc):
    user_doc.module_profile = None
    # Frappe stores unchecked modules as Block Module child rows.
    user_doc.set("block_modules", [
        {"module": module}
        for module in frappe.get_all("Module Def", pluck="name", order_by="name")
        if module != "Administration"
    ])
    user_doc.save(ignore_permissions=True)


def provision_employee_user_access(doc):
    user = doc.get("user_id")
    if not user or user in ("Administrator", "Guest"):
        return

    user_doc = frappe.get_doc("User", user)
    existing_roles = {row.role for row in user_doc.get("roles")}
    missing = [role for role in ("Employee", "Employee Self Service") if role not in existing_roles]
    if missing:
        user_doc.flags.ignore_permissions = True
        user_doc.add_roles(*missing)

    if doc.get("custom_project"):
        ensure_permission(user, "Project", doc.custom_project)
    if doc.get("create_user_permission"):
        ensure_permission(user, "Employee", doc.name, is_default=True)


def ensure_permission(user, allow, value, is_default=False):
    filters = {"user": user, "allow": allow, "for_value": value, "apply_to_all_doctypes": 1}
    name = frappe.db.exists("User Permission", filters)
    permission = frappe.get_doc("User Permission", name) if name else frappe.get_doc({
        "doctype": "User Permission", **filters, "is_default": int(is_default),
    })
    if is_default:
        # Frappe rejects overlapping defaults; retain other permissions but clear their default.
        for other in frappe.get_all("User Permission", filters={
            "user": user, "allow": allow, "is_default": 1,
        }, pluck="name"):
            if other != name:
                previous = frappe.get_doc("User Permission", other)
                previous.is_default = 0
                previous.save(ignore_permissions=True)
    if not name:
        permission.insert(ignore_permissions=True)
    elif is_default and not permission.is_default:
        permission.is_default = 1
        permission.save(ignore_permissions=True)
