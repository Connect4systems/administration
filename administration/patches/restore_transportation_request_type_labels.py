import frappe


def execute():
	# Label-only migration: leave options, document values and mappings untouched.
	for slug, doctype, fieldname in (
		("vehicle_request", "Vehicle Request", "request_type"),
		("private_vehicle_contract_request", "Private Vehicle Contract Request", "request_type"),
		("private_vehicle_contract", "Private Vehicle Contract", "request_type"),
		("vehicles", "Vehicles", "request_type"),
		("transportation_price_list", "Transportation Price List", "service_type"),
		("vehicle_route_table", "Vehicle Route Table", "service_type"),
	):
		frappe.reload_doc("administration", "doctype", slug, force=True)
		for name in frappe.get_all("Property Setter", filters={
			"doc_type": doctype, "field_name": fieldname, "property": "label",
		}, pluck="name"):
			frappe.db.set_value("Property Setter", name, "value", "Request Type")
		frappe.clear_cache(doctype=doctype)
