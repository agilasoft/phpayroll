# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import frappe
from frappe import _

from phpayroll.ph_payroll.timekeeping.exceptions_report import build_attendance_exception_rows


def execute(filters=None):
	filters = filters or {}
	branch = filters.get("branch")
	date_from = filters.get("date_from")
	date_to = filters.get("date_to")
	if not date_from or not date_to:
		frappe.throw(_("Date From and Date To are required."))

	columns = [
		_("Branch") + ":Link/Branch:120",
		_("Employee") + ":Link/Employee:120",
		_("Employee Name") + "::180",
		_("Date") + ":Date:100",
		_("Issue") + "::280",
	]
	data = build_attendance_exception_rows(branch, date_from, date_to)
	return columns, data
