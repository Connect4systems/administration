import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	rows = get_party_entries(filters)
	against_accounts = get_against_accounts(filters)
	opening_balance = get_opening_balance(filters)

	data = []
	running_balance = opening_balance

	if opening_balance:
		data.append(
			{
				"account": _("Opening Balance"),
				"debit": 0.0,
				"credit": 0.0,
				"running_balance": opening_balance,
			}
		)

	for row in rows:
		running_balance += flt(row.debit) - flt(row.credit)
		voucher_key = (row.voucher_type, row.voucher_no)
		counterpart_accounts = [
			account for account in against_accounts.get(voucher_key, []) if account != row.account
		]

		data.append(
			{
				"posting_date": row.posting_date,
				"account": row.account,
				"against_account": ", ".join(counterpart_accounts) or row.against,
				"debit": row.debit,
				"credit": row.credit,
				"running_balance": running_balance,
				"voucher_type": row.voucher_type,
				"voucher_no": row.voucher_no,
				"party_type": row.party_type,
				"party": row.party,
				"remarks": row.remarks,
			}
		)

	return get_columns(), data


def validate_filters(filters):
	required_filters = {
		"company": _("Company"),
		"from_date": _("From Date"),
		"to_date": _("To Date"),
		"party_type": _("Party Type"),
		"party": _("Party"),
	}
	missing = [label for fieldname, label in required_filters.items() if not filters.get(fieldname)]
	if missing:
		frappe.throw(_("Please provide: {0}").format(", ".join(missing)))

	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date"))


def get_party_entries(filters):
	"""Return only rows posted to the selected party.

	Counterpart voucher rows are used for display, but are deliberately excluded
	from the balance so a balanced voucher does not reduce every movement to zero.
	"""
	return frappe.db.sql(
		"""
		SELECT
			ge.posting_date,
			ge.account,
			ge.debit,
			ge.credit,
			ge.voucher_type,
			ge.voucher_no,
			ge.party_type,
			ge.party,
			ge.against,
			ge.remarks
		FROM `tabGL Entry` ge
		WHERE ge.company = %(company)s
			AND ge.posting_date BETWEEN %(from_date)s AND %(to_date)s
			AND ge.party_type = %(party_type)s
			AND ge.party = %(party)s
		ORDER BY ge.posting_date, ge.creation, ge.name
		""",
		filters,
		as_dict=True,
	)


def get_opening_balance(filters):
	result = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(ge.debit - ge.credit), 0) AS opening_balance
		FROM `tabGL Entry` ge
		WHERE ge.company = %(company)s
			AND ge.posting_date < %(from_date)s
			AND ge.party_type = %(party_type)s
			AND ge.party = %(party)s
		""",
		filters,
		as_dict=True,
	)
	return flt(result[0].opening_balance)


def get_against_accounts(filters):
	account_rows = frappe.db.sql(
		"""
		SELECT DISTINCT ge.voucher_type, ge.voucher_no, ge.account
		FROM `tabGL Entry` ge
		INNER JOIN `tabGL Entry` party_ge
			ON party_ge.company = ge.company
			AND party_ge.voucher_type = ge.voucher_type
			AND party_ge.voucher_no = ge.voucher_no
		WHERE ge.company = %(company)s
			AND party_ge.posting_date BETWEEN %(from_date)s AND %(to_date)s
			AND party_ge.party_type = %(party_type)s
			AND party_ge.party = %(party)s
		ORDER BY ge.voucher_type, ge.voucher_no, ge.account
		""",
		filters,
		as_dict=True,
	)

	result = {}
	for row in account_rows:
		key = (row.voucher_type, row.voucher_no)
		accounts = result.setdefault(key, [])
		if row.account not in accounts:
			accounts.append(row.account)

	return result


def get_columns():
	return [
		{"fieldname": "posting_date", "label": _("Posting Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "account", "label": _("Account"), "fieldtype": "Link", "options": "Account", "width": 220},
		{"fieldname": "against_account", "label": _("Against Account"), "fieldtype": "Data", "width": 220},
		{"fieldname": "debit", "label": _("Debit"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "credit", "label": _("Credit"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "running_balance", "label": _("Running Balance"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "voucher_type", "label": _("Voucher Type"), "fieldtype": "Data", "width": 120},
		{"fieldname": "voucher_no", "label": _("Voucher No"), "fieldtype": "Dynamic Link", "options": "voucher_type", "width": 140},
		{"fieldname": "party_type", "label": _("Party Type"), "fieldtype": "Data", "width": 110},
		{"fieldname": "party", "label": _("Party"), "fieldtype": "Dynamic Link", "options": "party_type", "width": 140},
		{"fieldname": "remarks", "label": _("Remarks"), "fieldtype": "Data", "width": 200},
	]
