# Copyright (c) 2026, Connect 4 Systems and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestLegaldocument(FrappeTestCase):
	def test_status_is_recalculated_from_last_row(self):
		doc = frappe.get_doc({
			"doctype": "Legal document",
			"status": "Active",
			"legal_document": [
				{"expire_date": "2025-01-01"},
				{"next_renew_date": "2026-09-01", "expire_date": "2026-09-30"},
			],
		})
		with patch(
			"administration.administration.doctype.legal_document.legal_document.today",
			return_value="2026-09-27",
		):
			doc.validate()
		self.assertEqual(doc.status, "Renew Now")
