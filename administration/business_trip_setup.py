"""Business trips share the employee leave approval policy."""
import frappe

from administration.leave_approval import permission_query as leave_permission_query
from administration.leave_approval_setup import setup_approval_workflow


def permission_query(user=None):
    return leave_permission_query(user, document_type="Business Trip Request")


def setup():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    from frappe.custom.doctype.property_setter.property_setter import make_property_setter
    from frappe.permissions import add_permission, setup_custom_perms, update_permission_property

    # Existing sites may have Custom DocPerm rows overriding DocType permissions.
    setup_custom_perms("Business Trip Request")
    for role in ("Leave Approver", "HR Leave Approver"):
        if not frappe.db.exists("Custom DocPerm", {"parent": "Business Trip Request", "role": role, "permlevel": 0}):
            add_permission("Business Trip Request", role)
        for right in ("read", "write", "report"):
            update_permission_property("Business Trip Request", role, 0, right, 1)
        if role == "HR Leave Approver":
            for right in ("submit", "cancel"):
                update_permission_property("Business Trip Request", role, 0, right, 1)
    for field in ("leave_approver", "custom_second_leave_approver"):
        make_property_setter("Business Trip Request", field, "fieldtype", "Data", "Data")
        make_property_setter("Business Trip Request", field, "options", "Email", "Data")

    create_custom_fields({"Attendance": [{
        "fieldname": "custom_business_trip_request", "label": "Business Trip Request",
        "fieldtype": "Link", "options": "Business Trip Request", "read_only": 1,
        "no_copy": 1, "insert_after": "employee", "search_index": 1,
    }]}, update=True)
    # Existing submitted trips have no approval history: do not silently approve
    # them or generate attendance retroactively.
    for row in frappe.get_all("Business Trip Request", fields=["name", "docstatus", "workflow_state"]):
        if not row.workflow_state:
            if row.docstatus == 1:
                frappe.throw("Resolve legacy submitted Business Trip Request " + row.name +
                    " through normal cancellation before enabling the approval workflow.")
            # Legacy drafts acquire a validated approval snapshot on their next
            # save. Incomplete Employee settings must not block site migration.
            values = {}
            values.update({
                "workflow_state": "Cancelled" if row.docstatus == 2 else "Open",
                "status": "Cancelled" if row.docstatus == 2 else "Open",
            })
            frappe.db.set_value("Business Trip Request", row.name, values, update_modified=False)
    setup_approval_workflow("Business Trip Request")
    frappe.clear_cache()
