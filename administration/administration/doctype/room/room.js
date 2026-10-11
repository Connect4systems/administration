// Copyright (c) 2025, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Room", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}
		frm.remove_custom_button(__("Create Bed"));
		if (frm.doc.flat && frappe.model.can_create("Bed")) {
			frm.add_custom_button(__("Create Bed"), () => {
				if (frm.is_dirty()) {
					frappe.msgprint(__("Save the Room before creating a Bed."));
					return;
				}
				return frappe.new_doc("Bed", {flat: frm.doc.flat, room: frm.doc.name});
			});
		}

		frm.add_custom_button(__("Employee Left"), () => {
			frappe.confirm(
				__("Clear all employees from this room's beds?"),
				() => {
					frappe.call({
						method: "administration.administration.doctype.room.room.employee_left",
						args: { room_name: frm.doc.name },
						freeze: true,
						callback: () => frm.reload_doc(),
					});
				}
			);
		});
	},
});
