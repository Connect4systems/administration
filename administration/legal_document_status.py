"""Date-based status for the last renewal row of a legal document."""

from datetime import date


def get_status(rows, today):
	if not rows:
		return ""
	row = rows[-1]
	today = date.fromisoformat(str(today))
	expiry = row.get("expire_date")
	next_renewal = row.get("next_renew_date")
	if not expiry:
		return ""
	if today > date.fromisoformat(str(expiry)):
		return "Expire"
	if next_renewal and today >= date.fromisoformat(str(next_renewal)):
		return "Renew Now"
	return "Active"


def update_statuses():
	"""Refresh existing records after migration and each day in the site timezone."""
	import frappe
	from frappe.utils import today

	current_date = today()
	for name in frappe.get_all("Legal document", pluck="name"):
		doc = frappe.get_doc("Legal document", name)
		status = get_status(doc.get("legal_document"), current_date)
		if doc.status != status:
			doc.db_set("status", status, update_modified=False)
