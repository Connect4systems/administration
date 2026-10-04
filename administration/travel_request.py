"""Convert travel costings from the company's currency to USD and CNY (RMB)."""

import math

import frappe
from frappe import _
from frappe.utils import flt, nowdate
from erpnext.setup.utils import get_exchange_rate


AMOUNT_FIELDS = ("sponsored_amount", "funded_amount", "total_amount")
TARGET_CURRENCIES = {"usd": "USD", "rmb": "CNY"}


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
	has_amounts = any(flt(row.get(field)) for row in rows for field in AMOUNT_FIELDS)
	rates = _get_rates(doc.get("company")) if has_amounts else dict.fromkeys(TARGET_CURRENCIES, 0)
	for row in rows:
		for field in AMOUNT_FIELDS:
			for suffix, rate in rates.items():
				target_field = f"custom_{field}_{suffix}"
				row.set(target_field, flt(flt(row.get(field)) * rate, row.precision(target_field)))
