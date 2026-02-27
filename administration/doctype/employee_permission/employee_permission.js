frappe.ui.form.on("Employee Permission", {
  refresh(frm) {
    if (frm.doc.employee && frm.doc.perm_date) {
      frappe.call({
        method: "administration.administration.doctype.employee_permission.employee_permission.permission_usage",
        args: { employee: frm.doc.employee, any_date: frm.doc.perm_date },
        callback(r) {
          if (!r.exc && r.message) {
            frm.set_intro(`This month: used ${r.message.used}/2 permissions. Remaining: ${r.message.remaining}.`);
          }
        }
      });
    }
  },
  duration_minutes(frm) {
    if (frm.doc.duration_minutes && frm.doc.duration_minutes !== 120) {
      frappe.msgprint(__("Duration must be exactly 120 minutes. Resetting to 120."));
      frm.set_value("duration_minutes", 120);
    }
  }
});
