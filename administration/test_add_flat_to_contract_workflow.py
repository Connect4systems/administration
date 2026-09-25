from unittest import TestCase
from unittest.mock import Mock, patch

from administration import add_flat_to_contract_workflow as config
from administration import flat_request_workflow as workflow
from administration.test_flat_request_workflow import Record


class TestAddFlatToContractWorkflow(TestCase):
	def test_routing_matches_requested_start_and_screenshot(self):
		self.assertEqual(config.TRANSITIONS[0],
			("Draft", "Request", "Administration Manager", workflow.SUPERVISOR))
		self.assertEqual(config.TRANSITIONS[2:], workflow.TRANSITIONS[6:])
		self.assertIn(("Admin Team leader", "Approve", "Administration Manager", workflow.SUPERVISOR), config.TRANSITIONS)
		self.assertEqual([state for state, status, role in config.STATES if status == 1], ["Approved"])

	def test_setup_targets_its_own_workflow(self):
		with patch.object(config, "setup_approval_workflow") as setup:
			config.setup_workflow()
			setup.assert_called_once_with(doctype="Add Flat to Contract", states=config.STATES,
				transitions=config.TRANSITIONS, creator_role=workflow.SUPERVISOR)

	def test_every_action_records_history_and_attachments_on_correct_document(self):
		for start, action, end, role in config.TRANSITIONS:
			with self.subTest(start=start, action=action), patch.object(workflow, "frappe") as frappe:
				frappe.flags = Record()
				frappe.session.user = "approver@example.com"
				frappe.db.get_value.return_value = "Approver"
				frappe.throw.side_effect = ValueError
				current = Record(doctype="Add Flat to Contract", name="AFTC-001", workflow_state=start, modified="time")
				current.check_permission = Mock()
				current.as_dict = lambda: dict(current)
				file = Record(name="file-1", file_name="evidence.pdf", attached_to_doctype=current.doctype,
					attached_to_name=current.name, check_permission=Mock())
				frappe.get_doc.side_effect = [current, file]
				doc = Record(doctype=current.doctype, name=current.name, workflow_state=end, document_approval=[])
				doc.get_doc_before_save = lambda: current
				doc.append = lambda field, row: doc[field].append(row)
				with patch.object(workflow, "get_workflow", return_value=Record(workflow_state_field="workflow_state")), \
					patch.object(workflow, "get_transitions", return_value=[Record(action=action, next_state=end, allowed=role)]), \
					patch.object(workflow, "has_approval_access", return_value=True), \
					patch.object(workflow, "core_apply_workflow", side_effect=lambda *_: workflow.validate_approval_history(doc)):
					workflow.apply_workflow(dict(current, __approval_attachments=[file.name]), action)
				self.assertEqual(len(doc.document_approval), 1)
				row = doc.document_approval[0]
				self.assertEqual((row['from_status'], row['status'], row['action'], row['approved_by_role']), (start, end, action, role))
				self.assertEqual(row['note'], '')
				self.assertIn('evidence.pdf', row['attachments'])
				self.assertIsNone(frappe.flags.flat_request_approval)

	def test_context_from_another_doctype_cannot_submit(self):
		with patch.object(workflow, "frappe") as frappe:
			frappe.throw.side_effect = ValueError
			doc = Record(doctype="Add Flat to Contract", name="same-name", workflow_state="Approved")
			frappe.flags = Record(flat_request_approval=dict(token=workflow._APPROVAL_TOKEN,
				name=doc.name, status="Approved", doctype="Flat Request"))
			with self.assertRaises(ValueError):
				workflow.require_workflow_submission(doc)
			frappe.flags.flat_request_approval['doctype'] = doc.doctype
			workflow.require_workflow_submission(doc)
