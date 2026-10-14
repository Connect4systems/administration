// Copyright (c) 2026, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Service Vehicle Contract Request", {
	before_workflow_action: (frm) => administration.approval.before_workflow_action(frm),
	after_workflow_action: (frm) => administration.approval.after_workflow_action(frm),
	refresh(frm) {
		administration.approval.refresh(frm);
		const grid = frm.fields_dict.contract_details.grid;
		grid.df.cannot_add_rows = frm.doc.docstatus === 1;
		grid.df.cannot_delete_rows = frm.doc.docstatus === 1;
		if (frm.doc.docstatus === 1 && frappe.model.can_create("Service Vehicle Contract")) {
			frm.add_custom_button(__("Create Contract"), () => {
				frappe.model.open_mapped_doc({
					method: "administration.administration.doctype.service_vehicle_contract_request.service_vehicle_contract_request.make_service_vehicle_contract",
					frm,
				});
			});
		}
	},
	setup(frm) {
		frm.set_query("route", "contract_details", () => ({
			filters: frm.doc.project ? { project: frm.doc.project } : { name: ["=", ""] },
		}));
	},
});
