// Copyright (c) 2026, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Vehicle Request", {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && frappe.model.can_create("Private Vehicle Contract Request")) {
			frm.add_custom_button(__("Private Vehicle Contract Request"), () => {
				frappe.model.open_mapped_doc({
					method: "administration.administration.doctype.vehicle_request.vehicle_request.make_private_vehicle_contract_request",
					frm,
				});
			}, __("Create"));
		}
	},
	setup(frm) {
		frm.set_query("employee", () => ({
			filters: { status: "Active", custom_transportation: "Privat car" },
		}));
		frm.set_query("code", "employees", () => ({
			filters: { status: "Active", custom_transportation: "Shared" },
		}));
	},
});
