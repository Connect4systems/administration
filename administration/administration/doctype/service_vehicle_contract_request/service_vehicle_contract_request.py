# Copyright (c) 2026, Connect 4 Systems and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.model.naming import getseries
from frappe.utils import nowdate

from administration.flat_request_workflow import require_workflow_submission, validate_approval_history


class ServiceVehicleContractRequest(Document):
	def autoname(self):
		if not self.project:
			frappe.throw(_("Please select a Project before saving."))
		abbreviation = frappe.db.get_value("Project", self.project, "custom_abbreviation")
		abbreviation = (abbreviation or "").strip()
		if not abbreviation:
			frappe.throw(_("Please set the abbreviation on Project {0} before saving.").format(self.project))
		prefix = f"{abbreviation}-{nowdate()[2:4]}-"
		self.name = prefix + getseries(prefix, 3)

	def validate(self):
		validate_approval_history(self)

	def before_update_after_submit(self):
		validate_approval_history(self)

	def before_submit(self):
		require_workflow_submission(self)


@frappe.whitelist()
def make_service_vehicle_contract(source_name, target_doc=None):
	return get_mapped_doc(
		"Service Vehicle Contract Request",
		source_name,
		{
			"Service Vehicle Contract Request": {
				"doctype": "Service Vehicle Contract",
				"field_map": {"name": "service_vehicle_contract_request"},
				"field_no_map": ["naming_series", "amended_from", "workflow_state", "document_approval"],
				"validation": {"docstatus": ["=", 1]},
			},
			"Vehicle Route Table": {"doctype": "Vehicle Route Table"},
		},
		target_doc,
	)
