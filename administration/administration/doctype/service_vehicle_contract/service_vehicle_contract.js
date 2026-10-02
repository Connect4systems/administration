// Copyright (c) 2026, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Service Vehicle Contract", {
	before_workflow_action: (frm) => administration.approval.before_workflow_action(frm),
	after_workflow_action: (frm) => administration.approval.after_workflow_action(frm),
	refresh(frm) {
		administration.approval.refresh(frm);
		enable_service_row_selection(frm);
		if (frm.doc.docstatus === 1 && frappe.model.can_create("Vehicles") && frappe.model.can_submit("Vehicles")) {
			frm.add_custom_button(__("Start service"), () => start_contract_service(frm));
		}
	},
});

function enable_service_row_selection(frm) {
	const grid = frm.fields_dict.contract_details.grid;
	grid.wrapper.off("change.start_service click.start_service");
	if (frm.doc.docstatus !== 1) return;
	grid.df.cannot_delete_rows = true;
	const show_selection = () => {
		grid.toggle_checkboxes(true);
		grid.wrapper.find(".grid-heading-row .grid-row-check").hide();
		grid.wrapper.find(".grid-body .grid-row-check").prop("disabled", false);
		grid.wrapper.find(".grid-remove-rows, .grid-remove-all-rows").addClass("hidden");
	};
	grid.wrapper.on("change.start_service", show_selection);
	grid.wrapper.on("click.start_service", ".grid-body .grid-row-check", function () {
		const selected_name = $(this).closest(".grid-row").attr("data-name");
		const checked = $(this).prop("checked");
		for (const row of frm.doc.contract_details || []) {
			row.__checked = checked && row.name === selected_name ? 1 : 0;
		}
		for (const row of grid.grid_rows || []) row?.refresh_check();
		show_selection();
	});
	show_selection();
}

async function start_contract_service(frm) {
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
	const remaining_response = await frappe.call({
		method: "administration.vehicle_creation.get_service_remaining_qty",
		args: { source_name: frm.doc.name, row_name: row.name },
	});
	const remaining_qty = remaining_response.message;
	if (remaining_qty <= 0) {
		frappe.msgprint(__("All vehicles created for this contract row."));
		return;
	}
	const request_id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
	const dialog = new frappe.ui.Dialog({
		title: __("Start service"),
		fields: [
			{ fieldname: "route", fieldtype: "Link", options: "Transportation Price List",
				label: __("Route"), default: row.route, read_only: 1 },
			{ fieldname: "vehicle_route", fieldtype: "Link", options: "Vehicle Route",
				label: __("Vehicle Route"), default: row.vehicle_route, read_only: 1 },
			{ fieldname: "qty", fieldtype: "Int", label: __("Quantity"), default: remaining_qty, reqd: 1,
				description: __("Remaining quantity: {0}", [remaining_qty]) },
			{ fieldname: "start_date", fieldtype: "Date", label: __("Start Date"),
				default: frm.doc.contract_start_date || frappe.datetime.get_today(), reqd: 1 },
		],
		primary_action_label: __("Confirm"),
		async primary_action(values) {
			if (!Number.isInteger(values.qty) || values.qty <= 0) {
				frappe.msgprint(__("Quantity must be a positive whole number."));
				return;
			}
			if (values.qty > remaining_qty) {
				frappe.msgprint(__("Quantity exceeds the remaining contract quantity ({0}).", [remaining_qty]));
				return;
			}
			dialog.get_primary_btn().prop("disabled", true);
			try {
				const response = await frappe.call({
					method: "administration.vehicle_creation.start_service",
					args: { source_name: frm.doc.name, row_name: row.name, start_date: values.start_date,
						qty: values.qty, request_id },
					freeze: true,
					freeze_message: __("Creating and submitting vehicles..."),
				});
				if (response.message) {
					dialog.hide();
					const remaining = await frappe.call({
						method: "administration.vehicle_creation.get_service_remaining_qty",
						args: { source_name: frm.doc.name, row_name: row.name },
					});
					if (remaining.message === 0) {
						frappe.msgprint(__("All vehicles created for this contract row."));
					}
					if (response.message.length === 1) {
						frappe.set_route("Form", "Vehicles", response.message[0]);
					} else {
						frappe.route_options = { service_vehicle_contract: frm.doc.name, service_contract_row: row.name };
						frappe.set_route("List", "Vehicles");
					}
				}
			} finally {
				dialog.get_primary_btn().prop("disabled", false);
			}
		},
	});
	dialog.show();
}
