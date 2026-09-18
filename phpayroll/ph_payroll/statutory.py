# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Philippine statutory contributions and BIR withholding.

Used by Payroll Voucher and the HRMS Salary Slip overlay.
"""

from __future__ import annotations

from frappe.utils import flt, getdate, get_first_day, get_last_day

import frappe

from phpayroll.ph_payroll.constants import THIRTEENTH_MONTH_CAP


def _flag(employee, fieldname):
	value = frappe.db.get_value("Employee", employee, fieldname)
	return str(value) in ("1", "True", "true")


def has_sss_contribution(employee):
	return _flag(employee, "sss_contribution")


def has_philhealth_contribution(employee):
	return _flag(employee, "phic_contribution")


def has_hdmf_contribution(employee):
	return _flag(employee, "hdmf_contribution")


def is_end_of_month_cutoff(date_to):
	date_to = getdate(date_to)
	return date_to == get_last_day(date_to)


def _active_table(doctype):
	name = frappe.db.get_value(doctype, {"active": 1}, "name")
	if not name:
		frappe.throw(f"No active {doctype} found.")
	return frappe.get_cached_doc(doctype, name)


def _match_bracket(items, amount):
	amount = flt(amount)
	for item in items:
		if flt(item.base_from) <= amount <= flt(item.base_to):
			return item
	return None


def lookup_sss(monthly_basic_pay):
	table = _active_table("SSS Table")
	item = _match_bracket(table.items, monthly_basic_pay)
	if not item:
		return frappe._dict(ss_ee=0, ss_er=0, wisp_ee=0, wisp_er=0, ec_er=0)
	return frappe._dict(
		ss_ee=flt(item.ss_ee),
		ss_er=flt(item.ss_er),
		wisp_ee=flt(item.wisp_ee),
		wisp_er=flt(item.wisp_er),
		ec_er=flt(item.ec_er),
	)


def lookup_philhealth(basic_pay):
	table = _active_table("Philhealth Table")
	item = _match_bracket(table.items, basic_pay)
	if not item:
		return frappe._dict(ph_ee=0, ph_er=0)
	total = flt(basic_pay) * (flt(item.rate) / 100) + flt(item.monthly_premium)
	return frappe._dict(
		ph_ee=flt(total * flt(item.employee_share) / 100),
		ph_er=flt(total * flt(item.employer_share) / 100),
	)


def lookup_pagibig(basic_pay):
	table = _active_table("Pagibig Table")
	item = _match_bracket(table.items, basic_pay)
	if not item:
		return frappe._dict(hd_ee=0, hd_er=0)
	return frappe._dict(
		hd_ee=flt(basic_pay) * (flt(item.employee_rate) / 100) + flt(item.employee_fixed),
		hd_er=flt(basic_pay) * (flt(item.employer_rate) / 100) + flt(item.employer_fixed),
	)


def annual_tax_from_brackets(annual_taxable, items=None):
	"""TRAIN-style: fixed + rate% of excess over bracket floor (`from`)."""
	annual_taxable = flt(annual_taxable)
	if annual_taxable <= 0:
		return 0.0
	if items is None:
		table_name = frappe.db.get_value("Annual Tax Table", {"active": 1}, "name")
		if not table_name:
			return 0.0
		items = frappe.get_cached_doc("Annual Tax Table", table_name).items
	for item in items:
		low = flt(item.get("from"))
		high = flt(item.get("to"))
		if high <= 0:
			high = 10**15
		if low <= annual_taxable <= high:
			excess = max(annual_taxable - low, 0)
			return flt(item.fixed) + excess * (flt(item.rate) / 100)
	return 0.0


def get_previous_period_amounts(employee, fields, date_from, source="auto"):
	"""Sum contribution/tax fields already posted earlier in the same month."""
	if not employee or not date_from:
		return {f: 0.0 for f in fields}
	first_day = get_first_day(date_from)
	totals = {f: 0.0 for f in fields}

	use_slip = source in ("auto", "salary_slip") and frappe.db.exists("DocType", "Salary Slip")
	use_voucher = source in ("auto", "payroll_voucher")

	if use_slip:
		slips = frappe.get_all(
			"Salary Slip",
			filters={
				"employee": employee,
				"docstatus": ["<", 2],
				"start_date": [">=", first_day],
				"end_date": ["<", date_from],
			},
			fields=fields,
		)
		for slip in slips:
			for field in fields:
				totals[field] += flt(slip.get(field))

	if use_voucher and frappe.db.exists("DocType", "Payroll Voucher"):
		vouchers = frappe.get_all(
			"Payroll Voucher",
			filters={
				"employee": employee,
				"date_from": [">=", first_day],
				"date_to": ["<", date_from],
			},
			fields=fields,
		)
		for voucher in vouchers:
			for field in fields:
				totals[field] += flt(voucher.get(field))

	return totals


def get_ytd_tax_withheld(employee, year, before_date=None):
	total = 0.0
	start = f"{int(year)}-01-01"
	end = before_date or f"{int(year)}-12-31"
	if frappe.db.exists("DocType", "Salary Slip"):
		for slip in frappe.get_all(
			"Salary Slip",
			filters={
				"employee": employee,
				"docstatus": 1,
				"start_date": [">=", start],
				"end_date": ["<", end] if before_date else ["<=", end],
			},
			fields=["tax"],
		):
			total += flt(slip.get("tax"))
	if frappe.db.exists("DocType", "Payroll Voucher"):
		for voucher in frappe.get_all(
			"Payroll Voucher",
			filters={
				"employee": employee,
				"date_from": [">=", start],
				"date_to": ["<", end] if before_date else ["<=", end],
			},
			fields=["tax"],
		):
			total += flt(voucher.get("tax"))
	return total


def remaining_periods_in_year(end_date, frequency="Bimonthly"):
	end_date = getdate(end_date)
	if frequency == "Monthly":
		months_left = 12 - end_date.month
		return max(months_left, 0) + 1
	months_left = 12 - end_date.month
	cutoffs_left_this_month = 0 if end_date == get_last_day(end_date) else 1
	return max(months_left * 2 + cutoffs_left_this_month + 1, 1)


def calculate_withholding_tax(
	employee,
	period_taxable,
	start_date,
	end_date,
	frequency="Bimonthly",
):
	"""Annualized BIR withholding using Annual Tax Table. MWEs pay 0."""
	if frappe.db.get_value("Employee", employee, "is_mwe"):
		return 0.0
	period_taxable = flt(period_taxable)
	if period_taxable <= 0:
		return 0.0
	end_date = getdate(end_date)
	remaining = remaining_periods_in_year(end_date, frequency)
	ytd_taxable = period_taxable
	if frappe.db.exists("DocType", "Salary Slip"):
		for slip in frappe.get_all(
			"Salary Slip",
			filters={
				"employee": employee,
				"docstatus": ["<", 2],
				"start_date": [">=", getdate(f"{end_date.year}-01-01")],
				"end_date": ["<", start_date],
			},
			fields=["taxable_income"],
		):
			ytd_taxable += flt(slip.get("taxable_income"))
	projected_annual = ytd_taxable + period_taxable * max(remaining - 1, 0)
	annual_tax = annual_tax_from_brackets(projected_annual)
	already = get_ytd_tax_withheld(employee, end_date.year, before_date=start_date)
	return max(flt(annual_tax) - already, 0) / remaining if remaining else 0.0


def empty_contributions():
	return frappe._dict(
		ss_ee=0,
		ss_er=0,
		wisp_ee=0,
		wisp_er=0,
		ec_er=0,
		ph_ee=0,
		ph_er=0,
		hd_ee=0,
		hd_er=0,
		sss=0,
		philhealth=0,
		hdmf=0,
		tax=0,
		taxable_income=0,
		total_contribution=0,
	)


def calculate_statutory(
	employee,
	basic_pay,
	start_date,
	end_date,
	other_taxable=0,
	thirteenth_month=0,
	frequency="Bimonthly",
	source="auto",
):
	"""Return EE/ER statutory amounts for one payroll period."""
	result = empty_contributions()
	basic_pay = flt(basic_pay)
	mode = "full" if is_end_of_month_cutoff(end_date) else "partial"
	monthly_basic = basic_pay
	if mode == "full":
		prior_basic = 0
		first_day = get_first_day(end_date)
		if frappe.db.exists("DocType", "Salary Slip"):
			for slip in frappe.get_all(
				"Salary Slip",
				filters={
					"employee": employee,
					"start_date": [">=", first_day],
					"end_date": ["<", start_date],
					"docstatus": ["<", 2],
				},
				fields=["total_basic_pay", "name"],
			):
				prior_basic += flt(slip.get("total_basic_pay"))
		if frappe.db.exists("DocType", "Payroll Voucher"):
			for voucher in frappe.get_all(
				"Payroll Voucher",
				filters={
					"employee": employee,
					"date_from": [">=", first_day],
					"date_to": ["<", start_date],
				},
				fields=["total_basic_pay"],
			):
				prior_basic += flt(voucher.get("total_basic_pay"))
		monthly_basic = prior_basic + basic_pay

	fields = ["ss_ee", "ss_er", "wisp_ee", "wisp_er", "ec_er", "ph_ee", "ph_er", "hd_ee", "hd_er"]
	prior = (
		get_previous_period_amounts(employee, fields, start_date, source=source)
		if mode == "full"
		else {f: 0.0 for f in fields}
	)

	if has_sss_contribution(employee):
		sss = lookup_sss(monthly_basic)
		result.ss_ee = flt(sss.ss_ee) - prior["ss_ee"]
		result.ss_er = flt(sss.ss_er) - prior["ss_er"]
		result.wisp_ee = flt(sss.wisp_ee) - prior["wisp_ee"]
		result.wisp_er = flt(sss.wisp_er) - prior["wisp_er"]
		result.ec_er = flt(sss.ec_er) - prior["ec_er"]

	if has_philhealth_contribution(employee):
		phic = lookup_philhealth(monthly_basic)
		result.ph_ee = flt(phic.ph_ee) - prior["ph_ee"]
		result.ph_er = flt(phic.ph_er) - prior["ph_er"]

	if has_hdmf_contribution(employee):
		hdmf = lookup_pagibig(monthly_basic)
		result.hd_ee = flt(hdmf.hd_ee) - prior["hd_ee"]
		result.hd_er = flt(hdmf.hd_er) - prior["hd_er"]

	result.sss = flt(result.ss_ee) + flt(result.wisp_ee)
	result.philhealth = flt(result.ph_ee)
	result.hdmf = flt(result.hd_ee)
	result.total_contribution = (
		flt(result.ss_ee)
		+ flt(result.ss_er)
		+ flt(result.wisp_ee)
		+ flt(result.wisp_er)
		+ flt(result.ec_er)
		+ flt(result.ph_ee)
		+ flt(result.ph_er)
		+ flt(result.hd_ee)
		+ flt(result.hd_er)
	)

	exempt_13th = min(flt(thirteenth_month), THIRTEENTH_MONTH_CAP)
	taxable = flt(basic_pay) + flt(other_taxable) - result.sss - result.philhealth - result.hdmf
	taxable -= exempt_13th
	result.taxable_income = max(taxable, 0)
	result.tax = calculate_withholding_tax(
		employee, result.taxable_income, start_date, end_date, frequency=frequency
	)
	return result


def apply_statutory_to_doc(doc, result):
	for key in (
		"ss_ee",
		"ss_er",
		"wisp_ee",
		"wisp_er",
		"ec_er",
		"ph_ee",
		"ph_er",
		"hd_ee",
		"hd_er",
		"sss",
		"philhealth",
		"hdmf",
		"tax",
		"taxable_income",
		"total_contribution",
	):
		if result.get(key) is None:
			continue
		try:
			doc.set(key, result.get(key))
		except Exception:
			setattr(doc, key, result.get(key))
	return doc
