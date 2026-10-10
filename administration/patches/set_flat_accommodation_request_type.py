import frappe


def execute():
	for doctype in ("Flat", "Flat Contract Request", "Flat Contract"):
		frappe.db.sql(
			f"UPDATE `tab{doctype}` SET request_type = 'Share' WHERE IFNULL(request_type, '') = ''"
		)
