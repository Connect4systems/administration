from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from administration import flat_title as module


class Doc(SimpleNamespace):
	def get(self, key):
		return getattr(self, key, None)


class TestFlatTitle(TestCase):
	def setUp(self):
		patcher = patch.object(module, "frappe")
		self.frappe = patcher.start()
		self.addCleanup(patcher.stop)
		self.frappe.throw.side_effect = ValueError
		self.docs = {}
		self.frappe.get_doc.side_effect = lambda dt, name: self.docs[(dt, name)]
		self.frappe.get_all.side_effect = lambda dt, **kwargs: [
			name for (kind, name), doc in self.docs.items()
			if kind == dt and doc.get("flat_title") == kwargs["filters"]["flat_title"]]

	def add(self, dt, name, **values):
		doc = Doc(doctype=dt, name=name, flat_title="BH-Z53", **values)
		self.docs[(dt, name)] = doc
		return doc

	def test_different_flat_is_rejected_in_every_doctype(self):
		for dt in module.DOCTYPES:
			with self.subTest(doctype=dt):
				self.docs.clear()
				self.add(dt, "EXISTING")
				with self.assertRaises(ValueError):
					module.validate_flat_title(Doc(doctype=dt, name="NEW", flat_title="BH-Z53"))

	def test_cross_doctype_duplicate_is_rejected(self):
		self.add("Flat Contract Request", "REQUEST-1")
		with self.assertRaises(ValueError):
			module.validate_flat_title(Doc(doctype="Add Flat to Contract", name="ADD-1", flat_title="BH-Z53"))

	def test_linked_request_contract_and_flat_share_title(self):
		request = self.add("Flat Contract Request", "REQUEST-1")
		contract = self.add("Flat Contract", "CONTRACT-1", flat_contract_request=request.name)
		flat = self.add("Flat", "BH-Z53", flat_contract=contract.name)
		for doc in (request, contract, flat):
			module.validate_flat_title(doc)

	def test_renewal_reuses_existing_flat_title(self):
		contract = self.add("Add Flat to Contract", "ADD-1")
		flat = self.add("Flat", "BH-Z53", add_flat_to_contract=contract.name)
		renewal = self.add("Add Flat to Contract", "RENEW-1", type="Renew", flat=flat.name)
		module.validate_flat_title(renewal)

	def test_cancelled_document_still_reserves_title(self):
		self.add("Flat Contract", "CANCELLED", docstatus=2)
		with self.assertRaises(ValueError):
			module.validate_flat_title(Doc(doctype="Flat Contract", name="NEW", flat_title="BH-Z53"))

	def test_whitespace_is_trimmed_and_title_check_is_serialized(self):
		doc = Doc(doctype="Flat Contract Request", name="NEW", flat_title="  New Title  ")
		module.validate_flat_title(doc)
		self.assertEqual(doc.flat_title, "New Title")
		self.assertIn("for update", self.frappe.db.sql.call_args.args[0])

	def test_empty_optional_title_is_allowed(self):
		module.validate_flat_title(Doc(doctype="Flat Contract Request", name="NEW", flat_title=""))
		self.frappe.db.sql.assert_not_called()
