from unittest import TestCase
from unittest.mock import Mock, patch

from administration.patches import rename_flat_rent_request as rename
from administration.patches import update_flat_request_references as references


class TestFlatRequestMigration(TestCase):
	def test_existing_doctype_and_customization_names_are_renamed(self):
		with patch.object(rename, "frappe") as frappe:
			frappe.db.exists.side_effect = [True, False, True]
			frappe.get_all.side_effect = [
				["Flat Rent Request-custom_no_of_rooms"],
				["Flat Rent Request-main-field_order"],
			]
			rename.execute()
			self.assertEqual([call.args for call in frappe.rename_doc.call_args_list], [
				("DocType", "Flat Rent Request", "Flat Request"),
				("Custom Field", "Flat Rent Request-custom_no_of_rooms", "Flat Request-custom_no_of_rooms"),
				("Property Setter", "Flat Rent Request-main-field_order", "Flat Request-main-field_order"),
			])

	def test_fresh_install_and_repeated_migration_do_not_rename_again(self):
		for new_exists in (False, True):
			with self.subTest(new_exists=new_exists), patch.object(rename, "frappe") as frappe:
				frappe.db.exists.side_effect = [False, new_exists]
				frappe.get_all.return_value = []
				rename.execute()
				frappe.rename_doc.assert_not_called()

	def test_conflicting_doctypes_are_not_merged_or_deleted(self):
		with patch.object(rename, "frappe") as frappe:
			frappe.db.exists.return_value = True
			frappe.throw.side_effect = ValueError
			with self.assertRaises(ValueError):
				rename.execute()
			frappe.rename_doc.assert_not_called()

	def test_existing_link_columns_are_migrated_after_schema_sync(self):
		with patch.object(references, "frappe") as frappe, patch.object(references, "rename_field") as rename_field:
			frappe.db.has_column.return_value = True
			frappe.db.exists.return_value = False
			references.execute()
			self.assertEqual([call.args for call in rename_field.call_args_list], [
				(doctype, "flat_rent_request", "flat_request")
				for doctype in ("Flat Contract Request", "Flat Contract", "Add Flat to Contract")
			])

	def test_fresh_install_does_not_copy_absent_columns(self):
		with patch.object(references, "frappe") as frappe, patch.object(references, "rename_field") as rename_field:
			frappe.db.has_column.return_value = False
			frappe.db.exists.return_value = False
			references.execute()
			rename_field.assert_not_called()

	def test_script_references_change_without_changing_other_contract_types(self):
		old = 'frappe.ui.form.on("Flat Rent Request", {refresh: frm => frm.doc.flat_rent_request}); /app/flat-rent-request/FRQ-26-005'
		new = references.replace_references(old)
		self.assertIn('frappe.ui.form.on("Flat Request"', new)
		self.assertIn("frm.doc.flat_request", new)
		self.assertIn("/app/flat-request/FRQ-26-005", new)
		self.assertEqual(references.replace_references(new), new)
		self.assertEqual(references.replace_references("Flat Contract Request"), "Flat Contract Request")
		self.assertIsNone(references.replace_references(None))

	def test_site_client_script_is_updated(self):
		row = Mock(name="row")
		row.name = "Custom request script"
		row.get.side_effect = {"script": 'frappe.ui.form.on("Flat Rent Request", {});'}.get
		with patch.object(references, "frappe") as frappe:
			frappe.db.has_column.return_value = False
			frappe.db.exists.side_effect = lambda _dt, name: name == "Client Script"
			frappe.get_meta.return_value.has_field.return_value = True
			frappe.get_all.return_value = [row]
			references.execute()
			frappe.db.set_value.assert_called_once_with(
				"Client Script", row.name, {"script": 'frappe.ui.form.on("Flat Request", {});'}, update_modified=False
			)
