// Replace the standard handler so creation waits for the dialog.
frappe.ui.form.off("Employee", "create_user");
frappe.ui.form.on("Employee", {
    create_user(frm) {
        if (frm.is_new() || frm.is_dirty()) {
            frappe.throw(__("Please save the Employee before creating a user."));
        }
        if (frm.doc.user_id) {
            frappe.throw(__("This Employee already has a linked user."));
        }
        const fields = [{
            fieldname: "email", label: __("Email"), fieldtype: "Data",
            options: "Email", reqd: 1, default: frm.doc.prefered_email,
        }];
        if (frappe.user.has_role(["User Manager", "System Manager"])) {
            fields.push(
                {fieldname: "leave_approver", label: __("Leave Approver"), fieldtype: "Check", default: 0},
                {fieldname: "expense_approver", label: __("Expense Approver"), fieldtype: "Check", default: 0},
                {fieldname: "line_manager", label: __("Line Manager"), fieldtype: "Check", default: 0}
            );
        }
        const dialog = new frappe.ui.Dialog({
            title: __("Create Employee User"), fields,
            primary_action_label: __("Create User"),
            async primary_action(values) {
                dialog.get_primary_btn().prop("disabled", true);
                try {
                    await frappe.call({
                        method: "administration.employee_user_permissions.create_user",
                        args: {employee: frm.doc.name, ...values},
                        freeze: true, freeze_message: __("Creating User..."),
                    });
                    dialog.hide();
                    await frm.reload_doc();
                } finally {
                    dialog.get_primary_btn().prop("disabled", false);
                }
            },
        });
        dialog.show();
    },
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
