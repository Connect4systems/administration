(() => {
	const amount_fields = ["sponsored_amount", "funded_amount", "total_amount"];

	async function update_costings(frm) {
		if (frm.doc.docstatus !== 0) return;
		const company = frm.doc.company;
		const date = frappe.datetime.get_today();
		const key = `${company}:${date}`;
		const rows = frm.doc.costings || [];
		for (const row of rows) {
			const total = flt(flt(row.sponsored_amount) + flt(row.funded_amount), precision("total_amount", row));
			if (flt(row.total_amount) !== total) {
				await frappe.model.set_value(row.doctype, row.name, "total_amount", total);
			}
		}
		const has_amounts = rows.some(row => amount_fields.some(field => flt(row[field])));
		let rates = { usd: 0, rmb: 0 };
		if (has_amounts) {
			if (!company) return;
			if (frm._costing_rates_key !== key) {
				frm._costing_rates_key = key;
				frm._costing_rates = frappe.call({
					method: "administration.travel_request.get_costing_exchange_rates",
					args: { company },
				}).then(result => result.message).catch(error => {
					if (frm._costing_rates_key === key) frm._costing_rates_key = null;
					throw error;
				});
			}
			rates = await frm._costing_rates;
		}
		if (frm.doc.company !== company || frm.doc.docstatus !== 0) return;
		for (const row of frm.doc.costings || []) {
			const values = {};
			for (const field of amount_fields) {
				for (const suffix of ["usd", "rmb"]) {
					const target = `custom_${field}_${suffix}`;
					const value = flt(flt(row[field]) * rates[suffix], precision(target, row));
					if (flt(row[target]) !== value) values[target] = value;
				}
			}
			if (Object.keys(values).length) {
				await frappe.model.set_value(row.doctype, row.name, values);
			}
		}
	}

	frappe.ui.form.on("Travel Request", {
		refresh: update_costings,
		company: update_costings,
	});
	frappe.ui.form.on("Travel Request Costing", {
		sponsored_amount: update_costings,
		funded_amount: update_costings,
		costings_add: update_costings,
	});
})();
