"""Keep the approval audit visible after site customizations are synchronized."""

import json

import frappe


APPROVAL_FIELDS = ("document_approval_tab", "document_approval_help", "document_approval")


def approval_field_order(fields):
	"""Preserve other fields while keeping the approval table inside its own tab."""
	managed = {"request_details_tab", *APPROVAL_FIELDS}
	return ["request_details_tab", *dict.fromkeys(
		field for field in fields if field not in managed
	), *APPROVAL_FIELDS]


def ensure_approval_layout(doctype="Flat Request", schema="flat_request"):
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	# Force synchronization even if a site's DocType timestamp is newer than the
	# shipped schema. Child first so the table's options are available on reload.
	frappe.reload_doc("administration", "doctype", "flat_request_approval", force=True)
	frappe.reload_doc("administration", "doctype", schema, force=True)
	meta = frappe.get_meta(doctype, cached=False)
	order = approval_field_order([field.fieldname for field in meta.fields])
	make_property_setter(doctype, None, "field_order", json.dumps(order), "Data", for_doctype=True)
	for field in ("request_details_tab", *APPROVAL_FIELDS):
		for prop, value, kind in (("hidden", 0, "Check"), ("depends_on", "", "Data"), ("permlevel", 0, "Int")):
			make_property_setter(doctype, field, prop, value, kind)
	make_property_setter(doctype, "document_approval", "read_only", 1, "Check")
	frappe.clear_cache(doctype=doctype)
	frappe.clear_cache(doctype="Flat Request Approval")


def ensure_contract_approval_layout():
	ensure_approval_layout("Add Flat to Contract", "add_flat_to_contract")
