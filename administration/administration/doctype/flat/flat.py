# Copyright (c) 2025, Connect 4 Systems and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Flat(Document):
	def before_insert(self):
		source = _get_source(self)
		_set_source_values(self, source)

	def validate(self):
		if self.get("add_flat_to_contract"):
			self.rent_type = "Contract"
		elif self.get("flat_contract_request"):
			self.rent_type = "Direct Rent"
		previous = self.get_doc_before_save()
		if previous:
			for field in ("flat_contract_request", "add_flat_to_contract", "rent_contract", "rent_contract_type", "accommodation_contract"):
				if (self.get(field) or "") != (previous.get(field) or ""):
					frappe.throw(_("The Flat's source and contract cannot be changed."))
		if self.get("accommodation_contract"):
			self.party = frappe.db.get_value("Accommodation Contract", self.accommodation_contract, "party")
		elif self.get("flat_contract_request"):
			self.party = frappe.db.get_value("Flat Contract Request", self.flat_contract_request, "flat_owner")


def _get_source(flat):
	sources = [
		(doctype, flat.get(field))
		for doctype, field in (
			("Flat Contract Request", "flat_contract_request"),
			("Add Flat to Contract", "add_flat_to_contract"),
		)
		if flat.get(field)
	]
	if len(sources) != 1:
		frappe.throw(_("Create a Flat from a Flat Contract Request or Add Flat to Contract."))
	source = frappe.get_doc(*sources[0])
	source.check_permission("read")
	if source.docstatus != 1:
		frappe.throw(_("Submit the source document before creating a Flat."))
	return source


def _set_source_values(flat, source):
	for target, origin in {
		"project": "project",
		"governorate": "governorate",
		"city": "city",
		"address": "address",
		"no_of_beds": "no_of_beds",
		"rent_start_date": "contract_start_date",
		"rent_end_date": "contract_end_date",
		"rent": "monthly_rent",
		"security_deposit": "deposit",
	}.items():
		flat.set(target, source.get(origin))
	flat.flat_title = flat.get("flat_title") or source.name
	rooms = source.get("no_of_rooms")
	flat.no_of_room = str(int(rooms)) if rooms is not None and float(rooms).is_integer() else str(rooms or "")
	flat.payment_schedule = "Annual" if source.payment_cycle == "Yearly" else source.payment_cycle
	flat.set("flat_contents", [])
	for row in source.get("flat_contents") or []:
		flat.append("flat_contents", {field: row.get(field) for field in ("item_name", "description", "qty", "image")})
	if source.doctype == "Add Flat to Contract":
		flat.rent_type = "Contract"
		if not source.get("accommodation_contract"):
			frappe.throw(_("Select an Accommodation Contract on Add Flat to Contract first."))
		contract = frappe.get_doc("Accommodation Contract", source.accommodation_contract)
		contract.check_permission("read")
		if contract.docstatus == 2:
			frappe.throw(_("The Accommodation Contract is cancelled."))
		flat.accommodation_contract = contract.name
		flat.rent_contract = None
		flat.party = contract.party
		flat.owner_name = source.flat_owner
	else:
		flat.rent_type = "Direct Rent"
		flat.rent_contract_type = "Flat Contract Request"
		flat.rent_contract = source.name
		flat.accommodation_contract = None
		flat.party = source.flat_owner
		flat.owner_name = source.get("flat_owner_name") or (
			frappe.db.get_value("Supplier", source.flat_owner, "supplier_name") if source.flat_owner else ""
		)


@frappe.whitelist()
def make_flat(source_doctype, source_name):
	fields = {"Flat Contract Request": "flat_contract_request", "Add Flat to Contract": "add_flat_to_contract"}
	if source_doctype not in fields:
		frappe.throw(_("Create a Flat from a Flat Contract Request or Add Flat to Contract."))
	flat = frappe.new_doc("Flat")
	flat.check_permission("create")
	flat.set(fields[source_doctype], source_name)
	_set_source_values(flat, _get_source(flat))
	return flat
