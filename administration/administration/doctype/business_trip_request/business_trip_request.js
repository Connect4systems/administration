frappe.ui.form.on("Business Trip Request", {
    onload(frm) {
        return load_business_trip_employee(frm);
    },
    employee(frm) {
        return load_business_trip_employee(frm);
    },
    async validate(frm) {
        await load_business_trip_employee(frm);
        if (frm.doc.employee && !frm.doc.company) {
            frappe.throw(__("Please set Company on the selected Employee before saving this request."));
        }
    }
});

async function load_business_trip_employee(frm) {
    // Saved approval snapshots must remain unchanged.
    if (!frm.is_new() && frm.doc.workflow_state !== "Open") return;
    const employee = frm.doc.employee;
    const fields = ["full_name", "department", "company"];
    const preview_approval = frm.is_new() || !frm.doc.custom_leave_approval_level;
    if (preview_approval) {
        fields.push("custom_leave_approval_level", "leave_approver", "custom_second_leave_approver");
    }
    if (!employee) {
        await frm.set_value(Object.fromEntries(fields.map((field) => [field, null])));
        return;
    }
    const result = await frappe.call({
        method: "administration.administration.doctype.business_trip_request.business_trip_request.employee_details",
        args: {employee}
    });
    if (frm.doc.employee !== employee) return;
    await frm.set_value(Object.fromEntries(fields.map((field) => [field, result.message?.[field] || null])));
}
