from unittest import TestCase
from unittest.mock import Mock, patch

from administration.administration.doctype.service_vehicle_contract import service_vehicle_contract as controller


class TestServiceVehicleContractNaming(TestCase):
	def test_project_abbreviation_and_title_naming(self):
		doc = Mock(project="PROJECT-001", title=" Staff Transport ")
		with patch.object(controller, "frappe") as frappe:
			frappe.db.get_value.return_value = " ABC "
			controller.ServiceVehicleContract.autoname(doc)
			self.assertEqual(doc.name, "ABC-Staff Transport")
			self.assertEqual(doc.title, "Staff Transport")
			frappe.db.get_value.assert_called_once_with("Project", "PROJECT-001", "custom_abbreviation")

	def test_missing_project_abbreviation_or_title_is_rejected(self):
		for project, abbreviation, title in (
			(None, "ABC", "Transport"), ("PROJECT-001", " ", "Transport"),
			("PROJECT-001", None, "Transport"), ("PROJECT-001", "ABC", None),
			("PROJECT-001", "ABC", "   "),
		):
			with self.subTest(project=project, abbreviation=abbreviation, title=title):
				doc = Mock(project=project, title=title)
				with patch.object(controller, "frappe") as frappe:
					frappe.throw.side_effect = ValueError
					frappe.db.get_value.return_value = abbreviation
					with self.assertRaises(ValueError):
						controller.ServiceVehicleContract.autoname(doc)


class TestContractAttachmentPermissions(TestCase):
	def test_attachment_changes_require_legal_role(self):
		for role in ("Fleet Manager", "Administration Manager", "System Manager", "Legal User", "Legal Manager"):
			for old, new in ((None, "/private/files/contract.pdf"), ("old.pdf", "new.pdf"), ("old.pdf", None)):
				with self.subTest(role=role, old=old, new=new), patch.object(controller, "frappe") as frappe:
					frappe.get_roles.return_value = [role]
					frappe.PermissionError = PermissionError
					frappe.throw.side_effect = PermissionError
					doc = Mock()
					doc.get.return_value = new
					doc.get_doc_before_save.return_value = {"attach_contract": old} if old else None
					if role in ("Legal User", "Legal Manager"):
						controller.ServiceVehicleContract.validate_contract_attachment(doc)
						frappe.throw.assert_not_called()
					else:
						with self.assertRaises(PermissionError):
							controller.ServiceVehicleContract.validate_contract_attachment(doc)

	def test_unchanged_attachment_does_not_block_other_edits(self):
		with patch.object(controller, "frappe") as frappe:
			frappe.get_roles.return_value = ["Fleet Manager"]
			for value in (None, "/private/files/contract.pdf"):
				doc = Mock()
				doc.get.return_value = value
				doc.get_doc_before_save.return_value = {"attach_contract": value}
				controller.ServiceVehicleContract.validate_contract_attachment(doc)
			frappe.throw.assert_not_called()
