// Extend only the General Ledger Employee party selector.
frappe.provide("frappe.query_reports");
(() => {
    const reports = frappe.query_reports;
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
                }).then(({message}) => (message || []).map(([value, description]) => ({value, description})));
            }
            return original.apply(this, arguments);
        };
        party.__administration_employee_query = true;
        return report;
    }
    let settings = configure(reports["General Ledger"]);
    Object.defineProperty(reports, "General Ledger", {
        configurable: true,
        enumerable: true,
        get: () => settings,
        set: (value) => { settings = configure(value); },
    });
})();
