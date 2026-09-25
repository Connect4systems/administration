"""Legal-role controls for Flat Contract attachment changes."""

import frappe
from frappe import _


LEGAL_ROLES = {"Legal User", "Legal Manager"}


def require_legal_role():
	if not LEGAL_ROLES.intersection(frappe.get_roles()):
		frappe.throw(_("Only Legal User or Legal Manager can add, replace or clear Flat Contract attachments."), frappe.PermissionError)


def validate_contract_attachments(doc, method=None):
	previous = doc.get_doc_before_save()
	for field in doc.meta.fields:
		if field.fieldtype in ("Attach", "Attach Image"):
			old = previous.get(field.fieldname) if previous else None
			if (doc.get(field.fieldname) or "") != (old or ""):
				require_legal_role()
				return


def validate_file_change(doc):
	previous = doc.get_doc_before_save()
	if doc.get("attached_to_doctype") == "Flat Contract" or (
		previous and previous.get("attached_to_doctype") == "Flat Contract"
	):
		require_legal_role()


def setup_legal_roles():
	from frappe.permissions import add_permission, setup_custom_perms, update_permission_property
	for role in sorted(LEGAL_ROLES):
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)
	setup_custom_perms("Flat Contract")
	for role in sorted(LEGAL_ROLES):
		if not frappe.db.exists("Custom DocPerm", {"parent": "Flat Contract", "role": role, "permlevel": 0, "if_owner": 0}):
			add_permission("Flat Contract", role)
		for permission in ("read", "write"):
			update_permission_property("Flat Contract", role, 0, permission, 1)
	frappe.clear_cache(doctype="Flat Contract")
