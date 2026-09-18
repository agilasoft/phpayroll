# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Idempotent demo masters for a site (statutory tables, settings, sample employees)."""

from __future__ import annotations

from datetime import datetime, timedelta

import frappe
from frappe.utils import flt

from phpayroll.ph_payroll.constants import ENGINE_HRMS, PH_SALARY_STRUCTURE, THIRTEENTH_MONTH_CAP
from phpayroll.ph_payroll.hrms_setup import ensure_salary_structure, setup_hrms_overlay

DEMO_COMPANY = "Agilasoft Technologies Inc (Demo)"
SAMPLE_BRANCH = "MNL"

SAMPLE_EMPLOYEES = {
	"EMP001": dict(
		reporting_branch="MNL",
		hourly_rate=125,
		basic_hours=8,
		sss_no="33-1234567-1",
		phic_no="12-345678901-2",
		hdmf_no="1211-1234-5678",
		tin="123-456-789-000",
		sss_contribution=1,
		phic_contribution=1,
		hdmf_contribution=1,
		is_mwe=0,
		allow_incentive=1,
		region="NCR",
		zip_code="1000",
	),
	"EMP002": dict(
		reporting_branch="MNL",
		hourly_rate=85,
		basic_hours=8,
		sss_no="33-2345678-2",
		phic_no="12-345678902-3",
		hdmf_no="1211-2345-6789",
		tin="234-567-890-000",
		sss_contribution=1,
		phic_contribution=1,
		hdmf_contribution=1,
		is_mwe=1,
		allow_incentive=0,
		region="NCR",
		zip_code="1000",
	),
	"EMP003": dict(
		reporting_branch="Las Pinas",
		hourly_rate=150,
		basic_hours=8,
		sss_no="33-3456789-3",
		phic_no="12-345678903-4",
		hdmf_no="1211-3456-7890",
		tin="345-678-901-000",
		sss_contribution=1,
		phic_contribution=1,
		hdmf_contribution=1,
		is_mwe=0,
		allow_incentive=1,
		region="NCR",
		zip_code="1740",
	),
	"EMP004": dict(
		reporting_branch="MNL",
		hourly_rate=110,
		basic_hours=8,
		sss_no="33-4567890-4",
		phic_no="12-345678904-5",
		hdmf_no="1211-4567-8901",
		tin="456-789-012-000",
		sss_contribution=1,
		phic_contribution=1,
		hdmf_contribution=1,
		is_mwe=0,
		allow_incentive=0,
		region="NCR",
		zip_code="1000",
	),
}


def create_sample(company=None):
	"""Create statutory tables, PH Payroll Settings, and sample employee rates."""
	frappe.flags.ignore_permissions = True
	company = company or _company()
	setup_hrms_overlay()
	ensure_salary_structure(company)
	_ensure_payroll_book()
	_ensure_holiday_types()
	_ensure_payroll_holidays()
	_ensure_overtime_type()
	_ensure_incentive_scheme()
	_ensure_sss_table()
	_ensure_philhealth_table()
	_ensure_pagibig_table()
	_ensure_annual_tax_table()
	_ensure_settings(company)
	_ensure_holiday_list(company)
	updated = _update_sample_employees(company)
	attendance = _ensure_sample_timekeeping()
	assignments = _ensure_structure_assignments(company)
	ob = _ensure_sample_official_business()
	ar = _ensure_sample_attendance_request(company)
	frappe.db.commit()
	return {
		"company": company,
		"engine": ENGINE_HRMS,
		"employees_updated": updated,
		"structure_assignments": assignments,
		"manual_attendance": attendance,
		"official_business": ob,
		"attendance_request": ar,
		"salary_structure": PH_SALARY_STRUCTURE if frappe.db.exists("Salary Structure", PH_SALARY_STRUCTURE) else None,
	}


def _company():
	if frappe.db.exists("Company", DEMO_COMPANY):
		return DEMO_COMPANY
	company = frappe.defaults.get_global_default("company")
	if company:
		return company
	return frappe.db.get_value("Company", {"country": "Philippines"}, "name")


def _ensure_payroll_book():
	if frappe.db.exists("Payroll Book", "MAIN"):
		return
	doc = frappe.new_doc("Payroll Book")
	doc.code = "MAIN"
	doc.description = "Main payroll book"
	doc.insert(ignore_permissions=True)


def _ensure_holiday_types():
	for code, description, rate in (
		("REG", "Regular Holiday", 1.0),
		("SPE", "Special Non-Working Holiday", 0.3),
	):
		if frappe.db.exists("Holiday Type", code):
			continue
		doc = frappe.new_doc("Holiday Type")
		doc.code = code
		doc.description = description
		doc.rate = rate
		doc.insert(ignore_permissions=True)


def _ensure_payroll_holidays():
	holidays = (
		("NY2026", "New Year's Day", "2026-01-01", "REG"),
		("MAU2026", "Maundy Thursday", "2026-04-02", "REG"),
		("GF2026", "Good Friday", "2026-04-03", "REG"),
		("Araw2026", "Araw ng Kagitingan", "2026-04-09", "REG"),
		("LAB2026", "Labor Day", "2026-05-01", "REG"),
		("IND2026", "Independence Day", "2026-06-12", "REG"),
		("NINOY2026", "Ninoy Aquino Day", "2026-08-21", "SPE"),
		("NH2026", "National Heroes Day", "2026-08-31", "REG"),
		("ALL2026", "All Saints' Day", "2026-11-01", "SPE"),
		("BON2026", "Bonifacio Day", "2026-11-30", "REG"),
		("IC2026", "Immaculate Conception", "2026-12-08", "SPE"),
		("XMAS2026", "Christmas Day", "2026-12-25", "REG"),
		("RIZ2026", "Rizal Day", "2026-12-30", "REG"),
	)
	for code, description, date, holiday_type in holidays:
		if frappe.db.exists("Payroll Holiday", code):
			continue
		rate = frappe.db.get_value("Holiday Type", holiday_type, "rate") or 0
		doc = frappe.new_doc("Payroll Holiday")
		doc.code = code
		doc.description = description
		doc.date = date
		doc.holiday_type = holiday_type
		doc.rate = rate
		doc.insert(ignore_permissions=True)


def _ensure_overtime_type():
	if frappe.db.exists("Overtime Type", "REGOT"):
		return
	doc = frappe.new_doc("Overtime Type")
	doc.code = "REGOT"
	doc.description = "Regular Overtime"
	doc.rate = 1.25
	doc.insert(ignore_permissions=True)


def _ensure_incentive_scheme():
	if not frappe.db.exists("Branch", SAMPLE_BRANCH):
		return
	if frappe.db.exists("Incentive Scheme", {"branch": SAMPLE_BRANCH, "amount_from": 10000}):
		return
	existing_zero = frappe.db.exists("Incentive Scheme", {"branch": SAMPLE_BRANCH, "amount_from": 0})
	if existing_zero:
		frappe.delete_doc("Incentive Scheme", existing_zero, ignore_permissions=True, force=True)
	doc = frappe.new_doc("Incentive Scheme")
	doc.branch = SAMPLE_BRANCH
	doc.amount_from = 10000
	doc.amount_to = 999999999
	doc.incentive = 250
	doc.insert(ignore_permissions=True)


def _sss_brackets():
	"""2025 SSS MSC 5,000–35,000, 15% (EE 5% / ER 10%), WISP above 20,000 MSC."""
	rows = []
	msc = 5000
	while msc <= 35000:
		if msc == 5000:
			base_from, base_to = 0, 5249.99
		elif msc == 35000:
			base_from, base_to = 34750, 999999999
		else:
			base_from = msc - 250
			base_to = msc + 249.99
		regular = min(msc, 20000)
		wisp_base = max(msc - 20000, 0)
		ss_ee = round(regular * 0.05, 2)
		ss_er = round(regular * 0.10, 2)
		wisp_ee = round(wisp_base * 0.05, 2)
		wisp_er = round(wisp_base * 0.10, 2)
		ec_er = 10 if msc < 15000 else 30
		rows.append(
			{
				"base_from": base_from,
				"base_to": base_to,
				"monthly_salary_credit": msc,
				"ss_ee": ss_ee,
				"ss_er": ss_er,
				"ss_total": ss_ee + ss_er,
				"wisp_ee": wisp_ee,
				"wisp_er": wisp_er,
				"ec_er": ec_er,
				"total_contribution": ss_ee + ss_er + wisp_ee + wisp_er + ec_er,
			}
		)
		msc += 500
	return rows


def _ensure_sss_table():
	code = "SSS-2025"
	if frappe.db.exists("SSS Table", code):
		frappe.db.set_value("SSS Table", code, "active", 1)
		frappe.db.sql("UPDATE `tabSSS Table` SET active=0 WHERE name != %s", code)
		return
	frappe.db.sql("UPDATE `tabSSS Table` SET active=0")
	doc = frappe.new_doc("SSS Table")
	doc.code = code
	doc.description = "SSS contribution table 2025 (sample)"
	doc.active = 1
	for row in _sss_brackets():
		doc.append("items", row)
	doc.insert(ignore_permissions=True)


def _ensure_philhealth_table():
	code = "PHIC-2025"
	if frappe.db.exists("Philhealth Table", code):
		frappe.db.set_value("Philhealth Table", code, "active", 1)
		frappe.db.sql("UPDATE `tabPhilhealth Table` SET active=0 WHERE name != %s", code)
		return
	frappe.db.sql("UPDATE `tabPhilhealth Table` SET active=0")
	doc = frappe.new_doc("Philhealth Table")
	doc.code = code
	doc.description = "PhilHealth 5% 2025, floor 10,000 ceiling 100,000"
	doc.active = 1
	doc.append(
		"items",
		{
			"base_from": 0,
			"base_to": 9999.99,
			"monthly_premium": 500,
			"rate": 0,
			"employee_share": 50,
			"employer_share": 50,
		},
	)
	doc.append(
		"items",
		{
			"base_from": 10000,
			"base_to": 100000,
			"monthly_premium": 0,
			"rate": 5,
			"employee_share": 50,
			"employer_share": 50,
		},
	)
	doc.append(
		"items",
		{
			"base_from": 100000.01,
			"base_to": 999999999,
			"monthly_premium": 5000,
			"rate": 0,
			"employee_share": 50,
			"employer_share": 50,
		},
	)
	doc.insert(ignore_permissions=True)


def _ensure_pagibig_table():
	code = "HDMF-2024"
	if frappe.db.exists("Pagibig Table", code):
		frappe.db.set_value("Pagibig Table", code, "active", 1)
		frappe.db.sql("UPDATE `tabPagibig Table` SET active=0 WHERE name != %s", code)
		return
	frappe.db.sql("UPDATE `tabPagibig Table` SET active=0")
	doc = frappe.new_doc("Pagibig Table")
	doc.code = code
	doc.description = "Pag-IBIG 2%/2% with 5,000 MSC cap"
	doc.active = 1
	doc.append(
		"items",
		{
			"base_from": 0,
			"base_to": 1500,
			"employee_rate": 1,
			"employer_rate": 2,
			"employee_fixed": 0,
			"employer_fixed": 0,
		},
	)
	doc.append(
		"items",
		{
			"base_from": 1500.01,
			"base_to": 5000,
			"employee_rate": 2,
			"employer_rate": 2,
			"employee_fixed": 0,
			"employer_fixed": 0,
		},
	)
	doc.append(
		"items",
		{
			"base_from": 5000.01,
			"base_to": 999999999,
			"employee_rate": 0,
			"employer_rate": 0,
			"employee_fixed": 100,
			"employer_fixed": 100,
		},
	)
	doc.insert(ignore_permissions=True)


def _ensure_annual_tax_table():
	code = "TRAIN"
	if frappe.db.exists("Annual Tax Table", code):
		frappe.db.set_value("Annual Tax Table", code, "active", 1)
		frappe.db.sql("UPDATE `tabAnnual Tax Table` SET active=0 WHERE name != %s", code)
		return
	frappe.db.sql("UPDATE `tabAnnual Tax Table` SET active=0")
	doc = frappe.new_doc("Annual Tax Table")
	doc.code = code
	doc.description = "TRAIN / CREATE more annual tax table"
	doc.active = 1
	for low, high, fixed, rate in (
		(0, 250000, 0, 0),
		(250000.01, 400000, 0, 15),
		(400000.01, 800000, 22500, 20),
		(800000.01, 2000000, 102500, 25),
		(2000000.01, 8000000, 402500, 30),
		(8000000.01, 999999999, 2202500, 35),
	):
		doc.append("items", {"from": low, "to": high, "fixed": fixed, "rate": rate})
	doc.insert(ignore_permissions=True)


def _ensure_settings(company):
	values = {
		"computation_engine": ENGINE_HRMS,
		"freeze_payroll_voucher": 1,
		"count_on_duty_as_official_business": 1,
		"default_salary_structure": PH_SALARY_STRUCTURE
		if frappe.db.exists("Salary Structure", PH_SALARY_STRUCTURE)
		else None,
		"sss_employer_no": "03-1234567-0",
		"philhealth_pen": "012345678901",
		"pagibig_employer_id": "123456789012",
		"tin": "000123456",
		"tin_branch_code": "000",
		"rdo_code": "039",
		"registered_name": company,
		"registered_address": "Manila, Philippines",
		"zip_code": "1000",
		"signatory_name": "Sample Signatory",
		"signatory_title": "Payroll Officer",
		"thirteenth_month_cap": THIRTEENTH_MONTH_CAP,
	}
	name = frappe.db.exists("PH Payroll Settings", {"company": company})
	if name:
		doc = frappe.get_doc("PH Payroll Settings", name)
		doc.update(values)
		doc.save(ignore_permissions=True)
		return doc
	doc = frappe.new_doc("PH Payroll Settings")
	doc.company = company
	doc.update(values)
	doc.insert(ignore_permissions=True)
	return doc


def _ensure_holiday_list(company):
	if not frappe.db.exists("DocType", "Holiday List"):
		return
	name = "Philippines 2026"
	if not frappe.db.exists("Holiday List", name):
		doc = frappe.new_doc("Holiday List")
		doc.holiday_list_name = name
		doc.from_date = "2026-01-01"
		doc.to_date = "2026-12-31"
		if doc.meta.has_field("country"):
			doc.country = "Philippines"
		for _code, description, date, _ht in (
			("NY2026", "New Year's Day", "2026-01-01", "REG"),
			("MAU2026", "Maundy Thursday", "2026-04-02", "REG"),
			("GF2026", "Good Friday", "2026-04-03", "REG"),
			("Araw2026", "Araw ng Kagitingan", "2026-04-09", "REG"),
			("LAB2026", "Labor Day", "2026-05-01", "REG"),
			("IND2026", "Independence Day", "2026-06-12", "REG"),
			("NINOY2026", "Ninoy Aquino Day", "2026-08-21", "SPE"),
			("NH2026", "National Heroes Day", "2026-08-31", "REG"),
			("ALL2026", "All Saints' Day", "2026-11-01", "SPE"),
			("BON2026", "Bonifacio Day", "2026-11-30", "REG"),
			("IC2026", "Immaculate Conception", "2026-12-08", "SPE"),
			("XMAS2026", "Christmas Day", "2026-12-25", "REG"),
			("RIZ2026", "Rizal Day", "2026-12-30", "REG"),
		):
			doc.append("holidays", {"holiday_date": date, "description": description})
		doc.insert(ignore_permissions=True)
	if frappe.db.has_column("Company", "default_holiday_list"):
		frappe.db.set_value("Company", company, "default_holiday_list", name, update_modified=False)
	_ensure_holiday_list_assignment(company, name)


def _ensure_holiday_list_assignment(company, holiday_list):
	if not frappe.db.exists("DocType", "Holiday List Assignment"):
		return
	existing = frappe.db.exists(
		"Holiday List Assignment",
		{"assigned_to": company, "holiday_list": holiday_list, "docstatus": ["<", 2]},
	)
	if existing:
		doc = frappe.get_doc("Holiday List Assignment", existing)
		if doc.docstatus == 0:
			try:
				doc.submit()
			except Exception:
				pass
		return
	doc = frappe.new_doc("Holiday List Assignment")
	doc.naming_series = "HR-HLA-.YYYY.-"
	doc.applicable_for = "Company"
	doc.assigned_to = company
	doc.holiday_list = holiday_list
	doc.from_date = "2026-01-01"
	doc.insert(ignore_permissions=True)
	try:
		doc.submit()
	except Exception:
		pass


def _update_sample_employees(company):
	updated = []
	for name, values in SAMPLE_EMPLOYEES.items():
		if not frappe.db.exists("Employee", name):
			continue
		emp = frappe.get_doc("Employee", name)
		if emp.company != company:
			continue
		if frappe.db.exists("Payroll Book", "MAIN") and emp.meta.has_field("payroll_book"):
			values = dict(values)
			values["payroll_book"] = "MAIN"
		if emp.meta.has_field("holiday_list") and frappe.db.exists("Holiday List", "Philippines 2026"):
			values["holiday_list"] = "Philippines 2026"
		if emp.meta.has_field("branch") and not emp.branch:
			values["branch"] = values.get("reporting_branch")
		emp.update(values)
		emp.flags.ignore_mandatory = True
		emp.save(ignore_permissions=True)
		updated.append(name)
	return updated


def _ensure_sample_timekeeping():
	created = []
	employee = "EMP001"
	if not frappe.db.exists("Employee", employee):
		return created
	branch = SAMPLE_BRANCH if frappe.db.exists("Branch", SAMPLE_BRANCH) else None
	days = ("2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04")
	for day in days:
		for kind, hour in (("Time In", 8), ("Time Out", 17)):
			if frappe.db.exists(
				"Manual Attendance",
				{"employee": employee, "date": day, "type": kind, "docstatus": ["<", 2]},
			):
				continue
			doc = frappe.new_doc("Manual Attendance")
			doc.employee = employee
			doc.date = day
			doc.branch = branch
			doc.type = kind
			doc.time = datetime.strptime(day, "%Y-%m-%d") + timedelta(hours=hour)
			doc.reason = "PH Payroll sample setup"
			doc.insert(ignore_permissions=True)
			try:
				doc.submit()
			except Exception:
				pass
			created.append(doc.name)
	if frappe.db.exists("Overtime Type", "REGOT") and not frappe.db.exists(
		"Overtime", {"employee": employee, "date": "2026-09-02", "docstatus": ["<", 2]}
	):
		ot = frappe.new_doc("Overtime")
		ot.employee = employee
		ot.date = "2026-09-02"
		ot.branch = branch
		ot.hours = 2
		ot.overtime_type = "REGOT"
		ot.reason = "PH Payroll sample OT"
		ot.insert(ignore_permissions=True)
		try:
			ot.submit()
		except Exception:
			pass
		created.append(ot.name)
	return created


def _ensure_sample_official_business():
	employee = "EMP002"
	if not frappe.db.exists("Employee", employee):
		return None
	if frappe.db.exists("Official Business", {"employee": employee, "date": "2026-09-03", "docstatus": ["<", 2]}):
		return frappe.db.get_value(
			"Official Business",
			{"employee": employee, "date": "2026-09-03", "docstatus": ["<", 2]},
			"name",
		)
	doc = frappe.new_doc("Official Business")
	doc.employee = employee
	doc.date = "2026-09-03"
	doc.number_of_days = 1
	doc.purpose = "Client Visit"
	doc.location = "Makati"
	if doc.meta.has_field("accomplishment_report"):
		doc.accomplishment_report = "Sample client visit for PH Payroll setup."
	doc.insert(ignore_permissions=True)
	try:
		doc.submit()
	except Exception:
		pass
	return doc.name


def _ensure_sample_attendance_request(company):
	if not frappe.db.exists("DocType", "Attendance Request"):
		return None
	employee = "EMP003"
	if not frappe.db.exists("Employee", employee):
		return None
	if frappe.db.exists(
		"Attendance Request",
		{"employee": employee, "from_date": "2026-09-04", "docstatus": ["<", 2]},
	):
		return frappe.db.get_value(
			"Attendance Request",
			{"employee": employee, "from_date": "2026-09-04", "docstatus": ["<", 2]},
			"name",
		)
	doc = frappe.new_doc("Attendance Request")
	doc.employee = employee
	doc.company = company
	doc.from_date = "2026-09-04"
	doc.to_date = "2026-09-04"
	doc.reason = "On Duty"
	doc.explanation = "PH Payroll sample On Duty (HRMS Official Business equivalent)"
	doc.include_holidays = 0
	doc.flags.ignore_mandatory = True
	try:
		doc.insert(ignore_permissions=True)
		doc.submit()
	except Exception as e:
		frappe.log_error(title="PH Payroll sample Attendance Request", message=str(e))
		return None
	return doc.name


def _ensure_structure_assignments(company):
	if not frappe.db.exists("DocType", "Salary Structure Assignment"):
		return []
	if not frappe.db.exists("Salary Structure", PH_SALARY_STRUCTURE):
		return []
	created = []
	from_date = "2026-01-01"
	for employee in SAMPLE_EMPLOYEES:
		if not frappe.db.exists("Employee", employee):
			continue
		if frappe.db.exists(
			"Salary Structure Assignment",
			{"employee": employee, "docstatus": 1, "from_date": ["<=", from_date]},
		) or frappe.db.exists(
			"Salary Structure Assignment",
			{"employee": employee, "salary_structure": PH_SALARY_STRUCTURE, "docstatus": ["<", 2]},
		):
			continue
		base = flt(SAMPLE_EMPLOYEES[employee]["hourly_rate"])
		doc = frappe.new_doc("Salary Structure Assignment")
		doc.employee = employee
		doc.salary_structure = PH_SALARY_STRUCTURE
		doc.company = company
		doc.from_date = from_date
		doc.base = base
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)
		try:
			doc.submit()
		except Exception:
			pass
		created.append(doc.name)
	return created
