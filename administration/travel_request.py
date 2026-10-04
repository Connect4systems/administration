"""Travel costing conversions and protected document approval history."""

import json
import math

import frappe
from frappe import _
from frappe.utils import flt, nowdate
from erpnext.setup.utils import get_exchange_rate


AMOUNT_FIELDS = ("sponsored_amount", "funded_amount", "total_amount")
TARGET_CURRENCIES = {"usd": "USD", "rmb": "CNY"}


def validate_document_approval(doc, method=None):
	from administration.flat_request_workflow import validate_approval_history

	validate_approval_history(doc)


def setup_document_approval():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	frappe.reload_doc("administration", "doctype", "flat_request_approval", force=True)
	meta = frappe.get_meta("Travel Request", cached=False)
	managed = ("document_approval_tab", "document_approval_help", "document_approval")
	other_fields = [field.fieldname for field in meta.fields if field.fieldname not in managed]
	create_custom_fields({"Travel Request": [
		{"fieldname": managed[0], "fieldtype": "Tab Break", "label": "Document Approval",
			"insert_after": other_fields[-1]},
		{"fieldname": managed[1], "fieldtype": "HTML", "insert_after": managed[0],
			"options": '<p class="text-muted">Workflow actions are recorded below with the status, approving role, user, date, note and attachments.</p>'},
		{"fieldname": managed[2], "fieldtype": "Table", "label": "Document Approval",
			"options": "Flat Request Approval", "insert_after": managed[1],
			"read_only": 1, "allow_on_submit": 1, "no_copy": 1},
	]})
	make_property_setter("Travel Request", None, "field_order", json.dumps(other_fields + list(managed)), "Data", for_doctype=True)
	for field in managed:
		for prop, value, kind in (("hidden", 0, "Check"), ("depends_on", "", "Data"), ("permlevel", 0, "Int")):
			make_property_setter("Travel Request", field, prop, value, kind)
	make_property_setter("Travel Request", "document_approval", "read_only", 1, "Check")
	frappe.clear_cache(doctype="Travel Request")


def _get_rates(company):
	if not company:
		frappe.throw(_("Please select a company to convert travel costing amounts."))
	currency = frappe.get_cached_value("Company", company, "default_currency")
	if not currency:
		frappe.throw(_("Please set the default currency for company {0}.").format(company))
	rates = {}
	for suffix, target in TARGET_CURRENCIES.items():
		rate = 1.0 if currency == target else flt(get_exchange_rate(currency, target, nowdate()))
		if not math.isfinite(rate) or rate <= 0:
			frappe.throw(_("Please configure an exchange rate from {0} to {1}.").format(currency, target))
		rates[suffix] = rate
	return rates


@frappe.whitelist()
def get_costing_exchange_rates(company):
	if not frappe.has_permission("Travel Request", "read"):
		frappe.throw(_("Not permitted to read Travel Requests."), frappe.PermissionError)
	frappe.get_doc("Company", company).check_permission("read")
	return _get_rates(company)


def update_costing_currencies(doc, method=None):
	rows = doc.get("costings") or []
	if not rows:
		return
	for row in rows:
		row.set("total_amount", flt(
			flt(row.get("sponsored_amount")) + flt(row.get("funded_amount")),
			row.precision("total_amount"),
		))
	has_amounts = any(flt(row.get(field)) for row in rows for field in AMOUNT_FIELDS)
	rates = _get_rates(doc.get("company")) if has_amounts else dict.fromkeys(TARGET_CURRENCIES, 0)
	for row in rows:
		for field in AMOUNT_FIELDS:
			for suffix, rate in rates.items():
				target_field = f"custom_{field}_{suffix}"
				row.set(target_field, flt(flt(row.get(field)) * rate, row.precision(target_field)))
