frappe.query_reports["Flat Report"] = {
	filters: [
		{fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Project"},
		{fieldname: "governorate", label: __("Governorate"), fieldtype: "Link", options: "Governorate"},
		{fieldname: "rent_type", label: __("Rent Type"), fieldtype: "Select", options: "\nDirect Rent\nContract"},
		{fieldname: "flat_status", label: __("Flat Status"), fieldtype: "Select", options: "\nActive\nInactive\nExpired"},
	],
};
