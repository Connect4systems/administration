// Copyright (c) 2025, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bed", {
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
