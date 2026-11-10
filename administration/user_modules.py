"""Keep the standard User module selector usable without legacy desktop config."""

import frappe


def ensure_module_choices(doc, method=None):
    """Supply installed modules when Frappe's desktop config returns no choices."""
    if doc.get_onload("all_modules"):
        return

    modules = frappe.get_all(
        "Module Def",
        filters={"app_name": ["in", frappe.get_installed_apps()]},
        pluck="name",
        order_by="name",
    )
    doc.set_onload("all_modules", modules)
