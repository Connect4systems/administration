"""Legal review followed by the accommodation approval chain."""

import frappe
from frappe import _

from administration.add_flat_to_contract_workflow import TRANSITIONS as CONTRACT_TRANSITIONS
from administration.flat_request_workflow import SUPERVISOR, setup_workflow as setup_approval_workflow


TRANSITIONS = (
	("Draft", "Request", "Legal Manager", "Legal User"),
	("Legal User", "Request", "Legal Manager", "Legal User"),
	("Legal Manager", "Review", "Legal User", "Legal Manager"),
	("Legal Manager", "Approve", "Admin Team leader", "Legal Manager"),
	*CONTRACT_TRANSITIONS[1:],
)
STATES = (
	("Draft", 0, "Legal User"),
	("Legal User", 0, "Legal User"),
	("Legal Manager", 0, "Legal Manager"),
	("Admin Team leader", 0, SUPERVISOR),
	("Administration Manager", 0, "Administration Manager"),
	("General Director", 0, "General Director"),
	("VP-General", 0, "VP-General"),
	("Approved", 1, SUPERVISOR),
	("Rejected", 0, "Legal User"),
	("Cancelled", 2, "System Manager"),
)


def require_legal_creator():
	if "Legal User" not in frappe.get_roles():
		frappe.throw(_("Only Legal User can create a Flat Contract."), frappe.PermissionError)


def validate_request(doc, action):
	if action == "Request" and not doc.get("attach_contract"):
		frappe.throw(_("Attach Contract is required before requesting approval."))


def setup_workflow():
	setup_approval_workflow("Flat Contract", STATES, TRANSITIONS, creator_role="Legal User")
	# Custom permissions override shipped DocPerms on existing installations.
	for permission in frappe.get_all("Custom DocPerm", filters={"parent": "Flat Contract"}, fields=["name", "role", "permlevel"]):
		frappe.db.set_value("Custom DocPerm", permission.name, "create",
			int(permission.role == "Legal User" and permission.permlevel == 0))
	frappe.clear_cache(doctype="Flat Contract")
