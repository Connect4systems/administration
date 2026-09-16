// Copyright (c) 2026, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Flat Contract", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		frm.add_custom_button(__("Create Flat"), () => {
			frappe.model.with_doctype("Flat", () => {
				const flat = frappe.model.get_new_doc("Flat");
				const field_map = {
					project: "project",
					governorate: "governorate",
					city: "city",
					address: "address",
					flat_owner: "flat_owner",
					owner_name: "second_party_name",
					no_of_beds: "no_of_beds",
					rent_start_date: "contract_start_date",
					rent_end_date: "contract_end_date",
					payment_schedule: "payment_cycle",
					rent: "monthly_rent",
					security_deposit: "deposit",
					rent_contract: "name",
				};

				Object.entries(field_map).forEach(([flat_field, contract_field]) => {
					flat[flat_field] = frm.doc[contract_field] || "";
				});
				flat.flat_title = frm.doc.flat_no || frm.doc.name;
				flat.no_of_room = frm.doc.no_of_rooms || "";

				(frm.doc.flat_contents || []).forEach((row) => {
					const content = frappe.model.add_child(flat, "Flat Contents", "flat_contents");
					["item_name", "description", "qty", "image"].forEach((fieldname) => {
						content[fieldname] = row[fieldname];
					});
				});

				frappe.model.sync(flat);
				frappe.set_route("Form", "Flat", flat.name);
			});
		});
	},
});
