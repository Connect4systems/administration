# Copyright (c) 2026, Connect 4 Systems and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from administration.flat_request_workflow import require_workflow_submission, validate_approval_history


class AddFlattoContract(Document):
	def validate(self):
		validate_approval_history(self)

	def before_update_after_submit(self):
		validate_approval_history(self)

	def before_submit(self):
		require_workflow_submission(self)
