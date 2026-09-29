# Copyright (c) 2026, Connect 4 Systems and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


class VehicleRequest(Document):
	pass


@frappe.whitelist()
def make_private_vehicle_contract_request(source_name, target_doc=None):
	return get_mapped_doc(
		"Vehicle Request",
		source_name,
		{
			"Vehicle Request": {
				"doctype": "Private Vehicle Contract Request",
				"field_map": {"name": "vehicle_request"},
				"field_no_map": ["naming_series", "amended_from", "workflow_state"],
				"validation": {"docstatus": ["=", 1]},
			},
			"Rent Emp": {"doctype": "Rent Emp"},
		},
		target_doc,
	)
