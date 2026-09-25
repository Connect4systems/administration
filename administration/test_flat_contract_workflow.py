from unittest import TestCase
from unittest.mock import Mock, patch

from administration import flat_contract_workflow as config
from administration import add_flat_to_contract_workflow as contract
from administration import flat_request_workflow as workflow
from administration.test_flat_request_workflow import Record


class TestFlatContractWorkflow(TestCase):
	def test_legal_review_and_downstream_routing(self):
		self.assertEqual(config.TRANSITIONS[:4], (
			("Draft", "Request", "Legal Manager", "Legal User"),
			("Legal User", "Request", "Legal Manager", "Legal User"),
			("Legal Manager", "Review", "Legal User", "Legal Manager"),
			("Legal Manager", "Approve", "Admin Team leader", "Legal Manager"),
		))
		self.assertEqual(config.TRANSITIONS[4:], contract.TRANSITIONS[1:])
		self.assertEqual([state for state, status, role in config.STATES if status == 1], ["Approved"])

	def test_only_legal_user_can_create(self):
		with patch.object(config, "frappe") as frappe:
			frappe.PermissionError = PermissionError
			frappe.throw.side_effect = PermissionError
			for role in ("System Manager", "Legal Manager", "Admin supervisor (Accommodation)"):
				frappe.get_roles.return_value = [role]
				with self.assertRaises(PermissionError):
					config.require_legal_creator()
			frappe.get_roles.return_value = ["Legal User"]
			config.require_legal_creator()

	def test_request_requires_contract_attachment_but_draft_can_be_saved(self):
		with patch.object(config, "frappe") as frappe:
			frappe.throw.side_effect = ValueError
			with self.assertRaises(ValueError):
				config.validate_request(Record(), "Request")
			config.validate_request(Record(attach_contract="/private/files/contract.pdf"), "Request")

	def test_each_transition_records_one_audit_row(self):
		for start, action, end, role in config.TRANSITIONS:
			with self.subTest(start=start, action=action), patch.object(workflow, "frappe") as frappe:
				frappe.flags = Record()
				frappe.session.user = "legal@example.com"
				frappe.db.get_value.return_value = "Legal Approver"
				frappe.throw.side_effect = ValueError
				current = Record(doctype="Flat Contract", name="FC-001", workflow_state=start,
					modified="time", attach_contract="/private/files/contract.pdf")
				current.check_permission = Mock()
				current.as_dict = lambda: dict(current)
				frappe.get_doc.return_value = current
				doc = Record(doctype=current.doctype, name=current.name, workflow_state=end, document_approval=[])
				doc.get_doc_before_save = lambda: current
				doc.append = lambda field, row: doc[field].append(row)
				with patch.object(workflow, "get_workflow", return_value=Record(workflow_state_field="workflow_state")), \
					patch.object(workflow, "get_transitions", return_value=[Record(action=action, next_state=end, allowed=role)]), \
					patch.object(workflow, "has_approval_access", return_value=True), \
					patch.object(workflow, "core_apply_workflow", side_effect=lambda *_: workflow.validate_approval_history(doc)):
					workflow.apply_workflow(dict(current, __approval_note=""), action)
				self.assertEqual(len(doc.document_approval), 1)
				self.assertEqual(doc.document_approval[0]['status'], end)
				self.assertEqual(doc.document_approval[0]['approved_by_role'], role)

	def test_migration_revokes_other_create_permissions(self):
		with patch.object(config, "setup_approval_workflow"), patch.object(config, "frappe") as frappe:
			frappe.get_all.return_value = [Record(name=role, role=role, permlevel=0) for role in ("Legal User", "Legal Manager", "System Manager")]
			config.setup_workflow()
			for role, allowed in (("Legal User", 1), ("Legal Manager", 0), ("System Manager", 0)):
				frappe.db.set_value.assert_any_call("Custom DocPerm", role, "create", allowed)
