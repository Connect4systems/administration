import frappe
from frappe import _
from frappe.desk.reportview import build_match_conditions
from frappe.utils import flt, getdate
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
	get_dimension_with_children,
)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)
	dimensions = get_report_dimensions()

	rows = get_gl_entries(filters, dimensions)
	opening_balance = get_opening_balance(filters, dimensions)
	company_currency = frappe.get_cached_value("Company", filters.company, "default_currency")

	data = [get_opening_row(opening_balance, company_currency)]
	running_balance = opening_balance

	for row in rows:
		# Counterpart rows provide the full voucher context, but only the direct
		# party row changes a party-wide running balance. When an account is
		# selected, every returned row belongs to that account and must affect its
		# balance, including Purchase Invoice rows linked through `against`.
		if row_changes_balance(row, filters):
			running_balance += flt(row.debit) - flt(row.credit)
		row.balance = running_balance
		row.company_currency = company_currency
		row.party_name = get_party_name(row.party_type, row.party)
		data.append(row)

	return get_columns(company_currency, filters, dimensions), data


def validate_filters(filters):
	required_filters = {
		"company": _("Company"),
		"from_date": _("From Date"),
		"to_date": _("To Date"),
	}
	missing = [label for fieldname, label in required_filters.items() if not filters.get(fieldname)]
	if missing:
		frappe.throw(_("Please provide: {0}").format(", ".join(missing)))

	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date"))

	if filters.get("party") and not filters.get("party_type"):
		frappe.throw(_("Please provide Party Type when filtering by Party"))

	if filters.get("party") and not frappe.db.exists(filters.party_type, filters.party):
		frappe.throw(_("Invalid {0}: {1}").format(filters.party_type, filters.party))


def get_gl_entries(filters, dimensions):
	conditions, params = get_common_conditions(filters, dimensions)
	conditions.insert(1, "`tabGL Entry`.posting_date BETWEEN %(from_date)s AND %(to_date)s")
	add_party_condition(conditions, filters)

	permission_conditions = build_match_conditions("GL Entry")
	if permission_conditions:
		conditions.append(permission_conditions)

	dimension_fields = "".join(f", `tabGL Entry`.`{dimension.fieldname}`" for dimension in dimensions)
	direct_party_field = "1"
	if filters.get("party"):
		direct_party_field = (
			"CASE WHEN `tabGL Entry`.party_type = %(party_type)s "
			"AND `tabGL Entry`.party = %(party)s THEN 1 ELSE 0 END"
		)

	return frappe.db.sql(
		f"""
		SELECT
			`tabGL Entry`.name AS gl_entry,
			`tabGL Entry`.posting_date,
			`tabGL Entry`.account,
			`tabGL Entry`.debit,
			`tabGL Entry`.credit,
			`tabGL Entry`.voucher_type,
			`tabGL Entry`.voucher_subtype,
			`tabGL Entry`.voucher_no,
			`tabGL Entry`.against,
			`tabGL Entry`.party_type,
			`tabGL Entry`.party,
			`tabGL Entry`.project,
			`tabGL Entry`.cost_center,
			`tabGL Entry`.against_voucher_type,
			`tabGL Entry`.against_voucher,
			`tabGL Entry`.remarks,
			{direct_party_field} AS is_direct_party
			{dimension_fields}
		FROM `tabGL Entry`
		WHERE {" AND ".join(conditions)}
		ORDER BY
			`tabGL Entry`.posting_date,
			`tabGL Entry`.voucher_type,
			`tabGL Entry`.voucher_no,
			`tabGL Entry`.creation,
			`tabGL Entry`.name
		""",
		params,
		as_dict=True,
	)


def get_opening_balance(filters, dimensions):
	conditions, params = get_common_conditions(filters, dimensions)
	conditions.append("`tabGL Entry`.posting_date < %(from_date)s")
	if filters.get("party"):
		if filters.get("account"):
			# Match the same direct and counterpart rows used by the report. This
			# keeps an account-filtered opening balance consistent with its rows.
			add_party_condition(conditions, filters)
		else:
			conditions.extend(
				[
					"`tabGL Entry`.party_type = %(party_type)s",
					"`tabGL Entry`.party = %(party)s",
				]
			)

	permission_conditions = build_match_conditions("GL Entry")
	if permission_conditions:
		conditions.append(permission_conditions)

	result = frappe.db.sql(
		f"""
		SELECT COALESCE(SUM(debit - credit), 0) AS opening_balance
		FROM `tabGL Entry`
		WHERE {" AND ".join(conditions)}
		""",
		params,
		as_dict=True,
	)
	return flt(result[0].opening_balance)


def row_changes_balance(row, filters):
	return bool(filters.get("account") or not filters.get("party") or row.is_direct_party)


def add_party_condition(conditions, filters):
	if not filters.get("party"):
		return

	# Return only the selected party row or an untagged counterpart whose Against
	# Account is exactly that party. Composite Against values belong to a voucher
	# covering multiple parties and must not be attributed wholly to one party.
	conditions.append(
		"""
		(
			(`tabGL Entry`.party_type = %(party_type)s AND `tabGL Entry`.party = %(party)s)
			OR (
				COALESCE(`tabGL Entry`.party, '') = ''
				AND TRIM(COALESCE(`tabGL Entry`.against, '')) = %(party)s
			)
		)
		"""
	)


def get_common_conditions(filters, dimensions):
	conditions = ["`tabGL Entry`.company = %(company)s"]
	params = dict(filters)

	if not filters.get("show_cancelled_entries"):
		conditions.append("`tabGL Entry`.is_cancelled = 0")

	optional_filters = {
		"account": "`tabGL Entry`.account = %(account)s",
		"voucher_no": "`tabGL Entry`.voucher_no = %(voucher_no)s",
		"finance_book": "`tabGL Entry`.finance_book = %(finance_book)s",
		"project": "`tabGL Entry`.project = %(project)s",
		"cost_center": "`tabGL Entry`.cost_center = %(cost_center)s",
	}
	for fieldname, condition in optional_filters.items():
		if filters.get(fieldname):
			conditions.append(condition)

	for dimension in dimensions:
		value = filters.get(dimension.fieldname)
		if not value:
			continue

		values = frappe.parse_json(value) if isinstance(value, str) and value.startswith("[") else value
		if not isinstance(values, (list, tuple)):
			values = [values]
		if frappe.get_cached_value("DocType", dimension.document_type, "is_tree"):
			values = get_dimension_with_children(dimension.document_type, values)

		params[dimension.fieldname] = tuple(values)
		conditions.append(f"`tabGL Entry`.`{dimension.fieldname}` IN %({dimension.fieldname})s")

	return conditions, params


def get_report_dimensions():
	return [
		dimension
		for dimension in get_accounting_dimensions(as_list=False)
		if dimension.fieldname not in {"finance_book", "project", "cost_center"}
	]


def get_opening_row(opening_balance, company_currency):
	return {
		"account": _("Opening"),
		"debit": opening_balance if opening_balance > 0 else 0.0,
		"credit": abs(opening_balance) if opening_balance < 0 else 0.0,
		"balance": opening_balance,
		"company_currency": company_currency,
	}


def get_party_name(party_type, party):
	if not party_type or not party:
		return None

	meta = frappe.get_meta(party_type)
	title_field = meta.title_field
	if not title_field or title_field == "name":
		return party
	return frappe.get_cached_value(party_type, party, title_field) or party


def get_columns(currency, filters, dimensions):
	currency_options = "company_currency"
	columns = [
		{"fieldname": "posting_date", "label": _("Posting Date"), "fieldtype": "Date", "width": 110},
		{"fieldname": "account", "label": _("Account"), "fieldtype": "Link", "options": "Account", "width": 210},
		{"fieldname": "debit", "label": _("Debit ({0})").format(currency), "fieldtype": "Currency", "options": currency_options, "width": 130},
		{"fieldname": "credit", "label": _("Credit ({0})").format(currency), "fieldtype": "Currency", "options": currency_options, "width": 130},
		{"fieldname": "balance", "label": _("Balance ({0})").format(currency), "fieldtype": "Currency", "options": currency_options, "width": 150},
		{"fieldname": "voucher_type", "label": _("Voucher Type"), "fieldtype": "Data", "width": 120},
		{"fieldname": "voucher_subtype", "label": _("Voucher Subtype"), "fieldtype": "Data", "width": 140},
		{"fieldname": "voucher_no", "label": _("Voucher No"), "fieldtype": "Dynamic Link", "options": "voucher_type", "width": 170},
		{"fieldname": "against", "label": _("Against Account"), "fieldtype": "Data", "width": 180},
		{"fieldname": "party_type", "label": _("Party Type"), "fieldtype": "Data", "width": 110},
		{"fieldname": "party", "label": _("Party"), "fieldtype": "Dynamic Link", "options": "party_type", "width": 130},
		{"fieldname": "party_name", "label": _("Party Name"), "fieldtype": "Data", "width": 170},
		{"fieldname": "project", "label": _("Project"), "fieldtype": "Link", "options": "Project", "width": 130},
	]
	for dimension in dimensions:
		columns.append(
			{
				"fieldname": dimension.fieldname,
				"label": _(dimension.label),
				"fieldtype": "Link",
				"options": dimension.document_type,
				"width": 130,
			}
		)
	columns.extend(
		[
			{"fieldname": "cost_center", "label": _("Cost Center"), "fieldtype": "Link", "options": "Cost Center", "width": 140},
			{"fieldname": "against_voucher_type", "label": _("Against Voucher Type"), "fieldtype": "Data", "width": 140},
			{"fieldname": "against_voucher", "label": _("Against Voucher"), "fieldtype": "Dynamic Link", "options": "against_voucher_type", "width": 160},
		]
	)
	if filters.get("show_remarks"):
		columns.append({"fieldname": "remarks", "label": _("Remarks"), "fieldtype": "Data", "width": 300})
	# Keep hidden columns last so Frappe's XLSX total row remains aligned with
	# the visible Debit, Credit, and Balance columns.
	columns.append(
		{"fieldname": "gl_entry", "label": _("GL Entry"), "fieldtype": "Link", "options": "GL Entry", "hidden": 1}
	)

	return columns
