# Copyright (c) 2025, Connect 4 Systems and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import escape_html


class Bed(Document):
	def validate(self):
		if self.flat and self.room:
			room_flat = frappe.db.get_value("Room", self.room, "flat")
			if room_flat != self.flat:
				frappe.throw("Room must belong to the selected Flat.")

		if self.employee:
			# Serialize assignments for this employee, including concurrent new Beds.
			frappe.db.sql("select name from `tabEmployee` where name = %s for update", self.employee)
			conflict = _get_employee_bed(self.employee, self.name, for_update=True)
			if conflict:
				frappe.throw(_assignment_message(self.employee, conflict), title=_("Employee Already Assigned"))
			self.status = "Booked"
		else:
			self.status = "Open"
			self.employee_status = None
			self.department = None
			self.type = None

	def on_update(self):
		if self.has_value_changed("employee") or self.has_value_changed("room"):
			previous_employee = self.get_doc_before_save()
			if previous_employee and previous_employee.employee != self.employee:
				_sync_employee_accommodation(previous_employee.employee, None, None)
			_sync_employee_accommodation(self.employee, self.room, self.name)

def _get_employee_bed(employee, bed_name=None, for_update=False):
	rows = frappe.db.sql(
		"""select name, flat from `tabBed`
		where employee = %s and name != %s
		order by name limit 1""" + (" for update" if for_update else ""),
		(employee, bed_name or ""), as_dict=True,
	)
	return rows[0] if rows else None


def _assignment_message(employee, bed):
	return _(
		"Employee {0} is already assigned to Bed {1} in Flat {2}. "
		"Please release the existing bed assignment before assigning this employee to another bed."
	).format(*(escape_html(value or "") for value in (employee, bed.name, bed.flat)))


@frappe.whitelist()
def check_employee_assignment(employee, bed_name=None):
	if not (frappe.has_permission("Bed", "write") or frappe.has_permission("Bed", "create")):
		frappe.throw(_("You do not have permission to assign employees to beds."), frappe.PermissionError)
	if employee:
		conflict = _get_employee_bed(employee, bed_name)
		if conflict:
			return _assignment_message(employee, conflict)


def _sync_employee_accommodation(employee_name, room_name, bed_name):
	if not employee_name:
		return

	flat_name = frappe.db.get_value("Room", room_name, "flat") if room_name else None
	frappe.db.set_value(
		"Employee",
		employee_name,
		{
			"custom_flat": flat_name or "",
			"custom_room": room_name or "",
			"custom_bed": bed_name or "",
		},
		update_modified=False,
	)


@frappe.whitelist()
def employee_left(bed_name):
	bed = frappe.get_doc("Bed", bed_name)
	employee = bed.employee
	bed.employee = None
	bed.status = "Open"
	bed.save()
	_sync_employee_accommodation(employee, None, None)
