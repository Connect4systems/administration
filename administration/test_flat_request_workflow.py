import json
from unittest import TestCase
from unittest.mock import Mock, patch

from administration import flat_request_workflow as workflow


class Record(dict):
	__getattr__ = dict.get
	__setattr__ = dict.__setitem__


class TestFlatRequestWorkflow(TestCase):
	def setUp(self):
		self.patcher = patch.object(workflow, "frappe")
		self.frappe = self.patcher.start()
		self.addCleanup(self.patcher.stop)
		self.frappe.flags = Record()
		self.frappe.session.user = "manager@example.com"
		self.frappe.PermissionError = PermissionError
		self.frappe.throw.side_effect = ValueError
		self.frappe.db.get_value.return_value = "Test Manager"
		self.current = Record(name="FRQ-001", workflow_state="Pending Project Manger", modified="2026-09-25 12:00:00")
		self.current.check_permission = Mock()
		self.current.as_dict = lambda: dict(self.current)
		self.frappe.get_doc.return_value = self.current
		self.payload = dict(doctype="Flat Request", name="FRQ-001", workflow_state=self.current.workflow_state,
			modified=self.current.modified, __approval_note="  Reviewed  ")

	def test_screenshot_transitions_and_document_statuses(self):
		self.assertEqual(len(workflow.TRANSITIONS), 14)
		states = {name: (status, role) for name, status, role in workflow.STATES}
		for start, action, end, role in workflow.TRANSITIONS:
			self.assertIn(start, states)
			self.assertIn(end, states)
			self.assertEqual(role, states[start][1])
			self.assertIn(action, ("Request", "Approve", "Reject", "Review", "Settled"))
		self.assertEqual(states["Approved"][0], 1)
		self.assertEqual(states["Settled"][0], 1)
		self.assertEqual(states["Rejected"][0], 0)
		self.assertIn(("Administration Manager", "Review", "Admin Team leader", "Administration Manager"), workflow.TRANSITIONS)
		self.assertFalse(any("AP Team Leader" in row for row in workflow.TRANSITIONS))

	def test_other_doctypes_keep_standard_workflow(self):
		with patch.object(workflow, "core_apply_workflow", return_value="unchanged") as core:
			self.assertEqual(workflow.apply_workflow({"doctype": "Purchase Order"}, "Approve"), "unchanged")
			core.assert_called_once_with({"doctype": "Purchase Order"}, "Approve")

	def test_non_text_note_is_rejected(self):
		for note in (["invalid"], 123):
			self.payload["__approval_note"] = note
			with self.subTest(note=note), self.assertRaises(ValueError):
				workflow.apply_workflow(self.payload, "Approve")
		self.frappe.get_doc.assert_not_called()

	def test_stale_workflow_action_is_rejected(self):
		self.payload["modified"] = "old version"
		with patch.object(workflow, "get_workflow", return_value=Record(workflow_state_field="workflow_state")):
			with self.assertRaises(ValueError):
				workflow.apply_workflow(self.payload, "Approve")

	def test_blank_notes_are_allowed(self):
		transition = Record(action="Approve", allowed="Project Manager", next_state="Admin Team leader")
		with patch.object(workflow, "get_workflow", return_value=Record(workflow_state_field="workflow_state")), \
			patch.object(workflow, "get_transitions", return_value=[transition]), \
			patch.object(workflow, "has_approval_access", return_value=True), \
			patch.object(workflow, "core_apply_workflow", side_effect=lambda *_: self.frappe.flags.flat_request_approval["note"]):
			for note in (None, "", "   "):
				self.payload["__approval_note"] = note
				self.assertEqual(workflow.apply_workflow(self.payload, "Approve"), "")

	def test_multiple_attachments_are_checked_and_deduplicated(self):
		files = [Record(name=name, file_name=name + ".pdf", attached_to_doctype="Flat Request",
			attached_to_name="FRQ-001", check_permission=Mock()) for name in ("file-1", "file-2")]
		self.frappe.get_doc.side_effect = files
		value = workflow.get_approval_attachments(["file-1", "file-2", "file-1"], "FRQ-001")
		self.assertEqual(json.loads(value), [{"name": file.name, "file_name": file.file_name} for file in files])
		for file in files:
			file.check_permission.assert_called_once_with("read")
		self.assertEqual(workflow.get_approval_attachments([], "FRQ-001"), "")

	def test_unrelated_and_invalid_attachments_are_rejected(self):
		self.frappe.get_doc.return_value = Record(attached_to_doctype="Flat Request",
			attached_to_name="OTHER", check_permission=Mock())
		for value in (["file-1"], "file-1", [{}]):
			with self.subTest(value=value), self.assertRaises(ValueError):
				workflow.get_approval_attachments(value, "FRQ-001")

	def test_attachment_history_cannot_be_changed(self):
		previous = Record(workflow_state="Draft", document_approval=[Record(attachments="original")])
		doc = Record(workflow_state="Draft", document_approval=[Record(attachments="changed")])
		doc.get_doc_before_save = lambda: previous
		with self.assertRaises(ValueError):
			workflow.validate_approval_history(doc)

	def test_disallowed_role_and_self_approval_are_rejected(self):
		transition = Record(action="Approve", allowed="Project Manager", next_state="Admin Team leader")
		for transitions, access in (([], True), ([transition], False)):
			with patch.object(workflow, "get_workflow", return_value=Record(workflow_state_field="workflow_state")), \
				patch.object(workflow, "get_transitions", return_value=transitions), \
				patch.object(workflow, "has_approval_access", return_value=access), \
				patch.object(workflow, "core_apply_workflow") as core:
				with self.assertRaises(ValueError):
					workflow.apply_workflow(self.payload, "Approve")
				core.assert_not_called()

	def test_action_records_trusted_identity_role_time_note_and_status(self):
		transition = Record(action="Approve", allowed="Project Manager", next_state="Admin Team leader")
		previous = Record(workflow_state=self.current.workflow_state, document_approval=[])
		doc = Record(name="FRQ-001", workflow_state=transition.next_state, document_approval=[])
		doc.get_doc_before_save = lambda: previous
		doc.append = lambda field, row: doc[field].append(row)
		with patch.object(workflow, "get_workflow", return_value=Record(workflow_state_field="workflow_state")), \
			patch.object(workflow, "get_transitions", return_value=[transition]), \
			patch.object(workflow, "has_approval_access", return_value=True), \
			patch.object(workflow, "now_datetime", return_value="server time"), \
			patch.object(workflow, "core_apply_workflow", side_effect=lambda *_: workflow.validate_approval_history(doc)):
			workflow.apply_workflow(self.payload, "Approve")
		self.assertEqual(doc.document_approval, [{
			"status": "Admin Team leader", "from_status": "Pending Project Manger", "action": "Approve",
			"approved_by_role": "Project Manager", "approved_by_user": "manager@example.com",
			"user_name": "Test Manager", "action_date": "server time", "note": "Reviewed", "attachments": "",
		}])
		self.assertIsNone(self.frappe.flags.flat_request_approval)
		self.frappe.get_doc.assert_called_once_with("Flat Request", "FRQ-001", for_update=True)

	def test_context_is_cleared_on_failure(self):
		transition = Record(action="Approve", allowed="Project Manager", next_state="Admin Team leader")
		with patch.object(workflow, "get_workflow", return_value=Record(workflow_state_field="workflow_state")), \
			patch.object(workflow, "get_transitions", return_value=[transition]), \
			patch.object(workflow, "has_approval_access", return_value=True), \
			patch.object(workflow, "core_apply_workflow", side_effect=RuntimeError):
			with self.assertRaises(RuntimeError):
				workflow.apply_workflow(self.payload, "Approve")
		self.assertIsNone(self.frappe.flags.flat_request_approval)

	def test_manual_history_changes_and_status_changes_are_rejected(self):
		previous = Record(workflow_state="Draft", document_approval=[Record(name="row-1", note="Original")])
		for rows, state in (([], "Draft"), ([Record(name="row-1", note="Forged")], "Draft"),
			(previous.document_approval, "Approved")):
			doc = Record(name="FRQ-001", workflow_state=state, document_approval=rows)
			doc.get_doc_before_save = lambda: previous
			with self.subTest(rows=rows, state=state), self.assertRaises(ValueError):
				workflow.validate_approval_history(doc)

	def test_new_draft_and_ordinary_saves_do_not_create_fake_approvals(self):
		for previous in (None, Record(workflow_state="Draft", document_approval=[])):
			doc = Record(workflow_state="Draft", document_approval=[])
			doc.get_doc_before_save = lambda: previous
			workflow.validate_approval_history(doc)
			self.assertEqual(doc.document_approval, [])

	def test_direct_submission_requires_the_trusted_workflow_context(self):
		doc = Record(name="FRQ-001", workflow_state="Approved")
		with self.assertRaises(ValueError):
			workflow.require_workflow_submission(doc)
		self.frappe.flags.flat_request_approval = {
			"token": workflow._APPROVAL_TOKEN, "name": doc.name, "status": "Approved",
		}
		workflow.require_workflow_submission(doc)
		doc.workflow_state = "Draft"
		with self.assertRaises(ValueError):
			workflow.require_workflow_submission(doc)

	def test_every_configured_action_appends_one_row_including_rejection_and_review(self):
		for start, action, end, role in workflow.TRANSITIONS:
			with self.subTest(start=start, action=action):
				previous = Record(workflow_state=start, document_approval=[])
				doc = Record(name="FRQ-001", workflow_state=end, document_approval=[])
				doc.get_doc_before_save = lambda: previous
				doc.append = lambda field, row: doc[field].append(row)
				self.frappe.flags.flat_request_approval = {
					"token": workflow._APPROVAL_TOKEN, "name": doc.name, "from_status": start,
					"status": end, "action": action, "approved_by_role": role, "note": "Reason",
				}
				workflow.validate_approval_history(doc)
				self.assertEqual(len(doc.document_approval), 1)
				self.assertEqual(doc.document_approval[0]["status"], end)
				self.assertEqual(doc.document_approval[0]["approved_by_role"], role)
