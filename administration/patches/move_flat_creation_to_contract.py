import frappe


def execute():
	# Existing standard permissions may not be reset by schema synchronization.
	frappe.db.set_value(
		"DocPerm", {"parent": "Flat", "role": "System Manager", "permlevel": 0},
		"submit", 1, update_modified=False,
	)
	frappe.clear_cache(doctype="Flat")
	# Preserve existing Flats that already link to an actual Flat Contract.
	for flat in frappe.get_all(
		"Flat",
		filters={"rent_contract_type": "Flat Contract", "rent_contract": ["is", "set"]},
		fields=["name", "rent_contract"],
	):
		frappe.db.set_value(
			"Flat", flat.name,
			{"flat_contract": flat.rent_contract, "rent_type": "Direct Rent"},
			update_modified=False,
		)

	for doctype, source_field in (
		("Flat Contract", "flat_contract"),
		("Add Flat to Contract", "add_flat_to_contract"),
	):
		for source in frappe.get_all(doctype, fields=["name", "flat_title"]):
			flats = frappe.get_all(
				"Flat", filters={source_field: source.name},
				fields=["name", "flat_title", "docstatus"], limit_page_length=2,
			)
			values = {}
			if len(flats) == 1:
				values["flat_title"] = flats[0].flat_title
				if flats[0].docstatus == 1:
					values["created_flat"] = flats[0].name
			elif not source.flat_title:
				# Removed DocFields retain their database columns; preserve entered names.
				legacy_doctype, legacy_name = doctype, source.name
				if doctype == "Flat Contract":
					legacy_doctype = "Flat Contract Request"
					legacy_name = frappe.db.get_value(doctype, source.name, "flat_contract_request")
				if legacy_name and frappe.db.has_column(legacy_doctype, "flat_name"):
					title = frappe.db.get_value(legacy_doctype, legacy_name, "flat_name")
					if title:
						values["flat_title"] = title
			if values:
				frappe.db.set_value(doctype, source.name, values, update_modified=False)
