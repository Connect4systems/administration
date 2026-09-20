from pathlib import PurePosixPath

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils.file_manager import check_max_file_size, get_max_file_size


UPLOAD_EXTENSIONS = {
	"custom_photo": {".png", ".jpg", ".jpeg", ".gif"},
	"resume_attachment": {".pdf", ".doc", ".docx"},
}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=60)
def upload_application_file(fieldname):
	"""Accept a private attachment before the public application is submitted."""
	form = frappe.get_doc("Web Form", "job-application")
	if not form.published or form.login_required or form.doc_type != "Job Applicant":
		frappe.throw(_("Guest application uploads are not available."), frappe.PermissionError)
	allowed = UPLOAD_EXTENSIONS.get(fieldname)
	if not allowed or not any(field.fieldname == fieldname for field in form.web_form_fields):
		frappe.throw(_("Please upload through the Photo or CV field."))
	upload = frappe.request.files.get("file")
	if upload is None or not upload.filename:
		frappe.throw(_("Please select a file."))
	filename = PurePosixPath(upload.filename.replace(chr(92), "/")).name
	if PurePosixPath(filename).suffix.lower() not in allowed:
		frappe.throw(_("Allowed file formats: {0}").format(", ".join(sorted(allowed))))
	content = upload.stream.read(get_max_file_size() + 1)
	check_max_file_size(content)
	if not content:
		frappe.throw(_("The selected file is empty."))
	# Frappe also enforces configured extension limits when saving.
	# Web form submission links this private file to the new Job Applicant.
	file = frappe.get_doc({
		"doctype": "File",
		"file_name": filename,
		"content": content,
		"is_private": 1,
	}).save(ignore_permissions=True)
	return {"file_url": file.file_url, "file_name": file.file_name}
