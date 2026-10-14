from datetime import date
from unittest import TestCase
from unittest.mock import patch

from administration.administration.report.flat_report import flat_report as report


class TestFlatReport(TestCase):
	def test_counts_connections_including_beds_without_rooms(self):
		flats = [{"name": "F1", "rent": 1500, "no_of_room": 9, "no_of_beds": 99}, {"name": "F2"}]
		rooms = [{"flat": "F1"}, {"flat": "F1"}]
		beds = [
			{"flat": "F1", "status": "Booked", "room": "R1"},
			{"flat": "F1", "status": "Open", "room": None},
			{"flat": "F1", "status": ""},
		]
		rows = report.build_rows(flats, rooms, beds, [])
		self.assertEqual(len(rows), 2)
		self.assertEqual(rows[0]["rent"], 1500)
		self.assertEqual([rows[0][key] for key in ("total_rooms", "total_beds", "booked_beds", "free_beds")],
			[2, 3, 1, 1])
		self.assertEqual([rows[1][key] for key in ("total_rooms", "total_beds", "booked_beds", "free_beds")],
			[0, 0, 0, 0])
		self.assertIsNone(rows[1]["rent_start_date"])
		self.assertIsNone(rows[1]["rent_end_date"])

	def test_latest_contract_uses_dates_before_grid_position(self):
		contracts = [
			{"parent": "F1", "idx": 1, "rent_start_date": date(2026, 1, 1), "rent_end_date": date(2026, 12, 31)},
			{"parent": "F1", "idx": 3, "rent_start_date": "2025-01-01", "rent_end_date": "2027-12-31"},
			{"parent": "F1", "idx": 4, "rent_start_date": None, "rent_end_date": None},
			{"parent": "F2", "idx": 1, "rent_start_date": "2024-01-01", "rent_end_date": "2024-12-31"},
		]
		rows = report.build_rows([{"name": "F1"}, {"name": "F2"}], [], [], contracts)
		self.assertEqual(rows[0]["rent_start_date"], date(2026, 1, 1))
		self.assertEqual(rows[0]["rent_end_date"], date(2026, 12, 31))
		self.assertEqual(rows[1]["rent_end_date"], "2024-12-31")

	@patch.object(report, "frappe")
	def test_filters_and_child_rows_are_scoped_to_visible_flats(self, frappe):
		frappe.get_list.side_effect = [[{"name": "F1"}], [], []]
		frappe.get_all.return_value = []
		report.execute({"project": "P1", "governorate": "G1", "rent_type": "Contract", "flat_status": "Inactive"})
		calls = frappe.get_list.call_args_list
		self.assertEqual(calls[0].kwargs["filters"], {
			"docstatus": 1, "project": "P1", "governorate": "G1", "rent_type": "Contract", "flat_status": "Inactive",
		})
		for call in calls[1:]:
			self.assertEqual(call.kwargs["filters"], {"flat": ["in", ["F1"]]})
		self.assertEqual(frappe.get_all.call_args.kwargs["filters"], {
			"parent": ["in", ["F1"]], "parenttype": "Flat", "parentfield": "rent_contracts",
		})
		self.assertTrue(all(call.kwargs["limit_page_length"] == 0 for call in calls))

	@patch.object(report, "frappe")
	def test_no_matching_flats_skips_connection_queries(self, frappe):
		frappe.get_list.return_value = []
		columns, rows = report.execute()
		self.assertEqual(rows, [])
		self.assertEqual(len(columns), 12)
		self.assertEqual(frappe.get_list.call_args.kwargs["filters"], {"docstatus": 1})
		frappe.get_list.assert_called_once()
		frappe.get_all.assert_not_called()
