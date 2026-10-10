// Copyright (c) 2026, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Vehicles", {
	setup(frm) {
		frm.set_query("employee", () => ({
			filters: {
				status: "Active",
				custom_transportation: "Privat car",
				custom_project: frm.doc.project || "",
			},
		}));
		frm.set_query("code", "employees", () => ({
			filters: {
				status: "Active",
				custom_transportation: "Shared",
				custom_project: frm.doc.project || "",
			},
		}));
	},
	employee(frm) {
		if (frm.doc.request_type !== "Private Vehicle") return;
		return check_vehicle_employee(frm, frm.doc.employee, () => frm.doc.employee,
			() => frm.set_value("employee", null));
	},
	request_type(frm) {
		return clear_unused_vehicle_employees(frm);
	},
	refresh(frm) {
		clear_unused_vehicle_employees(frm);
		const read_only = frm.doc.docstatus === 1 && !frappe.user.has_role("Fleet Manager");
		frm.set_df_property("employee", "read_only", read_only);
		frm.set_df_property("employees", "read_only", frm.doc.request_type !== "Transportation");
	},
});

frappe.ui.form.on("Rent Emp", {
	code(frm, cdt, cdn) {
		if (frm.doctype !== "Vehicles" || frm.doc.request_type !== "Transportation") return;
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

function clear_unused_vehicle_employees(frm) {
	if (["Transportation", "Site Service"].includes(frm.doc.request_type) && frm.doc.employee) {
		frm.set_value("employee", null);
	}
	if (["Private Vehicle", "Site Service"].includes(frm.doc.request_type) && frm.doc.employees?.length) {
		frm.clear_table("employees");
		frm.refresh_field("employees");
		frm.dirty();
	}
}
