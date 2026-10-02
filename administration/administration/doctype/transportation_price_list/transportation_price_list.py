# Copyright (c) 2026, Connect 4 Systems and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import getseries


class TransportationPriceList(Document):
	def validate(self):
		if self.half_day_allowance:
			if not self.allowance_time:
				self.allowance_time = "21:00:00"
		else:
			self.allowance_time = None

	def autoname(self):
		if not self.project:
			frappe.throw(_("Please select a Project before saving."))
		if not self.vehicle_route:
			frappe.throw(_("Please select a Vehicle Route before saving."))
		abbreviation = frappe.db.get_value("Project", self.project, "custom_abbreviation")
		abbreviation = (abbreviation or "").strip()
		if not abbreviation:
			frappe.throw(_("Please set the abbreviation on Project {0} before saving.").format(self.project))
		prefix = f"{abbreviation}-{self.vehicle_route}-"
		self.name = prefix + getseries(prefix, 3)
