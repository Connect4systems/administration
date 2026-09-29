import frappe
from frappe import _


LAYOUT_FIELDS = {"Section Break", "Column Break", "Tab Break", "HTML", "Button"}
EXCLUDED_FIELDS = {"naming_series", "amended_from", "workflow_state", "document_approval"}


@frappe.whitelist()
def create_vehicle(source_name):
	# Serialize creation for this contract so repeated requests return the same vehicle.
	source = frappe.get_doc("Private Vehicle Contract", source_name, for_update=True)
	source.check_permission("read")
	if source.docstatus != 1:
		frappe.throw(_("Submit the Private Vehicle Contract before creating a vehicle."))

	existing = frappe.db.get_value(
		"Vehicles",
		{"private_vehicle_contract": source.name, "docstatus": ["!=", 2]},
		"name",
	)
	if existing:
		frappe.get_doc("Vehicles", existing).check_permission("read")
		return existing

	vehicle = frappe.new_doc("Vehicles")
	vehicle.check_permission("create")
	vehicle.check_permission("submit")
	for field in source.meta.fields:
		name = field.fieldname
		if field.fieldtype in LAYOUT_FIELDS or name in EXCLUDED_FIELDS or field.no_copy:
			continue
		target_field = vehicle.meta.get_field(name)
		if not target_field:
			continue
		if field.fieldtype in {"Table", "Table MultiSelect"}:
			if target_field.options != field.options:
				continue
			for row in source.get(name) or []:
				vehicle.append(name, {
					child.fieldname: row.get(child.fieldname)
					for child in row.meta.fields
					if child.fieldtype not in LAYOUT_FIELDS and not child.no_copy
				})
		else:
			vehicle.set(name, source.get(name))

	vehicle.private_vehicle_contract = source.name
	vehicle.vehical_type = source.get("request_type") or "Private Vehicle"
	vehicle.insert()
	vehicle.submit()
	return vehicle.name
