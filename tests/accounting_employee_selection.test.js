// Run in a JavaScript engine after loading the selector source into selectorSource.
(() => {
    function assert(value, message) {
        if (!value) throw new Error(message);
    }
    let accounts_user = true;
    let party_type = "Employee";
    let standard_calls = 0;
    let standard_changes = 0;
    let request;
    const values = {party: ["EMP-002"]};
    const party = {
        fieldname: "party",
        get_data: () => { standard_calls++; return "standard"; },
        on_change: () => { standard_changes++; },
    };
    globalThis.frappe = {
        query_reports: {"General Ledger": {filters: [party]}},
        user: {has_role: () => accounts_user},
        query_report: {
            get_filter_value: (field) => field === "party_type" ? party_type : values[field],
            set_filter_value: (field, value) => { values[field] = value; },
        },
        call: (args) => {
            request = args;
            return {then: (callback) => callback({message: [["EMP-002", "Another Employee"]]})};
        },
    };
    eval(selectorSource);
    const results = party.get_data("Another");
    assert(results[0].value === "EMP-002", "Employee result must reach the selector");
    assert(request.args.filters.accounting_context === "General Ledger", "Missing accounting context");
    assert(standard_calls === 0, "Employee lookup must bypass the restricted standard query");
    party.on_change();
    assert(values.party_name === "Another Employee", "Name should use minimal lookup result");
    assert(standard_changes === 0, "Do not fetch the restricted Employee document");
    party_type = "Supplier";
    assert(party.get_data("") === "standard", "Other parties must retain standard lookup");
    party.on_change();
    assert(standard_changes === 1, "Other parties must retain standard change handler");
    accounts_user = false;
    party_type = "Employee";
    assert(party.get_data("") === "standard", "Other roles must retain Employee restrictions");
})();
