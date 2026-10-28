app_name = "administration"
app_title = "Administration"
app_publisher = "Connect 4 Systems"
app_description = "Administration Management System AMS"
app_email = "info@connect4systems.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "administration",
# 		"logo": "/assets/administration/logo.png",
# 		"title": "Administration",
# 		"route": "/administration",
# 		"has_permission": "administration.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/administration/css/administration.css"
app_include_js = [
    "/assets/administration/js/document_approval.js?v=20261013-flat-actions",
    "/assets/administration/js/flat_transaction_buttons.js?v=20261013-2",
]

# include js, css files in header of web template
# web_include_css = "/assets/administration/css/administration.css"
# web_include_js = "/assets/administration/js/administration.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "administration/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}
webform_include_css = {"job-application": "/assets/administration/css/job_application.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "administration/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "administration.utils.jinja_methods",
# 	"filters": "administration.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "administration.install.before_install"
# after_install = "administration.install.after_install"
after_install = [
    "administration.travel_request.setup_document_approval",
    "administration.flat_request_layout.ensure_service_vehicle_contract_layout",
    "administration.flat_request_layout.ensure_service_vehicle_contract_request_layout",
    "administration.flat_request_layout.ensure_private_vehicle_contract_layout",
    "administration.flat_request_layout.ensure_private_vehicle_contract_approval_layout",
    "administration.flat_contract_attachments.setup_legal_roles",
    "administration.user_employee.setup_employee_details",
    "administration.flat_request_workflow.setup_workflow",
    "administration.add_flat_to_contract_workflow.setup_workflow",
    "administration.flat_contract_workflow.setup_workflow",
    "administration.flat_request_layout.ensure_approval_layout",
    "administration.flat_request_layout.ensure_contract_approval_layout",
    "administration.flat_request_layout.ensure_flat_contract_approval_layout",
    "administration.flat_request_layout.ensure_flat_contract_request_approval_layout",
    "administration.flat_lifecycle_setup.install",
    "administration.leave_approval_setup.setup",
    "administration.business_trip_setup.setup",
    "administration.employee_user_permissions.setup_user_manager_permissions",
    "administration.system_email.setup_system_sender",
]
after_migrate = [
    "administration.system_email.setup_system_sender",
    "administration.employee_user_permissions.setup_user_manager_permissions",
    "administration.flat_lifecycle_setup.allow_submitted_flat_contents",
    "administration.leave_approval_setup.setup",
    "administration.business_trip_setup.setup",
	"administration.flat_lifecycle_setup.repair_termination_permissions",
    "administration.travel_request.setup_document_approval",
    "administration.legal_document_status.update_statuses",
    "administration.flat_request_layout.ensure_service_vehicle_contract_layout",
    "administration.flat_request_layout.ensure_service_vehicle_contract_request_layout",
    "administration.flat_request_layout.ensure_private_vehicle_contract_layout",
    "administration.flat_request_layout.ensure_private_vehicle_contract_approval_layout",
    "administration.flat_lifecycle_setup.ensure_layouts",
    "administration.flat_request_layout.ensure_flat_contract_approval_layout",
    "administration.flat_request_layout.ensure_flat_contract_request_approval_layout",
    "administration.user_employee.setup_employee_details",
    "administration.flat_request_layout.ensure_approval_layout",
    "administration.flat_request_layout.ensure_contract_approval_layout",
]

# Uninstallation
# ------------

# before_uninstall = "administration.uninstall.before_uninstall"
# after_uninstall = "administration.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "administration.utils.before_app_install"
# after_app_install = "administration.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "administration.utils.before_app_uninstall"
# after_app_uninstall = "administration.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "administration.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }
override_doctype_class = {
    "File": "administration.legal_attachment_file.LegalAttachmentFile",
    "Employee": "administration.employee_access.AdministrationEmployee",
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Email Queue": {
        "before_insert": "administration.system_email.enforce_system_sender",
    },
    "Email Account": {
        "validate": "administration.system_email.configure_system_sender",
    },
    "Leave Application": {
        "before_validate": "administration.leave_approval.validate_leave",
        "before_update_after_submit": "administration.leave_approval.validate_leave",
        "before_cancel": "administration.leave_approval.before_cancel",
        "on_update": "administration.leave_approval.sync_assignments",
        "on_cancel": "administration.leave_approval.sync_assignments",
    },
    "Flat": {
        "validate": "administration.flat_title.validate_flat_title",
        "before_update_after_submit": "administration.flat_title.validate_flat_title",
    },
    "Travel Request": {
        "validate": ["administration.travel_request.validate_document_approval", "administration.travel_request.update_costing_currencies"],
        "before_update_after_submit": "administration.travel_request.validate_document_approval",
    },
    "Flat Contract": {
        "validate": ["administration.flat_contract_attachments.validate_contract_attachments", "administration.flat_lifecycle.validate_document", "administration.flat_title.validate_flat_title"],
        "before_update_after_submit": ["administration.flat_contract_attachments.validate_contract_attachments", "administration.flat_lifecycle.validate_document", "administration.flat_title.validate_flat_title"],
        "on_submit": ["administration.flat_lifecycle.apply_renewal", "administration.administration.doctype.flat.flat.create_flat_on_submit"],
        "on_update": "administration.flat_lifecycle.workflow_updated",
        "before_cancel": "administration.flat_lifecycle.prevent_cancel_or_delete",
        "on_trash": "administration.flat_lifecycle.prevent_cancel_or_delete",
    },
    "Flat Request": {
        "validate": "administration.flat_lifecycle.validate_document",
        "before_update_after_submit": "administration.flat_lifecycle.validate_document",
        "after_insert": "administration.flat_lifecycle.reserve_request",
        "on_update": "administration.flat_lifecycle.workflow_updated",
        "before_cancel": "administration.flat_lifecycle.prevent_cancel_or_delete",
        "on_trash": "administration.flat_lifecycle.prevent_cancel_or_delete",
    },
    "Flat Contract Request": {
        "after_insert": "administration.flat_lifecycle.reserve_request",
        "validate": ["administration.flat_lifecycle.validate_document", "administration.flat_title.validate_flat_title"],
        "before_update_after_submit": ["administration.flat_lifecycle.validate_document", "administration.flat_title.validate_flat_title"],
        "before_cancel": "administration.flat_lifecycle.prevent_cancel_or_delete",
        "on_trash": "administration.flat_lifecycle.prevent_cancel_or_delete",
    },
    "Add Flat to Contract": {
        "validate": ["administration.flat_lifecycle.validate_document", "administration.flat_title.validate_flat_title"],
        "before_update_after_submit": ["administration.flat_lifecycle.validate_document", "administration.flat_title.validate_flat_title"],
        "after_insert": "administration.flat_lifecycle.reserve_request",
        "on_submit": ["administration.flat_lifecycle.apply_renewal", "administration.administration.doctype.flat.flat.create_flat_on_submit"],
        "on_update": "administration.flat_lifecycle.workflow_updated",
        "before_cancel": "administration.flat_lifecycle.prevent_cancel_or_delete",
        "on_trash": "administration.flat_lifecycle.prevent_cancel_or_delete",
    },
    "Employee": {
        "validate": ["administration.employee.validate_accommodation_status", "administration.leave_approval.validate_employee"],
        "on_update": [
            "administration.user_employee.sync_employee_to_user",
        ],
        "on_trash": "administration.user_employee.clear_employee_from_user",
    },
    "User": {
        "validate": "administration.user_employee.set_user_employee_details",
    },
}

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------
scheduler_events = {"daily": [
    "administration.flat_lifecycle.expire_flats",
    "administration.legal_document_status.update_statuses",
]}

# scheduler_events = {
# 	"all": [
# 		"administration.tasks.all"
# 	],
# 	"daily": [
# 		"administration.tasks.daily"
# 	],
# 	"hourly": [
# 		"administration.tasks.hourly"
# 	],
# 	"weekly": [
# 		"administration.tasks.weekly"
# 	],
# 	"monthly": [
# 		"administration.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "administration.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
    "frappe.client.get": "administration.employee_selection_access.get_document",
    "frappe.desk.query_report.get_script": "administration.accounting_employee_selection.get_report_script",
    "frappe.model.workflow.apply_workflow": "administration.flat_request_workflow.apply_workflow",
    "erpnext.setup.doctype.employee.employee.create_user": "administration.employee_user_permissions.create_user",
}

# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "administration.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "administration.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["administration.utils.before_request"]
# after_request = ["administration.utils.after_request"]

# Job Events
# ----------
# before_job = ["administration.utils.before_job"]
# after_job = ["administration.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"administration.auth.validate"
# ]
auth_hooks = ["administration.employee_selection_access.allow_employee_selection"]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# ... keep your existing hooks

# Load JS only on the Purchase Order doctype
doctype_js = {
    "Journal Entry": "public/js/journal_entry_employee_selection.js",
    "Flat": "public/js/flat_transaction_buttons.js",
    "Flat Contract": "public/js/flat_transaction_buttons.js",
    "Add Flat to Contract": "public/js/flat_transaction_buttons.js",
    "Employee": "public/js/employee_leave_approval.js",
    "Leave Application": "public/js/leave_approval.js",
    "Travel Request": "public/js/doctype/travel_request/travel_request.js",
    "Job Applicant": "public/js/doctype/job_applicant/job_applicant.js",
    "Purchase Order": "public/js/doctype/purchase_order/create_shipment_request.js",
}



fixtures = [
    # Exclude optional DocTypes that are unavailable on administration sites.
    {"dt": "Custom Field", "filters": [["dt", "not in", ["Loan", "Loan Disbursement", "Loan Interest Accrual", "Loan Demand", "Loan Repayment", "Loan Refund", "Wages"]]]},
    "Property Setter", "DocType Link", "Web Form",
    {"dt": "Role", "filters": [["name", "=", "User Manager"]]},
    {"dt": "Custom DocPerm", "filters": [["role", "=", "User Manager"]]},
]

permission_query_conditions = {
    "Leave Application": "administration.leave_approval.permission_query",
    "Business Trip Request": "administration.business_trip_setup.permission_query",
}
has_permission = {
    "Leave Application": "administration.leave_approval.has_permission",
    "Business Trip Request": "administration.leave_approval.has_permission",
}
