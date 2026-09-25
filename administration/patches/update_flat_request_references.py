"""Preserve request links and update site-stored scripts after the schema rename."""

import frappe
from frappe.model.utils.rename_field import rename_field


REPLACEMENTS = (
	("Flat Rent Request", "Flat Request"),
	("FlatRentRequest", "FlatRequest"),
	("flat_rent_request", "flat_request"),
	("flat-rent-request", "flat-request"),
)


def replace_references(value):
	if not isinstance(value, str):
		return value
	for old, new in REPLACEMENTS:
		value = value.replace(old, new)
	return value


def execute():
	for doctype in ("Flat Contract Request", "Flat Contract", "Add Flat to Contract"):
		if frappe.db.has_column(doctype, "flat_rent_request"):
			rename_field(doctype, "flat_rent_request", "flat_request")

	# Link/Dynamic Link metadata, workflows, permissions, children and attachments
	# are handled by Frappe's DocType rename. Text/code references need updating too.
	for doctype, candidates in {
		"Client Script": ("script",),
		"Server Script": ("script",),
		"Print Format": ("html", "format_data"),
		"Report": ("query", "javascript", "json"),
		"Workspace": ("content",),
		"Workspace Shortcut": ("label", "link_to", "url", "stats_filter"),
		"Workspace Link": ("label", "link_to"),
		"Number Card": ("label", "filters_json", "dynamic_filters_json"),
		"Dashboard Chart": ("filters_json", "dynamic_filters_json"),
		"Notification": ("condition", "message"),
		"Web Form": ("route", "client_script"),
		"Custom Field": ("fetch_from", "depends_on", "mandatory_depends_on", "read_only_depends_on"),
		"DocField": ("fetch_from", "depends_on", "mandatory_depends_on", "read_only_depends_on"),
		"Property Setter": ("value",),
	}.items():
		if not frappe.db.exists("DocType", doctype):
			continue
		meta = frappe.get_meta(doctype)
		fields = [field for field in candidates if meta.has_field(field)]
		if not fields:
			continue
		for row in frappe.get_all(
			doctype, fields=["name", *fields],
			or_filters=[[field, "like", f"%{old}%"] for field in fields for old, _new in REPLACEMENTS],
		):
			values = {
				field: replace_references(row.get(field))
				for field in fields if replace_references(row.get(field)) != row.get(field)
			}
			if values:
				frappe.db.set_value(doctype, row.name, values, update_modified=False)
	frappe.clear_cache()
