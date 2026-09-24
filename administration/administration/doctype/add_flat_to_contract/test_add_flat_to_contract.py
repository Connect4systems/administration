# Copyright (c) 2026, Connect 4 Systems and contributors
# For license information, please see license.txt

from unittest import TestCase

from frappe.model.base_document import import_controller

from administration.administration.doctype.add_flat_to_contract.add_flat_to_contract import (
	AddFlattoContract,
)


class TestAddFlatToContract(TestCase):
	def test_controller_can_be_loaded_during_migration(self):
		# Migration removes standard DocTypes whose controller raises ImportError.
		self.assertIs(import_controller("Add Flat to Contract"), AddFlattoContract)
