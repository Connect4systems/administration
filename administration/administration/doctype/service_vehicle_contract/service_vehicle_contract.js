// Copyright (c) 2026, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Service Vehicle Contract", {
	before_workflow_action: (frm) => administration.approval.before_workflow_action(frm),
	after_workflow_action: (frm) => administration.approval.after_workflow_action(frm),
	refresh(frm) {
		administration.approval.refresh(frm);
		if (frm.doc.docstatus === 1 && frappe.model.can_create("Vehicles")) {
			frm.add_custom_button(__("Start service"), () => start_contract_service(frm));
		}
	},
});

function start_contract_service(frm) {
	const rows = frm.get_selected().contract_details || [];
	if (rows.length !== 1) {
		frappe.msgprint(__("Select exactly one row in Contract Terms to start service."));
		return;
	}
	if (frm.is_dirty()) {
		frappe.msgprint(__("Save your changes before starting service."));
		return;
	}
	const row = frm.doc.contract_details.find(row => row.name === rows[0]);
	const dialog = new frappe.ui.Dialog({
		title: __("Start service"),
		fields: [
			{ fieldname: "route", fieldtype: "Link", options: "Transportation Price List",
				label: __("Route"), default: row.route, read_only: 1 },
			{ fieldname: "vehicle_route", fieldtype: "Link", options: "Vehicle Route",
				label: __("Vehicle Route"), default: row.vehicle_route, read_only: 1 },
			{ fieldname: "start_date", fieldtype: "Date", label: __("Start Date"),
				default: frm.doc.contract_start_date || frappe.datetime.get_today(), reqd: 1 },
		],
		primary_action_label: __("Confirm"),
		async primary_action(values) {
			dialog.get_primary_btn().prop("disabled", true);
			try {
				const response = await frappe.call({
					method: "administration.vehicle_creation.start_service",
					args: { source_name: frm.doc.name, row_name: row.name, start_date: values.start_date },
					freeze: true,
					freeze_message: __("Creating vehicle..."),
				});
				if (response.message) {
					dialog.hide();
					frappe.set_route("Form", "Vehicles", response.message);
				}
			} finally {
				dialog.get_primary_btn().prop("disabled", false);
			}
		},
	});
	dialog.show();
}
