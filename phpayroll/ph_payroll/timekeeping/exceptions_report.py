# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import add_days, getdate


def iter_dates(d0, d1):
	cur = getdate(d0)
	end = getdate(d1)
	while cur <= end:
		yield cur
		cur = add_days(cur, 1)


def build_attendance_exception_rows(branch, date_from, date_to):
	"""Rows for script report: (branch, employee, employee_name, date, issue)."""
	filters = {"status": "Active"}
	if branch:
		filters["reporting_branch"] = branch
	employees = frappe.get_all(
		"Employee",
		filters=filters,
		fields=["name", "employee_name", "reporting_branch"],
	)
	rows = []
	for emp in employees:
		br = emp.reporting_branch or branch or ""
		for d in iter_dates(date_from, date_to):
			if frappe.get_all(
				"Official Business",
				filters={"employee": emp.name, "date": d, "docstatus": 1},
				limit=1,
			):
				continue
			if frappe.get_all(
				"Leave",
				filters={"employee": emp.name, "date": d, "docstatus": 1},
				limit=1,
			):
				continue
			c_in = frappe.db.count("Time In", {"employee": emp.name, "date": d})
			c_out = frappe.db.count("Time Out", {"employee": emp.name, "date": d})
			sub_in = frappe.get_all(
				"Manual Attendance",
				filters={
					"employee": emp.name,
					"date": d,
					"type": "Time In",
					"docstatus": 1,
				},
				limit=1,
			)
			sub_out = frappe.get_all(
				"Manual Attendance",
				filters={
					"employee": emp.name,
					"date": d,
					"type": "Time Out",
					"docstatus": 1,
				},
				limit=1,
			)
			has_in = c_in > 0 or sub_in
			has_out = c_out > 0 or sub_out
			if frappe.db.exists("DocType", "Attendance"):
				if frappe.get_all(
					"Attendance",
					filters={
						"employee": emp.name,
						"attendance_date": d,
						"docstatus": 1,
					},
					limit=1,
				):
					continue
			if c_in > 1:
				rows.append([br, emp.name, emp.employee_name, d, _("Duplicate Time In records")])
			if c_out > 1:
				rows.append([br, emp.name, emp.employee_name, d, _("Duplicate Time Out records")])
			if has_in and not has_out:
				rows.append([br, emp.name, emp.employee_name, d, _("Missing Time Out")])
			elif has_out and not has_in:
				rows.append([br, emp.name, emp.employee_name, d, _("Missing Time In")])
			elif not has_in and not has_out:
				rows.append(
					[
						br,
						emp.name,
						emp.employee_name,
						d,
						_("No attendance (no Time In/Out, Manual, or Attendance)"),
					]
				)
	return rows
