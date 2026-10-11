"""Reserve a Flat Title across its request, contract and Flat documents."""

import frappe
from frappe import _


DOCTYPES = ("Flat Contract Request", "Flat Contract", "Add Flat to Contract", "Flat")


def flat_identity(doc, seen=None):
	"""Linked stages and renewals represent the same flat, not duplicate titles."""
	key = (doc.doctype, doc.name)
	seen = set() if seen is None else seen
	if key in seen:
		frappe.throw(_("Circular Flat source references must be corrected."))
	seen.add(key)
	parent = None
	if doc.doctype == "Flat":
		if doc.get("flat_contract"):
			parent = ("Flat Contract", doc.flat_contract)
		elif doc.get("add_flat_to_contract"):
			parent = ("Add Flat to Contract", doc.add_flat_to_contract)
		elif doc.get("flat_contract_request"):
			parent = ("Flat Contract Request", doc.flat_contract_request)
	elif doc.get("type") == "Renew" and doc.get("flat"):
		parent = ("Flat", doc.flat)
	elif doc.doctype == "Flat Contract" and doc.get("flat_contract_request"):
		parent = ("Flat Contract Request", doc.flat_contract_request)
	if parent:
		return flat_identity(frappe.get_doc(*parent), seen)
	if doc.doctype in ("Flat Contract Request", "Flat Contract") and doc.get("flat_request"):
		return "Flat Request", doc.flat_request
	return key


def validate_flat_title(doc, method=None):
	title = (doc.get("flat_title") or "").strip()
	if not title:
		return
	doc.flat_title = title
	# Lock a stable row until transaction end, including when no matching title
	# exists yet. Two concurrent requests cannot both reserve the same title.
	frappe.db.sql("select name from `tabDocType` where name = %s for update", "Flat")
	identity = flat_identity(doc)
	for doctype in DOCTYPES:
		for name in frappe.get_all(doctype, filters={"flat_title": title}, pluck="name"):
			if (doctype, name) == (doc.doctype, doc.name):
				continue
			if flat_identity(frappe.get_doc(doctype, name)) != identity:
				frappe.throw(_("Flat Title {0} is already used by {1} {2}. Choose a unique Flat Title.").format(
					title, doctype, name))
