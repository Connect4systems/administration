// Copyright (c) 2026, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Vehicles", {
	refresh(frm) {
		frm.set_df_property(
			"employee",
			"read_only",
			frm.doc.docstatus === 1 && !frappe.user.has_role("Fleet Manager")
		);
	},
});
