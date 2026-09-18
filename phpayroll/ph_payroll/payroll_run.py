# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate

from phpayroll.ph_payroll.constants import PH_SALARY_STRUCTURE
from phpayroll.ph_payroll.doctype.ph_payroll_settings.ph_payroll_settings import PHPayrollSettings


def _structure_for(company):
	settings = PHPayrollSettings.get_settings(company)
	if settings and settings.default_salary_structure:
		return settings.default_salary_structure
	if frappe.db.exists("Salary Structure", PH_SALARY_STRUCTURE):
		return PH_SALARY_STRUCTURE
	return frappe.db.get_value("Salary Structure", {"is_active": "Yes", "company": company}, "name")


def _ensure_assignment(employee, company, from_date):
	if not frappe.db.exists("DocType", "Salary Structure Assignment"):
		return
	structure = _structure_for(company)
	if not structure:
		return
	exists = frappe.db.exists(
		"Salary Structure Assignment",
		{"employee": employee, "docstatus": 1, "from_date": ["<=", from_date]},
	)
	if exists:
		return
	base = frappe.db.get_value("Employee", employee, "hourly_rate") or 0
	doc = frappe.new_doc("Salary Structure Assignment")
	doc.employee = employee
	doc.salary_structure = structure
	doc.company = company
	doc.from_date = from_date
	doc.base = base
	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True)
	try:
		doc.submit()
	except Exception:
		pass


@frappe.whitelist()
def prepare_salary_slips(date_from, date_to, branch, company=None):
	"""Create draft Salary Slips for Active employees at a reporting branch."""
	from phpayroll.ph_payroll.engine import assert_hrms_payroll

	if not frappe.db.exists("DocType", "Salary Slip"):
		frappe.throw(_("Frappe HR is not installed. Install the hrms app to create Salary Slips."))
	company = company or frappe.defaults.get_user_default("Company")
	assert_hrms_payroll(company)
	employees = frappe.get_all(
		"Employee",
		filters={"status": "Active", "reporting_branch": branch},
		fields=["name", "company"],
	)
	created = []
	for emp in employees:
		use_company = emp.company or company
		_ensure_assignment(emp.name, use_company, date_from)
		existing = frappe.db.get_value(
			"Salary Slip",
			{
				"employee": emp.name,
				"start_date": date_from,
				"end_date": date_to,
				"docstatus": ["<", 2],
			},
			"name",
		)
		if existing:
			slip = frappe.get_doc("Salary Slip", existing)
			slip.flags.ignore_permissions = True
			slip.save()
			created.append(slip.name)
			continue
		slip = frappe.new_doc("Salary Slip")
		slip.employee = emp.name
		slip.company = use_company
		slip.start_date = date_from
		slip.end_date = date_to
		slip.posting_date = date_to
		if _structure_for(use_company):
			slip.salary_structure = _structure_for(use_company)
		slip.flags.ignore_permissions = True
		slip.insert()
		created.append(slip.name)
	return {"created": created, "count": len(created)}


@frappe.whitelist()
def prepare_payroll_entry(payroll_entry):
	"""Ensure Salary Structure Assignments for employees on a Payroll Entry."""
	from phpayroll.ph_payroll.engine import assert_hrms_payroll

	entry = frappe.get_doc("Payroll Entry", payroll_entry)
	assert_hrms_payroll(entry.company)
	for row in entry.get("employees") or []:
		company = entry.company
		employee = row.employee
		_ensure_assignment(employee, company, entry.start_date)
	return {"ok": True}
