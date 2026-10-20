import frappe
from administration.leave_approval import pending_conditions


def execute(filters=None):
    if not set(frappe.get_roles()) & {"Leave Approver", "HR Leave Approver"}:
        frappe.throw("Leave approval role required", frappe.PermissionError)
    columns = [
        {"fieldname": "document_type", "label": "Document Type", "fieldtype": "Data", "width": 160},
        {"fieldname": "name", "label": "Request", "fieldtype": "Dynamic Link", "options": "document_type", "width": 190},
        {"fieldname": "employee", "label": "Employee", "fieldtype": "Link", "options": "Employee", "width": 140},
        {"fieldname": "employee_name", "label": "Employee Name", "fieldtype": "Data", "width": 180},
        {"fieldname": "workflow_state", "label": "Approval State", "fieldtype": "Data", "width": 210},
        {"fieldname": "from_date", "label": "From Date", "fieldtype": "Date", "width": 110},
        {"fieldname": "to_date", "label": "To Date", "fieldtype": "Date", "width": 110},
    ]
    rows = []
    for document_type, employee_name in (("Leave Application", "employee_name"), ("Business Trip Request", "full_name")):
        requests = frappe.db.sql(
            f"SELECT name, employee, {employee_name} AS employee_name, workflow_state, from_date, to_date "
            f"FROM `tab{document_type}` WHERE " + pending_conditions(frappe.session.user) + " ORDER BY modified DESC",
            as_dict=True,
        )
        for row in requests:
            if frappe.has_permission(document_type, "read", doc=row.name):
                row.document_type = document_type
                rows.append(row)
    return columns, rows
