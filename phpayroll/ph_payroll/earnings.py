# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Time-based earnings used by Payroll Voucher and Salary Slip."""

from __future__ import annotations

import frappe
from frappe.utils import add_days, flt, get_datetime, getdate, time_diff_in_hours


def dates_between(start_date, end_date):
	dates = []
	current = getdate(start_date)
	end = getdate(end_date)
	while current <= end:
		dates.append(current)
		current = add_days(current, 1)
	return dates


def hours_worked(timestamp_in, timestamp_out):
	if not timestamp_in or not timestamp_out:
		return 0
	return round(time_diff_in_hours(get_datetime(timestamp_out), get_datetime(timestamp_in)), 2)


def holiday_rate(date):
	rate = frappe.db.get_value("Payroll Holiday", {"date": date}, "rate")
	return flt(rate) if rate else 0


def overtime_hours(employee, date):
	rows = frappe.get_all(
		"Overtime",
		filters={"employee": employee, "date": date, "docstatus": 1},
		fields=["hours"],
	)
	return flt(sum(flt(row.hours) for row in rows))


def overtime_multiplier():
	return 1.25


def incentive_for(branch, net_sales):
	if not branch:
		return 0
	rows = frappe.db.get_all(
		"Incentive Scheme",
		filters={
			"branch": branch,
			"amount_from": ["<=", net_sales],
			"amount_to": [">=", net_sales],
		},
		fields=["incentive"],
		limit=1,
	)
	return flt(rows[0].incentive) if rows else 0


def cash_count_sales(branch, date):
	if not branch or not frappe.db.exists("DocType", "Cash Count"):
		return 0
	try:
		rows = frappe.get_all(
			"Cash Count",
			filters={"branch": branch, "date": date},
			fields=["net_sales"],
		)
		return flt(sum(flt(row.net_sales) for row in rows))
	except Exception:
		return 0


def official_business(employee, date):
	if frappe.db.exists("DocType", "Official Business"):
		rows = frappe.get_all(
			"Official Business",
			filters={"employee": employee, "date": date, "docstatus": 1},
			fields=["name", "number_of_days", "total_additional_costs"],
			limit=1,
		)
		if rows:
			return frappe.get_doc("Official Business", rows[0].name)
	return attendance_request_as_ob(employee, date)


def attendance_request_as_ob(employee, date):
	"""HRMS has no Official Business. Pay submitted Attendance Request On Duty / WFH as a full (or half) day."""
	from phpayroll.ph_payroll.doctype.ph_payroll_settings.ph_payroll_settings import PHPayrollSettings
	from phpayroll.ph_payroll.engine import uses_hrms_payroll

	if not frappe.db.exists("DocType", "Attendance Request"):
		return None
	company = frappe.db.get_value("Employee", employee, "company")
	if not uses_hrms_payroll(company):
		return None
	settings = PHPayrollSettings.get_settings(company)
	flag = settings.get("count_on_duty_as_official_business") if settings else None
	if flag in (0, "0", False):
		return None
	date = getdate(date)
	rows = frappe.get_all(
		"Attendance Request",
		filters={
			"employee": employee,
			"docstatus": 1,
			"from_date": ["<=", date],
			"to_date": [">=", date],
			"reason": ["in", ["On Duty", "Work From Home"]],
		},
		fields=["name", "half_day", "half_day_date", "include_holidays", "reason"],
		limit=1,
	)
	if not rows:
		return None
	row = rows[0]
	if not row.include_holidays:
		try:
			from erpnext.setup.doctype.employee.employee import is_holiday

			if is_holiday(employee, date, raise_exception=False):
				return None
		except Exception:
			if holiday_rate(date):
				return None
	if frappe.db.exists("DocType", "Leave Application") and frappe.db.exists(
		"Leave Application",
		{
			"employee": employee,
			"docstatus": 1,
			"from_date": ("<=", date),
			"to_date": (">=", date),
			"status": "Approved",
			"half_day": 0,
		},
	):
		return None
	days = 0.5 if row.half_day and row.half_day_date and getdate(row.half_day_date) == date else 1.0
	return frappe._dict(
		name=row.name,
		number_of_days=days,
		total_additional_costs=0,
		additional_costs=[],
	)


def manual_attendance_time(employee, date, attendance_type, branch=None):
	rows = frappe.get_all(
		"Manual Attendance",
		filters={
			"employee": employee,
			"date": date,
			"type": attendance_type,
			"docstatus": 1,
		},
		fields=["time", "branch"],
		limit=1,
	)
	if not rows:
		return {"time": None, "branch": None}
	return {"time": rows[0].time, "branch": rows[0].branch}


def cash_advance_for_date(employee, date, bucket=None):
	total = 0
	parents = frappe.get_all("Cash Advance", filters={"employee": employee}, pluck="name")
	for name in parents:
		liquidations = frappe.get_all(
			"Cash Advance Liquidation",
			filters={"parent": name, "date": date},
			fields=["amount"],
		)
		for row in liquidations:
			amount = flt(row.amount)
			total += amount
			if bucket is not None and amount:
				ca = frappe.db.get_value(
					"Cash Advance", name, ["type", "purpose"], as_dict=True
				) or {}
				exists = any(
					getattr(d, "reference_no", None) == name
					and str(getattr(d, "date", "")) == str(date)
					for d in bucket.deductions
				)
				if not exists:
					bucket.append(
						"deductions",
						{
							"reference_no": name,
							"date": date,
							"type": ca.get("type"),
							"amount": amount,
							"remarks": f"{ca.get('purpose') or ''} - Liquidation: {amount}",
						},
					)
	return total


def populate_day(employee, date, branch, bucket):
	ob = official_business(employee, date)
	basic_hours = flt(bucket.basic_hours)
	hourly_rate = flt(bucket.hourly_rate)
	holiday = holiday_rate(date)

	if ob:
		worked = basic_hours * flt(ob.number_of_days)
		basic_pay = worked * hourly_rate
		holiday_pay = worked * hourly_rate * holiday if holiday else 0
		cash_advance = cash_advance_for_date(employee, date, bucket)
		cash_advance -= flt(ob.total_additional_costs)
		if getattr(ob, "additional_costs", None):
			for cost in ob.additional_costs:
				if flt(cost.amount) > 0:
					bucket.append(
						"deductions",
						{
							"reference_no": ob.name,
							"date": date,
							"type": "Official Business",
							"amount": -flt(cost.amount),
							"remarks": f"OB: {cost.description or 'Additional Cost'}",
						},
					)
		sales = cash_count_sales(branch, date)
		bucket.append(
			"items",
			{
				"date": date,
				"time_in": None,
				"time_out": None,
				"hours_worked": worked,
				"net_sales": sales,
				"basic_pay": basic_pay,
				"holiday_pay": holiday_pay,
				"ot_hours": 0,
				"overtime_pay": 0,
				"cash_advance": cash_advance,
				"incentive": incentive_for(branch, sales),
			},
		)
		return

	time_in = frappe.db.get_value(
		"Time In", {"employee": employee, "date": date}, ["time", "branch"], as_dict=True
	)
	time_out = frappe.db.get_value("Time Out", {"employee": employee, "date": date}, "time")
	time_in_ts = time_in.time if time_in else None
	time_in_branch = time_in.branch if time_in else None
	if not time_in_ts:
		manual_in = manual_attendance_time(employee, date, "Time In", branch)
		time_in_ts = manual_in["time"]
		time_in_branch = time_in_branch or manual_in["branch"]
	if not time_out:
		time_out = manual_attendance_time(employee, date, "Time Out", branch)["time"]

	worked = hours_worked(time_in_ts, time_out)
	pay_hours = min(worked, basic_hours) if basic_hours else worked
	basic_pay = pay_hours * hourly_rate
	holiday_pay = pay_hours * hourly_rate * holiday if holiday else 0
	ot_fetched = overtime_hours(employee, date)
	ot_hours = min(ot_fetched, max(worked - basic_hours, 0)) if basic_hours else ot_fetched
	overtime_pay = ot_hours * hourly_rate * overtime_multiplier()
	use_branch = time_in_branch or branch
	sales = cash_count_sales(use_branch, date)
	bucket.append(
		"items",
		{
			"date": date,
			"time_in": time_in_ts,
			"time_out": time_out,
			"hours_worked": worked,
			"net_sales": sales,
			"basic_pay": basic_pay,
			"holiday_pay": holiday_pay,
			"ot_hours": ot_hours,
			"overtime_pay": overtime_pay,
			"cash_advance": cash_advance_for_date(employee, date, bucket),
			"incentive": incentive_for(use_branch, sales),
		},
	)


def apply_manual_entries(employee, date_from, date_to, bucket):
	manual = frappe.get_all(
		"Manual Payroll Entry",
		filters={"employee": employee, "date": ["between", [date_from, date_to]]},
		fields=["date", "type", "amount"],
	)
	for entry in manual:
		amount = flt(entry.amount)
		matched = False
		for item in bucket.items:
			if getdate(item.date) == getdate(entry.date):
				matched = True
				if entry.type == "Basic Pay":
					item.basic_pay = flt(item.basic_pay) + amount
				elif entry.type == "Overtime":
					item.overtime_pay = flt(item.overtime_pay) + amount
				elif entry.type == "Holiday Pay":
					item.holiday_pay = flt(item.holiday_pay) + amount
				elif entry.type == "Deduction":
					item.cash_advance = flt(item.cash_advance) + amount
				elif entry.type == "Others":
					item.incentive = flt(item.incentive) + amount
				break
		if not matched:
			bucket.append(
				"items",
				{
					"date": entry.date,
					"basic_pay": amount if entry.type == "Basic Pay" else 0,
					"overtime_pay": amount if entry.type == "Overtime" else 0,
					"holiday_pay": amount if entry.type == "Holiday Pay" else 0,
					"cash_advance": amount if entry.type == "Deduction" else 0,
					"incentive": amount if entry.type == "Others" else 0,
					"hours_worked": 0,
					"ot_hours": 0,
					"net_sales": 0,
				},
			)


class PayBucket:
	def __init__(self, employee_doc, branch=None):
		self.employee = employee_doc.name
		self.basic_hours = flt(employee_doc.basic_hours)
		self.hourly_rate = flt(employee_doc.hourly_rate)
		self.branch = branch or employee_doc.get("reporting_branch")
		self.items = []
		self.deductions = []

	def append(self, field, values):
		row = frappe._dict(values)
		getattr(self, field).append(row)
		return row

	def set(self, field, value):
		setattr(self, field, value)


def compute_period_pay(employee, date_from, date_to, branch=None, voucher=None):
	employee_doc = frappe.get_doc("Employee", employee)
	if voucher is not None:
		if not flt(voucher.basic_hours):
			voucher.basic_hours = flt(employee_doc.basic_hours)
		if not flt(voucher.hourly_rate):
			voucher.hourly_rate = flt(employee_doc.hourly_rate)
		voucher.set("items", [])
		voucher.set("deductions", [])
		bucket = voucher
	else:
		bucket = PayBucket(employee_doc, branch)

	use_branch = branch or getattr(bucket, "branch", None) or employee_doc.get("reporting_branch")
	for date in dates_between(date_from, date_to):
		populate_day(employee, date, use_branch, bucket)

	apply_manual_entries(employee, date_from, date_to, bucket)

	totals = frappe._dict(
		total_basic_pay=sum(flt(i.basic_pay) for i in bucket.items),
		total_overtime_pay=sum(flt(i.overtime_pay) for i in bucket.items),
		total_holiday_pay=sum(flt(i.holiday_pay) for i in bucket.items),
		total_incentive=sum(flt(i.incentive) for i in bucket.items),
		less_cash_advance=sum(flt(i.cash_advance) for i in bucket.items),
		items=bucket.items,
		deductions=bucket.deductions,
	)
	totals.gross = (
		totals.total_basic_pay
		+ totals.total_overtime_pay
		+ totals.total_holiday_pay
		+ totals.total_incentive
	)
	return totals
