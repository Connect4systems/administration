frappe.ui.form.on("Leave Application", {
    refresh(frm) { frm.set_df_property("leave_approver", "read_only", 1); }
});
