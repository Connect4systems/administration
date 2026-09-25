import frappe


def execute():
	name = "Flat Request Approval"
	if not frappe.db.exists("Workflow", name):
		return
	workflow = frappe.get_doc("Workflow", name)
	changed = False
	for transition in workflow.transitions:
		if (
			transition.state == "Administration Manager"
			and transition.action == "Review"
			and transition.allowed == "Administration Manager"
			and transition.next_state == "AP Team Leader"
		):
			transition.next_state = "Admin Team leader"
			changed = True
	if changed:
		workflow.save(ignore_permissions=True)
		frappe.clear_cache(doctype="Flat Request")
