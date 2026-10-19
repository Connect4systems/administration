"""Restore Company defaults without reprovisioning existing users' access."""

import frappe

from administration.employee_user_permissions import ensure_permission


def execute():
    companies_by_user = {}
    for employee in frappe.get_all(
        "Employee",
        filters={"create_user_permission": 1},
        fields=["user_id", "company"],
    ):
        user, company = employee.get("user_id"), employee.get("company")
        if user and company and user not in ("Administrator", "Guest"):
            companies_by_user.setdefault(user, set()).add(company)

    for user, companies in sorted(companies_by_user.items()):
        if len(companies) != 1:
            # A linked user with multiple employee companies needs an explicit choice.
            frappe.logger().warning(
                "Company default repair skipped user %s: multiple Employee companies %s",
                user, sorted(companies),
            )
            continue
        ensure_permission(user, "Company", next(iter(companies)), is_default=True)
