import frappe


def execute():
	for source_field, rent_type in (
		("flat_contract_request", "Direct Rent"),
		("add_flat_to_contract", "Contract"),
	):
		frappe.db.set_value(
			"Flat",
			{source_field: ["is", "set"]},
			"rent_type",
			rent_type,
			update_modified=False,
		)
