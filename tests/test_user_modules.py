"""Module selector regressions runnable without a Frappe bench."""

import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch


class UserModuleTests(unittest.TestCase):
    def setUp(self):
        self.frappe = Mock()
        spec = importlib.util.spec_from_file_location(
            "user_modules_test",
            Path(__file__).parents[1] / "administration/user_modules.py",
        )
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"frappe": self.frappe}):
            spec.loader.exec_module(self.module)

    def test_empty_choices_use_only_installed_app_modules(self):
        self.frappe.get_installed_apps.return_value = ["frappe", "administration"]
        self.frappe.get_all.return_value = ["Administration", "Core"]
        for existing in (None, []):
            with self.subTest(existing=existing):
                doc = Mock()
                doc.get_onload.return_value = existing
                self.module.ensure_module_choices(doc)
                doc.set_onload.assert_called_once_with(
                    "all_modules", ["Administration", "Core"]
                )
                doc.save.assert_not_called()
        self.frappe.get_all.assert_called_with(
            "Module Def",
            filters={"app_name": ["in", ["frappe", "administration"]]},
            pluck="name",
            order_by="name",
        )

    def test_existing_standard_choices_are_preserved(self):
        doc = Mock()
        doc.get_onload.return_value = ["Administration"]
        self.module.ensure_module_choices(doc)
        self.frappe.get_all.assert_not_called()
        doc.set_onload.assert_not_called()
