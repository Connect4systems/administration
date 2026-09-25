"""Rename before schema sync so the existing request table is preserved."""

import frappe
from frappe import _


def execute():
	old, new = "Flat Rent Request", "Flat Request"
	if frappe.db.exists("DocType", old):
		if frappe.db.exists("DocType", new):
			frappe.throw(_("Both Flat Rent Request and Flat Request exist. Resolve the duplicate DocTypes before migrating."))
		# The patch runner sets in_patch, preventing filesystem renames/developer exports.
		frappe.rename_doc("DocType", old, new, force=True, show_alert=False, rebuild_search=False)
	if not frappe.db.exists("DocType", new):
		return
	# Customization sync uses exported record names when updating existing fields.
	for doctype, parent_field in (("Custom Field", "dt"), ("Property Setter", "doc_type")):
		for name in frappe.get_all(doctype, filters={parent_field: new}, pluck="name"):
			if name.startswith(old + "-"):
				frappe.rename_doc(
					doctype, name, new + name[len(old):],
					force=True, show_alert=False, rebuild_search=False,
				)
