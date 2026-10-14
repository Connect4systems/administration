import json
from pathlib import Path

import frappe


DOCTYPES = (
	"vehicle_request", "private_vehicle_contract_request", "private_vehicle_contract",
	"vehicles", "transportation_price_list", "vehicle_route_table",
)


def execute():
	# Update metadata only; historical documents and workflow records are untouched.
	root = Path(__file__).resolve().parents[1] / "administration" / "doctype"
	for slug in DOCTYPES:
		schema = json.loads((root / slug / f"{slug}.json").read_text(encoding="utf-8"))
		frappe.reload_doc("administration", "doctype", slug, force=True)
		fields = {field["fieldname"]: field for field in schema["fields"]}
		for item in frappe.get_all("Property Setter", filters={"doc_type": schema["name"]},
			fields=["name", "field_name", "property", "value"]):
			field = fields.get(item.field_name, {})
			if item.property == "label" and item.field_name in {"request_type", "vehicle_type", "service_type"}:
				value = field.get("label", item.value)
			elif item.property == "options" and item.field_name in {"request_type", "service_type"}:
				# Retain site-specific options as well as every standard option.
				value = "\n".join(dict.fromkeys((item.value or "").split("\n") + field["options"].split("\n")))
			elif item.property == "depends_on" and "depends_on" in field and "doc.request_type" in field["depends_on"]:
				value = (item.value or "").replace("doc.request_type == 'Transportation'",
					"['Transportation', 'Transportation and Service'].includes(doc.request_type)")
			else:
				continue
			frappe.db.set_value("Property Setter", item.name, "value", value)
		frappe.clear_cache(doctype=schema["name"])
