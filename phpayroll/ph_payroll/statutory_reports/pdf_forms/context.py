# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Values for official BIR 1601-C / 1604-C / 2316 PDFs."""

from __future__ import annotations

import re

from frappe.utils import flt, getdate

from phpayroll.ph_payroll.statutory_reports.aggregator import aggregate_employees


def digits_only(value, length: int | None = None) -> str:
	text = re.sub(r"\D", "", str(value or ""))
	if length is not None:
		return text[:length]
	return text


def format_amount(value, blank_if_zero=False) -> str:
	amount = flt(value)
	if blank_if_zero and not amount:
		return ""
	return f"{amount:,.2f}"


def checkbox(flag: bool) -> str:
	return "1" if flag else ""


def split_tin(tin, branch=None) -> tuple[str, str, str, str]:
	digits = digits_only(tin)
	branch_digits = digits_only(branch)
	if len(digits) >= 14:
		digits, branch_digits = digits[:9], digits[9:14]
	elif len(digits) > 9:
		digits, extra = digits[:9], digits[9:]
		branch_digits = (extra + branch_digits)[:5]
	tin9 = digits.ljust(9)[:9]
	branch5 = (branch_digits or "000").ljust(5, "0")[:5]
	return tin9[0:3], tin9[3:6], tin9[6:9], branch5


def format_tin_display(tin, branch=None) -> str:
	a, b, c, d = split_tin(tin, branch)
	if not digits_only(a + b + c):
		return ""
	return f"{a}-{b}-{c}-{d}"


def zip_from_address(address: str, fallback: str = "") -> str:
	if fallback:
		return digits_only(fallback, 4)
	matches = re.findall(r"\b(\d{4})\b", str(address or ""))
	return matches[-1] if matches else ""


def _employer_from_profile(profile) -> dict:
	return {
		"company": profile.get("company"),
		"registered_name": (profile.get("registered_name") or "").upper(),
		"registered_address": (profile.get("registered_address") or "").upper(),
		"tin": digits_only(profile.get("tin"), 9),
		"tin_branch": digits_only(profile.get("tin_branch_code") or "000", 5).ljust(5, "0")[:5],
		"rdo_code": digits_only(profile.get("rdo_code"), 3),
		"zip": zip_from_address(profile.get("registered_address") or "", profile.get("zip_code") or ""),
		"contact_number": digits_only(profile.get("contact_number") or ""),
		"email": (profile.get("email") or "").strip(),
		"sss_employer_no": digits_only(profile.get("sss_employer_no") or ""),
		"philhealth_pen": digits_only(profile.get("philhealth_pen") or ""),
		"pagibig_employer_id": digits_only(profile.get("pagibig_employer_id") or ""),
		"signatory_name": (profile.get("signatory_name") or "").upper(),
		"signatory_title": (profile.get("signatory_title") or "").upper(),
	}


def _nontaxable_split(totals, employees) -> dict:
	gross = flt(totals.gross)
	taxable = flt(totals.taxable)
	contributions = flt(totals.ss_ee) + flt(totals.ph_ee) + flt(totals.hd_ee) + flt(totals.wisp_ee)
	thirteenth = flt(totals.thirteenth)
	mwe_basic = 0.0
	mwe_premium = 0.0
	for row in employees:
		if not row.get("is_mwe"):
			continue
		mwe_basic += flt(row.get("basic"))
		mwe_premium += flt(row.get("overtime")) + flt(row.get("holiday"))
	other = max(0.0, gross - taxable - contributions - thirteenth - mwe_basic - mwe_premium)
	return {
		"item_14": gross,
		"item_15": mwe_basic,
		"item_16": mwe_premium,
		"item_17": thirteenth,
		"item_18": 0.0,
		"item_19": contributions,
		"item_20": other,
		"item_21": mwe_basic + mwe_premium + thirteenth + contributions + other,
		"item_22": taxable,
		"item_23": 0.0,
		"item_24": taxable,
		"item_25": flt(totals.tax),
	}


def get_1601c_context(filters) -> dict:
	company = filters.get("company")
	year = int(filters.get("year"))
	month = int(filters.get("month"))
	data = aggregate_employees(company, year, month=month, branch=filters.get("branch"))
	employer = _employer_from_profile(data["employer"])
	split = _nontaxable_split(data["totals"], data["employees"])
	tax = flt(data["totals"].tax)
	return {
		**employer,
		"year": year,
		"month": month,
		"any_taxes_withheld": tax > 0,
		"employees": data["employees"],
		"totals": data["totals"],
		**split,
		"item_26": 0.0,
		"item_27": tax,
		"item_28": 0.0,
		"item_29": 0.0,
		"item_30": 0.0,
		"item_31": tax,
		"item_32": 0.0,
		"item_33": 0.0,
		"item_34": 0.0,
		"item_35": 0.0,
		"item_36": tax,
	}


def monthly_tax_withheld(company, year, branch=None) -> dict[int, float]:
	monthly = {month: 0.0 for month in range(1, 13)}
	for month in range(1, 13):
		data = aggregate_employees(company, year, month=month, branch=branch)
		monthly[month] = flt(data["totals"].tax)
	return monthly


def get_1604c_context(filters) -> dict:
	company = filters.get("company")
	year = int(filters.get("year"))
	data = aggregate_employees(company, year, branch=filters.get("branch"))
	employer = _employer_from_profile(data["employer"])
	monthly = monthly_tax_withheld(company, year, branch=filters.get("branch"))
	return {
		**employer,
		"year": year,
		"employees": data["employees"],
		"totals": data["totals"],
		"monthly_tax": monthly,
		"total_tax": sum(monthly.values()),
		"sheets_attached": 1,
	}


def _employment_period(row, year: int) -> tuple[str, str]:
	start = getdate(f"{year}-01-01")
	end = getdate(f"{year}-12-31")
	joined = getdate(row.get("date_of_joining")) if row.get("date_of_joining") else start
	left = getdate(row.get("relieving_date")) if row.get("relieving_date") else end
	if joined < start:
		joined = start
	if left > end:
		left = end
	return joined.strftime("%m%d"), left.strftime("%m%d")


def get_2316_context(filters) -> dict:
	import frappe

	employee = filters.get("employee")
	year = int(filters.get("year"))
	company = filters.get("company") or frappe.db.get_value("Employee", employee, "company")
	data = aggregate_employees(company, year, branch=filters.get("branch"))
	row = next((e for e in data["employees"] if e.employee == employee or e.name == employee), None)
	if not row:
		frappe.throw(f"No payroll totals for this employee in {year}.")
	employer = _employer_from_profile(data["employer"])
	period_from, period_to = _employment_period(row, year)
	contributions = flt(row.ss_ee) + flt(row.ph_ee) + flt(row.hd_ee) + flt(row.wisp_ee)
	nontaxable = max(0.0, flt(row.gross) - flt(row.taxable))
	mwe_basic = flt(row.basic) if row.get("is_mwe") else 0.0
	item_38 = mwe_basic + flt(row.thirteenth) + contributions
	if item_38 > nontaxable:
		item_38 = nontaxable
	taxable_basic = 0.0 if row.get("is_mwe") else flt(row.basic)
	return {
		**employer,
		"year": year,
		"employee": employee,
		"employee_name": (row.employee_name or "").upper(),
		"employee_tin": digits_only(row.tin),
		"employee_address": (row.current_address or row.permanent_address or "").upper(),
		"employee_zip": digits_only(row.zip_code, 4),
		"date_of_birth": getdate(row.date_of_birth).strftime("%m%d%Y") if row.get("date_of_birth") else "",
		"contact_number": digits_only(row.get("cell_number") or row.get("contact_number") or ""),
		"is_mwe": bool(row.get("is_mwe")),
		"period_from": period_from,
		"period_to": period_to,
		"item_29": mwe_basic,
		"item_34": flt(row.thirteenth),
		"item_36": contributions,
		"item_38": item_38,
		"item_39": taxable_basic,
		"item_50": flt(row.overtime),
		"item_52": flt(row.taxable),
		"item_19": flt(row.gross),
		"item_20": item_38,
		"item_21": flt(row.taxable),
		"item_24": flt(row.tax),
		"item_25a": flt(row.tax),
		"item_26": flt(row.tax),
		"item_28": flt(row.tax),
		"substituted_filing": (not row.get("is_mwe")) and flt(row.tax) > 0,
	}


def get_agency_listing_context(filters) -> dict:
	company = filters.get("company")
	year = int(filters.get("year"))
	month = int(filters.get("month"))
	data = aggregate_employees(company, year, month=month, branch=filters.get("branch"))
	employer = _employer_from_profile(data["employer"])
	return {
		**employer,
		"year": year,
		"month": month,
		"employees": data["employees"],
		"totals": data["totals"],
	}
