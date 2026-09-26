"""Flat Request workflow configuration and server-owned approval history."""

import json

import frappe
from frappe import _
from frappe.model.workflow import apply_workflow as core_apply_workflow
from frappe.model.workflow import get_transitions, get_workflow, has_approval_access
from frappe.utils import now_datetime


SUPERVISOR = "Admin supervisor (Accommodation)"
TRANSITIONS = (
	("Draft", "Request", "Pending Project Manger", "Site Admin"),
	("Pending Project Manger", "Approve", "Admin Team leader", "Project Manager"),
	("Pending Project Manger", "Reject", "Draft", "Project Manager"),
	("Admin Team leader", "Approve", "Administration Manager", SUPERVISOR),
	("Admin Team leader", "Reject", "Rejected", SUPERVISOR),
	("Admin Team leader", "Settled", "Settled", SUPERVISOR),
	("Administration Manager", "Approve", "General Director", "Administration Manager"),
	("Administration Manager", "Review", "Admin Team leader", "Administration Manager"),
	("General Director", "Approve", "VP-General", "General Director"),
	("General Director", "Review", "Administration Manager", "General Director"),
	("General Director", "Reject", "Rejected", "General Director"),
	("VP-General", "Approve", "Approved", "VP-General"),
	("VP-General", "Review", "Administration Manager", "VP-General"),
	("VP-General", "Reject", "Rejected", "VP-General"),
)
STATES = (
	("Draft", 0, "Site Admin"),
	("Pending Project Manger", 0, "Project Manager"),
	("Admin Team leader", 0, SUPERVISOR),
	("Administration Manager", 0, "Administration Manager"),
	("General Director", 0, "General Director"),
	("VP-General", 0, "VP-General"),
	("Approved", 1, "Site Admin"),
	("Settled", 1, SUPERVISOR),
	("Rejected", 0, "Site Admin"),
	("Cancelled", 2, "System Manager"),  # Preserve previously cancelled requests.
)
HISTORY_FIELDS = (
	"name", "status", "from_status", "action", "approved_by_role",
	"approved_by_user", "user_name", "action_date", "note", "attachments",
)
_APPROVAL_TOKEN = object()


@frappe.whitelist()
def apply_workflow(doc, action):
	payload = frappe.parse_json(doc) if isinstance(doc, str) else doc
	if payload.get("doctype") not in ("Flat Request", "Add Flat to Contract", "Flat Contract", "Rent Termination Request", "Flat Termination", "Private Vehicle Contract Request", "Private Vehicle Contract", "Service Vehicle Contract"):
		return core_apply_workflow(doc, action)
	note = payload.get("__approval_note") or ""
	if not isinstance(note, str):
		frappe.throw(_("Note must be text."))
	current = frappe.get_doc(payload["doctype"], payload.get("name"), for_update=True)
	current.check_permission("read")
	workflow = get_workflow(payload["doctype"])
	state_field = workflow.workflow_state_field
	if payload.get(state_field) != current.get(state_field) or str(payload.get("modified")) != str(current.modified):
		frappe.throw(_("This request has changed. Reload it before taking a workflow action."))
	transition = next((row for row in get_transitions(current, workflow) if row.action == action), None)
	if not transition or not has_approval_access(frappe.session.user, current, transition):
		frappe.throw(_("You are not allowed to take this workflow action."), frappe.PermissionError)
	if payload["doctype"] == "Flat Contract":
		from administration.flat_contract_workflow import validate_request
		validate_request(current, action)
	attachments = get_approval_attachments(payload.get("__approval_attachments"), current.name, payload["doctype"])
	previous_context = frappe.flags.get("flat_request_approval")
	frappe.flags.flat_request_approval = {
		"token": _APPROVAL_TOKEN, "name": current.name, "doctype": payload["doctype"],
		"from_status": current.get(state_field), "status": transition.next_state,
		"action": action, "approved_by_role": transition.allowed, "note": note.strip(),
		"attachments": attachments,
	}
	try:
		# Frappe still validates the workflow, permissions and submission lifecycle.
		return core_apply_workflow(current.as_dict(), action)
	finally:
		frappe.flags.flat_request_approval = previous_context


def get_approval_attachments(file_names, request_name, doctype="Flat Request"):
	if file_names is None:
		return ""
	if not isinstance(file_names, list) or any(not isinstance(name, str) or not name for name in file_names):
		frappe.throw(_("Invalid approval attachments."))
	if file_names and doctype == "Flat Contract":
		from administration.flat_contract_attachments import require_legal_role
		require_legal_role()
	attachments = []
	for name in dict.fromkeys(file_names):
		file = frappe.get_doc("File", name)
		file.check_permission("read")
		if file.attached_to_doctype != doctype or file.attached_to_name != request_name:
			frappe.throw(_("Approval attachments must belong to this document."))
		attachments.append({"name": file.name, "file_name": file.file_name})
	return json.dumps(attachments, ensure_ascii=False) if attachments else ""


def validate_approval_history(doc):
	previous = doc.get_doc_before_save()
	rows = doc.get("document_approval") or []
	old_rows = (previous.get("document_approval") or []) if previous else []
	def signature(items):
		return [tuple(str(row.get(field) or "") for field in HISTORY_FIELDS) for row in items]
	if signature(rows) != signature(old_rows):
		frappe.throw(_("Document Approval history cannot be edited manually."))
	old_state = previous.get("workflow_state") if previous else "Draft"
	new_state = doc.get("workflow_state") or "Draft"
	if new_state == old_state:
		return
	context = frappe.flags.get("flat_request_approval") or {}
	if (
		context.get("token") is not _APPROVAL_TOKEN
		or context.get("name") != doc.name
		or context.get("doctype", "Flat Request") != (doc.get("doctype") or "Flat Request")
		or context.get("from_status") != old_state
		or context.get("status") != new_state
	):
		frappe.throw(_("Use a workflow action to change the request status."))
	doc.append("document_approval", {
		field: context[field]
		for field in ("status", "from_status", "action", "approved_by_role", "note")
	} | {
		"approved_by_user": frappe.session.user,
		"user_name": frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user,
		"action_date": now_datetime(),
		"attachments": context.get("attachments", ""),
	})


def require_workflow_submission(doc):
	context = frappe.flags.get("flat_request_approval") or {}
	if (
		context.get("token") is not _APPROVAL_TOKEN
		or context.get("name") != doc.name
		or context.get("doctype", "Flat Request") != (doc.get("doctype") or "Flat Request")
		or context.get("status") != doc.get("workflow_state")
		or doc.get("workflow_state") not in (("Approved", "Settled") if doc.get("doctype") in (None, "Flat Request") else ("Approved",))
	):
		frappe.throw(_("Submit this request through an approval workflow action."))


def setup_workflow(doctype="Flat Request", states=STATES, transitions=TRANSITIONS, creator_role="Site Admin"):
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
	from frappe.permissions import add_permission, setup_custom_perms, update_permission_property

	roles = {role for _state, _status, role in states} | {"System Manager"}
	for role in sorted(roles):
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)
	for state, _status, _role in states:
		if not frappe.db.exists("Workflow State", state):
			frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": state}).insert(ignore_permissions=True)
	for action in sorted({row[1] for row in transitions}):
		if not frappe.db.exists("Workflow Action Master", action):
			frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": action}).insert(ignore_permissions=True)
	# An existing site may already have a workflow_state Custom Field. Reuse it.
	if not frappe.get_meta(doctype).has_field("workflow_state"):
		create_custom_fields({doctype: [{
			"fieldname": "workflow_state", "label": "Status", "fieldtype": "Link",
			"options": "Workflow State", "read_only": 1, "no_copy": 1,
			"allow_on_submit": 1, "in_list_view": 1, "insert_after": "request_details_tab",
		}]})
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter
	for prop, value, kind in (("hidden", 0, "Check"), ("read_only", 1, "Check"), ("label", "Status", "Data")):
		make_property_setter(doctype, "workflow_state", prop, value, kind)
	setup_custom_perms(doctype)
	for role in sorted(roles):
		if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0, "if_owner": 0}):
			add_permission(doctype, role)
		for permission in ("read", "write"):
			update_permission_property(doctype, role, 0, permission, 1)
		if role in (creator_role, "System Manager"):
			update_permission_property(doctype, role, 0, "create", 1)
		if role in (SUPERVISOR, "VP-General", "System Manager"):
			update_permission_property(doctype, role, 0, "submit", 1)

	valid_status = {state: status for state, status, _role in states}
	for request in frappe.get_all(doctype, fields=["name", "workflow_state", "docstatus"]):
		if valid_status.get(request.workflow_state) != request.docstatus:
			frappe.db.set_value(doctype, request.name, "workflow_state",
				{0: "Draft", 1: "Approved", 2: "Cancelled"}[request.docstatus], update_modified=False)
	name = f"{doctype} Approval"
	workflow = frappe.get_doc("Workflow", name) if frappe.db.exists("Workflow", name) else frappe.new_doc("Workflow")
	workflow.update({
		"workflow_name": name, "document_type": doctype, "is_active": 1,
		"workflow_state_field": "workflow_state", "send_email_alert": 0,
		"states": [{"state": state, "doc_status": str(status), "allow_edit": role} for state, status, role in states],
		"transitions": [{"state": state, "action": action, "next_state": next_state, "allowed": role,
			"allow_self_approval": int(action == "Request")} for state, action, next_state, role in transitions],
	})
	workflow.save(ignore_permissions=True)
	frappe.clear_cache(doctype=doctype)
