"""Shared and private Flat assignment rules."""

import frappe
from frappe import _


def ensure_shared_flat(flat):
	if flat and frappe.db.get_value("Flat", flat, "request_type") == "Private":
		frappe.throw(_("Rooms and beds are only available for Share flats."))


def validate_flat_accommodation(flat):
	request_type = flat.get("request_type") or "Share"
	if request_type != "Private":
		flat.employee = None
		return
	previous = flat.get_doc_before_save()
	if previous and previous.get("request_type") != "Private":
		if frappe.db.exists("Room", {"flat": flat.name}) or frappe.db.exists("Bed", {"flat": flat.name}):
			frappe.throw(_("Remove existing rooms and beds before changing the Flat to Private."))
	if flat.get("employee"):
		employee = frappe.db.get_value(
			"Employee", flat.employee, ["status", "custom_project", "custom_accommidation"], as_dict=True
		)
		if not employee or employee.status != "Active" or employee.custom_project != flat.project or employee.custom_accommidation != "Private":
			frappe.throw(_("Select an active employee in the Flat's Project with Accommodation set to Private."))
