// Copyright (c) 2026, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Add Flat to Contract", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1) return;

		frm.add_custom_button(__("Create Flat"), () => {
			frappe.call({
				method: "administration.administration.doctype.flat.flat.make_flat",
				args: { source_doctype: frm.doc.doctype, source_name: frm.doc.name },
				freeze: true,
				callback(r) {
					if (r.message) {
						const flat = frappe.model.sync(r.message)[0];
						frappe.set_route("Form", "Flat", flat.name);
					}
				},
			});
		});
	},
});
