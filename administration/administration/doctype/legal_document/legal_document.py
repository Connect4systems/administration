# Copyright (c) 2026, Connect 4 Systems and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.utils import today

from administration.legal_document_status import get_status


class Legaldocument(Document):
	def validate(self):
		self.status = get_status(self.get("legal_document"), today())
