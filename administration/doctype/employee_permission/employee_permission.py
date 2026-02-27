from __future__ import annotations
import calendar
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, cint

ALLOWED_PERMISSIONS_PER_MONTH = 2
FIXED_DURATION_MINUTES = 120

def _month_bounds(d):
    d = getdate(d)
    first = d.replace(day=1)
    last_day = calendar.monthrange(d.year, d.month)[1]
    last = d.replace(day=last_day)
    return first, last

def _count_submitted(employee: str, date_obj):
    start, end = _month_bounds(date_obj)
    return frappe.db.count(
        "Employee Permission",
        filters={"employee": employee, "perm_date": ["between", [start, end]], "docstatus": 1},
    )

def _get_or_create_attendance(employee: str, perm_date, company: str | None = None):
    name = frappe.db.get_value("Attendance", {"employee": employee, "attendance_date": perm_date}, "name")
    if name:
        return frappe.get_doc("Attendance", name)
    att = frappe.new_doc("Attendance")
    att.employee = employee
    att.attendance_date = perm_date
    att.status = "Present"
    if not company:
        company = frappe.db.get_value("Employee", employee, "company")
    att.company = company
    att.insert(ignore_permissions=True)
    return att

class EmployeePermission(Document):
    def validate(self):
        if cint(self.duration_minutes) != FIXED_DURATION_MINUTES:
            frappe.throw(f"Duration must be exactly {FIXED_DURATION_MINUTES} minutes.")
        if self.permission_type not in ("Late Entry", "Early Exit"):
            frappe.throw("Permission Type must be either 'Late Entry' or 'Early Exit'.")
        submitted_count = _count_submitted(self.employee, self.perm_date)
        if self.docstatus == 1:
            submitted_count = frappe.db.count(
                "Employee Permission",
                filters={
                    "employee": self.employee,
                    "perm_date": ["between", list(_month_bounds(self.perm_date))],
                    "docstatus": 1,
                    "name": ["!=", self.name],
                },
            )
        if submitted_count >= ALLOWED_PERMISSIONS_PER_MONTH:
            start, end = _month_bounds(self.perm_date)
            frappe.throw(
                f"Monthly limit reached. Employee already used {submitted_count} permissions between {start} and {end}."
            )

    def on_submit(self):
        att = _get_or_create_attendance(self.employee, self.perm_date)
        late = cint(att.get("custom_permission_late_minutes") or 0)
        early = cint(att.get("custom_permission_early_minutes") or 0)
        if self.permission_type == "Late Entry":
            late += FIXED_DURATION_MINUTES
            att.db_set("custom_permission_late_minutes", late)
        else:
            early += FIXED_DURATION_MINUTES
            att.db_set("custom_permission_early_minutes", early)
        att.db_set("custom_permission_applied", 1)
        note_parts = [att.get("custom_permission_note") or ""]
        note_parts.append(f"{self.name}: {self.permission_type} ({FIXED_DURATION_MINUTES} min)")
        att.db_set("custom_permission_note", "\n".join([p for p in note_parts if p.strip()]))
        self.db_set("attendance", att.name)
        self.db_set("status_info", f"Applied to Attendance {att.name}")

    def on_cancel(self):
        if not self.attendance:
            return
        att = frappe.get_doc("Attendance", self.attendance)
        if self.permission_type == "Late Entry":
            current = cint(att.get("custom_permission_late_minutes") or 0)
            current = max(0, current - FIXED_DURATION_MINUTES)
            att.db_set("custom_permission_late_minutes", current)
        else:
            current = cint(att.get("custom_permission_early_minutes") or 0)
            current = max(0, current - FIXED_DURATION_MINUTES)
            att.db_set("custom_permission_early_minutes", current)
        late = cint(att.get("custom_permission_late_minutes") or 0)
        early = cint(att.get("custom_permission_early_minutes") or 0)
        if late == 0 and early == 0:
            att.db_set("custom_permission_applied", 0)
        note = (att.get("custom_permission_note") or "").splitlines()
        note = [ln for ln in note if self.name not in ln]
        att.db_set("custom_permission_note", "\n".join(note))

@frappe.whitelist()
def permission_usage(employee: str, any_date: str):
    used = _count_submitted(employee, any_date)
    return {"used": used, "remaining": max(0, ALLOWED_PERMISSIONS_PER_MONTH - used)}
