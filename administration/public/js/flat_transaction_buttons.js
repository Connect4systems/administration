// Flat actions are loaded with their forms, independently of the global approval asset.
frappe.provide("administration.approval");

administration.approval.flat_transaction_buttons = function (frm) {
	const is_flat = frm.doc.doctype === "Flat";
	const source_doctype = is_flat
		? (frm.doc.flat_contract ? "Flat Contract" : "Add Flat to Contract") : frm.doc.doctype;
	const source_name = is_flat
		? (frm.doc.flat_contract || frm.doc.add_flat_to_contract) : frm.doc.name;
	frm.remove_custom_button(__("Unlink and Cancel"));
	if (frm.doc.docstatus !== 1 || !source_name) return;
	if (!is_flat && frm.doc.contract_status === "Terminated") return;
	if (!is_flat && frm.doc.type === "Renew") {
		if (frm.doc.flat) {
			frm.add_custom_button(__("View Flat"), () => frappe.set_route("Form", "Flat", frm.doc.flat));
		}
		return;
	}
	if (!is_flat && !frm.doc.created_flat) {
		frm.add_custom_button(__("Create Flat"), () => {
			frappe.call({
				method: "administration.administration.doctype.flat.flat.make_flat",
				args: { source_doctype, source_name },
				freeze: true,
				freeze_message: __("Creating Flat..."),
				callback: (r) => {
					if (r.message?.name) frappe.set_route("Form", "Flat", r.message.name);
				},
			});
		});
		return;
	}
	if (!is_flat) {
		frm.add_custom_button(__("View Flat"), () => frappe.set_route("Form", "Flat", frm.doc.created_flat));
	}
	if (!frappe.user_roles.includes("System Manager")) return;
	frm.add_custom_button(__("Unlink and Cancel"), () => {
		if (frm.is_dirty()) {
			frappe.msgprint(__("Save or reload the document before cancelling."));
			return;
		}
		frappe.confirm(__("Cancel this document and its linked Flat, and clear their links? Both documents will remain saved as Cancelled."), () => {
			frappe.call({
				method: "administration.administration.doctype.flat.flat.unlink_and_cancel",
				args: { source_doctype, source_name },
				freeze: true,
				freeze_message: __("Unlinking and cancelling..."),
				callback: (r) => { if (r.message) frm.reload_doc(); },
			});
		});
	});
};

for (const doctype of ["Flat Contract", "Add Flat to Contract", "Flat"]) {
	frappe.ui.form.on(doctype, {
		refresh: (frm) => administration.approval.flat_transaction_buttons(frm),
	});
}
