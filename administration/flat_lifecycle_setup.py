"""Repeatable schema layout and one-time lifecycle workflow installation."""

import frappe

from administration.flat_request_layout import ensure_approval_layout


def ensure_layouts():
	for doctype, schema in (("Rent Termination Request", "rent_termination_request"), ("Flat Termination", "flat_termination")):
		ensure_approval_layout(doctype, schema)


def allow_submitted_flat_contents():
	"""Keep the contents table editable on existing submitted Flats."""
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	for schema in ("flat_contents", "flat"):
		frappe.reload_doc("administration", "doctype", schema, force=True)
	for doctype, fields in (
		("Flat", ("flat_contents",)),
		("Flat Contents", ("item_name", "description", "qty", "image")),
	):
		for field in fields:
			make_property_setter(doctype, field, "allow_on_submit", 1, "Check")
		frappe.clear_cache(doctype=doctype)


def install():
	from administration.flat_contract_workflow import STATES as legal_states, TRANSITIONS as legal_transitions
	from administration.add_flat_to_contract_workflow import STATES, TRANSITIONS
	from administration.flat_request_workflow import SUPERVISOR, setup_workflow
	setup_workflow("Rent Termination Request", legal_states, legal_transitions, creator_role="Legal User")
	setup_workflow("Flat Termination", STATES, TRANSITIONS, creator_role=SUPERVISOR)
	from frappe.permissions import add_permission, setup_custom_perms, update_permission_property
	from administration.flat_request_workflow import STATES as request_states
	# Participants need to inspect the Flat; only approved server actions update it.
	read_roles = {role for _state, _status, role in (*request_states, *legal_states, *STATES)}
	for doctype, roles in (("Flat", read_roles), ("Flat Contract", {"Site Admin"})):
		setup_custom_perms(doctype)
		for role in roles:
			if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0, "if_owner": 0}):
				add_permission(doctype, role)
			update_permission_property(doctype, role, 0, "read", 1)
		frappe.clear_cache(doctype=doctype)
	# Enforce the same creation-role boundary as Flat Contract.
	for row in frappe.get_all("Custom DocPerm", filters={"parent": "Rent Termination Request"}, fields=["name", "role", "permlevel"]):
		frappe.db.set_value("Custom DocPerm", row.name, "create", int(row.role == "Legal User" and row.permlevel == 0))
	for doctype in ("Flat Request", "Flat Contract Request", "Flat Contract", "Add Flat to Contract"):
		frappe.db.set_value(doctype, {"type": ["is", "not set"]}, "type", "New Flat", update_modified=False)
	for doctype in ("Flat Contract", "Add Flat to Contract"):
		frappe.db.set_value(doctype, {"contract_status": ["is", "not set"]}, "contract_status", "Active", update_modified=False)
	frappe.db.set_value("Flat", {"flat_status": ["is", "not set"]}, "flat_status", "Active", update_modified=False)
	repair_termination_permissions()
	ensure_layouts()
	from administration.flat_lifecycle import expire_flats
	expire_flats()


def repair_termination_permissions():
	"""Grant draft deletion without replacing the site's workflow."""
	from frappe.permissions import add_permission, setup_custom_perms, update_permission_property
	doctype = "Rent Termination Request"
	setup_custom_perms(doctype)
	for role in ("Legal User", "Legal Manager"):
		if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0, "if_owner": 0}):
			add_permission(doctype, role)
		update_permission_property(doctype, role, 0, "delete", 1)
	frappe.clear_cache(doctype=doctype)
	# System Managers must be able to remove an abandoned draft termination
	# so on_trash releases the Flat's pending lifecycle reservation.
	doctype = "Flat Termination"
	setup_custom_perms(doctype)
	role = "System Manager"
	if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0, "if_owner": 0}):
		add_permission(doctype, role)
	for permission in ("read", "delete"):
		update_permission_property(doctype, role, 0, permission, 1)
	frappe.clear_cache(doctype=doctype)
