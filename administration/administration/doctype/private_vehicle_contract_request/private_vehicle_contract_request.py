# Copyright (c) 2026, Connect 4 Systems and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

from administration.flat_request_workflow import require_workflow_submission, validate_approval_history


class PrivateVehicleContractRequest(Document):
	def validate(self):
		validate_approval_history(self)

	def before_update_after_submit(self):
		validate_approval_history(self)

	def before_submit(self):
		require_workflow_submission(self)


@frappe.whitelist()
def make_private_vehicle_contract(source_name, target_doc=None):
	return get_mapped_doc(
		"Private Vehicle Contract Request",
		source_name,
		{
			"Private Vehicle Contract Request": {
				"doctype": "Private Vehicle Contract",
				"field_map": {"name": "private_vehicle_contract_request"},
				"field_no_map": [
					"naming_series", "amended_from", "workflow_state", "document_approval"
				],
				"validation": {"docstatus": ["=", 1]},
			},
			"Rent Emp": {"doctype": "Rent Emp"},
		},
		target_doc,
	)
