// Copyright (c) 2025, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Flat", {
	refresh(frm) {
		if (frm.is_new()) {
			frm.disable_save();
			frm.set_intro(__("Create a Flat using the Create Flat button on a submitted Flat Contract or Add Flat to Contract."));
		}
	},
});
