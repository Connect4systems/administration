import frappe
from frappe import _
from frappe.model.document import Document


class FlatRequestApproval(Document):
	def validate(self):
		# Parent saves persist child rows directly; standalone child API writes are not allowed.
		frappe.throw(_("Approval history can only be written by a Flat Request workflow action."))

	def on_trash(self):
		frappe.throw(_("Approval history cannot be deleted directly."))
