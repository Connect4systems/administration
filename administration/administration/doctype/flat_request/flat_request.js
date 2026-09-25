// Copyright (c) 2025, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Flat Request", {
	before_workflow_action(frm) {
		frappe.dom.unfreeze();
		return new Promise((resolve, reject) => {
			let confirmed = false;
			let closed = false;
			let uploader = null;
			const attachments = new Map();
			const dialog = new frappe.ui.Dialog({
				title: __("{0}: Note and Attachments", [frm.selected_workflow_action]),
				fields: [
					{fieldname: "note", fieldtype: "Small Text", label: __("Note")},
					{fieldname: "attach_files", fieldtype: "Button", label: __("Attach Files"), click() {
						if (uploader) return;
						uploader = new frappe.ui.FileUploader({
							wrapper: dialog.fields_dict.upload_area.$wrapper,
							doctype: frm.doctype, docname: frm.doc.name,
							allow_multiple: true, allow_web_link: false,
							disable_file_browser: true,
							on_success(file) {
								if (closed || !file?.name) return;
								attachments.set(file.name, file);
								dialog.fields_dict.attachment_list.$wrapper.empty();
								for (const attachment of attachments.values()) {
									$("<div>").text(attachment.file_name).appendTo(dialog.fields_dict.attachment_list.$wrapper);
								}
							},
						});
					}},
					{fieldname: "upload_area", fieldtype: "HTML"},
					{fieldname: "attachment_list", fieldtype: "HTML"},
				],
				primary_action_label: __("Confirm"),
				primary_action(values) {
					if (uploader?.uploader.files.some((file) => !file.doc?.name)) {
						frappe.msgprint(__("Finish uploading the selected files, or remove them from the uploader, before confirming."));
						return;
					}
					confirmed = true;
					frm.doc.__approval_note = (values.note || "").trim();
					frm.doc.__approval_attachments = [...attachments.keys()];
					dialog.hide();
					frappe.dom.freeze();
					resolve();
				},
				onhide() {
					closed = true;
					if (!confirmed) {
						delete frm.doc.__approval_note;
						delete frm.doc.__approval_attachments;
						frm.selected_workflow_action = null;
						frappe.dom.unfreeze();
						reject(new Error("Workflow action cancelled"));
					}
				},
			});
			dialog.show();
		});
	},
	after_workflow_action(frm) {
		delete frm.doc.__approval_note;
		delete frm.doc.__approval_attachments;
		frm.refresh_field("document_approval");
	},
	refresh(frm) {
		const grid = frm.fields_dict.document_approval?.grid;
		if (grid) {
			grid.update_docfield_property("attachments", "formatter", format_approval_attachments);
			frm.refresh_field("document_approval");
		}
		if (frm.doc.docstatus !== 1) {
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

function format_approval_attachments(value) {
	let files;
	try { files = JSON.parse(value || "[]"); } catch { return ""; }
	if (!Array.isArray(files)) return "";
	return files.filter((file) => file && typeof file.name === "string").map((file) =>
		`<a href="/app/file/${encodeURIComponent(file.name)}" target="_blank" rel="noopener noreferrer">${frappe.utils.escape_html(file.file_name || file.name)}</a>`
	).join("<br>");
}
