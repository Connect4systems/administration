// Copyright (c) 2025, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Flat", {
	refresh(frm) {
		const grid = frm.fields_dict.rent_contracts?.grid;
		if (grid) {
			grid.update_docfield_property("rent_contract", "hidden", frm.doc.rent_type === "Contract" ? 1 : 0);
			grid.update_docfield_property("add_flat_to_contract", "hidden", frm.doc.rent_type === "Contract" ? 0 : 1);
			grid.refresh();
		}
		if (frm.is_new()) {
			frm.disable_save();
			frm.set_intro(__("Create a Flat using the Create Flat button on a submitted Flat Contract or Add Flat to Contract."));
		}
	},
});
