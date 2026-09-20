"""Keep User's employee details derived from Employee.user_id."""

import frappe


EMPLOYEE_FIELDS = {
	"custom_employee_id": "name",
	"custom_employee_name": "employee_name",
	"custom_department": "department",
	"custom_branch_location": "branch",
	"custom_project": "custom_project",
	"custom_position": "designation",
}


def setup_employee_details():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	fields = [{
		"fieldname": "custom_employee_details_tab",
		"label": "Employee Details",
		"fieldtype": "Tab Break",
		"insert_after": frappe.get_meta("User").fields[-1].fieldname,
	}]
	previous = "custom_employee_details_tab"
	for fieldname, label, options in (
		("custom_employee_id", "Employee ID", "Employee"),
		("custom_employee_name", "Employee Name", None),
		("custom_department", "Department", "Department"),
		("custom_branch_location", "Branch Location", "Branch"),
		("custom_project", "Project", "Project"),
		("custom_position", "Position", "Designation"),
	):
		fields.append({
			"fieldname": fieldname,
			"label": label,
			"fieldtype": "Link" if options else "Data",
			"options": options,
			"insert_after": previous,
			"read_only": 1,
			"no_copy": 1,
			"ignore_user_permissions": 1 if options else 0,
		})
		previous = fieldname

	# Preserve the original insertion point on subsequent migrations.
	existing = frappe.db.get_value(
		"Custom Field", {"dt": "User", "fieldname": "custom_employee_details_tab"}, "insert_after"
	)
	if existing:
		fields[0]["insert_after"] = existing
	create_custom_fields({"User": fields})
	for user in frappe.get_all("User", pluck="name"):
		_update_user(user, _employee_for_user(user))


def _ready():
	return all(frappe.get_meta("User").has_field(field) for field in EMPLOYEE_FIELDS)


def _employee_for_user(user):
	# Prefer an active employee if historical records share the same User ID.
	employees = frappe.get_all(
		"Employee",
		filters={"user_id": user},
		fields=list(EMPLOYEE_FIELDS.values()),
		order_by="status asc, modified desc, name asc",
		limit_page_length=1,
	)
	return employees[0] if employees else None


def _values(employee):
	return {
		field: employee.get(source) if employee else None
		for field, source in EMPLOYEE_FIELDS.items()
	}


def set_user_employee_details(doc, method=None):
	if _ready():
		doc.update(_values(_employee_for_user(doc.name)))


def _update_user(user, employee):
	if not user or not frappe.db.exists("User", user):
		return
	values = _values(employee)
	current = frappe.db.get_value("User", user, list(EMPLOYEE_FIELDS), as_dict=True)
	if all((current.get(field) or None) == (value or None) for field, value in values.items()):
		return
	# Avoid saving User: its controller can write back to Employee.
	frappe.db.set_value("User", user, values)
	frappe.clear_cache(user=user)
	frappe.get_doc("User", user).notify_update()


def sync_employee_to_user(doc, method=None):
	if not _ready():
		return
	previous = doc.get_doc_before_save()
	users = {doc.get("user_id"), previous.get("user_id") if previous else None}
	for user in users:
		if user:
			_update_user(user, _employee_for_user(user))


def clear_employee_from_user(doc, method=None):
	if not _ready():
		return
	# Clear links before Frappe checks whether the Employee can be deleted.
	for user in frappe.get_all("User", filters={"custom_employee_id": doc.name}, pluck="name"):
		_update_user(user, None)
