frappe.ui.form.on("Job Applicant", {
	custom_photo(frm) {
		frm.refresh_field("custom_image");
	},
});
