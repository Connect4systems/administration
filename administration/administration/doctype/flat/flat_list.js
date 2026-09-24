frappe.listview_settings["Flat"] = {
	onload(listview) {
		listview.can_create = false;
		listview.page.clear_primary_action();
	},
};
