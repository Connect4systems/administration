# Copyright (c) 2025, Connect 4 Systems and Contributors
# See license.txt

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from administration.administration.doctype.bed import bed as module


class TestBed(TestCase):
	def setUp(self):
		patcher = patch.object(module, "frappe")
		self.frappe = patcher.start()
		self.addCleanup(patcher.stop)
		self.frappe.throw.side_effect = ValueError
		self.bed = SimpleNamespace(name="B2", flat="F2", room=None, employee="E1")

	def test_duplicate_is_blocked_with_existing_bed_and_flat(self):
		self.frappe.db.sql.side_effect = [[], [SimpleNamespace(name="B1", flat="F1")]]
		with self.assertRaises(ValueError):
			module.Bed.validate(self.bed)
		message = self.frappe.throw.call_args.args[0]
		for value in ("E1", "B1", "F1", "release"):
			self.assertIn(value, message)
		calls = self.frappe.db.sql.call_args_list
		self.assertIn("tabEmployee", calls[0].args[0])
		self.assertIn("for update", calls[0].args[0])
		self.assertIn("for update", calls[1].args[0])
		self.assertEqual(calls[1].args[1], ("E1", "B2"))

	def test_unassigned_employee_can_book_and_current_bed_is_excluded(self):
		self.frappe.db.sql.return_value = []
		module.Bed.validate(self.bed)
		self.assertEqual(self.bed.status, "Booked")
		self.assertEqual(self.frappe.db.sql.call_args.args[1], ("E1", "B2"))

	def test_releasing_bed_does_not_check_duplicate(self):
		self.bed.employee = None
		module.Bed.validate(self.bed)
		self.assertEqual(self.bed.status, "Open")
		self.assertIsNone(self.bed.employee_status)
		self.frappe.db.sql.assert_not_called()

	def test_selection_alert_and_html_escaping(self):
		self.frappe.db.sql.return_value = [SimpleNamespace(name="B<1>", flat="F1")]
		message = module.check_employee_assignment("E1", "B2")
		self.assertIn("B&lt;1&gt;", message)
		self.assertNotIn("for update", self.frappe.db.sql.call_args.args[0])

	def test_selection_check_requires_bed_permission(self):
		self.frappe.has_permission.return_value = False
		with self.assertRaises(ValueError):
			module.check_employee_assignment("E1")
		self.frappe.db.sql.assert_not_called()
