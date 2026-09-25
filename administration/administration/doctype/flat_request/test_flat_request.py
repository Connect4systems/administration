# Copyright (c) 2025, Connect 4 Systems and Contributors
# See license.txt

from frappe.model.base_document import import_controller
from frappe.tests.utils import FrappeTestCase

from administration.administration.doctype.flat_request.flat_request import FlatRequest


class TestFlatRequest(FrappeTestCase):
	def test_controller_resolves_after_rename(self):
		self.assertIs(import_controller("Flat Request"), FlatRequest)
