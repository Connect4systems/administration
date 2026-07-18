import frappe
from frappe.utils import flt


def execute(filters=None):
    """Return columns and data for Party Ledger report.

    Logic:
    - Include GL Entry rows where the row has the selected party OR the voucher contains any row with that party.
    - Optionally include Journal Entries that touch deduction accounts (to capture JE returns of deductions).
    - Aggregate other accounts in the same voucher into `against_account` using GROUP_CONCAT.
    - Compute opening balance (posting_date < from_date) using the same inclusion logic.
    """
    filters = filters or {}
    company = filters.get("company")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    party_type = filters.get("party_type")
    party = filters.get("party")

    if not (company and from_date and to_date and party_type and party):
        frappe.throw("Please provide Company, From Date, To Date, Party Type and Party")

    include_je_deduction = filters.get("include_je_deduction_accounts") or False
    deduction_accounts_raw = (filters.get("deduction_accounts") or "").strip()
    deduction_accounts = [a.strip() for a in deduction_accounts_raw.split(",") if a.strip()]

    # Base date/company params
    base_params = [company, from_date, to_date]

    # We'll need party params twice (for direct row match and for exists() check on voucher)
    # Final params order: company, from_date, to_date, party_type, party, party_type, party, [deduction_accounts...]
    params_for_rows = base_params + [party_type, party, party_type, party]
    if include_je_deduction and deduction_accounts:
        params_for_rows += deduction_accounts

    # Build optional JE deduction clause
    je_clause = ""
    if include_je_deduction and deduction_accounts:
        placeholders = ",".join(["%s"] * len(deduction_accounts))
        je_clause = f" OR (ge.voucher_type='Journal Entry' AND ge.account IN ({placeholders})) "

    # Where clause selects rows in date range and company, and either directly references party or belongs to a voucher that references the party
    where_clause = (
        "ge.company=%s AND ge.posting_date BETWEEN %s AND %s AND ("
        "(ge.party_type=%s AND ge.party=%s) "
        "OR EXISTS(SELECT 1 FROM `tabGL Entry` gep WHERE gep.voucher_type=ge.voucher_type AND gep.voucher_no=ge.voucher_no AND gep.party_type=%s AND gep.party=%s)"
        f" {je_clause} )"
    )

    # Main query: pull GL entries (we'll batch fetch against_account per voucher to avoid N+1 queries)
    sql = f"""
    SELECT
        ge.name, ge.posting_date, ge.account, ge.debit, ge.credit, ge.voucher_type, ge.voucher_no,
        ge.party_type, ge.party, ge.against, ge.remarks
    FROM `tabGL Entry` ge
    WHERE {where_clause}
    ORDER BY ge.posting_date, ge.voucher_no, ge.account
    """

    rows = frappe.db.sql(sql, tuple(params_for_rows), as_dict=1)

    # Batch fetch against accounts per voucher
    voucher_keys = []
    for r in rows:
        vt = r.get("voucher_type") or ""
        vn = r.get("voucher_no") or ""
        voucher_keys.append(f"{vt}||{vn}")

    contra_map = {}
    if voucher_keys:
        # build placeholders and params
        placeholders = ",".join(["%s"] * len(voucher_keys))
        contra_sql = f"SELECT CONCAT(voucher_type, '||', voucher_no) as vkey, GROUP_CONCAT(DISTINCT account SEPARATOR ', ') as accounts FROM `tabGL Entry` WHERE CONCAT(voucher_type, '||', voucher_no) IN ({placeholders}) GROUP BY voucher_type, voucher_no"
        contra_rows = frappe.db.sql(contra_sql, tuple(voucher_keys), as_dict=1)
        for cr in contra_rows:
            contra_map[cr.get("vkey")] = cr.get("accounts")

    # Opening balance: same inclusion logic but posting_date < from_date
    params_opening = [company, from_date, party_type, party, party_type, party]
    if include_je_deduction and deduction_accounts:
        params_opening += deduction_accounts

    opening_sql = (
        "SELECT COALESCE(SUM(ge.debit - ge.credit), 0) as opening_balance FROM `tabGL Entry` ge"
        " WHERE ge.company=%s AND ge.posting_date < %s AND ("
        "(ge.party_type=%s AND ge.party=%s) OR EXISTS(SELECT 1 FROM `tabGL Entry` gep WHERE gep.voucher_type=ge.voucher_type AND gep.voucher_no=ge.voucher_no AND gep.party_type=%s AND gep.party=%s)"
    )
    if include_je_deduction and deduction_accounts:
        placeholders = ",".join(["%s"] * len(deduction_accounts))
        opening_sql += f" OR (ge.voucher_type='Journal Entry' AND ge.account IN ({placeholders}))"
    opening_sql += ")"

    opening_balance = flt(frappe.db.sql(opening_sql, tuple(params_opening), as_dict=1)[0].get("opening_balance"))

    # Build report rows and running balance
    data = []
    running = opening_balance

    for r in rows:
        running += flt(r.get("debit")) - flt(r.get("credit"))
        vt = r.get("voucher_type") or ""
        vn = r.get("voucher_no") or ""
        vkey = f"{vt}||{vn}"
        against_account = contra_map.get(vkey) if contra_map.get(vkey) else r.get("against")
        data.append(
            [
                r.get("posting_date"),
                r.get("account"),
                against_account,
                r.get("debit") or 0.0,
                r.get("credit") or 0.0,
                running,
                r.get("voucher_type"),
                r.get("voucher_no"),
                r.get("party_type"),
                r.get("party"),
                r.get("remarks"),
            ]
        )

    # Columns in Frappe Script Report format
    columns = [
        "Posting Date:Date:90",
        "Account:Link/Account:220",
        "Against Account:Data:220",
        "Debit:Currency:120",
        "Credit:Currency:120",
        "Running Balance:Currency:140",
        "Voucher Type:Data:120",
        "Voucher No:Data:140",
        "Party Type:Data:100",
        "Party:Data:140",
        "Remarks:Data:200",
    ]

    # Prepend opening balance row if non-zero
    if opening_balance:
        data.insert(0, [None, "Opening Balance", "", 0.0, 0.0, opening_balance, "", "", "", "", ""])

    return columns, data


def validate_filters(filters):
    # placeholder for future validation
    return True
