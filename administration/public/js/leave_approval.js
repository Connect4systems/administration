frappe.ui.form.on("Leave Application", {
    onload(frm) {
        if (frm.is_new() && !frm.doc.company) {
            return set_employee_company(frm);
        }
    },
    refresh(frm) {
        frm.set_df_property("leave_approver", "read_only", 1);
        frm.set_df_property("company", "hidden", 0);
        frm.set_df_property("company", "depends_on", "");
        frm.set_df_property("company", "read_only", 0);
        if (frm.is_new() && !frm.doc.company) {
            return set_employee_company(frm);
        }
    },
    employee(frm) {
        return set_employee_company(frm);
    },
    validate(frm) {
        if (!frm.doc.company) {
            return set_employee_company(frm);
        }
    }
});

async function set_employee_company(frm) {
    const employee = frm.doc.employee;
    const default_company = frappe.defaults.get_user_default("Company");
    if (!employee) {
        if (!frm.doc.company && default_company) {
            return frm.set_value("company", default_company);
        }
        return;
    }
    const result = await frappe.db.get_value("Employee", employee, "company");
    if (frm.doc.employee === employee) {
        const company = result.message?.company || frm.doc.company || default_company;
        if (company) {
            return frm.set_value("company", company);
        }
    }
}
