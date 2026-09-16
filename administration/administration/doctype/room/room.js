// Copyright (c) 2025, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Room", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
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
