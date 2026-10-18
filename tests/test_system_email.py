"""System sender regression tests without a Frappe bench."""

import importlib.util
from email import policy
from email.message import EmailMessage
from email.parser import Parser
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class Doc(SimpleNamespace):
    def get(self, key):
        return getattr(self, key, None)


class SystemEmailTests(unittest.TestCase):
    def setUp(self):
        self.frappe = Mock()
        spec = importlib.util.spec_from_file_location("system_email_test",
            Path(__file__).parents[1] / "administration/system_email.py")
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"frappe": self.frappe}):
            spec.loader.exec_module(self.module)
        self.frappe.db.get_value.return_value = Doc(
            name="CSCEC System", email_id="cscec@cscec.live", email_account_name="CSCEC System")

    def test_envelope_and_message_use_system_mailbox_preserving_content(self):
        mail = EmailMessage(policy=policy.SMTP)
        mail["From"] = "Employee <employee@example.com>"
        mail["Sender"] = "employee@example.com"
        mail["To"] = "<!--recipient-->"
        mail["Subject"] = "Welcome"
        mail["Reply-To"] = "replies@example.com"
        mail.set_content("Welcome to the company")
        mail.add_alternative("<p>Welcome</p>", subtype="html")
        attachment = bytes(range(256))
        mail.add_attachment(attachment, maintype="application", subtype="octet-stream", filename="test.bin")
        doc = Doc(sender="employee@example.com", email_account="Personal", message=mail.as_string())
        self.module.enforce_system_sender(doc)
        parsed = Parser(policy=policy.SMTP).parsestr(doc.message)
        self.assertEqual(doc.sender, "CSCEC System <cscec@cscec.live>")
        self.assertEqual(doc.email_account, "CSCEC System")
        self.assertEqual(str(parsed["From"]), doc.sender)
        self.assertEqual(str(parsed["Sender"]), doc.sender)
        self.assertEqual(str(parsed["Reply-To"]), "replies@example.com")
        self.assertIn("<!--recipient-->", doc.message)
        self.assertIn("Welcome to the company", parsed.get_body(preferencelist=("plain",)).get_content())
        self.assertEqual(next(parsed.iter_attachments()).get_payload(decode=True), attachment)

    def test_duplicate_from_headers_are_replaced(self):
        doc = Doc(message="From: a@example.com\r\nFrom: b@example.com\r\nSubject: Test\r\n\r\nBody")
        self.module.enforce_system_sender(doc)
        parsed = Parser(policy=policy.SMTP).parsestr(doc.message)
        self.assertEqual(len(parsed.get_all("From")), 1)

    def test_missing_account_does_not_invent_a_mailbox(self):
        self.frappe.db.get_value.return_value = None
        doc = Doc(sender="original@example.com", message="original")
        self.module.enforce_system_sender(doc)
        self.assertEqual(doc.sender, "original@example.com")
        self.assertEqual(doc.message, "original")

    def test_default_outgoing_account_enables_framework_sender_setting(self):
        doc = Doc(enable_outgoing=1, default_outgoing=1)
        self.module.configure_system_sender(doc)
        self.assertEqual(doc.always_use_account_email_id_as_sender, 1)
        other = Doc(enable_outgoing=1, default_outgoing=0)
        self.module.configure_system_sender(other)
        self.assertIsNone(other.get("always_use_account_email_id_as_sender"))

    def test_migration_updates_default_outgoing_account_without_credentials(self):
        self.frappe.get_all.return_value = ["CSCEC System"]
        self.module.setup_system_sender()
        self.frappe.db.set_value.assert_called_once_with(
            "Email Account", "CSCEC System", "always_use_account_email_id_as_sender", 1)
        self.frappe.clear_cache.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
