# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe


OPTIONAL_APPS = (
	("hrms", "Employee and Salary Slip"),
	("pdffiller", "fillable statutory PDFs"),
)


def after_install():
	_note_optional_apps()
	after_migrate()


def _note_optional_apps():
	installed = set(frappe.get_installed_apps())
	notes = [f"install {app} for {purpose}" for app, purpose in OPTIONAL_APPS if app not in installed]
	if not notes:
		return
	print("PH Payroll installed. Next: " + "; ".join(notes) + ". Then run bench migrate.")


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
