import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import getseries


VEHICLE_PREFIXES = {
	"Private Vehicle": "PV",
	"Transportation": "TV",
	"Site Service": "SV",
}


class Vehicles(Document):
	def autoname(self):
		prefix = VEHICLE_PREFIXES.get(self.vehical_type)
		if not prefix:
			frappe.throw(_("Please select a valid Vehical Type."))
		if not self.project:
			frappe.throw(_("Please select a Project before saving."))
		abbreviation = frappe.db.get_value("Project", self.project, "custom_abbreviation")
		abbreviation = (abbreviation or "").strip()
		if not abbreviation:
			frappe.throw(_("Please set the abbreviation on Project {0} before saving.").format(self.project))
		self.naming_series = f"{prefix}-{abbreviation}-"
		self.name = self.naming_series + getseries(self.naming_series, 3)
