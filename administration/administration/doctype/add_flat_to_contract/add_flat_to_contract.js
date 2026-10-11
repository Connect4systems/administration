// Copyright (c) 2026, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Add Flat to Contract", {
	before_workflow_action: (frm) => administration.approval.before_workflow_action(frm),
	after_workflow_action: (frm) => administration.approval.after_workflow_action(frm),
	refresh(frm) {
		administration.approval.refresh(frm);
		if (frm.doc.docstatus !== 1 || frm.doc.workflow_state !== "Approved") return;
		if (frm.doc.contract_status === "Terminated") return;
		if (frm.doc.type === "Renew") {
			frm.add_custom_button(__("View Flat"), () => frappe.set_route("Form", "Flat", frm.doc.flat));
			return;
		}

		administration.approval.flat_transaction_buttons(frm);
	},
});
