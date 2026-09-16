import frappe


def validate_accommodation_status(doc, method=None):
    if doc.status != "Left":
        return

    occupied_bed = frappe.db.exists("Bed", {"employee": doc.name})
    if occupied_bed:
        frappe.throw("Bed must be cleared to allow employee left.")
