frappe.ui.form.on("Flat Termination", {
	before_workflow_action: (frm) => administration.approval.before_workflow_action(frm),
	after_workflow_action: (frm) => administration.approval.after_workflow_action(frm),
	refresh: (frm) => administration.approval.refresh(frm),
});
