# -*- coding: utf-8 -*-
"""Resolve worked hours for a duty date: submitted Attendance punches, else Time In/Out + Manual."""

from __future__ import unicode_literals

import frappe
from frappe.utils import get_datetime, getdate, time_diff_in_hours

from phpayroll.ph_payroll.timekeeping.policy import apply_worked_hours_policy


def get_timekeeping_config():
	from phpayroll.ph_payroll.doctype.payroll_settings.payroll_settings import get_timekeeping_settings

	return get_timekeeping_settings()


def _pair_punch_hours(sorted_rows):
	"""sorted_rows: list of (datetime, str type In/Out). Sum In->Out segment lengths."""
	total = 0.0
	open_in = None
	for ts, ptype in sorted_rows:
		ptype = (ptype or "").strip().lower()
		if ptype == "in":
			if open_in is not None:
				continue
			open_in = ts
		elif ptype == "out":
			if open_in is None:
				continue
			total += time_diff_in_hours(ts, open_in)
			open_in = None
	return round(total, 4), open_in is not None


def hours_from_submitted_attendance(employee, attendance_date, branch):
	"""If a submitted Attendance exists for employee + date (+ branch if set on doc), return hours from punches."""
	if not frappe.db.exists("DocType", "Attendance"):
		return None
	filters = {"employee": employee, "attendance_date": getdate(attendance_date), "docstatus": 1}
	rows = frappe.get_all("Attendance", filters=filters, fields=["name", "branch"], order_by="modified desc")
	if not rows:
		return None
	name = rows[0].name
	doc = frappe.get_doc("Attendance", name)
	if doc.branch and branch and doc.branch != branch:
		return None
	punches = []
	for row in doc.get("punches") or []:
		if not row.punch_time:
			continue
		punches.append((get_datetime(row.punch_time), (row.punch_type or "").strip()))
	punches.sort(key=lambda x: x[0])
	if not punches:
		return 0.0
	raw, _orphan = _pair_punch_hours(punches)
	cfg = get_timekeeping_config()
	return apply_worked_hours_policy(raw, cfg)


def legacy_time_in_out_hours(employee, date, branch, fetch_manual_fn):
	"""Replicate Time In / Time Out + Manual Attendance path; return (hours, time_in, time_out, time_in_branch)."""
	time_in, time_out, time_in_branch = None, None, None
	try:
		time_in_response = frappe.db.get_value("Time In", {"employee": employee, "date": date}, ["time", "branch"])
		if time_in_response:
			time_in, time_in_branch = time_in_response

		time_out_response = frappe.db.get_value("Time Out", {"employee": employee, "date": date}, "time")
		if time_out_response:
			time_out = time_out_response

		if not time_in:
			manual_time_in = fetch_manual_fn(employee, date, "Time In", branch)
			time_in = manual_time_in.get("time")
			if not time_in_branch:
				time_in_branch = manual_time_in.get("branch")

		if not time_out:
			manual_time_out = fetch_manual_fn(employee, date, "Time Out", branch)
			time_out = manual_time_out.get("time")

	except Exception:
		pass

	if not time_in or not time_out:
		return 0.0, time_in, time_out, time_in_branch

	date_time_in = get_datetime(time_in)
	date_time_out = get_datetime(time_out)
	raw = time_diff_in_hours(date_time_out, date_time_in)
	raw = round(raw, 4)
	cfg = get_timekeeping_config()
	h = apply_worked_hours_policy(raw, cfg)
	return h, time_in, time_out, time_in_branch


def resolve_worked_hours_for_day(employee, date, branch, fetch_manual_fn):
	"""
	Return dict: hours_worked, time_in, time_out, time_in_branch, source (attendance|legacy).
	"""
	d = getdate(date)
	att_h = hours_from_submitted_attendance(employee, d, branch)
	if att_h is not None:
		return {
			"hours_worked": att_h,
			"time_in": None,
			"time_out": None,
			"time_in_branch": branch,
			"source": "attendance",
		}
	h, ti, to, br = legacy_time_in_out_hours(employee, d, branch, fetch_manual_fn)
	return {
		"hours_worked": h,
		"time_in": ti,
		"time_out": to,
		"time_in_branch": br or branch,
		"source": "legacy",
	}
