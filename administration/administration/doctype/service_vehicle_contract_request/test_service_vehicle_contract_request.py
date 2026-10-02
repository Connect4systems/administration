# Copyright (c) 2026, Connect 4 Systems and Contributors
# See license.txt

from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from administration.administration.doctype.service_vehicle_contract_request import service_vehicle_contract_request as controller


class TestServiceVehicleContractRequest(FrappeTestCase):
	def test_contract_mapping_requires_submission_and_includes_terms(self):
		with patch.object(controller, "get_mapped_doc") as mapper:
			result = controller.make_service_vehicle_contract("ABC-26-001")
			self.assertIs(result, mapper.return_value)
			source_type, source_name, mappings, target = mapper.call_args.args
			self.assertEqual(source_type, "Service Vehicle Contract Request")
			self.assertEqual(source_name, "ABC-26-001")
			self.assertIsNone(target)
			parent = mappings[source_type]
			self.assertEqual(parent["doctype"], "Service Vehicle Contract")
			self.assertEqual(parent["validation"], {"docstatus": ["=", 1]})
			self.assertEqual(parent["field_map"]["name"], "service_vehicle_contract_request")
			self.assertIn("document_approval", parent["field_no_map"])
			self.assertIn("workflow_state", parent["field_no_map"])
			self.assertEqual(mappings["Vehicle Route Table"]["doctype"], "Vehicle Route Table")

	def test_project_and_year_naming(self):
		doc = controller.ServiceVehicleContractRequest()
		doc.project = "PROJECT-001"
		with patch.object(controller, "frappe") as frappe, \
			patch.object(controller, "nowdate", return_value="2026-10-02"), \
			patch.object(controller, "getseries", return_value="001") as series:
			frappe.db.get_value.return_value = " ABC "
			doc.autoname()
			self.assertEqual(doc.name, "ABC-26-001")
			series.assert_called_once_with("ABC-26-", 3)
			frappe.db.get_value.assert_called_once_with("Project", "PROJECT-001", "custom_abbreviation")

	def test_missing_project_or_abbreviation_is_rejected(self):
		for project, abbreviation in ((None, "ABC"), ("PROJECT-001", " "), ("PROJECT-001", None)):
			with self.subTest(project=project, abbreviation=abbreviation):
				doc = controller.ServiceVehicleContractRequest()
				doc.project = project
				with patch.object(controller, "frappe") as frappe, patch.object(controller, "getseries") as series:
					frappe.throw.side_effect = ValueError
					frappe.db.get_value.return_value = abbreviation
					with self.assertRaises(ValueError):
						doc.autoname()
					series.assert_not_called()

	def test_approval_history_and_submission_are_protected(self):
		doc = controller.ServiceVehicleContractRequest()
		with patch.object(controller, "validate_approval_history") as history, \
			patch.object(controller, "require_workflow_submission") as submission:
			doc.validate()
			doc.before_update_after_submit()
			self.assertEqual(history.call_count, 2)
			history.assert_called_with(doc)
			doc.before_submit()
			submission.assert_called_once_with(doc)
