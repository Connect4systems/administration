frappe.query_reports["Accommodation Report"] = {
	formatter(value, row, column, data, default_formatter) {
		if (column.fieldname === "employee" && data?.employee) {
			const label = data.employee_name ? `${data.employee} - ${data.employee_name}` : data.employee;
			const href = `/app/employee/${encodeURIComponent(data.employee)}`;
			return `<a href="${frappe.utils.escape_html(href)}">${frappe.utils.escape_html(label)}</a>`;
		}
		return default_formatter(value, row, column, data);
	},
	filters: [
		{fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Project"},
		{fieldname: "governorate", label: __("Governorate"), fieldtype: "Link", options: "Governorate"},
		{fieldname: "bed_status", label: __("Bed Status"), fieldtype: "Select", options: "\nOpen\nBooked"},
		{fieldname: "employee", label: __("Employee"), fieldtype: "Link", options: "Employee"},
		{fieldname: "rent_type", label: __("Rent Type"), fieldtype: "Select", options: "\nDirect Rent\nContract"},
	],
};
