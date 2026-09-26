frappe.listview_settings["Flat"] = {
	add_fields: ["flat_status"],
	get_indicator(doc) {
		if (doc.docstatus === 1 && doc.flat_status) {
			const colors = {Active: "green", Inactive: "gray", Expired: "orange"};
			return [__(doc.flat_status), colors[doc.flat_status] || "gray", "flat_status,=," + doc.flat_status];
		}
	},
	onload(listview) {
		listview.can_create = false;
		listview.page.clear_primary_action();
	},
};
