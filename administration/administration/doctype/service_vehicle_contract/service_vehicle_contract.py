import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import getseries
from frappe.utils import nowdate

from administration.flat_request_workflow import require_workflow_submission, validate_approval_history


class ServiceVehicleContract(Document):
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
		self.validate_contract_attachment()
		validate_approval_history(self)

	def before_update_after_submit(self):
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
