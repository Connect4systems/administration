// Copyright (c) 2025, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Flat", {
	setup(frm) {
		frm.set_query("employee", () => ({
			filters: {
				status: "Active",
				custom_project: frm.doc.project || "",
				custom_accommidation: "Private",
			},
		}));
	},
	request_type(frm) {
		if (frm.doc.request_type !== "Private" && frm.doc.employee) {
			frm.set_value("employee", null);
		}
		frm.trigger("refresh");
	},
	refresh(frm) {
		// Hide Room and Bed dashboard links and their create buttons for private flats.
		for (const doctype of ["Room", "Bed"]) {
			frm.dashboard?.wrapper.find(`[data-doctype="${doctype}"]`)
				.closest(".document-link").toggle(frm.doc.request_type !== "Private");
		}
		if (frm.doc.docstatus === 1 && !frm.is_dirty() && frm.doc.flat_status) {
			const colors = {Active: "green", Inactive: "gray", Expired: "orange"};
			frm.page.set_indicator(__(frm.doc.flat_status), colors[frm.doc.flat_status] || "gray");
		}
		const grid = frm.fields_dict.rent_contracts?.grid;
		if (grid) {
			grid.update_docfield_property("rent_contract", "hidden", frm.doc.rent_type === "Contract" ? 1 : 0);
			grid.update_docfield_property("add_flat_to_contract", "hidden", frm.doc.rent_type === "Contract" ? 0 : 1);
			grid.refresh();
		}
		if (frm.is_new()) {
			frm.disable_save();
			frm.set_intro(__("Create a Flat using the Create Flat button on a submitted Flat Contract or Add Flat to Contract."));
		}
		frm.remove_custom_button(__("Renew"));
		frm.remove_custom_button(__("Terminate"));
		if (frm.doc.docstatus === 1 && frm.doc.flat_status !== "Inactive") {
			for (const action of ["Renew", "Terminate"]) {
				const direct = frm.doc.rent_type === "Direct Rent";
				const target = action === "Renew" ? (direct ? "Flat Contract Request" : "Add Flat to Contract") : (direct ? "Rent Termination Request" : "Flat Termination");
				if (!frappe.model.can_create(target)) continue;
				frm.add_custom_button(__(action), async () => {
					if (frm.is_dirty()) {
						frappe.msgprint(__("Save the Flat before starting an action."));
						return;
					}
					const result = await frappe.call({
						method: "administration.flat_lifecycle.start_action",
						args: {flat_name: frm.doc.name, action}, freeze: true,
					});
					if (result.message) frappe.set_route("Form", result.message.doctype, result.message.name);
				});
			}
		}
	},
});
