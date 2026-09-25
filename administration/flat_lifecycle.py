"""Transactional renewal, termination and rental coverage for an existing Flat."""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, today


TERMINATIONS = {"Rent Termination Request": "Direct Rent", "Flat Termination": "Contract"}
CONTRACTS = {"Direct Rent": "Flat Contract", "Contract": "Add Flat to Contract"}
ROOTS = ("Flat Request", "Add Flat to Contract", *TERMINATIONS)
_FLAT_UPDATE = object()


def row_reference(row):
	if row.get("add_flat_to_contract"):
		return "Add Flat to Contract", row.get("add_flat_to_contract")
	return row.get("rent_contract_type") or "Flat Contract", row.get("rent_contract")


def approved_rows(flat):
	"""Use actual approval/termination state, not just a historical table entry."""
	rows = []
	for row in flat.get("rent_contracts") or []:
		doctype, name = row_reference(row)
		if doctype not in CONTRACTS.values() or not name:
			continue
		state = frappe.db.get_value(doctype, name, ["docstatus", "workflow_state", "contract_status"], as_dict=True, for_update=True)
		if state and state.docstatus == 1 and state.workflow_state == "Approved" and state.contract_status != "Terminated":
			rows.append(row)
	return rows


def latest_row(rows):
	if not rows:
		return None
	# Dates, not grid ordering, determine which approved agreement is latest.
	return max(rows, key=lambda row: (
		getdate(row.get("rent_start_date")) if row.get("rent_start_date") else getdate("0001-01-01"),
		getdate(row.get("rent_end_date")) if row.get("rent_end_date") else getdate("0001-01-01"),
		str(row_reference(row)),
	))


def coverage_status(rows, current_status="Active", date=None):
	date = getdate(date or today())
	ends = [getdate(row.get("rent_end_date")) for row in rows if row.get("rent_end_date")]
	last_end = max(ends) if ends else None
	if current_status == "Inactive":
		return "Inactive", last_end
	if any(row.get("rent_end_date") and getdate(row.get("rent_end_date")) >= date
		and (not row.get("rent_start_date") or getdate(row.get("rent_start_date")) <= date) for row in rows):
		return "Active", last_end
	# Missing legacy dates cannot safely be interpreted as an expired agreement.
	return ("Expired" if ends else current_status or "Active"), last_end


def update_flat_status(flat):
	status, last_end = coverage_status(approved_rows(flat), flat.get("flat_status"))
	if (flat.get("flat_status"), flat.get("last_rent_end_date")) != (status, last_end):
		flat.db_set({"flat_status": status, "last_rent_end_date": last_end}, update_modified=False)


def expire_flats():
	# Lock and re-read each Flat, so renewal/termination cannot race the scheduler.
	for name in frappe.get_all("Flat", filters={"docstatus": 1}, pluck="name"):
		flat = frappe.get_doc("Flat", name, for_update=True)
		update_flat_status(flat)


def lock_flat(name):
	flat = frappe.get_doc("Flat", name, for_update=True)
	if flat.docstatus != 1:
		frappe.throw(_("Renewal and termination require a submitted Flat."))
	return flat


def latest_for_action(flat):
	row = latest_row(approved_rows(flat))
	if not row:
		frappe.throw(_("This Flat has no approved, non-terminated rent contract."))
	if row_reference(row)[0] != CONTRACTS.get(flat.rent_type):
		frappe.throw(_("The latest contract does not match the Flat's Rent Type."))
	return row


def root_reference(doc):
	if doc.doctype in ROOTS:
		return doc.doctype, doc.name
	if doc.doctype in ("Flat Contract Request", "Flat Contract"):
		return "Flat Request", doc.get("flat_request")
	return None, None


def is_lifecycle(doc):
	return doc.doctype in TERMINATIONS or doc.get("type") == "Renew"


def ensure_pending(flat, root, allow_empty=False):
	pending = (flat.get("pending_document_type"), flat.get("pending_document"))
	if pending[1] and pending != root:
		frappe.throw(_("This Flat already has a pending renewal or termination: {0} {1}.").format(*pending))
	if not pending[1] and not allow_empty:
		frappe.throw(_("This renewal or termination process is closed. Start a new action from the Flat."))


def reference_field(doc):
	return "last_add_flat_to_contract" if doc.doctype in ("Add Flat to Contract", "Flat Termination") else "last_rent_contract"


def validate_latest(doc, flat):
	row = latest_for_action(flat)
	if doc.get(reference_field(doc)) != row_reference(row)[1]:
		frappe.throw(_("The Flat's latest contract has changed. Start a new request from the Flat."))
	return row


def inherit_renewal(doc):
	"""Never trust client-side mapping of renewal identity or preceding contract."""
	parent_type, parent_name = None, None
	if doc.doctype == "Flat Contract Request" and doc.get("flat_request"):
		parent_type, parent_name = "Flat Request", doc.flat_request
	elif doc.doctype == "Flat Contract" and doc.get("flat_contract_request"):
		parent_type, parent_name = "Flat Contract Request", doc.flat_contract_request
	if not parent_name:
		if doc.get("type") == "Renew" and doc.doctype in ("Flat Contract Request", "Flat Contract"):
			frappe.throw(_("Renewals must follow Flat Request, Flat Contract Request, then Flat Contract."))
		return
	parent = frappe.get_doc(parent_type, parent_name)
	parent.check_permission("read")
	if parent.get("type") != "Renew":
		if doc.get("type") == "Renew":
			frappe.throw(_("A renewal contract must originate from a renewal request."))
		return
	if parent.docstatus != 1 or (parent_type == "Flat Request" and parent.workflow_state != "Approved"):
		frappe.throw(_("Approve the preceding renewal request first."))
	for field in ("type", "flat", "last_rent_contract"):
		doc.set(field, parent.get(field))
	if parent_type == "Flat Contract Request":
		doc.flat_request = parent.flat_request
	# There may only be one live successor at each stage of the renewal chain.
	link = "flat_request" if doc.doctype == "Flat Contract Request" else "flat_contract_request"
	other = frappe.db.get_value(doc.doctype, {link: parent_name, "docstatus": ["!=", 2], "name": ["!=", doc.name or ""]}, "name", for_update=True)
	if other:
		frappe.throw(_("A document already exists for this renewal stage: {0}").format(other))


def validate_document(doc, method=None):
	previous = doc.get_doc_before_save()
	if not previous:
		if doc.get("lifecycle_applied") or doc.get("contract_status") not in (None, "", "Active"):
			frappe.throw(_("Lifecycle status cannot be set when creating a document."))
		inherit_renewal(doc)
	else:
		for field in ("type", "flat", "last_rent_contract", "last_add_flat_to_contract", "lifecycle_applied", "contract_status"):
			if (doc.get(field) or "") != (previous.get(field) or ""):
				frappe.throw(_("Renewal links and lifecycle status cannot be changed manually."))
		if is_lifecycle(doc):
			for field in ("flat_request", "flat_contract_request"):
				if (doc.get(field) or "") != (previous.get(field) or ""):
					frappe.throw(_("The renewal request chain cannot be changed."))
	if not is_lifecycle(doc):
		if doc.get("flat"):
			frappe.throw(_("A Flat link is only used for Renew documents."))
		return
	if not doc.get("flat"):
		frappe.throw(_("Select a Flat using its Renew or Terminate action."))
	if doc.get("lifecycle_applied"):
		return
	flat = lock_flat(doc.flat)
	flat.check_permission("read")
	if doc.doctype not in ROOTS:
		inherit_renewal(doc)
	if not previous and doc.meta.has_field("flat_title") and not doc.get("flat_title"):
		doc.flat_title = flat.flat_title
	if flat.get("flat_status") == "Inactive":
		frappe.throw(_("Inactive Flats cannot be renewed or terminated again."))
	expected = TERMINATIONS.get(doc.doctype) or ("Contract" if doc.doctype == "Add Flat to Contract" else "Direct Rent")
	if flat.rent_type != expected:
		frappe.throw(_("This document does not match the Flat's Rent Type."))
	root = root_reference(doc)
	ensure_pending(flat, root, allow_empty=not previous and doc.doctype in ROOTS)
	latest = validate_latest(doc, flat)
	if doc.doctype in ("Flat Contract Request", "Flat Contract") and not doc.get("flat_request"):
		frappe.throw(_("Renewals must follow Flat Request, Flat Contract Request, then Flat Contract."))
	if doc.doctype in CONTRACTS.values():
		validate_dates(doc)
		if latest.get("rent_start_date") and getdate(doc.contract_start_date) <= getdate(latest.get("rent_start_date")):
			frappe.throw(_("A renewal must start after the previous contract's start date."))


def validate_dates(doc):
	if not doc.get("contract_start_date") or not doc.get("contract_end_date"):
		frappe.throw(_("Set both contract dates for the renewal."))
	if getdate(doc.contract_end_date) < getdate(doc.contract_start_date):
		frappe.throw(_("Rent End Date cannot be before Rent Start Date."))


def reserve_request(doc, method=None):
	if is_lifecycle(doc) and doc.doctype in ROOTS:
		flat = lock_flat(doc.flat)
		ensure_pending(flat, root_reference(doc), allow_empty=True)
		flat.db_set({"pending_document_type": doc.doctype, "pending_document": doc.name}, update_modified=False)


def release_request(doc):
	flat = lock_flat(doc.flat)
	if (flat.get("pending_document_type"), flat.get("pending_document")) == root_reference(doc):
		flat.db_set({"pending_document_type": None, "pending_document": None}, update_modified=False)


def workflow_updated(doc, method=None):
	if is_lifecycle(doc) and doc.get("workflow_state") in ("Rejected", "Settled"):
		release_request(doc)


def prevent_cancel_or_delete(doc, method=None):
	if not is_lifecycle(doc):
		return
	if doc.get("lifecycle_applied"):
		frappe.throw(_("Completed renewal and termination documents cannot be cancelled or deleted."))
	# Do not close a root while an approved successor is still processing.
	for doctype, field in (("Flat Contract Request", "flat_request"), ("Flat Contract", "flat_contract_request")):
		parent_type = "Flat Request" if field == "flat_request" else "Flat Contract Request"
		if doc.doctype == parent_type and frappe.db.exists(doctype, {field: doc.name, "docstatus": ["!=", 2]}):
			frappe.throw(_("Cancel the downstream renewal document first."))
	if doc.get("flat"):
		release_request(doc)


def apply_renewal(doc, method=None):
	if doc.get("type") != "Renew" or doc.get("lifecycle_applied"):
		return
	if doc.docstatus != 1 or doc.workflow_state != "Approved":
		frappe.throw(_("Only final approval can apply a renewal."))
	flat = lock_flat(doc.flat)
	ensure_pending(flat, root_reference(doc))
	validate_latest(doc, flat)
	validate_dates(doc)
	if flat.get("flat_status") == "Inactive":
		frappe.throw(_("Inactive Flats cannot be renewed."))
	if any(row_reference(row) == (doc.doctype, doc.name) for row in flat.rent_contracts):
		frappe.throw(_("This renewal has already been recorded on the Flat."))
	from administration.administration.doctype.flat.flat import _set_source_values
	old_rows = [row.as_dict() for row in flat.rent_contracts]
	original_title = flat.flat_title
	original_request = flat.get("flat_contract_request")
	# Reuse value mapping, but retain the Flat's identity, origin and all history.
	_set_source_values(flat, doc)
	if doc.doctype != "Flat Contract":
		flat.flat_title = original_title
	new_row = flat.rent_contracts[0].as_dict()
	flat.set("rent_contracts", old_rows)
	flat.append("rent_contracts", {key: new_row.get(key) for key in (
		"rent_contract_type", "rent_contract", "add_flat_to_contract", "rent_start_date", "rent_end_date")})
	flat.flat_contract_request = original_request
	flat.flat_status, flat.last_rent_end_date = coverage_status(approved_rows(flat), flat.get("flat_status"))
	flat.pending_document_type = None
	flat.pending_document = None
	flat.flags.lifecycle_update = _FLAT_UPDATE
	flat.flags.ignore_validate_update_after_submit = True
	try:
		flat.save(ignore_permissions=True)
	finally:
		flat.flags.pop("lifecycle_update", None)
		flat.flags.pop("ignore_validate_update_after_submit", None)
	doc.db_set({"created_flat": flat.name, "flat_title": flat.flat_title, "lifecycle_applied": 1})
	if doc.doctype == "Flat Contract":
		for doctype, name in (("Flat Request", doc.flat_request), ("Flat Contract Request", doc.flat_contract_request)):
			frappe.db.set_value(doctype, name, "lifecycle_applied", 1)


def apply_termination(doc, method=None):
	if doc.get("lifecycle_applied"):
		return
	flat = lock_flat(doc.flat)
	ensure_pending(flat, root_reference(doc))
	if doc.docstatus != 1 or doc.workflow_state != "Approved":
		frappe.throw(_("Only final approval can apply a termination."))
	row = validate_latest(doc, flat)
	doctype, name = row_reference(row)
	frappe.db.set_value(doctype, name, "contract_status", "Terminated")
	flat.db_set({"flat_status": "Inactive", "pending_document_type": None, "pending_document": None})
	doc.db_set("lifecycle_applied", 1)


def validate_flat_update(doc, method=None):
	if doc.flags.get("lifecycle_update") is _FLAT_UPDATE:
		return
	previous = doc.get_doc_before_save()
	if previous:
		for field in ("flat_status", "last_rent_end_date", "pending_document_type", "pending_document"):
			if (doc.get(field) or "") != (previous.get(field) or ""):
				frappe.throw(_("Flat status is maintained by approval actions and rental coverage."))


def snapshot_flat(target, flat, source):
	"""Copy typed values and child data, never source identities or audit rows."""
	excluded = {"name", "amended_from", "naming_series", "workflow_state", "document_approval", "lifecycle_applied",
		"created_flat", "contract_status", "type", "flat", "last_rent_contract", "last_add_flat_to_contract"}
	for field in target.meta.fields:
		key = field.fieldname
		if key in excluded or field.fieldtype in ("Section Break", "Column Break", "Tab Break", "HTML", "Button"):
			continue
		value = flat.get(key) if flat.meta.has_field(key) else source.get(key)
		if value is None:
			continue
		if field.fieldtype == "Table":
			target.set(key, [])
			for row in value:
				target.append(key, {f.fieldname: row.get(f.fieldname) for f in frappe.get_meta(field.options).fields})
		else:
			target.set(key, value)
	for key, value in {"monthly_rent": flat.rent, "deposit": flat.security_deposit,
		"no_of_rooms": flat.no_of_room, "flat_title": flat.flat_title,
		"payment_cycle": "Yearly" if flat.payment_schedule == "Annual" else flat.payment_schedule}.items():
		if target.meta.has_field(key):
			target.set(key, value)
	target.date = today()


@frappe.whitelist()
def start_action(flat_name, action):
	if action not in ("Renew", "Terminate"):
		frappe.throw(_("Invalid Flat action."))
	flat = lock_flat(flat_name)
	flat.check_permission("read")
	if flat.get("flat_status") == "Inactive":
		frappe.throw(_("Inactive Flats cannot be renewed or terminated again."))
	ensure_pending(flat, (None, None), allow_empty=True)
	row = latest_for_action(flat)
	direct = flat.rent_type == "Direct Rent"
	doctype = ("Flat Request" if direct else "Add Flat to Contract") if action == "Renew" else (
		"Rent Termination Request" if direct else "Flat Termination")
	doc = frappe.new_doc(doctype)
	doc.check_permission("create")
	if doctype == "Rent Termination Request" and "Legal User" not in frappe.get_roles():
		frappe.throw(_("Only Legal User can create a Rent Termination Request."), frappe.PermissionError)
	source = frappe.get_doc(*row_reference(row))
	source.check_permission("read")
	snapshot_flat(doc, flat, source)
	doc.flat = flat.name
	doc.set(reference_field(doc), source.name)
	if action == "Renew":
		doc.type = "Renew"
		if doctype == "Flat Request":
			doc.no_of_employees = source.get("no_of_employees") or flat.no_of_beds or 1
			for field in ("custom_no_of_rooms", "custom_no_of_beds"):
				if doc.meta.has_field(field):
					doc.set(field, flat.no_of_room if field.endswith("rooms") else flat.no_of_beds)
		else:
			doc.contract_start_date = add_days(row.get("rent_end_date") or today(), 1)
			duration = (getdate(row.get("rent_end_date")) - getdate(row.get("rent_start_date"))).days if row.get("rent_start_date") and row.get("rent_end_date") else 364
			doc.contract_end_date = add_days(doc.contract_start_date, max(duration, 0))
	# Save a draft immediately to reserve the Flat even before missing business
	# fields are filled. Subsequent saves and workflow submission enforce them.
	doc.insert(ignore_mandatory=True)
	return {"doctype": doc.doctype, "name": doc.name}


class TerminationDocument(Document):
	def before_insert(self):
		if not self.get("flat"):
			frappe.throw(_("Create this request using Terminate on a Flat."))
		if self.doctype == "Rent Termination Request":
			from administration.flat_contract_workflow import require_legal_creator
			require_legal_creator()
		flat = lock_flat(self.flat)
		flat.check_permission("read")
		row = latest_for_action(flat)
		source = frappe.get_doc(*row_reference(row))
		source.check_permission("read")
		snapshot_flat(self, flat, source)
		self.set(reference_field(self), source.name)

	def validate(self):
		from administration.flat_request_workflow import validate_approval_history
		validate_approval_history(self)
		validate_document(self)
		previous = self.get_doc_before_save()
		if previous:
			for field in self.meta.fields:
				if field.fieldname in ("workflow_state", "document_approval"):
					continue
				if field.read_only and field.fieldtype == "Table":
					keys = [f.fieldname for f in frappe.get_meta(field.options).fields]
					def values(doc):
						return [tuple(row.get(key) for key in keys) for row in doc.get(field.fieldname) or []]
					if values(self) != values(previous):
						frappe.throw(_("Termination snapshot tables cannot be changed manually."))
				if field.read_only and field.fieldtype not in ("Table", "Section Break", "Tab Break", "HTML", "Column Break"):
					if (self.get(field.fieldname) or "") != (previous.get(field.fieldname) or ""):
						frappe.throw(_("Termination reference information cannot be changed manually."))

	def before_update_after_submit(self):
		self.validate()

	def after_insert(self):
		reserve_request(self)

	def before_submit(self):
		from administration.flat_request_workflow import require_workflow_submission
		require_workflow_submission(self)

	def on_submit(self):
		apply_termination(self)

	def on_update(self):
		workflow_updated(self)

	def before_cancel(self):
		prevent_cancel_or_delete(self)

	def on_trash(self):
		prevent_cancel_or_delete(self)
