// Copyright (c) 2026, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Vehicle Request", {
	setup(frm) {
		frm.set_query("employee", () => ({
			filters: { status: "Active", custom_transportation: "Privat car" },
		}));
		frm.set_query("code", "employees", () => ({
			filters: { status: "Active", custom_transportation: "Shared" },
		}));
	},
});
