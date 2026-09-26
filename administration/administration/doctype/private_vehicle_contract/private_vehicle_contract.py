import frappe
from frappe import _
from frappe.model.document import Document

from administration.flat_request_workflow import require_workflow_submission, validate_approval_history


class PrivateVehicleContract(Document):
	def validate(self):
		self.validate_contract_attachment()
		validate_approval_history(self)

	def before_update_after_submit(self):
		self.validate_contract_attachment()
		validate_approval_history(self)

	def before_submit(self):
		require_workflow_submission(self)

	def validate_contract_attachment(self):
		previous = self.get_doc_before_save()
		old_value = previous.get("contract_attachment") if previous else None
		if (self.get("contract_attachment") or "") != (old_value or ""):
			if not {"Legal User", "Legal Manager"}.intersection(frappe.get_roles()):
				frappe.throw(
					_("Only Legal User or Legal Manager can add, replace or clear the Contract Attachment."),
					frappe.PermissionError,
				)
