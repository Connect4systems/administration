// Copyright (c) 2025, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Flat Rent Request", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1) {
			return;
		}

		frm.add_custom_button(__("Create Flat Contract Request"), () => {
			frappe.model.with_doctype("Flat Contract Request", () => {
				const contract_meta = frappe.get_meta("Flat Contract Request");
				const contract_fields = new Set(
					contract_meta.fields.map((field) => field.fieldname)
				);
				const contract_values = {};

				frm.meta.fields.forEach((field) => {
					if (
						contract_fields.has(field.fieldname) &&
						!["Column Break", "Section Break", "Table"].includes(field.fieldtype)
					) {
						contract_values[field.fieldname] = frm.doc[field.fieldname];
					}
				});

				frappe.new_doc("Flat Contract Request", contract_values);
			});
		});
	},
});
