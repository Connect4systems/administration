import frappe
from frappe import _
from frappe.model.document import Document

from administration.flat_request_workflow import require_workflow_submission, validate_approval_history


class ServiceVehicleContract(Document):
	def autoname(self):
		if not self.project:
			frappe.throw(_("Please select a Project before saving."))
		abbreviation = frappe.db.get_value("Project", self.project, "custom_abbreviation")
		abbreviation = (abbreviation or "").strip()
		if not abbreviation:
			frappe.throw(_("Please set the abbreviation on Project {0} before saving.").format(self.project))
		title = (self.title or "").strip()
		if not title:
			frappe.throw(_("Please enter a Title before saving."))
		self.title = title
		self.name = f"{abbreviation}-{title}"

	def validate(self):
		self.validate_contract_attachment()
		validate_approval_history(self)

	def before_update_after_submit(self):
		previous = self.get_doc_before_save()
		if previous:
			quantities = {row.name: row.get("qty") for row in previous.get("contract_details") or []}
			for row in self.get("contract_details") or []:
				if row.name in quantities and row.get("qty") != quantities[row.name]:
					frappe.throw(_("Contract Terms Quantity cannot be changed on a submitted Service Vehicle Contract."))
		self.validate_contract_attachment()
		validate_approval_history(self)

	def before_submit(self):
		require_workflow_submission(self)

	def validate_contract_attachment(self):
		previous = self.get_doc_before_save()
		old_value = previous.get("attach_contract") if previous else None
		if (self.get("attach_contract") or "") != (old_value or ""):
			if not {"Legal User", "Legal Manager"}.intersection(frappe.get_roles()):
				frappe.throw(
					_("Only Legal User or Legal Manager can add, replace or clear Attach Contract."),
					frappe.PermissionError,
				)
