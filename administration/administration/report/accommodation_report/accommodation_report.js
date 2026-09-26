frappe.query_reports["Accommodation Report"] = {
	filters: [
		{fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Project"},
		{fieldname: "governorate", label: __("Governorate"), fieldtype: "Link", options: "Governorate"},
		{fieldname: "bed_status", label: __("Bed Status"), fieldtype: "Select", options: "\nOpen\nBooked"},
		{fieldname: "employee", label: __("Employee"), fieldtype: "Link", options: "Employee"},
		{fieldname: "rent_type", label: __("Rent Type"), fieldtype: "Select", options: "\nDirect Rent\nContract"},
	],
};
