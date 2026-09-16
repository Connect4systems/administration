# Copyright (c) 2025, Connect 4 Systems and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Bed(Document):
	def validate(self):
		if self.flat and self.room:
			room_flat = frappe.db.get_value("Room", self.room, "flat")
			if room_flat != self.flat:
				frappe.throw("Room must belong to the selected Flat.")

		if self.employee:
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
