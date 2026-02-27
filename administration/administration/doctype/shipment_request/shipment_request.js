frappe.ui.form.on('Shipment Request', {
  transporter: fetch_rate,   // Supplier
  direction: fetch_rate,     // Item
  type: fetch_rate           // UOM
});

async function fetch_rate(frm) {
  const supplier = frm.doc.transporter || "";
  const item_code = frm.doc.direction || "";
  const uom = frm.doc.type || "";

  if (!item_code) return;

  try {
    const r = await frappe.call({
      method: 'administration.administration.doctype.shipment_request.shipment_request.get_rate_by_supplier',
      args: { item_code, uom, supplier }
    });

    const msg = (r && r.message) || {};
    if (msg.price_list && frm.fields_dict.price_list) {
      frm.set_value('price_list', msg.price_list);
    }
    frm.set_value('rate', msg.rate || 0);
  } catch (e) {
    console.error(e);
    frappe.msgprint({
      title: __('Rate Fetch Error'),
      message: e.message || e,
      indicator: 'red'
    });
  }
}

frappe.ui.form.on('Shipment Request', {
  setup(frm) {
    // Filter CONTACT by selected Supplier using ERPNext's built-in contact_query
    frm.set_query('contact', () => {
      const supplier = frm.doc.supplier || frm.doc.transporter || ""; // support both fieldnames if you have 'transporter'
      return {
        query: 'frappe.contacts.doctype.contact.contact.contact_query',
        filters: {
          link_doctype: 'Supplier',
          link_name: supplier || null
        }
      };
    });

    // Filter ADDRESS by selected Supplier using ERPNext's built-in address_query
    frm.set_query('address', () => {
      const supplier = frm.doc.supplier || frm.doc.transporter || "";
      return {
        query: 'frappe.contacts.doctype.address.address.address_query',
        filters: {
          link_doctype: 'Supplier',
          link_name: supplier || null
        }
      };
    });
  },

  // When supplier changes: clear contact/address to avoid mismatched selections
  supplier(frm) {
    // If you use 'transporter' instead of 'supplier', duplicate this handler for transporter
    frm.set_value('contact', null);
    frm.set_value('address', null);
    // Read-only “Fetch From” fields will auto-clear when the link fields clear
  },

  // If your form uses 'transporter' (Link ▸ Supplier) instead of 'supplier'
  transporter(frm) {
    frm.set_value('contact', null);
    frm.set_value('address', null);
  }
});
