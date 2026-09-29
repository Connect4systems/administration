// Copyright (c) 2026, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Private Vehicle Contract", {
	before_workflow_action: (frm) => administration.approval.before_workflow_action(frm),
	after_workflow_action: (frm) => administration.approval.after_workflow_action(frm),
	refresh(frm) {
		administration.approval.refresh(frm);
		if (frm.doc.docstatus === 1 && frappe.model.can_create("Vehicles") && frappe.model.can_submit("Vehicles")) {
			frm.add_custom_button(__("Create Vehicle"), async () => {
				const response = await frappe.call({
					method: "administration.vehicle_creation.create_vehicle",
					args: { source_name: frm.doc.name },
					freeze: true,
					freeze_message: __("Creating vehicle..."),
				});
				if (response.message) {
					frappe.set_route("Form", "Vehicles", response.message);
				}
			});
		}
	},
});
