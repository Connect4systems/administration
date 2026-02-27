// Purchase Order → Create ▸ Shipment Request (only when submitted + Ex-Work)
frappe.ui.form.on('Purchase Order', {
  refresh(frm) {
    const is_submitted = frm.doc.docstatus === 1;
    const raw = (frm.doc.custom_delivery_location || frm.doc.delivery_location || "").trim();
    const is_ex_work = raw.toLowerCase() === "ex-work";

    if (is_submitted && is_ex_work) {
      frm.add_custom_button(__('Shipment Request'), async () => {
        const r = await frappe.call({
          method: 'administration.administration.doctype.shipment_request.shipment_request.make_from_purchase_order',
          args: { po_name: frm.doc.name },
          freeze: true,
          freeze_message: __('Preparing Shipment Request...')
        });
        const doc = r && r.message;
        if (!doc) return frappe.msgprint(__('Could not prepare Shipment Request.'));

        frappe.model.with_doctype('Shipment Request', () => {
          const newdoc = frappe.model.sync(doc)[0];
          frappe.set_route('Form', 'Shipment Request', newdoc.name);
        });
      }, __('Create'));
    }
  }
});
