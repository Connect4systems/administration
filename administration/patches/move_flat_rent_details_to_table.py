"""Preserve old scalar rent details in the Flat's contract table."""

import frappe


def execute():
	# Frappe retains removed columns. Read only columns present on this site;
	# fresh installations have no legacy date/contract columns.
	fields = ["name", "docstatus", "rent_type", "flat_contract", "add_flat_to_contract"]
	fields += [field for field in ("rent_contract", "rent_contract_type", "rent_start_date", "rent_end_date")
		if frappe.db.has_column("Flat", field)]
	for flat in frappe.db.get_values("Flat", {}, fields, as_dict=True):
		if frappe.db.exists("Flat Rent Contract", {"parent": flat.name, "parenttype": "Flat", "parentfield": "rent_contracts"}):
			continue
		row = legacy_contract_row(flat)
		if not any(row.get(field) for field in ("rent_contract", "add_flat_to_contract", "rent_start_date", "rent_end_date")):
			continue
		child = frappe.get_doc({"doctype": "Flat Rent Contract", "parent": flat.name,
			"parenttype": "Flat", "parentfield": "rent_contracts", "idx": 1,
			"docstatus": flat.docstatus, **row})
		# Preserve submitted/cancelled Flats without running creation or submit actions.
		child.db_insert()
	frappe.clear_cache(doctype="Flat")


def legacy_contract_row(flat):
	contract_source = flat.get("add_flat_to_contract")
	row = {
		"rent_contract_type": flat.get("rent_contract_type") or "Flat Contract",
		"rent_contract": None if contract_source else (flat.get("rent_contract") or flat.get("flat_contract")),
		"add_flat_to_contract": contract_source,
		"rent_start_date": flat.get("rent_start_date"),
		"rent_end_date": flat.get("rent_end_date"),
	}
	return row
