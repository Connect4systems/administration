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


@frappe.whitelist()
def get_service_remaining_qty(source_name, row_name):
	source = frappe.get_doc("Service Vehicle Contract", source_name)
	source.check_permission("read")
	if source.docstatus != 1:
		frappe.throw(_("Submit the Service Vehicle Contract before starting service."))
	row = next((row for row in source.get("contract_details") or [] if row.name == row_name), None)
	if not row:
		frappe.throw(_("The selected row does not belong to this contract."))
	created = frappe.db.count("Vehicles", {
		"service_vehicle_contract": source.name,
		"service_contract_row": row_name,
		"docstatus": ["!=", 2],
	})
	return max(0, int(row.get("qty") or 0) - created)


@frappe.whitelist()
def start_service(source_name, row_name, start_date, qty, request_id):
	from frappe.utils import getdate

	source = frappe.get_doc("Service Vehicle Contract", source_name, for_update=True)
	source.check_permission("read")
	if source.docstatus != 1:
		frappe.throw(_("Submit the Service Vehicle Contract before starting service."))
	if not isinstance(row_name, str) or not row_name:
		frappe.throw(_("Select exactly one Contract Terms row."))
	row = next((row for row in source.get("contract_details") or [] if row.name == row_name), None)
	if not row:
		frappe.throw(_("The selected row does not belong to this contract."))
	if not start_date:
		frappe.throw(_("Start Date is required."))
	start_date = getdate(start_date)
	if source.get("contract_start_date") and start_date < getdate(source.contract_start_date):
		frappe.throw(_("Start Date cannot be before the contract start date."))
	if source.get("contract_end_date") and start_date > getdate(source.contract_end_date):
		frappe.throw(_("Start Date cannot be after the contract end date."))
	if row.get("service_type") not in {"Transportation", "Site Service"}:
		frappe.throw(_("The selected row must have a valid Service Type."))

	try:
		quantity = float(qty)
		contract_qty = float(row.get("qty") or 0)
	except (TypeError, ValueError):
		frappe.throw(_("Quantity must be a positive whole number."))
	if not quantity.is_integer() or quantity <= 0:
		frappe.throw(_("Quantity must be a positive whole number."))
	if not contract_qty.is_integer() or contract_qty <= 0:
		frappe.throw(_("The contract row must have a positive whole-number quantity."))
	quantity = int(quantity)
	if not isinstance(request_id, str) or not request_id or len(request_id) > 140:
		frappe.throw(_("A valid service request reference is required."))

	existing = frappe.get_all(
		"Vehicles",
		filters={"service_vehicle_contract": source.name, "service_contract_row": row_name, "docstatus": ["!=", 2]},
		fields=["name", "service_start_request", "docstatus"],
	)
	repeated = [item for item in existing if item.service_start_request == request_id]
	if repeated:
		for item in repeated:
			frappe.get_doc("Vehicles", item.name).check_permission("read")
		return [item.name for item in repeated]
	if quantity + len(existing) > contract_qty:
		frappe.throw(_("Quantity exceeds the remaining contract quantity ({0}).").format(max(0, contract_qty - len(existing))))

	created = []
	for _index in range(quantity):
		vehicle = frappe.new_doc("Vehicles")
		vehicle.check_permission("create")
		vehicle.check_permission("submit")
		vehicle.update({
			"service_vehicle_contract": source.name,
			"service_contract_row": row_name,
			"service_start_request": request_id,
			"project": source.get("project"),
			"vehicle_owner": source.get("provider_company"),
			"rent_start_date": start_date,
			"rent_end_date": source.get("contract_end_date"),
			"request_type": row.get("service_type"),
			"vehical_type": row.get("service_type"),
			"drive_type": "With Driver",
		})
		field_map = {
			"route": "route", "qty": "qty", "vehicle_type": "vehicle_type",
			"vehicle_route": "vehicle_route", "location": "location",
			"passengers": "no_of_employee", "overtime": "extra_hour_fees",
			"extra_km": "extra_kelometer_fees", "allowance": "midnight_allowance",
			"half_day_allowance": "half_day_allowance", "allowance_time": "allowance_time",
			"rent_cycle": "payment_cycle", "rent_amount": "rent_amount",
			"check_in": "check_in", "check_out": "check_out",
		}
		for source_field, target_field in field_map.items():
			vehicle.set(target_field, row.get(source_field))
		vehicle.set("qty", 1)
		vehicle.insert()
		vehicle.submit()
		created.append(vehicle.name)
	return created
