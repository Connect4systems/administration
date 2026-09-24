// Copyright (c) 2026, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Add Flat to Contract", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1) return;

		frm.add_custom_button(__(frm.doc.created_flat ? "View Flat" : "Create Flat"), () => {
			if (frm.doc.created_flat) {
				frappe.set_route("Form", "Flat", frm.doc.created_flat);
				return;
			}
			if (frm.is_dirty()) {
				frappe.msgprint(__("Save the document before creating its Flat."));
				return;
			}
			frappe.call({
				method: "administration.administration.doctype.flat.flat.make_flat",
				args: { source_doctype: frm.doc.doctype, source_name: frm.doc.name },
				freeze: true,
				freeze_message: __("Creating and submitting Flat..."),
				async callback(r) {
					if (r.message) {
						await frm.reload_doc();
						frappe.set_route("Form", "Flat", r.message.name);
					}
				},
			});
		});
	},
});
