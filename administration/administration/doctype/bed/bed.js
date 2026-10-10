// Copyright (c) 2025, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bed", {
	setup(frm) {
		frm.set_query("employee", () => ({
			filters: {
				status: "Active",
				custom_accommidation: frm.doc.request_type === "Private" ? "Private" : "Share",
				custom_project: frm.doc.project || "",
			},
		}));
		frm.set_query("room", () => ({
			filters: {
				flat: frm.doc.flat || "",
			},
		}));
	},
	onload(frm) {
		return load_bed_flat_details(frm);
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
		frm.set_value({room: null, employee: null});
		return load_bed_flat_details(frm);
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

async function load_bed_flat_details(frm) {
	const flat = frm.doc.flat;
	frm.doc.project = "";
	frm.doc.request_type = "";
	if (!flat) return;
	const result = await frappe.db.get_value("Flat", flat, ["project", "request_type"]);
	if (frm.doc.flat === flat) {
		frm.doc.project = result.message?.project || "";
		frm.doc.request_type = result.message?.request_type || "Share";
	}
}
