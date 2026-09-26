from unittest import TestCase

from administration.legal_document_status import get_status


class TestLegalDocumentStatus(TestCase):
	def setUp(self):
		self.row = dict(renew_date="2026-01-01", next_renew_date="2026-09-01",
			expire_date="2026-09-30")

	def test_date_boundaries(self):
		for today, expected in [
			("2026-08-31", "Active"),
			("2026-09-01", "Renew Now"),
			("2026-09-15", "Renew Now"),
			("2026-09-30", "Renew Now"),
			("2026-10-01", "Expire"),
		]:
			with self.subTest(today=today):
				self.assertEqual(get_status([self.row], today), expected)

	def test_last_row_controls_status(self):
		new_row = dict(next_renew_date="2027-09-01", expire_date="2027-09-30")
		self.assertEqual(get_status([self.row, new_row], "2026-10-01"), "Active")
		self.assertEqual(get_status([new_row, self.row], "2026-10-01"), "Expire")

	def test_missing_dates_and_empty_table(self):
		self.assertEqual(get_status([], "2026-10-01"), "")
		self.assertEqual(get_status([{}], "2026-10-01"), "")
		self.assertEqual(get_status([dict(expire_date="2026-10-01")], "2026-10-01"), "Active")
		self.assertEqual(get_status([dict(expire_date="2026-10-01")], "2026-10-02"), "Expire")

	def test_expiration_takes_priority(self):
		self.row["next_renew_date"] = "2026-12-01"
		self.assertEqual(get_status([self.row], "2026-10-01"), "Expire")
