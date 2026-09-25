// Shared workflow note, uploads and audit display for accommodation documents.
frappe.provide("administration.approval");

administration.approval = {
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
					{fieldname: "attach_files", fieldtype: "Button", label: __("Attach Files"),
						hidden: frm.doctype === "Flat Contract" && !["Legal User", "Legal Manager"].some((role) => frappe.user_roles.includes(role)), click() {
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
	},
};

function format_approval_attachments(value) {
	let files;
	try { files = JSON.parse(value || "[]"); } catch { return ""; }
	if (!Array.isArray(files)) return "";
	return files.filter((file) => file && typeof file.name === "string").map((file) =>
		`<a href="/app/file/${encodeURIComponent(file.name)}" target="_blank" rel="noopener noreferrer">${frappe.utils.escape_html(file.file_name || file.name)}</a>`
	).join("<br>");
}
