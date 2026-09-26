from unittest import TestCase
from unittest.mock import patch

from administration.administration.report.accommodation_report import accommodation_report as report


class Record(dict):
	__getattr__ = dict.get


class TestAccommodationReport(TestCase):
	def setUp(self):
		self.flats = [Record(name="F1"), Record(name="F2")]
		self.rooms = [Record(name="R1", flat="F1"), Record(name="R2", flat="F1")]
		self.beds = [
			Record(name="B1", flat="F1", room="R1", status="Booked", employee="E1"),
			Record(name="B2", flat="F1", room="R1", status="Open", employee=None),
			Record(name="B3", flat="F2", room=None, status="Open", employee=None),
		]

	def test_beds_keep_room_flat_and_employee_relationships(self):
		rows = report.build_rows(
			self.flats, self.rooms, self.beds,
			[{"name": "E1", "employee_name": "Employee One"}], {},
		)
		self.assertEqual(len(rows), 4)
		self.assertEqual((rows[0]["flat"], rows[0]["room"], rows[0]["employee_name"]),
			("F1", "R1", "Employee One"))
		self.assertEqual(rows[1]["bed"], "B2")
		self.assertEqual(rows[2]["room"], "R2")
		self.assertNotIn("bed", rows[2])
		self.assertEqual(rows[3]["bed"], "B3")
		self.assertIsNone(rows[3]["room"])

	def test_empty_flats_and_rooms_are_hidden_when_filtering_beds(self):
		for filters in ({"employee": "E1"}, {"bed_status": "Booked"}):
			rows = report.build_rows(self.flats, self.rooms, self.beds[:1], [], filters)
			self.assertEqual([row["bed"] for row in rows], ["B1"])
		rows = report.build_rows(self.flats, [], [], [], {})
		self.assertEqual([row["flat"] for row in rows], ["F1", "F2"])

	@patch.object(report, "frappe")
	def test_queries_apply_status_and_all_standard_filters(self, frappe):
		frappe.get_list.side_effect = [self.flats, self.rooms, self.beds[:1], []]
		report.execute({"project": "P1", "governorate": "G1", "rent_type": "Contract",
			"bed_status": "Booked", "employee": "E1"})
		calls = frappe.get_list.call_args_list
		self.assertEqual(calls[0].kwargs["filters"], {
			"flat_status": ["in", ["Active", "Expired"]], "docstatus": 1,
			"project": "P1", "governorate": "G1", "rent_type": "Contract",
		})
		self.assertEqual(calls[2].kwargs["filters"], {
			"flat": ["in", ["F1", "F2"]], "status": "Booked", "employee": "E1",
		})
		self.assertTrue(all(call.kwargs["limit_page_length"] == 0 for call in calls))

	@patch.object(report, "frappe")
	def test_no_matching_flats_skips_other_queries(self, frappe):
		frappe.get_list.return_value = []
		columns, rows = report.execute()
		self.assertEqual(rows, [])
		self.assertEqual(len(columns), 11)
		frappe.get_list.assert_called_once()
