// Copyright (c) 2026, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Vehicles", {
	setup(frm) {
		frm.set_query("employee", () => ({
			filters: { status: "Active", custom_transportation: "Privat car" },
		}));
		frm.set_query("code", "employees", () => ({
			filters: { status: "Active", custom_transportation: "Shared" },
		}));
	},
	employee(frm) {
		return check_vehicle_employee(frm, frm.doc.employee, () => frm.doc.employee,
			() => frm.set_value("employee", null));
	},
	refresh(frm) {
		const read_only = frm.doc.docstatus === 1 && !frappe.user.has_role("Fleet Manager");
		for (const fieldname of ["employee", "employees"]) {
			frm.set_df_property(fieldname, "read_only", read_only);
		}
	},
});

frappe.ui.form.on("Rent Emp", {
	code(frm, cdt, cdn) {
		if (frm.doctype !== "Vehicles") return;
		const row = locals[cdt][cdn];
		return check_vehicle_employee(frm, row.code, () => locals[cdt]?.[cdn]?.code,
			() => frappe.model.set_value(cdt, cdn, {
				code: null, employee: null, job_title: null, department: null,
			}));
	},
});

async function check_vehicle_employee(frm, employee, current_value, clear_value) {
	if (!employee) return;
	const response = await frappe.call({
		method: "administration.administration.doctype.vehicles.vehicles.get_employee_vehicles",
		args: { employee, current_vehicle: frm.doc.name },
	});
	if (current_value() !== employee || !response.message?.length) return;
	await clear_value();
	frappe.msgprint({
		title: __("Employee already assigned"),
		indicator: "orange",
		message: __("Employee {0} is already registered in Vehicles: {1}. Clear the employee from those Vehicles before selecting them here.", [
			frappe.utils.escape_html(employee),
			response.message.map(name => frappe.utils.escape_html(name)).join(", "),
		]),
	});
}
