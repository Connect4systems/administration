import frappe


def execute():
	# Clean drafts, submitted and cancelled vehicles without changing their lifecycle.
	frappe.db.sql("""
		UPDATE `tabVehicles` SET employee = NULL
		WHERE request_type IN ('Transportation', 'Site Service')
	""")
	frappe.db.sql("""
		DELETE passenger FROM `tabRent Emp` passenger
		INNER JOIN `tabVehicles` vehicle ON vehicle.name = passenger.parent
		WHERE passenger.parenttype = 'Vehicles'
			AND passenger.parentfield = 'employees'
			AND vehicle.request_type IN ('Private Vehicle', 'Site Service')
	""")
