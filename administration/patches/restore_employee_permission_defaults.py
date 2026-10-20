"""Repair both defaults for employees opting into automatic user permissions."""

import frappe

from administration.employee_user_permissions import ensure_employee_default_permissions


def execute():
    employees_by_user = {}
    for employee in frappe.get_all(
        "Employee", filters={"create_user_permission": 1},
        fields=["name", "user_id", "company", "create_user_permission"],
    ):
        user = employee.get("user_id")
        if user and user not in ("Administrator", "Guest"):
            employees_by_user.setdefault(user, []).append(employee)

    for user, employees in sorted(employees_by_user.items()):
        if len(employees) != 1:
            frappe.logger().warning(
                "Employee permission default repair skipped user %s: multiple linked Employees %s",
                user, [employee["name"] for employee in employees],
            )
            continue
        ensure_employee_default_permissions(employees[0])
