// Copyright (c) 2026, Connect 4 Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on("Service Vehicle Contract Request", {
	setup(frm) {
		frm.set_query("route", "contract_details", () => ({
			filters: frm.doc.project ? { project: frm.doc.project } : { name: ["=", ""] },
		}));
	},
});
