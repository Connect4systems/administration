import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname


VEHICLE_PREFIXES = {
	"Private Vehicle": "PV",
	"Transportation": "TV",
	"Site Service": "SV",
	"Transportation and Service": "TSV",
}

VEHICLE_DETAIL_FIELDS = ("brand", "model", "motor_number", "chassis_number", "plat_number")
EDITABLE_VEHICLE_TYPES = {"Transportation", "Site Service", "Transportation and Service"}


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
			AND ((vehicle.request_type = 'Private Vehicle' AND vehicle.employee = %(employee)s)
				OR (vehicle.request_type IN ('Transportation', 'Transportation and Service') AND passenger.code = %(employee)s))
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

	def validate_vehicle_details_update(self):
		if self.request_type not in EDITABLE_VEHICLE_TYPES and any(
			self.has_value_changed(fieldname) for fieldname in VEHICLE_DETAIL_FIELDS
		):
			frappe.throw(_("Vehicle details can only be updated after submission for Transportation, Site Service, or Transportation and Service."))

	def before_update_after_submit(self):
		self.validate_vehicle_details_update()
		self.validate_employee()
		if self.request_type == "Private Vehicle" and self.has_value_changed("employee") and "Fleet Manager" not in frappe.get_roles():
			frappe.throw(
				_("Only Fleet Manager can change Employee after submission."),
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
		if self.request_type in {"Transportation", "Transportation and Service", "Site Service"}:
			self.employee = None
		if self.request_type in {"Private Vehicle", "Site Service"}:
			self.set("employees", [])

	def autoname(self):
		prefix = VEHICLE_PREFIXES.get(self.request_type) or VEHICLE_PREFIXES.get(self.get("vehical_type"))
		if not prefix:
			frappe.throw(_("Please select a valid Vehicle Type."))
		if not self.project:
			frappe.throw(_("Please select a Project before saving."))
		self.naming_series = f"{prefix}-.YY.-.###"
		self.name = make_autoname(self.naming_series, doc=self)
