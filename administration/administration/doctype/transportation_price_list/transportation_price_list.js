// Copyright (c) 2026, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Transportation Price List", {
	refresh(frm) {
		if (frm.doc.docstatus === 0) {
			update_allowance_time(frm);
		}
	},
	half_day_allowance(frm) {
		update_allowance_time(frm);
	},
});

function update_allowance_time(frm) {
	if (frm.doc.half_day_allowance == 1) {
		if (!frm.doc.allowance_time) {
			frm.set_value("allowance_time", "21:00:00");
		}
	} else if (frm.doc.allowance_time) {
		frm.set_value("allowance_time", null);
	}
}
