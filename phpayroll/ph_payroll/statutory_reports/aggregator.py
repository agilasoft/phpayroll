# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Month / year aggregations from Salary Slip (fallback: Payroll Voucher)."""

from __future__ import annotations

from calendar import monthrange

import frappe
from frappe.utils import flt, getdate

from phpayroll.ph_payroll.doctype.ph_payroll_settings.ph_payroll_settings import get_employer_profile


def _period_bounds(year, month=None):
	year = int(year)
	if month:
		month = int(month)
		last = monthrange(year, month)[1]
		return getdate(f"{year}-{month:02d}-01"), getdate(f"{year}-{month:02d}-{last}")
	return getdate(f"{year}-01-01"), getdate(f"{year}-12-31")


def _employee_fields():
	fields = [
		"name",
		"employee_name",
		"first_name",
		"middle_name",
		"last_name",
		"date_of_birth",
		"date_of_joining",
		"relieving_date",
		"tin",
		"sss_no",
		"phic_no",
		"hdmf_no",
		"is_mwe",
		"status",
		"company",
		"reporting_branch",
		"zip_code",
		"permanent_address",
		"current_address",
		"cell_number",
		"personal_email",
	]
	if frappe.db.exists("DocType", "Employee"):
		meta = frappe.get_meta("Employee")
		return [field for field in fields if meta.has_field(field)]
	return fields


def _empty_totals():
	return frappe._dict(
		basic=0,
		overtime=0,
		holiday=0,
		incentive=0,
		thirteenth=0,
		taxable=0,
		tax=0,
		ss_ee=0,
		ss_er=0,
		wisp_ee=0,
		wisp_er=0,
		ec_er=0,
		ph_ee=0,
		ph_er=0,
		hd_ee=0,
		hd_er=0,
		cash_advance=0,
		gross=0,
	)


def _add_slip(totals, slip):
	totals.basic += flt(slip.get("total_basic_pay"))
	totals.taxable += flt(slip.get("taxable_income"))
	totals.tax += flt(slip.get("tax"))
	totals.ss_ee += flt(slip.get("ss_ee"))
	totals.ss_er += flt(slip.get("ss_er"))
	totals.wisp_ee += flt(slip.get("wisp_ee"))
	totals.wisp_er += flt(slip.get("wisp_er"))
	totals.ec_er += flt(slip.get("ec_er"))
	totals.ph_ee += flt(slip.get("ph_ee"))
	totals.ph_er += flt(slip.get("ph_er"))
	totals.hd_ee += flt(slip.get("hd_ee"))
	totals.hd_er += flt(slip.get("hd_er"))
	totals.gross += flt(slip.get("gross_pay") or slip.get("net_pay"))
	return totals


def _add_voucher(totals, voucher):
	totals.basic += flt(voucher.get("total_basic_pay"))
	totals.overtime += flt(voucher.get("total_overtime_pay"))
	totals.holiday += flt(voucher.get("total_holiday_pay"))
	totals.incentive += flt(voucher.get("total_incentive"))
	totals.taxable += flt(voucher.get("taxable_income"))
	totals.tax += flt(voucher.get("tax"))
	totals.ss_ee += flt(voucher.get("ss_ee"))
	totals.ss_er += flt(voucher.get("ss_er"))
	totals.wisp_ee += flt(voucher.get("wisp_ee"))
	totals.wisp_er += flt(voucher.get("wisp_er"))
	totals.ec_er += flt(voucher.get("ec_er"))
	totals.ph_ee += flt(voucher.get("ph_ee"))
	totals.ph_er += flt(voucher.get("ph_er"))
	totals.hd_ee += flt(voucher.get("hd_ee"))
	totals.hd_er += flt(voucher.get("hd_er"))
	totals.cash_advance += flt(voucher.get("less_cash_advance"))
	totals.gross += (
		flt(voucher.get("total_basic_pay"))
		+ flt(voucher.get("total_overtime_pay"))
		+ flt(voucher.get("total_holiday_pay"))
		+ flt(voucher.get("total_incentive"))
	)
	return totals


def aggregate_employees(company, year, month=None, branch=None):
	start, end = _period_bounds(year, month)
	emp_filters = {"company": company}
	if branch:
		emp_filters["reporting_branch"] = branch
	employees = frappe.get_all("Employee", filters=emp_filters, fields=_employee_fields())
	emp_names = [emp.name for emp in employees]
	has_salary_slip = bool(emp_names) and frappe.db.exists("DocType", "Salary Slip")
	has_payroll_voucher = bool(emp_names) and frappe.db.exists("DocType", "Payroll Voucher")

	slips_by_employee: dict[str, list] = {}
	if has_salary_slip:
		for slip in frappe.get_all(
			"Salary Slip",
			filters={
				"employee": ["in", emp_names],
				"docstatus": 1,
				"company": company,
				"start_date": ["<=", end],
				"end_date": [">=", start],
			},
			fields=[
				"employee",
				"total_basic_pay",
				"taxable_income",
				"tax",
				"ss_ee",
				"ss_er",
				"wisp_ee",
				"wisp_er",
				"ec_er",
				"ph_ee",
				"ph_er",
				"hd_ee",
				"hd_er",
				"gross_pay",
				"net_pay",
			],
		):
			slips_by_employee.setdefault(slip.employee, []).append(slip)

	vouchers_by_employee: dict[str, list] = {}
	if has_payroll_voucher:
		vfilters = {"employee": ["in", emp_names], "date_from": ["<=", end], "date_to": [">=", start]}
		if branch:
			vfilters["branch"] = branch
		for voucher in frappe.get_all(
			"Payroll Voucher",
			filters=vfilters,
			fields=[
				"employee",
				"total_basic_pay",
				"total_overtime_pay",
				"total_holiday_pay",
				"total_incentive",
				"taxable_income",
				"tax",
				"ss_ee",
				"ss_er",
				"wisp_ee",
				"wisp_er",
				"ec_er",
				"ph_ee",
				"ph_er",
				"hd_ee",
				"hd_er",
				"less_cash_advance",
				"net_pay",
			],
		):
			vouchers_by_employee.setdefault(voucher.employee, []).append(voucher)

	rows = []
	company_totals = _empty_totals()
	for emp in employees:
		totals = _empty_totals()
		slips = slips_by_employee.get(emp.name) or []
		if slips:
			for slip in slips:
				_add_slip(totals, slip)
		else:
			for voucher in vouchers_by_employee.get(emp.name) or []:
				_add_voucher(totals, voucher)

		if not (
			totals.basic
			or totals.tax
			or totals.ss_ee
			or totals.ph_ee
			or totals.hd_ee
			or totals.gross
		):
			continue

		row = frappe._dict(emp)
		row.update(totals)
		row.employee = emp.name
		row.sss_ee_total = flt(totals.ss_ee) + flt(totals.wisp_ee)
		row.sss_er_total = flt(totals.ss_er) + flt(totals.wisp_er) + flt(totals.ec_er)
		row.period_start = start
		row.period_end = end
		rows.append(row)
		for key in (
			"basic",
			"overtime",
			"holiday",
			"incentive",
			"thirteenth",
			"taxable",
			"tax",
			"ss_ee",
			"ss_er",
			"wisp_ee",
			"wisp_er",
			"ec_er",
			"ph_ee",
			"ph_er",
			"hd_ee",
			"hd_er",
			"cash_advance",
			"gross",
		):
			company_totals[key] = flt(company_totals.get(key)) + flt(totals.get(key))

	return {
		"employees": rows,
		"totals": company_totals,
		"period_start": start,
		"period_end": end,
		"employer": get_employer_profile(company),
	}


def missing_ids(row, required):
	missing = []
	for field, label in required:
		if not (row.get(field) or "").strip():
			missing.append(label)
	return missing
