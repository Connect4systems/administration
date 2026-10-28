"""Request-local Employee selection access without changing stored permissions."""

from copy import deepcopy

import frappe


SEARCH_METHODS = {"frappe.desk.search.search_link", "frappe.desk.search.search_widget"}
DOCUMENT_METHODS = {
    "frappe.desk.form.save.savedocs",
    "frappe.desk.form.load.getdoc",
    "frappe.desk.form.run_method.run_doc_method",
    "run_doc_method",
    "frappe.client.insert",
    "frappe.client.save",
    "frappe.client.submit",
    "frappe.client.cancel",
}
# These masters must always retain their ordinary permission checks.
ACCESS_MASTERS = {"Employee", "User", "User Permission", "DocType", "Role", "Custom DocPerm"}


def _document_type(args):
    if args.get("doctype"):
        return args["doctype"]
    if args.get("dt"):
        return args["dt"]
    document = args.get("doc") or args.get("docs")
    if isinstance(document, str):
        document = frappe.parse_json(document)
    return document.get("doctype") if isinstance(document, dict) else None


def allow_employee_selection():
    """Expand only this request's cached Employee permissions for document use.

    Redis and User Permission records are never updated. Frappe discards the local
    cache at request end. Direct Employee list/form/read/write requests stay normal.
    All standard role checks and other User Permission rules still run.
    """
    args = frappe.local.form_dict
    command = args.get("cmd", "")
    searching = command in SEARCH_METHODS and args.get("doctype") == "Employee"
    document_operation = command in DOCUMENT_METHODS
    accounting_operation = command.startswith("erpnext.accounts.")
    if not (searching or document_operation or accounting_operation):
        return
    if document_operation:
        doctype = _document_type(args)
        if not doctype or doctype in ACCESS_MASTERS:
            return
        # Child records can inherit Employee write access from their parent.
        # Document forms send their parent document, so no child RPC needs this.
        if frappe.get_meta(doctype).istable:
            return
    if "Accounts User" not in frappe.get_roles():
        return

    from frappe.core.doctype.user_permission.user_permission import get_user_permissions

    user = frappe.session.user
    permissions = deepcopy(get_user_permissions(user))
    active = frappe.get_all("Employee", filters={"status": "Active"}, pluck="name")
    # Keep existing defaults, scoped permissions and access to historical records.
    employee_permissions = permissions.setdefault("Employee", [])
    existing = {row.get("doc") for row in employee_permissions if not row.get("applicable_for")}
    employee_permissions.extend(
        frappe._dict(doc=name, applicable_for=None, is_default=0, hide_descendants=1)
        for name in active if name not in existing
    )
    key = frappe.cache.make_key("user_permissions")
    frappe.local.cache.setdefault(key, {})[user] = permissions

    if searching:
        filters = args.get("filters") or {}
        if isinstance(filters, str):
            filters = frappe.parse_json(filters)
        if isinstance(filters, dict):
            filters = {**filters, "status": "Active"}
        else:
            filters = [*filters, ["Employee", "status", "=", "Active"]]
        args["filters"] = filters
