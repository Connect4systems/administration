from collections import Counter

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	flat_filters = {"docstatus": 1}
	for field in ("project", "governorate", "rent_type", "flat_status"):
		if filters.get(field):
			flat_filters[field] = filters[field]
	# Apply document permissions before reading connections or child records.
	flats = frappe.get_list(
		"Flat", filters=flat_filters,
		fields=["name", "project", "governorate", "rent_type", "flat_status", "rent"],
		order_by="project asc, name asc", limit_page_length=0,
	)
	if not flats:
		return get_columns(), []
	flat_names = [flat["name"] for flat in flats]
	rooms = frappe.get_list(
		"Room", filters={"flat": ["in", flat_names]}, fields=["name", "flat"],
		limit_page_length=0,
	)
	beds = frappe.get_list(
		"Bed", filters={"flat": ["in", flat_names]}, fields=["name", "flat", "status"],
		limit_page_length=0,
	)
	# Child rows inherit access from the already permission-filtered Flat parents.
	contracts = frappe.get_all(
		"Flat Rent Contract",
		filters={"parent": ["in", flat_names], "parenttype": "Flat", "parentfield": "rent_contracts"},
		fields=["parent", "idx", "rent_start_date", "rent_end_date"],
		limit_page_length=0,
	)
	return get_columns(), build_rows(flats, rooms, beds, contracts)


def build_rows(flats, rooms, beds, contracts):
	room_counts = Counter(room["flat"] for room in rooms)
	bed_counts = Counter(bed["flat"] for bed in beds)
	booked_counts = Counter(bed["flat"] for bed in beds if bed.get("status") == "Booked")
	free_counts = Counter(bed["flat"] for bed in beds if bed.get("status") == "Open")
	latest_contracts = {}
	for contract in contracts:
		parent = contract["parent"]
		if parent not in latest_contracts or contract_key(contract) > contract_key(latest_contracts[parent]):
			latest_contracts[parent] = contract
	rows = []
	for flat in flats:
		name = flat["name"]
		contract = latest_contracts.get(name, {})
		rows.append({
			**flat, "flat": name, "total_rooms": room_counts[name], "total_beds": bed_counts[name],
			"booked_beds": booked_counts[name], "free_beds": free_counts[name],
			"rent_start_date": contract.get("rent_start_date"),
			"rent_end_date": contract.get("rent_end_date"),
		})
	return rows


def contract_key(contract):
	# ISO dates sort chronologically; grid position breaks ties for equal periods.
	return (
		str(contract.get("rent_start_date") or ""),
		str(contract.get("rent_end_date") or ""),
		contract.get("idx") or 0,
	)


def get_columns():
	return [
		{"fieldname": field, "label": _(label), "fieldtype": fieldtype, "options": options, "width": width}
		for field, label, fieldtype, options, width in (
			("project", "Project", "Link", "Project", 150),
			("governorate", "Governorate", "Link", "Governorate", 130),
			("flat", "Flat", "Link", "Flat", 180),
			("rent_type", "Rent Type", "Data", None, 110),
			("flat_status", "Flat Status", "Data", None, 100),
			("rent", "Rent", "Currency", None, 120),
			("total_rooms", "Total Rooms", "Int", None, 110),
			("total_beds", "Total Beds", "Int", None, 110),
			("booked_beds", "Booked Beds", "Int", None, 110),
			("free_beds", "Free Beds", "Int", None, 110),
			("rent_start_date", "Rent Start Date", "Date", None, 120),
			("rent_end_date", "Rent End Date", "Date", None, 120),
		)
	]
