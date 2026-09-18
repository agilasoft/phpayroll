# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today


def grant_scheduled_leave_accrual():
	"""Monthly scheduler: post annual leave grant once per year per employee (idempotent)."""
	if not frappe.db.exists("DocType", "Payroll Settings"):
		return
	doc = frappe.get_single("Payroll Settings")
	lt = getattr(doc, "leave_accrual_leave_type", None)
	days = flt(getattr(doc, "leave_accrual_days_per_year", None))
	month = cint(getattr(doc, "leave_accrual_grant_month", None)) or 1
	if not lt or days <= 0:
		return
	if getdate(today()).month != month:
		return

	year = getdate(today()).year
	marker = "YEAR-{0}-SCHED-ACCRUAL".format(year)
	employees = frappe.get_all("Employee", filters={"status": "Active"}, pluck="name")
	for emp in employees:
		dup = frappe.db.sql(
			"""
			SELECT 1 FROM `tabLeave Credit Line` lc
			INNER JOIN `tabLeave Credits` p ON lc.parent = p.name AND lc.parenttype = 'Leave Credits'
			WHERE p.employee = %(emp)s AND lc.leave_type = %(lt)s AND lc.entry_type = 'Grant'
				AND lc.remarks LIKE %(mk)s
			LIMIT 1
			""",
			{"emp": emp, "lt": lt, "mk": "%" + marker + "%"},
		)
		if dup:
			continue
		from phpayroll.ph_payroll.doctype.leave_credits.leave_credits import get_or_create_leave_credits

		lc = get_or_create_leave_credits(emp)
		lc.append(
			"entries",
			{
				"posting_date": today(),
				"entry_type": "Grant",
				"leave_type": lt,
				"days": days,
				"remarks": _("Annual leave accrual ({0})").format(marker),
			},
		)
		lc.save(ignore_permissions=True)
