# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt, getdate

from phpayroll.ph_payroll.constants import THIRTEENTH_MONTH, THIRTEENTH_MONTH_CAP
from phpayroll.ph_payroll.doctype.ph_payroll_settings.ph_payroll_settings import PHPayrollSettings


def year_basic_pay(employee, year):
	total = 0.0
	start = f"{int(year)}-01-01"
	end = f"{int(year)}-12-31"
	if frappe.db.exists("DocType", "Salary Slip"):
		for slip in frappe.get_all(
			"Salary Slip",
			filters={"employee": employee, "docstatus": 1, "start_date": ["between", [start, end]]},
			fields=["total_basic_pay"],
		):
			total += flt(slip.total_basic_pay)
	if not total and frappe.db.exists("DocType", "Payroll Voucher"):
		for voucher in frappe.get_all(
			"Payroll Voucher",
			filters={"employee": employee, "date_from": ["between", [start, end]]},
			fields=["total_basic_pay"],
		):
			total += flt(voucher.total_basic_pay)
	return total


@frappe.whitelist()
def generate_thirteenth_month(year, company, branch=None, payroll_date=None):
	"""Create Additional Salary (13th Month) = year basic / 12 for Active employees."""
	if not frappe.db.exists("DocType", "Additional Salary"):
		frappe.throw(_("Additional Salary is not available. Install Frappe HR (hrms)."))
	year = int(year)
	payroll_date = payroll_date or f"{year}-12-24"
	settings = PHPayrollSettings.get_settings(company)
	cap = flt(settings.thirteenth_month_cap) if settings else THIRTEENTH_MONTH_CAP
	filters = {"status": "Active", "company": company}
	if branch:
		filters["reporting_branch"] = branch
	created = []
	for emp in frappe.get_all("Employee", filters=filters, pluck="name"):
		amount = flt(year_basic_pay(emp, year) / 12.0, 2)
		if amount <= 0:
			continue
		exists = frappe.db.exists(
			"Additional Salary",
			{
				"employee": emp,
				"salary_component": THIRTEENTH_MONTH,
				"payroll_date": payroll_date,
				"docstatus": ["<", 2],
			},
		)
		if exists:
			continue
		doc = frappe.new_doc("Additional Salary")
		doc.employee = emp
		doc.company = company
		doc.salary_component = THIRTEENTH_MONTH
		doc.amount = amount
		doc.payroll_date = payroll_date
		doc.overwrite_salary_structure_amount = 1
		doc.insert(ignore_permissions=True)
		try:
			doc.submit()
		except Exception:
			pass
		created.append({"employee": emp, "amount": amount, "name": doc.name})
	return {"created": created, "count": len(created), "cap": cap}
