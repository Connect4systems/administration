import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate

from administration.leave_approval import before_cancel, sync_assignments, validate_leave


class BusinessTripRequest(Document):
    def before_validate(self):
        validate_leave(self)
        old = self.get_doc_before_save()
        if not old or old.get("workflow_state") == "Open":
            employee = frappe.db.get_value(
                "Employee", self.employee, ["employee_name", "department", "company"], as_dict=True
            ) if self.employee else None
            self.full_name = employee.get("employee_name") if employee else None
            self.department = employee.get("department") if employee else None
            self.company = employee.get("company") if employee else None

    def validate(self):
        if not self.employee or not self.from_date or not self.to_date:
            frappe.throw(_("Employee, From Date and To Date are required."))
        if getdate(self.from_date) > getdate(self.to_date):
            frappe.throw(_("To Date must be on or after From Date."))
        old = self.get_doc_before_save()
        if old and old.workflow_state != "Open":
            for field in ("from_date", "to_date", "company", "reason"):
                if self.get(field) != old.get(field):
                    frappe.throw(_("Trip details cannot change after requesting approval."))

    def before_update_after_submit(self):
        validate_leave(self)
        self.validate()

    def on_update(self):
        sync_assignments(self)

    def on_submit(self):
        frappe.db.get_value("Employee", self.employee, "name", for_update=True)
        dates = []
        date = getdate(self.from_date)
        while date <= getdate(self.to_date):
            if frappe.db.exists("Attendance", {
                "employee": self.employee, "attendance_date": date, "docstatus": ["!=", 2],
            }):
                frappe.throw(_("Attendance already exists for {0} on {1}.").format(self.employee, date))
            dates.append(date)
            date = getdate(add_days(date, 1))
        for date in dates:
            attendance = frappe.get_doc({
                "doctype": "Attendance", "employee": self.employee, "company": self.company,
                "attendance_date": date, "status": "Present",
                "custom_business_trip_request": self.name,
            })
            attendance.insert(ignore_permissions=True)
            attendance.flags.ignore_permissions = True
            attendance.submit()

    def before_cancel(self):
        before_cancel(self)

    def on_cancel(self):
        for name in frappe.get_all("Attendance", filters={
            "custom_business_trip_request": self.name, "docstatus": ["!=", 2],
        }, pluck="name"):
            attendance = frappe.get_doc("Attendance", name)
            attendance.flags.ignore_permissions = True
            if attendance.docstatus == 1:
                attendance.cancel()
            else:
                frappe.delete_doc("Attendance", name, ignore_permissions=True)
        sync_assignments(self)


@frappe.whitelist()
def employee_details(employee):
    """Permission-checked employee details for the unsaved request form."""
    employee = frappe.get_doc("Employee", employee)
    employee.check_permission("read")
    level = employee.get("custom_leave_approval_level") or "One Level Approval"
    first = employee.get("custom_first_approval")
    second = employee.get("custom_second_approval")
    return {
        "full_name": employee.employee_name,
        "department": employee.department,
        "company": employee.company,
        "custom_leave_approval_level": level,
        "leave_approver": (
            frappe.db.get_value("Employee", first, "user_id") if first else employee.get("leave_approver")
        ) if level != "No Approval Required" else None,
        "custom_second_leave_approver": (
            frappe.db.get_value("Employee", second, "user_id") if second else employee.get("custom_second_leave_approver")
        ) if level == "Two Level Approval" else None,
    }
