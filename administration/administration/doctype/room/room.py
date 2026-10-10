# Copyright (c) 2025, Connect 4 Systems and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Room(Document):
	def validate(self):
		from administration.flat_accommodation import ensure_shared_flat
		ensure_shared_flat(self.flat)


@frappe.whitelist()
def employee_left(room_name):
	for bed_name in frappe.get_all(
		"Bed", filters={"room": room_name, "employee": ["is", "set"]}, pluck="name"
	):
		bed = frappe.get_doc("Bed", bed_name)
		bed.employee = None
		bed.status = "Open"
		bed.save()
