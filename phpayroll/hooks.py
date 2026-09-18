# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "phpayroll"
app_title = "PH Payroll"
app_publisher = "Agilasoft Technologies Inc."
app_description = "Philippine Payroll"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "info@agilasoft.com"
app_license = "MIT"

required_apps = ["frappe", "erpnext", "hrms", "pdffiller"]

app_include_js = [
	"/assets/phpayroll/js/query_report_guard.js",
	"/assets/phpayroll/js/printable_pdf_preview.js",
	"/assets/phpayroll/js/report_buttons.js",
]

doctype_js = {
	"Salary Slip": "public/js/salary_slip.js",
	"Payroll Entry": "public/js/payroll_entry.js",
	"Employee": "public/js/employee.js",
}

after_install = "phpayroll.install.after_install"
after_migrate = "phpayroll.install.after_migrate"

override_doctype_class = {
	"Salary Slip": "phpayroll.overrides.salary_slip.PHSalarySlip",
}

doc_events = {
	"Employee": {
		"validate": "phpayroll.ph_payroll.employee_hooks.sync_reporting_branch",
	},
	"Payroll Voucher": {
		"validate": "phpayroll.ph_payroll.doctype.payroll_voucher.payroll_voucher.enforce_freeze",
	},
}

scheduler_events = {
	"monthly": [
		"phpayroll.tasks.grant_scheduled_leave_accrual",
	],
}

# Company → Delete Transactions: keep payroll setup; operational slips/entries stay deletable.
company_data_to_be_ignored = [
	"PH Payroll Settings",
]
