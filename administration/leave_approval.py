"""Leave approval policy. Runs before the standard HRMS validations."""
import frappe
from frappe import _

ONE = "One Level Approval"
TWO = "Two Level Approval"
NONE = "No Approval Required"
SNAPSHOT = ("custom_leave_approval_level", "leave_approver", "custom_second_leave_approver")
PENDING = ("Pending Approval", "Pending Management Approval", "Pending HR Approval")


def employee_user(employee, label):
    user = frappe.db.get_value("Employee", employee, "user_id") if employee else None
    if not user:
        frappe.throw(_("The Employee selected as {0} does not have a User ID. Please assign a User ID to the Employee first.").format(label))
    if not frappe.db.get_value("User", user, "enabled"):
        frappe.throw(_("The User selected as {0} must be enabled.").format(label))
    return user


def validate_employee(doc, method=None):
    doc.custom_leave_approval_level = doc.get("custom_leave_approval_level") or ONE
    if doc.custom_leave_approval_level not in (ONE, TWO, NONE):
        frappe.throw(_("Invalid Leave Approval Level."))
    if doc.custom_leave_approval_level == NONE:
        for field in ("custom_first_approval", "custom_second_approval", "leave_approver", "custom_second_leave_approver"):
            doc.set(field, None)
        return
    if not doc.get("custom_first_approval"):
        frappe.throw(_("First Approval is required."))
    doc.leave_approver = employee_user(doc.custom_first_approval, "First Approval")
    if doc.custom_leave_approval_level == TWO:
        if not doc.get("custom_second_approval"):
            frappe.throw(_("Second Approval is required."))
        if doc.custom_first_approval == doc.custom_second_approval:
            frappe.throw(_("First Approval and Second Approval must be different Employees."))
        doc.custom_second_leave_approver = employee_user(doc.custom_second_approval, "Second Approval")
        if doc.leave_approver == doc.custom_second_leave_approver:
            frappe.throw(_("First and Second Approval must have different Users."))
    else:
        doc.custom_second_approval = None
        doc.custom_second_leave_approver = None


def can_act(doc, user=None):
    user = user or frappe.session.user
    roles = frappe.get_roles(user)
    state = doc.get("workflow_state")
    return bool(
        (state == "Pending Approval" and "Leave Approver" in roles and user == doc.leave_approver)
        or (state == "Pending Management Approval" and doc.custom_leave_approval_level == TWO
            and "Leave Approver" in roles and user == doc.custom_second_leave_approver)
        or (state == "Pending HR Approval" and "HR Leave Approver" in roles)
    )


def validate_leave(doc, method=None):
    if doc.employee and not doc.get("company"):
        doc.company = frappe.db.get_value("Employee", doc.employee, "company")
    old = doc.get_doc_before_save()
    if not old:
        employee = frappe.get_doc("Employee", doc.employee)
        validate_employee(employee)
        for field in SNAPSHOT:
            doc.set(field, employee.get(field))
        if doc.get("workflow_state") not in (None, "", "Open") or doc.docstatus:
            frappe.throw(_("New Leave Applications must start in Open."))
        doc.workflow_state = "Open"
    else:
        for field in ("employee", *SNAPSHOT):
            if doc.get(field) != old.get(field):
                frappe.throw(_("The Employee and approval configuration cannot be changed. Create a new application."))
    state = doc.get("workflow_state") or "Open"
    previous = old.get("workflow_state") if old else "Open"
    if state != previous:
        if previous == "Open" and state == (
            "Pending HR Approval" if doc.custom_leave_approval_level == NONE else "Pending Approval"
        ):
            employee_user_id = frappe.db.get_value("Employee", doc.employee, "user_id")
            if frappe.session.user not in (doc.owner, employee_user_id):
                frappe.throw(_("Only the applicant may request approval."), frappe.PermissionError)
        elif previous == "Approved" and state == "Cancelled" and doc.docstatus == 2:
            if "HR Leave Approver" not in frappe.get_roles():
                frappe.throw(_("HR Leave Approver is required to cancel."), frappe.PermissionError)
        else:
            next_state = {
                "Pending Approval": "Pending Management Approval" if doc.custom_leave_approval_level == TWO else "Pending HR Approval",
                "Pending Management Approval": "Pending HR Approval",
                "Pending HR Approval": "Approved",
            }.get(previous)
            if not can_act(old) or state not in (next_state, "Rejected"):
                frappe.throw(_("You are not authorized for this approval transition."), frappe.PermissionError)
    expected = 1 if state == "Approved" else 2 if state == "Cancelled" else 0
    if state not in ("Open", *PENDING, "Approved", "Rejected", "Cancelled") or doc.docstatus != expected:
        frappe.throw(_("Invalid approval state or document status. Use the workflow actions."))
    if state == "Pending Management Approval" and doc.custom_leave_approval_level != TWO:
        frappe.throw(_("Management approval requires Two Level Approval."))
    if state == "Pending Approval" and doc.custom_leave_approval_level == NONE:
        frappe.throw(_("No Approval Required applications must go directly to HR approval."))
    doc.status = state if state in ("Approved", "Rejected", "Cancelled") else "Open"


def before_cancel(doc, method=None):
    # Cancellation skips before_validate in Frappe.
    doc.workflow_state = "Cancelled"
    validate_leave(doc)


def sync_assignments(doc, method=None):
    from frappe.desk.form.assign_to import _add, set_status
    target = doc.leave_approver if doc.workflow_state == "Pending Approval" else (
        doc.custom_second_leave_approver if doc.workflow_state == "Pending Management Approval" else None
    )
    todos = frappe.get_all("ToDo", filters={"reference_type": doc.doctype,
        "reference_name": doc.name, "status": "Open"}, fields=["name", "allocated_to"])
    kept = False
    for todo in todos:
        if target and todo.allocated_to == target and not kept:
            kept = True
        else:
            set_status(doc.doctype, doc.name, todo=todo.name, assign_to=todo.allocated_to, status="Closed", ignore_permissions=True)
    if target:
        if not frappe.has_permission(doc.doctype, "write", doc=doc, user=target):
            frappe.share.add_docshare(doc.doctype, doc.name, target, read=1, write=1,
                flags={"ignore_share_permission": True})
        if not kept:
            _add({"doctype": doc.doctype, "name": doc.name, "assign_to": [target],
                "description": _("Leave Application awaiting your approval")}, ignore_permissions=True)


def pending_conditions(user):
    roles = frappe.get_roles(user)
    quoted = frappe.db.escape(user)
    parts = []
    if "Leave Approver" in roles:
        parts += [f"(workflow_state='Pending Approval' AND leave_approver={quoted})",
            f"(workflow_state='Pending Management Approval' AND custom_second_leave_approver={quoted})"]
    if "HR Leave Approver" in roles:
        parts.append("workflow_state='Pending HR Approval'")
    return "docstatus=0 AND (" + " OR ".join(parts or ["1=0"]) + ")"


def permission_query(user=None):
    user = user or frappe.session.user
    roles = frappe.get_roles(user)
    if user == "Administrator" or set(roles) & {"System Manager", "HR Manager", "HR User", "HR Leave Approver"}:
        return ""
    quoted = frappe.db.escape(user)
    return (f"(`tabLeave Application`.owner={quoted} OR `tabLeave Application`.employee IN "
        f"(SELECT name FROM `tabEmployee` WHERE user_id={quoted}) OR (" + pending_conditions(user) + "))")


def has_permission(doc, user=None, ptype=None):
    user = user or frappe.session.user
    if user == "Administrator" or set(frappe.get_roles(user)) & {"System Manager", "HR Manager", "HR User", "HR Leave Approver"}:
        return None
    if doc.owner == user or frappe.db.get_value("Employee", doc.employee, "user_id") == user or can_act(doc, user):
        return None
    return False
