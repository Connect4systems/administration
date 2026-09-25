// Copyright (c) 2025, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Flat Request", {
	before_workflow_action: (frm) => administration.approval.before_workflow_action(frm),
	after_workflow_action: (frm) => administration.approval.after_workflow_action(frm),
	refresh(frm) {
		administration.approval.refresh(frm);
		frm.remove_custom_button(__("Add Flat to Contract"));
		frm.remove_custom_button(__("Create Flat Contract Request"));
		if (
			frm.doc.docstatus !== 1 ||
			frm.doc.workflow_state !== "Approved" ||
			!frappe.user_roles.includes("Admin supervisor (Accommodation)")
		) {
			return;
		}

		frm.add_custom_button(__("Add Flat to Contract"), async () => {
			const supplier = frm.doc.flat_owner
				? (await frappe.db.get_value("Supplier", frm.doc.flat_owner, [
					"supplier_name", "custom_legal_name",
				])).message || {}
				: {};

			frappe.model.with_doctype("Add Flat to Contract", () => {
				const target = frappe.model.get_new_doc("Add Flat to Contract");
				const source_fields = new Map(frm.meta.fields.map((field) => [field.fieldname, field]));
				const excluded_types = ["Column Break", "Section Break", "Tab Break", "HTML", "Button"];
				frappe.get_meta("Add Flat to Contract").fields.forEach((field) => {
					if (field.no_copy || field.fieldname === "naming_series" || excluded_types.includes(field.fieldtype)) {
						return;
					}
					const source = source_fields.get(field.fieldname) || source_fields.get(`custom_${field.fieldname}`);
					if (!source || frm.doc[source.fieldname] == null) {
						return;
					}
					if (["Table", "Table MultiSelect"].includes(field.fieldtype)) {
						if (source.options !== field.options) return;
						(frm.doc[source.fieldname] || []).forEach((row) => {
							const child = frappe.model.add_child(target, field.options, field.fieldname);
							frappe.get_meta(field.options).fields.forEach((child_field) => {
								if (!child_field.no_copy && !excluded_types.includes(child_field.fieldtype)) {
									child[child_field.fieldname] = row[child_field.fieldname];
								}
							});
						});
					} else {
						target[field.fieldname] = frm.doc[source.fieldname];
					}
				});
				target.flat_request = frm.doc.name;
				target.flat_owner = supplier.supplier_name || target.flat_owner || "";
				target.flat_owner_name = target.flat_owner;
				target.legal_name = target.legal_name || supplier.custom_legal_name || "";
				frappe.set_route("Form", target.doctype, target.name);
			});
		});

		frm.add_custom_button(__("Create Flat Contract Request"), () => {
			frappe.model.with_doctype("Flat Contract Request", () => {
				const contract_meta = frappe.get_meta("Flat Contract Request");
				const contract_fields = new Set(
					contract_meta.fields.map((field) => field.fieldname)
				);
				const contract_values = {};
				contract_values.flat_request = frm.doc.name;

				frm.meta.fields.forEach((field) => {
					const target_field = contract_fields.has(field.fieldname)
						? field.fieldname
						: field.fieldname.replace(/^custom_/, "");
					if (
						contract_fields.has(target_field) &&
						!field.no_copy &&
						!["naming_series", "amended_from"].includes(target_field) &&
						!["Column Break", "Section Break", "Tab Break", "Table", "Table MultiSelect", "HTML", "Button"].includes(field.fieldtype)
					) {
						contract_values[target_field] = frm.doc[field.fieldname];
					}
				});

				frappe.new_doc("Flat Contract Request", contract_values);
			});
		});
	},
});
