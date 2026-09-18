# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe


def after_install():
	after_migrate()


def after_migrate():
	from frappe.modules.utils import sync_customizations

	from phpayroll.ph_payroll.hrms_setup import setup_hrms_overlay

	try:
		sync_customizations("phpayroll")
	except Exception:
		frappe.log_error(title="phpayroll custom field sync failed")
	setup_hrms_overlay()
	try:
		from phpayroll.ph_payroll.statutory_reports.pdf_forms import sync_payroll_pdf_forms

		sync_payroll_pdf_forms()
	except Exception:
		frappe.log_error(title="phpayroll PDF form sync failed")
