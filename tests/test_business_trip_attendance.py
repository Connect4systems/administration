"""Attendance lifecycle checks without requiring a Frappe bench."""
import datetime
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch


class AttendanceTests(unittest.TestCase):
    def setUp(self):
        self.frappe = types.ModuleType("frappe")
        self.frappe._ = lambda text: text
        self.frappe.throw = Mock(side_effect=ValueError("conflict"))
        self.frappe.db = types.SimpleNamespace(get_value=Mock(), exists=Mock(return_value=False))
        self.records = []
        def create(values):
            doc = types.SimpleNamespace(**values, flags=types.SimpleNamespace(), insert=Mock(), submit=Mock())
            self.records.append(doc)
            return doc
        self.frappe.get_doc = Mock(side_effect=create)
        utils = types.ModuleType("frappe.utils")
        utils.getdate = lambda value: datetime.date.fromisoformat(value) if isinstance(value, str) else value
        utils.add_days = lambda value, days: value + datetime.timedelta(days=days)
        document = types.ModuleType("frappe.model.document")
        document.Document = type("Document", (), {})
        policy = types.ModuleType("administration.leave_approval")
        policy.before_cancel = Mock()
        policy.sync_assignments = Mock()
        policy.validate_leave = Mock()
        self.modules = patch.dict(sys.modules, {"frappe": self.frappe, "frappe.utils": utils,
            "frappe.model.document": document, "administration.leave_approval": policy})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        path = Path(__file__).parents[1] / "administration/administration/doctype/business_trip_request/business_trip_request.py"
        spec = importlib.util.spec_from_file_location("trip_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.trip = module.BusinessTripRequest()
        for key, value in dict(employee="EMP", company="Company", name="TRIP", from_date="2026-10-01", to_date="2026-10-03").items():
            setattr(self.trip, key, value)

    def test_inclusive_range_submits_linked_present_attendance(self):
        self.trip.on_submit()
        self.assertEqual(len(self.records), 3)
        self.assertEqual([r.attendance_date.day for r in self.records], [1, 2, 3])
        for row in self.records:
            self.assertEqual(row.custom_business_trip_request, "TRIP")
            self.assertEqual(row.status, "Present")
            row.submit.assert_called_once()

    def test_conflict_preflight_creates_nothing(self):
        self.frappe.db.exists.side_effect = [False, True]
        with self.assertRaises(ValueError):
            self.trip.on_submit()
        self.assertEqual(self.records, [])

    def test_cancel_only_fetches_attendance_linked_to_this_trip(self):
        row = types.SimpleNamespace(docstatus=1, flags=types.SimpleNamespace(), cancel=Mock())
        self.frappe.get_all = Mock(return_value=["ATT"])
        self.frappe.get_doc.side_effect = None
        self.frappe.get_doc.return_value = row
        self.trip.on_cancel()
        self.assertEqual(self.frappe.get_all.call_args.kwargs["filters"]["custom_business_trip_request"], "TRIP")
        row.cancel.assert_called_once()
