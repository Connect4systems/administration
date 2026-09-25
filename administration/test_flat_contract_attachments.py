from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from administration import flat_contract_attachments as policy


def record(values, previous=None):
	return SimpleNamespace(get=values.get, get_doc_before_save=lambda: previous,
		meta=SimpleNamespace(fields=[SimpleNamespace(fieldname="attachment", fieldtype="Attach")]))


class TestContractAttachments(TestCase):
	def setUp(self):
		self.patcher = patch.object(policy, "frappe")
		self.frappe = self.patcher.start()
		self.addCleanup(self.patcher.stop)
		self.frappe.PermissionError = PermissionError
		self.frappe.throw.side_effect = PermissionError
		self.frappe.get_roles.return_value = ["System Manager"]

	def test_nonlegal_cannot_add_clear_or_replace_fields(self):
		for old, new in ((None, "file.pdf"), ("file.pdf", ""), ("old.pdf", "new.pdf")):
			with self.subTest(old=old, new=new), self.assertRaises(PermissionError):
				policy.validate_contract_attachments(record({"attachment": new}, record({"attachment": old})))

	def test_unchanged_fields_and_empty_new_contract_are_allowed(self):
		policy.validate_contract_attachments(record({"attachment": "same.pdf"}, record({"attachment": "same.pdf"})))
		policy.validate_contract_attachments(record({}))
		self.frappe.throw.assert_not_called()

	def test_each_legal_role_can_change_attachments(self):
		for role in policy.LEGAL_ROLES:
			self.frappe.get_roles.return_value = [role]
			policy.validate_contract_attachments(record({"attachment": "file.pdf"}))
			policy.validate_contract_attachments(record({}, record({"attachment": "file.pdf"})))
			policy.validate_file_change(record({"attached_to_doctype": "Flat Contract"}))

	def test_files_cannot_be_added_removed_or_reassigned_by_nonlegal(self):
		for current, old in (("Flat Contract", None), ("", "Flat Contract"), ("Other", "Flat Contract")):
			with self.subTest(current=current, old=old), self.assertRaises(PermissionError):
				policy.validate_file_change(record({"attached_to_doctype": current}, record({"attached_to_doctype": old})))

	def test_other_document_attachments_are_unaffected(self):
		policy.validate_file_change(record({"attached_to_doctype": "Flat Request"}))
		self.frappe.get_roles.assert_not_called()

	def test_file_lifecycle_checks_before_filesystem_operations(self):
		from administration.legal_attachment_file import LegalAttachmentFile
		for event in ("before_insert", "validate", "on_trash"):
			with self.subTest(event=event), patch("administration.legal_attachment_file.validate_file_change", side_effect=PermissionError), \
				patch.object(LegalAttachmentFile.__bases__[0], event) as original:
				with self.assertRaises(PermissionError):
					getattr(LegalAttachmentFile, event)(Mock())
				original.assert_not_called()
