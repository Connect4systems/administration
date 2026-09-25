"""Approval routing for adding a flat to an accommodation contract."""

from administration.flat_request_workflow import SUPERVISOR, setup_workflow as setup_approval_workflow


TRANSITIONS = (
	("Draft", "Request", "Administration Manager", SUPERVISOR),
	("Admin Team leader", "Approve", "Administration Manager", SUPERVISOR),
	("Administration Manager", "Approve", "General Director", "Administration Manager"),
	("Administration Manager", "Review", "Admin Team leader", "Administration Manager"),
	("General Director", "Approve", "VP-General", "General Director"),
	("General Director", "Review", "Administration Manager", "General Director"),
	("General Director", "Reject", "Rejected", "General Director"),
	("VP-General", "Approve", "Approved", "VP-General"),
	("VP-General", "Review", "Administration Manager", "VP-General"),
	("VP-General", "Reject", "Rejected", "VP-General"),
)
STATES = (
	("Draft", 0, SUPERVISOR),
	("Admin Team leader", 0, SUPERVISOR),
	("Administration Manager", 0, "Administration Manager"),
	("General Director", 0, "General Director"),
	("VP-General", 0, "VP-General"),
	("Approved", 1, SUPERVISOR),
	("Rejected", 0, SUPERVISOR),
	("Cancelled", 2, "System Manager"),
)


def setup_workflow():
	setup_approval_workflow(
		doctype="Add Flat to Contract", states=STATES,
		transitions=TRANSITIONS, creator_role=SUPERVISOR,
	)
