"""Minimal employee lookups for Accounts User accounting party selectors."""

import frappe
from frappe.utils import cint


@frappe.whitelist()
def employee_query(doctype, txt, searchfield, start, page_len, filters=None):
    frappe.only_for("Accounts User")
    filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
    context = filters.get("accounting_context")
    if doctype != "Employee" or context not in ("Journal Entry", "General Ledger"):
        frappe.throw("Invalid employee selection context", frappe.PermissionError)
    if context == "Journal Entry":
        frappe.has_permission("Journal Entry", "read", throw=True)
    else:
        from frappe.desk.query_report import get_report_doc

        get_report_doc("General Ledger").check_permission("read")
        frappe.has_permission("GL Entry", "read", throw=True)

    # Deliberately bypass Employee user permissions for this minimal selector only.
    # Never accept caller-supplied fields, status, ordering, or arbitrary filters.
    return frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        or_filters={"name": ["like", f"%{txt or ''}%"],
                    "employee_name": ["like", f"%{txt or ''}%"]},
        fields=["name", "employee_name"],
        order_by="name",
        start=max(0, cint(start)),
        page_length=min(100, max(1, cint(page_len))),
        as_list=True,
    )
