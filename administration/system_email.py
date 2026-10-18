"""Send application mail using the configured default outgoing mailbox."""

from email import policy
from email.parser import Parser
from email.utils import formataddr

import frappe


def enforce_system_sender(doc, method=None):
    account = frappe.db.get_value("Email Account", {
        "enable_outgoing": 1, "default_outgoing": 1,
    }, ["name", "email_id", "email_account_name"], as_dict=True)
    if not account or not account.email_id:
        return
    sender = formataddr((account.email_account_name or "", account.email_id))
    doc.sender = sender
    doc.email_account = account.name
    if doc.get("message"):
        message = Parser(policy=policy.SMTP).parsestr(doc.message)
        # Replace every From header, including incorrectly duplicated headers.
        del message["From"]
        message["From"] = sender
        # An explicit Sender header must not retain the logged-in user's address.
        if "Sender" in message:
            del message["Sender"]
            message["Sender"] = sender
        doc.message = message.as_string()


def configure_system_sender(doc, method=None):
    if doc.get("enable_outgoing") and doc.get("default_outgoing"):
        doc.always_use_account_email_id_as_sender = 1


def setup_system_sender():
    for name in frappe.get_all("Email Account", filters={
        "enable_outgoing": 1, "default_outgoing": 1,
    }, pluck="name"):
        frappe.db.set_value("Email Account", name, "always_use_account_email_id_as_sender", 1)
    frappe.clear_cache()
