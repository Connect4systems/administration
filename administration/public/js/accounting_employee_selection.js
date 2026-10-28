// Appended by get_report_script after the standard report definition is loaded.
(() => {
    const names = new Map();
    function configure(report) {
        const party = report?.filters?.find((field) => field.fieldname === "party");
        if (!party || party.__administration_employee_query) return report;
        const original = party.get_data;
        party.get_data = function (txt) {
            if (frappe.user.has_role("Accounts User") &&
                frappe.query_report.get_filter_value("party_type") === "Employee") {
                return frappe.call({
                    method: "administration.accounting_employee_selection.employee_query",
                    args: {
                        doctype: "Employee", txt, searchfield: "name", start: 0, page_len: 50,
                        filters: {accounting_context: "General Ledger"},
                    },
                }).then(({message}) => (message || []).map(([value, description]) => {
                    names.set(value, description);
                    return {value, description};
                }));
            }
            return original.apply(this, arguments);
        };
        const original_change = party.on_change;
        party.on_change = function () {
            if (frappe.user.has_role("Accounts User") &&
                frappe.query_report.get_filter_value("party_type") === "Employee") {
                const values = frappe.query_report.get_filter_value("party") || [];
                // Do not read the Employee document to obtain its display name.
                frappe.query_report.set_filter_value("party_name",
                    values.length === 1 ? names.get(values[0]) || "" : "");
                frappe.query_report.set_filter_value("tax_id", "");
                return;
            }
            return original_change?.apply(this, arguments);
        };
        party.__administration_employee_query = true;
        return report;
    }
    configure(frappe.query_reports["General Ledger"]);
})();
