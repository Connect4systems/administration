from unittest import TestCase
from unittest.mock import Mock, patch

from administration import travel_request


class CostingRow(dict):
	def set(self, key, value):
		self[key] = value

	def precision(self, key):
		return 2


class TestTravelRequestCurrencies(TestCase):
	def setUp(self):
		self.frappe_patch = patch.object(travel_request, "frappe")
		self.frappe = self.frappe_patch.start()
		self.addCleanup(self.frappe_patch.stop)
		self.frappe.get_cached_value.return_value = "EGP"
		self.frappe.throw.side_effect = ValueError
		self.rate_patch = patch.object(travel_request, "get_exchange_rate")
		self.get_rate = self.rate_patch.start()
		self.addCleanup(self.rate_patch.stop)
		self.get_rate.side_effect = lambda source, target, date: {"USD": 0.02, "CNY": 0.14}[target]

	def test_all_amounts_are_converted_and_rounded(self):
		row = CostingRow(sponsored_amount=100.30, funded_amount=200, total_amount=300.30)
		travel_request.update_costing_currencies({"company": "Company", "costings": [row]})
		for field, usd, rmb in (
			("sponsored_amount", 2.01, 14.04),
			("funded_amount", 4, 28),
			("total_amount", 6.01, 42.04),
		):
			self.assertEqual(row[f"custom_{field}_usd"], usd)
			self.assertEqual(row[f"custom_{field}_rmb"], rmb)
		self.assertEqual(self.get_rate.call_count, 2)

	def test_zero_amounts_clear_old_conversions_without_fetching(self):
		row = CostingRow(custom_sponsored_amount_usd=100)
		travel_request.update_costing_currencies({"costings": [row]})
		self.assertEqual(row["custom_sponsored_amount_usd"], 0)
		self.get_rate.assert_not_called()

	def test_company_currency_is_used_and_same_currency_has_rate_one(self):
		self.frappe.get_cached_value.return_value = "USD"
		row = CostingRow(sponsored_amount=100)
		travel_request.update_costing_currencies({"company": "Company", "costings": [row]})
		self.assertEqual(row["custom_sponsored_amount_usd"], 100)
		self.get_rate.assert_called_once()
		self.assertEqual(self.get_rate.call_args.args[:2], ("USD", "CNY"))

	def test_missing_rate_prevents_save(self):
		self.get_rate.return_value = 0
		self.get_rate.side_effect = None
		with self.assertRaises(ValueError):
			travel_request.update_costing_currencies({"company": "Company", "costings": [CostingRow(total_amount=10)]})

	def test_missing_company_prevents_nonzero_conversion(self):
		with self.assertRaises(ValueError):
			travel_request.update_costing_currencies({"costings": [CostingRow(total_amount=10)]})

	def test_rate_endpoint_checks_company_permissions(self):
		travel_request.get_costing_exchange_rates("Company")
		self.frappe.get_doc.return_value.check_permission.assert_called_once_with("read")
