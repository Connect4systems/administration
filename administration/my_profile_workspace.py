"""Make employee self service independent of the Administration module filter."""

import frappe


def setup():
    if not frappe.db.exists("Workspace", "My Profile"):
        return

    workspace = frappe.get_doc("Workspace", "My Profile")
    roles = {row.role for row in workspace.roles}
    changed = False
    for role in ("Employee", "Employee Self Service"):
        if role not in roles:
            workspace.append("roles", {"role": role})
            changed = True
    if changed:
        workspace.save(ignore_permissions=True)

    # Keep the source JSON assigned to Administration so Frappe can sync it.
    # Clear only the installed workspace's module after sync and other setup.
    # An empty string also passes the sidebar's SQL NOT IN blocked_modules filter.
    frappe.db.set_value(
        "Workspace", "My Profile",
        {"module": "", "public": 1, "is_hidden": 0, "for_user": "", "parent_page": ""},
        update_modified=False,
    )
    frappe.clear_cache()
