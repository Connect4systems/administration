import frappe


def execute():
	# Repair sites whose Vehicles table predates service creation tracking.
	frappe.reload_doc("administration", "doctype", "vehicles", force=True)
