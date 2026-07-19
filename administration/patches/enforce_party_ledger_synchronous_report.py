import frappe


def execute():
	meta = frappe.get_meta("Report")
	values = {"prepared_report": 0}

	if meta.has_field("disable_prepared_report"):
		values["disable_prepared_report"] = 1
	if meta.has_field("disable_prepared_report_automation"):
		values["disable_prepared_report_automation"] = 1

	frappe.db.set_value(
		"Report",
		"Party Ledger (Party & Against)",
		values,
		update_modified=False,
	)
