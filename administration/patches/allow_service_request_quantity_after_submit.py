import frappe


def execute():
	for slug, doctype, fieldname in (
		("vehicle_route_table", "Vehicle Route Table", "qty"),
		("service_vehicle_contract_request", "Service Vehicle Contract Request", "contract_details"),
	):
		frappe.reload_doc("administration", "doctype", slug, force=True)
		for setter in frappe.get_all("Property Setter", filters={
			"doc_type": doctype, "field_name": fieldname, "property": "allow_on_submit",
		}, pluck="name"):
			frappe.db.set_value("Property Setter", setter, "value", "1")
		frappe.clear_cache(doctype=doctype)
