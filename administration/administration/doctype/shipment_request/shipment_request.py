from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import today


class ShipmentRequest(Document):
    pass


# ------------------------------------------------------------
# Create Shipment Request from a submitted Purchase Order
# ------------------------------------------------------------
@frappe.whitelist()
def make_from_purchase_order(po_name: str):
    """
    Return a new, UNSAVED Shipment Request draft prefilled from a submitted PO.
    Prefills:
      - project        = PO.project
      - purchase_order = PO.name
      - date           = today()
    """
    po = frappe.get_doc("Purchase Order", po_name)
    if po.docstatus != 1:
        frappe.throw("Purchase Order must be submitted.")

    sr = frappe.new_doc("Shipment Request")
    sr.project = getattr(po, "project", None)
    sr.purchase_order = po.name
    sr.date = today()
    return sr.as_dict()


# ------------------------------------------------------------
# Helper: detect Supplier's Price List field safely
# ------------------------------------------------------------
def _get_supplier_price_list(supplier: str | None) -> str | None:
    """
    Return supplier's price list using any present field on Supplier:
      - 'default_price_list'
      - 'price_list'
      - 'buying_price_list'
      - 'default_buying_price_list'
    Fallback: Buying Settings 'buying_price_list'.
    """
    if not supplier:
        return frappe.db.get_single_value("Buying Settings", "buying_price_list")

    meta = frappe.get_meta("Supplier")
    fields = {df.fieldname for df in meta.fields}

    candidates = [
        "default_price_list",
        "price_list",
        "buying_price_list",
        "default_buying_price_list",
    ]

    for fname in candidates:
        if fname in fields:
            val = frappe.db.get_value("Supplier", supplier, fname)
            if val:
                return val

    return frappe.db.get_single_value("Buying Settings", "buying_price_list")


# ------------------------------------------------------------
# Public API: fetch rate using (Supplier -> Price List) + Item + UOM
# ------------------------------------------------------------
@frappe.whitelist()
def get_rate_by_supplier(item_code: str, uom: str | None = None, supplier: str | None = None):
    """
    Use the Supplier's price list to fetch rate for the given Item and UOM.
    Returns: {"rate": float, "price_list": str|None}

    Matching priority inside Item Price:
      1) exact UOM row (if provided)
      2) blank/any UOM row (treated as default)

    Only rows within valid_from/valid_upto are considered.
    """
    out = {"rate": 0.0, "price_list": None}

    price_list = _get_supplier_price_list(supplier)
    out["price_list"] = price_list
    if not price_list or not item_code:
        return out

    params = {
        "item_code": item_code,
        "price_list": price_list,
        "uom": (uom or "").strip(),
    }

    query = """
        SELECT price_list_rate
        FROM `tabItem Price`
        WHERE item_code = %(item_code)s
          AND price_list = %(price_list)s
          AND IFNULL(valid_from, '1900-01-01') <= CURDATE()
          AND IFNULL(valid_upto, '2999-12-31') >= CURDATE()
          AND (
                (uom = %(uom)s AND %(uom)s <> '')
             OR (IFNULL(uom,'') = '')
          )
        ORDER BY
          CASE
            WHEN uom = %(uom)s AND %(uom)s <> '' THEN 0
            WHEN IFNULL(uom,'') = '' THEN 1
            ELSE 2
          END,
          creation DESC
        LIMIT 1
    """

    rows = frappe.db.sql(query, params, as_dict=True)
    out["rate"] = float(rows[0].price_list_rate) if rows else 0.0
    return out
