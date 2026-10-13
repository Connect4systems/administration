// Copyright (c) 2026, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Flat Contract", {
	before_workflow_action(frm) {
		if (frm.selected_workflow_action === "Request" && !frm.doc.attach_contract) {
			frappe.dom.unfreeze();
			frappe.throw(__("Attach Contract is required before requesting approval."));
		}
		return administration.approval.before_workflow_action(frm);
	},
	after_workflow_action: (frm) => administration.approval.after_workflow_action(frm),
	setup(frm) {
		$(frm.wrapper).on("attachments_change.legal_roles", () => {
			if (!can_manage_contract_attachments()) {
				frm.attachments?.parent.find(".add-attachment-btn, .attachment-row .btn-remove").hide();
			}
		});
	},
	refresh(frm) {
		administration.approval.refresh(frm);
		const allowed = can_manage_contract_attachments();
		for (const field of frm.meta.fields) {
			if (["Attach", "Attach Image"].includes(field.fieldtype)) {
				frm.set_df_property(field.fieldname, "read_only", allowed ? field.read_only : 1);
			}
		}
		if (frm.attachments && !frm.attachments.legal_role_guard) {
			const attachments = frm.attachments;
			const can_delete = attachments.can_delete_attachment.bind(attachments);
			attachments.can_delete_attachment = () => can_manage_contract_attachments() && can_delete();
			const new_attachment = attachments.new_attachment.bind(attachments);
			attachments.new_attachment = (...args) => {
				if (can_manage_contract_attachments()) return new_attachment(...args);
			};
			attachments.legal_role_guard = true;
			attachments.refresh();
		}
		if (frm.doc.docstatus !== 1) return;
		if (frm.doc.contract_status === "Terminated") return;
		if (frm.doc.type === "Renew") {
			frm.add_custom_button(__("View Flat"), () => frappe.set_route("Form", "Flat", frm.doc.flat));
			return;
		}

		administration.approval.flat_transaction_buttons(frm);
	},
});

function can_manage_contract_attachments() {
	return ["Legal User", "Legal Manager"].some((role) => frappe.user_roles.includes(role));
}
