import frappe
from administration.leave_approval import pending_conditions


def execute(filters=None):
    if not set(frappe.get_roles()) & {"Leave Approver", "HR Leave Approver"}:
        frappe.throw("Leave approval role required", frappe.PermissionError)
    columns = [
        {"fieldname": "name", "label": "Leave Application", "fieldtype": "Link", "options": "Leave Application", "width": 190},
        {"fieldname": "employee", "label": "Employee", "fieldtype": "Link", "options": "Employee", "width": 140},
        {"fieldname": "employee_name", "label": "Employee Name", "fieldtype": "Data", "width": 180},
        {"fieldname": "workflow_state", "label": "Approval State", "fieldtype": "Data", "width": 210},
        {"fieldname": "from_date", "label": "From Date", "fieldtype": "Date", "width": 110},
        {"fieldname": "to_date", "label": "To Date", "fieldtype": "Date", "width": 110},
    ]
    rows = frappe.db.sql("SELECT name, employee, employee_name, workflow_state, from_date, to_date "
        "FROM `tabLeave Application` WHERE " + pending_conditions(frappe.session.user) + " ORDER BY modified DESC", as_dict=True)
    return columns, [row for row in rows if frappe.has_permission("Leave Application", "read", doc=row.name)]
