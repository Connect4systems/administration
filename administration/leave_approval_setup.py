"""Idempotent setup after fixtures and customizations have been synchronized."""
import json
import frappe
from administration.leave_approval import ONE, TWO, NONE, SNAPSHOT


def setup_leave_company_field():
    from frappe.custom.doctype.property_setter.property_setter import make_property_setter

    # Keep the mandatory field accessible to ordinary employees, including sites
    # with older Customize Form settings that hid it or raised its permission level.
    for property_name, value, property_type in (
        ("hidden", 0, "Check"),
        ("permlevel", 0, "Int"),
        ("read_only", 0, "Check"),
        ("depends_on", "", "Data"),
        ("read_only_depends_on", "", "Data"),
        # The form script handles the employee/default fallback. A native fetch
        # would overwrite the user's default with an empty Employee.company.
        ("fetch_from", "", "Small Text"),
        ("fetch_if_empty", 1, "Check"),
        ("insert_after", "employee", "Data"),
    ):
        make_property_setter("Leave Application", "company", property_name, value, property_type)


def setup():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    from frappe.custom.doctype.property_setter.property_setter import make_property_setter
    from frappe.permissions import add_permission, setup_custom_perms, update_permission_property

    setup_leave_company_field()

    for role in ("Leave Approver", "HR Leave Approver"):
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)
    two = 'eval:doc.custom_leave_approval_level == "Two Level Approval"'
    approval = 'eval:doc.custom_leave_approval_level != "No Approval Required"'
    fields = [
        {"fieldname": "custom_leave_approval_level", "label": "Leave Approval Level", "fieldtype": "Select",
            "options": "\n".join((ONE, TWO, NONE)), "default": ONE, "insert_after": "approvers_section", "reqd": 1},
        {"fieldname": "custom_first_approval", "label": "First Approval", "fieldtype": "Link",
            "options": "Employee", "insert_after": "custom_leave_approval_level", "reqd": 0,
            "depends_on": approval, "mandatory_depends_on": approval},
        {"fieldname": "custom_second_approval", "label": "Second Approval", "fieldtype": "Link",
            "options": "Employee", "insert_after": "leave_approver", "depends_on": two, "mandatory_depends_on": two},
        {"fieldname": "custom_second_leave_approver", "label": "Second Leave Approver", "fieldtype": "Link",
            "options": "User", "insert_after": "custom_second_approval", "read_only": 1, "depends_on": two},
    ]
    create_custom_fields({"Employee": fields, "Leave Application": [
        {"fieldname": "custom_leave_approval_level", "label": "Leave Approval Level", "fieldtype": "Select",
            "options": "\n".join((ONE, TWO, NONE)), "read_only": 1, "insert_after": "leave_approver"},
        {"fieldname": "custom_second_leave_approver", "label": "Second Leave Approver", "fieldtype": "Link",
            "options": "User", "read_only": 1, "insert_after": "custom_leave_approval_level", "depends_on": two},
        {"fieldname": "workflow_state", "label": "Approval State", "fieldtype": "Link", "options": "Workflow State",
            "read_only": 1, "allow_on_submit": 1, "no_copy": 1, "insert_after": "status"},
    ]}, update=True)
    for dt in ("Employee", "Leave Application"):
        make_property_setter(dt, "leave_approver", "read_only", 1, "Check")
        make_property_setter(dt, "leave_approver", "reqd", 0, "Check")
        make_property_setter(dt, "leave_approver", "depends_on", approval, "Data")
    make_property_setter("Employee", "leave_approver", "insert_after", "custom_first_approval", "Data")
    order = [f.fieldname for f in frappe.get_meta("Employee").fields]
    approval_fields = ["custom_leave_approval_level", "custom_first_approval", "leave_approver",
        "custom_second_approval", "custom_second_leave_approver"]
    order = [name for name in order if name not in approval_fields]
    anchor = "approvers_section" if "approvers_section" in order else "attendance_and_leave_details"
    index = order.index(anchor) + 1
    order[index:index] = approval_fields
    make_property_setter("Employee", None, "field_order", json.dumps(order), "Data", for_doctype=True)
    # Pending business status uses standard HRMS Open; workflow_state identifies the stage.
    setup_custom_perms("Leave Application")
    for role in ("Leave Approver", "HR Leave Approver"):
        if not frappe.db.exists("Custom DocPerm", {"parent": "Leave Application", "role": role, "permlevel": 0}):
            add_permission("Leave Application", role)
        for permission in ("read", "write", "report"):
            update_permission_property("Leave Application", role, 0, permission, 1)
        if role == "HR Leave Approver":
            for permission in ("submit", "cancel"):
                update_permission_property("Leave Application", role, 0, permission, 1)

    backfill()
    setup_approval_workflow("Leave Application")
    from administration.leave_approval import sync_assignments
    for name in frappe.get_all("Leave Application", pluck="name"):
        sync_assignments(frappe.get_doc("Leave Application", name))
    workspace = frappe.get_doc("Workspace", "My Profile")
    if not any(row.label == "Pending Approval" for row in workspace.shortcuts):
        workspace.append("shortcuts", {"label": "Pending Approval", "type": "Report",
            "link_to": "Pending Leave Approval", "report_ref_doctype": "Leave Application", "color": "Orange"})
    content = json.loads(workspace.content or "[]")
    if not any(block.get("data", {}).get("shortcut_name") == "Pending Approval" for block in content):
        content.append({"id": "pending-leave", "type": "shortcut", "data": {"shortcut_name": "Pending Approval", "col": 6}})
    workspace.content = json.dumps(content)
    existing_roles = {r.role for r in workspace.roles}
    for role in ("Leave Approver", "HR Leave Approver"):
        if role not in existing_roles:
            workspace.append("roles", {"role": role})
    workspace.save(ignore_permissions=True)
    frappe.clear_cache()


def backfill():
    # Recover unambiguous existing first approvers without inventing a management approver.
    for employee in frappe.get_all("Employee", fields=["name", "leave_approver", "custom_first_approval", *SNAPSHOT[:1]]):
        if employee.custom_leave_approval_level == NONE:
            frappe.db.set_value("Employee", employee.name, {field: None for field in
                ("custom_first_approval", "custom_second_approval", "leave_approver", "custom_second_leave_approver")}, update_modified=False)
            continue
        values = {}
        if not employee.custom_leave_approval_level:
            values["custom_leave_approval_level"] = ONE
        if not employee.custom_first_approval and employee.leave_approver:
            matches = frappe.get_all("Employee", filters={"user_id": employee.leave_approver}, pluck="name")
            if len(matches) == 1:
                values["custom_first_approval"] = matches[0]
        first = employee.custom_first_approval or values.get("custom_first_approval")
        if first:
            user = frappe.db.get_value("Employee", first, "user_id")
            if user:
                values["leave_approver"] = user
        if values:
            frappe.db.set_value("Employee", employee.name, values, update_modified=False)
    # Synchronize complete configurations, but let HR repair incomplete legacy masters.
    from administration.leave_approval import validate_employee
    for name in frappe.get_all("Employee", filters={"custom_first_approval": ["is", "set"]}, pluck="name"):
        employee = frappe.get_doc("Employee", name)
        if employee.custom_leave_approval_level == TWO and not employee.custom_second_approval:
            continue
        validate_employee(employee)
        frappe.db.set_value("Employee", name, {field: employee.get(field) for field in SNAPSHOT}, update_modified=False)
    valid_states = {"Open", "Pending Approval", "Pending Management Approval", "Pending HR Approval", "Approved", "Rejected", "Cancelled"}
    for doc in frappe.get_all("Leave Application", fields=["name", "employee", "docstatus", "status", "workflow_state", *SNAPSHOT]):
        values = {}
        if doc.docstatus == 1 and doc.status != "Approved":
            frappe.throw("Leave Application " + doc.name + " is a legacy submitted non-approved application. Resolve it through normal cancellation before enabling the approval workflow.")
        if doc.docstatus == 0 and doc.workflow_state not in valid_states | {None, "", "Pending", "Draft"}:
            frappe.throw("Leave Application " + doc.name + " has an unknown legacy workflow state: " + str(doc.workflow_state) + ". Map this state explicitly before migration.")
        if not doc.custom_leave_approval_level:
            # Historical requests only have a first approver. Preserve that stored user.
            values["custom_leave_approval_level"] = ONE
        if doc.workflow_state not in valid_states:
            values["workflow_state"] = ("Approved" if doc.docstatus == 1 else "Cancelled" if doc.docstatus == 2
                else "Rejected" if doc.status == "Rejected" else "Pending Approval" if doc.workflow_state == "Pending" else "Open")
        if values:
            frappe.db.set_value("Leave Application", doc.name, values, update_modified=False)


def setup_approval_workflow(document_type):
    """Keep leave and business trip approval routes identical."""
    states = [("Open", 0, "Employee"), ("Pending Approval", 0, "Leave Approver"),
        ("Pending Management Approval", 0, "Leave Approver"), ("Pending HR Approval", 0, "HR Leave Approver"),
        ("Approved", 1, "HR Leave Approver"), ("Rejected", 0, "HR Leave Approver"),
        ("Cancelled", 2, "HR Leave Approver")]
    first = "doc.leave_approver == frappe.session.user"
    second = 'doc.custom_second_leave_approver == frappe.session.user and doc.custom_leave_approval_level == "Two Level Approval"'
    applicant = "(doc.owner == frappe.session.user or frappe.db.get_value('Employee', doc.employee, 'user_id') == frappe.session.user)"
    transitions = [
        ("Open", "Submit for Approval", "Pending Approval", "Employee", applicant + ' and doc.custom_leave_approval_level in ("One Level Approval", "Two Level Approval")'),
        ("Open", "Submit for Approval", "Pending HR Approval", "Employee", applicant + ' and doc.custom_leave_approval_level == "No Approval Required"'),
        ("Pending Approval", "Approve", "Pending HR Approval", "Leave Approver", first + ' and doc.custom_leave_approval_level == "One Level Approval"'),
        ("Pending Approval", "Approve", "Pending Management Approval", "Leave Approver", first + ' and doc.custom_leave_approval_level == "Two Level Approval"'),
        ("Pending Approval", "Reject", "Rejected", "Leave Approver", first),
        ("Pending Management Approval", "Approve", "Pending HR Approval", "Leave Approver", second),
        ("Pending Management Approval", "Reject", "Rejected", "Leave Approver", second),
        ("Pending HR Approval", "Approve", "Approved", "HR Leave Approver", ""),
        ("Pending HR Approval", "Reject", "Rejected", "HR Leave Approver", ""),
        ("Approved", "Cancel", "Cancelled", "HR Leave Approver", ""),
    ]
    for state, _, _ in states:
        if not frappe.db.exists("Workflow State", state):
            frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": state}).insert(ignore_permissions=True)
    for action in {row[1] for row in transitions}:
        if not frappe.db.exists("Workflow Action Master", action):
            frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": action}).insert(ignore_permissions=True)
    name = "Administration Leave Approval" if document_type == "Leave Application" else "Administration Business Trip Approval"
    for existing in frappe.get_all("Workflow", filters={"document_type": document_type, "is_active": 1}, pluck="name"):
        if existing != name:
            frappe.db.set_value("Workflow", existing, "is_active", 0)
    workflow = frappe.get_doc("Workflow", name) if frappe.db.exists("Workflow", name) else frappe.new_doc("Workflow")
    workflow.update({"workflow_name": name, "document_type": document_type, "is_active": 1,
        "workflow_state_field": "workflow_state", "send_email_alert": 0,
        "states": [{"state": state, "doc_status": str(status), "allow_edit": role,
            "update_field": "status", "update_value": state if state in ("Approved", "Rejected", "Cancelled") else "Open"}
            for state, status, role in states],
        "transitions": [{"state": state, "action": action, "next_state": target, "allowed": role,
            "condition": condition, "allow_self_approval": 1} for state, action, target, role, condition in transitions]})
    workflow.save(ignore_permissions=True)
