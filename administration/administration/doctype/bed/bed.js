// Copyright (c) 2025, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bed", {
	setup(frm) {
		frm.set_query("room", () => ({
			filters: {
				flat: frm.doc.flat || "",
			},
		}));
	},
	refresh(frm) {
		if (frm.is_new() || !frm.doc.employee) {
			return;
		}

		frm.add_custom_button(__("Employee Left"), () => {
			frappe.confirm(
				__("Clear this employee from the bed?"),
				() => {
					frappe.call({
						method: "administration.administration.doctype.bed.bed.employee_left",
						args: { bed_name: frm.doc.name },
						freeze: true,
						callback: () => frm.reload_doc(),
					});
				}
			);
		});
	},
	flat(frm) {
		frm.set_value("room", null);
	},
	async employee(frm) {
		frm.set_value("status", frm.doc.employee ? "Booked" : "Open");
		const employee = frm.doc.employee;
		if (!employee) return;
		const result = await frappe.call({
			method: "administration.administration.doctype.bed.bed.check_employee_assignment",
			args: {employee, bed_name: frm.is_new() ? null : frm.doc.name},
		});
		if (frm.doc.employee === employee && result.message) {
			frappe.msgprint({
				title: __("Employee Already Assigned"),
				indicator: "orange",
				message: result.message,
			});
			await frm.set_value("employee", null);
		}
	},
	employee_left(frm) {
		if (!frm.doc.employee) {
			return;
		}

		frappe.call({
			method: "administration.administration.doctype.bed.bed.employee_left",
			args: { bed_name: frm.doc.name },
			freeze: true,
			callback: () => frm.reload_doc(),
		});
	},
});
