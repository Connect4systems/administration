import frappe


def execute():
	# Existing Rent Contract values link to Flat Contract, not the new request source.
	frappe.db.set_value(
		"Flat",
		{"rent_contract_type": ["is", "not set"]},
		"rent_contract_type",
		"Flat Contract",
		update_modified=False,
	)
