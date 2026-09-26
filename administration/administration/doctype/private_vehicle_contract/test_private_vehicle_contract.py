from unittest import TestCase
from unittest.mock import Mock, patch

from administration.administration.doctype.private_vehicle_contract import private_vehicle_contract as controller


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
					doc.get_doc_before_save.return_value = {"contract_attachment": old} if old else None
					if role in ("Legal User", "Legal Manager"):
						controller.PrivateVehicleContract.validate_contract_attachment(doc)
						frappe.throw.assert_not_called()
					else:
						with self.assertRaises(PermissionError):
							controller.PrivateVehicleContract.validate_contract_attachment(doc)

	def test_unchanged_attachment_does_not_block_other_edits(self):
		with patch.object(controller, "frappe") as frappe:
			frappe.get_roles.return_value = ["Fleet Manager"]
			for value in (None, "/private/files/contract.pdf"):
				doc = Mock()
				doc.get.return_value = value
				doc.get_doc_before_save.return_value = {"contract_attachment": value}
				controller.PrivateVehicleContract.validate_contract_attachment(doc)
			frappe.throw.assert_not_called()
