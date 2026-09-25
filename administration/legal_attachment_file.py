from frappe.core.doctype.file.file import File

from administration.flat_contract_attachments import validate_file_change


class LegalAttachmentFile(File):
	"""Check before File lifecycle methods can write, move or delete a blob."""

	def before_insert(self):
		validate_file_change(self)
		super().before_insert()

	def validate(self):
		validate_file_change(self)
		super().validate()

	def on_trash(self):
		validate_file_change(self)
		super().on_trash()
