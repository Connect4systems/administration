frappe.ui.form.on("User", {
    refresh(frm) {
        // Production can leave this HTML control hidden despite creating its editor.
        // Keep the standard role access check and profile-controlled editor state.
        if (
            frm.is_new() ||
            !frm.can_edit_roles ||
            !frm.module_editor ||
            !frm.doc.enabled ||
            frm.doc.user_type !== "System User"
        ) {
            return;
        }

        frm.set_df_property("modules_html", "hidden", 0);
        frm.toggle_display("modules_html", true);
        frm.module_editor.show();
    },
});
