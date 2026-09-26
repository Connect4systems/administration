from collections import defaultdict

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	flat_filters = {"flat_status": ["in", ["Active", "Expired"]], "docstatus": 1}
	for field in ("project", "governorate", "rent_type"):
		if filters.get(field):
			flat_filters[field] = filters[field]
	# get_list applies the current user's document permissions to each source.
	flats = frappe.get_list(
		"Flat", filters=flat_filters,
		fields=["name", "project", "governorate", "owner_name", "flat_status", "rent_type"],
		order_by="project asc, name asc", limit_page_length=0,
	)
	if not flats:
		return get_columns(), []
	flat_names = [flat.name for flat in flats]
	rooms = frappe.get_list(
		"Room", filters={"flat": ["in", flat_names]}, fields=["name", "flat"],
		order_by="name asc", limit_page_length=0,
	)
	bed_filters = {"flat": ["in", flat_names]}
	for field, source in (("status", "bed_status"), ("employee", "employee")):
		if filters.get(source):
			bed_filters[field] = filters[source]
	beds = frappe.get_list(
		"Bed", filters=bed_filters, fields=["name", "flat", "room", "status", "employee"],
		order_by="name asc", limit_page_length=0,
	)
	employee_ids = sorted({bed.employee for bed in beds if bed.employee})
	employees = frappe.get_list(
		"Employee", filters={"name": ["in", employee_ids]}, fields=["name", "employee_name"],
		limit_page_length=0,
	) if employee_ids and frappe.has_permission("Employee", "read") else []
	return get_columns(), build_rows(flats, rooms, beds, employees, filters)


def build_rows(flats, rooms, beds, employees, filters):
	rooms_by_flat = defaultdict(list)
	beds_by_room = defaultdict(list)
	employee_names = {employee["name"]: employee["employee_name"] for employee in employees}
	for room in rooms:
		rooms_by_flat[room["flat"]].append(room["name"])
	for bed in beds:
		beds_by_room[(bed["flat"], bed.get("room") or None)].append(bed)
	rows = []
	include_empty = not (filters.get("bed_status") or filters.get("employee"))
	for flat in flats:
		base = {**flat, "flat": flat["name"]}
		room_names = rooms_by_flat[flat["name"]]
		# Beds may be created without a Room; retain those under their Flat.
		if beds_by_room.get((flat["name"], None)) or not room_names:
			room_names = [*room_names, None]
		for room in room_names:
			room_beds = beds_by_room.get((flat["name"], room), [])
			if not room_beds and include_empty:
				rows.append({**base, "room": room})
			for bed in room_beds:
				rows.append({
					**base, "room": room, "bed": bed["name"], "bed_status": bed["status"],
					"employee": bed.get("employee"),
					"employee_name": employee_names.get(bed.get("employee"), ""),
				})
	return rows


def get_columns():
	return [
		{"fieldname": field, "label": _(label), "fieldtype": "Link" if target else "Data",
		 "options": target, "width": width}
		for field, label, target, width in (
			("project", "Project", "Project", 150),
			("governorate", "Governorate", "Governorate", 130),
			("flat", "Flat", "Flat", 180),
			("flat_status", "Flat Status", None, 100),
			("rent_type", "Rent Type", None, 110),
			("owner_name", "Owner Name", None, 160),
			("room", "Room", "Room", 160),
			("bed", "Bed", "Bed", 160),
			("bed_status", "Bed Status", None, 100),
			("employee", "Employee ID", "Employee", 130),
			("employee_name", "Employee Name", None, 180),
		)
	]
