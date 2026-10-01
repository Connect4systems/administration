import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import getseries


VEHICLE_PREFIXES = {
	"Private Vehicle": "PV",
	"Transportation": "TV",
	"Site Service": "SV",
}


def find_employee_vehicles(employee, current_vehicle=None):
	return frappe.db.sql(
		"""
		SELECT DISTINCT vehicle.name
		FROM `tabVehicles` vehicle
		LEFT JOIN `tabRent Emp` passenger
			ON passenger.parent = vehicle.name
			AND passenger.parenttype = 'Vehicles'
			AND passenger.parentfield = 'employees'
		WHERE vehicle.docstatus < 2
			AND vehicle.name != %(current_vehicle)s
			AND (vehicle.employee = %(employee)s OR passenger.code = %(employee)s)
		ORDER BY vehicle.name
		""",
		{"employee": employee, "current_vehicle": current_vehicle or ""},
		pluck=True,
	)


@frappe.whitelist()
def get_employee_vehicles(employee, current_vehicle=None):
	if not frappe.has_permission("Vehicles", "read"):
		frappe.throw(_("You do not have permission to read Vehicles."), frappe.PermissionError)
	return find_employee_vehicles(employee, current_vehicle) if employee else []


class Vehicles(Document):
	def validate(self):
		self.validate_employee()
		self.validate_employee_assignments()

	def before_update_after_submit(self):
		self.validate_employee()
		previous = self.get_doc_before_save()
		passenger_fields = ("name", "idx", "code", "employee", "job_title", "department")
		def passenger_values(doc):
			return [
				tuple(row.get(field) for field in passenger_fields)
				for row in (doc.get("employees") or [])
			] if doc else []

		employees_changed = passenger_values(self) != passenger_values(previous)
		if (self.has_value_changed("employee") or employees_changed) and "Fleet Manager" not in frappe.get_roles():
			frappe.throw(
				_("Only Fleet Manager can change Employee or the Employees table after submission."),
				frappe.PermissionError,
			)
		self.validate_employee_assignments()

	def validate_employee_assignments(self):
		employees = {row.code for row in self.get("employees") or [] if row.code}
		if self.employee:
			employees.add(self.employee)
		for employee in sorted(employees):
			assigned_vehicles = find_employee_vehicles(employee, self.name)
			if assigned_vehicles:
				frappe.throw(
					_("Employee {0} is already registered in Vehicles: {1}. Clear the employee from those Vehicles before selecting them here.").format(
						employee, ", ".join(assigned_vehicles)
					)
				)

	def validate_employee(self):
		if self.request_type == "Private Vehicle" and not self.employee:
			frappe.throw(_("Employee is required for a Private Vehicle."))

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
