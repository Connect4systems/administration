frappe.ui.form.on("Employee", {
    refresh(frm) { frm.set_df_property("leave_approver", "read_only", 1); },
    custom_leave_approval_level(frm) {
        if (frm.doc.custom_leave_approval_level === "No Approval Required") {
            frm.set_value("custom_first_approval", null);
            frm.set_value("leave_approver", null);
        }
        if (frm.doc.custom_leave_approval_level !== "Two Level Approval") {
            frm.set_value("custom_second_approval", null);
            frm.set_value("custom_second_leave_approver", null);
        }
    },
    async custom_first_approval(frm) {
        const employee = frm.doc.custom_first_approval;
        const result = employee ? await frappe.db.get_value("Employee", employee, "user_id") : null;
        if (employee === frm.doc.custom_first_approval) frm.set_value("leave_approver", result?.message?.user_id || null);
    },
    async custom_second_approval(frm) {
        const employee = frm.doc.custom_second_approval;
        const result = employee ? await frappe.db.get_value("Employee", employee, "user_id") : null;
        if (employee === frm.doc.custom_second_approval) frm.set_value("custom_second_leave_approver", result?.message?.user_id || null);
    }
});
