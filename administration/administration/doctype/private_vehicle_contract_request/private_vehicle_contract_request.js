// Copyright (c) 2026, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Private Vehicle Contract Request", {
	before_workflow_action: (frm) => administration.approval.before_workflow_action(frm),
	after_workflow_action: (frm) => administration.approval.after_workflow_action(frm),
	refresh(frm) {
		administration.approval.refresh(frm);
		if (frm.doc.docstatus === 1 && frappe.model.can_create("Private Vehicle Contract")) {
			frm.add_custom_button(__("Private Vehicle Contract"), () => {
				frappe.model.open_mapped_doc({
					method: "administration.administration.doctype.private_vehicle_contract_request.private_vehicle_contract_request.make_private_vehicle_contract",
					frm,
				});
			}, __("Create"));
		}
	},
});
