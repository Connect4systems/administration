// Copyright (c) 2026, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Flat Contract", {
	refresh(frm) {
		frm.set_df_property("arabic_terms", "dir", "rtl");
	},
});
