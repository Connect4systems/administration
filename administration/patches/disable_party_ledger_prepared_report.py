import frappe


def execute():
	frappe.db.set_value(
		"Report",
		"Party Ledger (Party & Against)",
		"prepared_report",
		0,
		update_modified=False,
	)
