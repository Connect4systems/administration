from unittest import TestCase
from unittest.mock import Mock, patch

from administration.administration.doctype.service_vehicle_contract import service_vehicle_contract as controller


class TestServiceVehicleContractNaming(TestCase):
	def test_project_and_year_naming(self):
		doc = Mock(project="PROJECT-001")
		with patch.object(controller, "frappe") as frappe, \
			patch.object(controller, "nowdate", return_value="2026-10-14"), \
			patch.object(controller, "getseries", return_value="001") as series:
			frappe.db.get_value.return_value = " ABC "
			controller.ServiceVehicleContract.autoname(doc)
			self.assertEqual(doc.name, "ABC-26-001")
			series.assert_called_once_with("ABC-26-", 3)
			frappe.db.get_value.assert_called_once_with("Project", "PROJECT-001", "custom_abbreviation")

	def test_missing_project_or_abbreviation_is_rejected(self):
		for project, abbreviation in ((None, "ABC"), ("PROJECT-001", " "), ("PROJECT-001", None)):
			with self.subTest(project=project, abbreviation=abbreviation):
				doc = Mock(project=project)
				with patch.object(controller, "frappe") as frappe, patch.object(controller, "getseries") as series:
					frappe.throw.side_effect = ValueError
					frappe.db.get_value.return_value = abbreviation
					with self.assertRaises(ValueError):
						controller.ServiceVehicleContract.autoname(doc)
					series.assert_not_called()


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
