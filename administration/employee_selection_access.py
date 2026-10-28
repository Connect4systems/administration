"""Request-local Employee selection access without changing stored permissions."""

from copy import deepcopy

import frappe


EMPLOYEE_SELECTION_ROLES = frozenset({
    "Accounts User", "Site Admin", "Fleet Manager", "Fleet admin",
    "Admin supervisor (Accommodation)", "Admin supervisor (Travel)",
    "Administration Manager",
})
EMPLOYEE_SELECTION_FIELDS = frozenset({
    "name", "employee_name", "company", "status", "department", "employment_type",
    "branch", "designation", "custom_project", "custom_accommidation",
    "custom_transportation", "reports_to", "leave_approver", "company_email",
})


def has_employee_selection_role():
    return bool(EMPLOYEE_SELECTION_ROLES.intersection(frappe.get_roles()))


@frappe.whitelist()
def get_document(doctype, name=None, filters=None, parent=None):
    """Allow identity-only Employee fetches used by document client scripts.

    A normal permitted read still uses Frappe's full, field-filtered response.
    An eligible restricted user gets only the same identity information as a link
    selector. Employee form loading and all Employee writes remain unchanged.
    """
    from frappe.client import get as standard_get
    from frappe.permissions import has_permission

    if doctype != "Employee" or not name or not has_employee_selection_role():
        return standard_get(doctype, name=name, filters=filters, parent=parent)
    doc = frappe.get_doc("Employee", str(name))
    # Document.has_permission logs a user-facing denial even when it merely
    # returns False. This is a capability probe; the select check below remains
    # authoritative and must still report real failures.
    if has_permission("Employee", "read", doc=doc, raise_exception=False) or doc.get("status") != "Active":
        return standard_get(doctype, name=name, filters=filters, parent=parent)

    from frappe.core.doctype.user_permission.user_permission import get_user_permissions

    # Check role and all other link restrictions without the Employee self rule.
    # Restore the request cache immediately; never persist this projection scope.
    user = frappe.session.user
    permissions = deepcopy(get_user_permissions(user))
    permissions.pop("Employee", None)
    key = frappe.cache.make_key("user_permissions")
    cache = frappe.local.cache.setdefault(key, {})
    missing = object()
    previous = cache.get(user, missing)
    try:
        cache[user] = permissions
        doc.check_permission("select")
        allowed_fields = ("name", "employee_name", "company", "status")
        result = {field: doc.get(field) for field in allowed_fields}
        result["doctype"] = "Employee"
        return result
    finally:
        if previous is missing:
            cache.pop(user, None)
        else:
            cache[user] = previous


SEARCH_METHODS = {"frappe.desk.search.search_link", "frappe.desk.search.search_widget"}
APP_SELECTION_METHODS = {
    "administration.administration.doctype.bed.bed.check_employee_assignment",
    "administration.administration.doctype.bed.bed.employee_left",
    "administration.administration.doctype.vehicles.vehicles.get_employee_vehicles",
}
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


def _request_command(args):
    # API dispatch sets form_dict.cmd only AFTER request/auth hooks have run.
    # Match the v1 router, including its legacy trailing-path handling. The URL
    # wins over a payload cmd, since the dispatcher also overwrites that value.
    request = getattr(frappe.local, "request", None)
    path = getattr(request, "path", "") if request else ""
    for prefix in ("/api/method/", "/api/v1/method/"):
        if path.startswith(prefix):
            return path[len(prefix):].split("/", 1)[0]
    return args.get("cmd") or ""


def _selection_field_fetch(command, args):
    """Permit operational fetch_from fields, never arbitrary Employee fields."""
    if args.get("doctype") != "Employee":
        return False
    if command == "frappe.client.get_value":
        fields = args.get("fieldname")
        filters = args.get("filters")
        if isinstance(filters, str) and filters.startswith("{"):
            filters = frappe.parse_json(filters)
        if not (isinstance(filters, str) and filters or
                isinstance(filters, dict) and set(filters) == {"name"} and filters.get("name")):
            return False
    elif command == "frappe.client.validate_link":
        fields = args.get("fields") or []
    else:
        return False
    if isinstance(fields, str):
        fields = frappe.parse_json(fields) if fields.startswith("[") else [fields]
    return isinstance(fields, (list, tuple)) and set(fields).issubset(EMPLOYEE_SELECTION_FIELDS)


def allow_employee_selection():
    """Expand only this request's cached Employee permissions for document use.

    Redis and User Permission records are never updated. Frappe discards the local
    cache at request end. Direct Employee list/form/read/write requests stay normal.
    All standard role checks and other User Permission rules still run.
    """
    args = frappe.local.form_dict
    command = _request_command(args)
    searching = command in SEARCH_METHODS and args.get("doctype") == "Employee"
    document_operation = command in DOCUMENT_METHODS
    accounting_operation = command.startswith("erpnext.accounts.")
    field_fetch = _selection_field_fetch(command, args)
    app_operation = command in APP_SELECTION_METHODS
    if not (searching or document_operation or accounting_operation or field_fetch or app_operation):
        return
    if document_operation:
        doctype = _document_type(args)
        if not doctype or doctype in ACCESS_MASTERS:
            return
        # Child records can inherit Employee write access from their parent.
        # Document forms send their parent document, so no child RPC needs this.
        if frappe.get_meta(doctype).istable:
            return
    if not has_employee_selection_role():
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


def diagnose_employee_selection(user, employee):
    """Read-only bench diagnostic; deliberately not exposed as a browser RPC.

    Reports actual installed hooks and permission outcomes using the site's own
    Frappe code. Restores the original user and request-local state even on failure.
    """
    from hashlib import sha256
    from pathlib import Path
    from types import SimpleNamespace

    from frappe.core.doctype.user_permission.user_permission import get_user_permissions

    original_user = frappe.session.user
    original_args = frappe.local.form_dict
    original_request = getattr(frappe.local, "request", None)
    original_cache = deepcopy(frappe.local.cache)
    try:
        frappe.set_user(user)
        employee = str(employee)
        report = {
            "frappe_version": frappe.__version__,
            "module_revision": sha256(Path(__file__).read_bytes()).hexdigest()[:12],
            "auth_hooks": list(frappe.get_hooks("auth_hooks", [])),
            "before_request_hooks": list(frappe.get_hooks("before_request", [])),
            "is_accounts_user": "Accounts User" in frappe.get_roles(),
            "has_employee_selection_role": has_employee_selection_role(),
            "employee_exists": bool(frappe.db.exists("Employee", employee)),
            "employee_status": frappe.db.get_value("Employee", employee, "status"),
            "employee_read_before": bool(frappe.has_permission("Employee", "read", employee)),
        }
        frappe.local.form_dict = frappe._dict(party_type="Employee", party=employee)
        # Reproduce a browser RPC before Frappe dispatch populates cmd.
        frappe.local.request = SimpleNamespace(path="/api/method/erpnext.accounts.utils.get_balance_on")
        report["resolved_command"] = _request_command(frappe.local.form_dict)
        baseline = deepcopy(get_user_permissions(user))
        allow_employee_selection()
        effective = get_user_permissions(user)
        report.update({
            "employee_in_effective_permissions": any(
                str(row.get("doc")) == employee and not row.get("applicable_for")
                for row in effective.get("Employee", [])
            ),
            "employee_read_after": bool(frappe.has_permission("Employee", "read", employee)),
            "other_user_permissions_unchanged": {
                key: value for key, value in baseline.items() if key != "Employee"
            } == {key: value for key, value in effective.items() if key != "Employee"},
        })
        return report
    finally:
        frappe.set_user(original_user)
        frappe.local.form_dict = original_args
        frappe.local.request = original_request
        frappe.local.cache = original_cache
