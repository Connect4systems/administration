frappe.ui.form.on("Journal Entry", {
    refresh(frm) {
        if (!frappe.user.has_role("Accounts User")) return;
        const field = frm.fields_dict.accounts.grid.get_field("party");
        if (field.__administration_employee_query) return;
        const original = field.get_query;
        frm.set_query("party", "accounts", function (doc, cdt, cdn) {
            const row = locals[cdt][cdn];
            if (row.party_type === "Employee") {
                return {
                    query: "administration.accounting_employee_selection.employee_query",
                    filters: {accounting_context: "Journal Entry"},
                };
            }
            return original ? original.apply(this, arguments) : {};
        });
        field.__administration_employee_query = true;
    },
});
