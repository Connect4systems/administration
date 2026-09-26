frappe.listview_settings["Legal document"] = {
	add_fields: ["status"],
	get_indicator(doc) {
		const colors = { Active: "blue", "Renew Now": "green", Expire: "red" };
		if (colors[doc.status]) {
			return [__(doc.status), colors[doc.status], `status,=,${doc.status}`];
		}
	},
};
