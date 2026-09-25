from unittest import TestCase
from unittest.mock import Mock, patch

from administration.patches import move_flat_rent_details_to_table as migration
from administration.test_flat_request_workflow import Record


class TestRentDetailsMigration(TestCase):
	def test_preserves_direct_rent_reference_and_dates(self):
		row = migration.legacy_contract_row(Record(rent_contract="FC-1", rent_contract_type="Flat Contract",
			rent_start_date="2026-10-01", rent_end_date="2027-09-30"))
		self.assertEqual(row["rent_contract"], "FC-1")
		self.assertEqual(row["rent_start_date"], "2026-10-01")
		self.assertEqual(row["rent_end_date"], "2027-09-30")
		self.assertIsNone(row["add_flat_to_contract"])

	def test_contract_row_uses_add_flat_source(self):
		row = migration.legacy_contract_row(Record(add_flat_to_contract="AFTC-1", rent_contract="old"))
		self.assertEqual(row["add_flat_to_contract"], "AFTC-1")
		self.assertIsNone(row["rent_contract"])

	def test_repeat_migration_does_not_duplicate_rows(self):
		with patch.object(migration, "frappe") as frappe:
			frappe.db.has_column.return_value = True
			frappe.db.get_values.return_value = [Record(name="Flat 1", docstatus=1, rent_contract="FC-1")]
			frappe.db.exists.side_effect = [False, True]
			child = Mock()
			frappe.get_doc.return_value = child
			migration.execute()
			migration.execute()
			child.db_insert.assert_called_once()
			values = frappe.get_doc.call_args.args[0]
			self.assertEqual((values['parent'], values['docstatus'], values['rent_contract']), ('Flat 1', 1, 'FC-1'))

	def test_fresh_schema_never_queries_removed_columns(self):
		with patch.object(migration, "frappe") as frappe:
			frappe.db.has_column.return_value = False
			frappe.db.get_values.return_value = []
			migration.execute()
			fields = frappe.db.get_values.call_args.args[2]
			self.assertNotIn('rent_start_date', fields)
			self.assertNotIn('rent_contract', fields)
