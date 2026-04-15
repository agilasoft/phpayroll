# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint


def execute(filters=None):
	filters = filters or {}
	branch = filters.get("branch")
	df = filters.get("date_from")
	dt = filters.get("date_to")
	if not df or not dt:
		frappe.throw(_("Date From and Date To are required."))

	f = {"docstatus": 1, "date": ["between", [df, dt]]}
	if branch:
		f["branch"] = branch

	leaves = frappe.get_all(
		"Leave",
		filters=f,
		fields=["name", "employee", "employee_name", "date", "type", "branch", "number_of_days", "docstatus"],
		order_by="date asc, employee asc",
	)

	columns = [
		_("Leave") + ":Link/Leave:120",
		_("Date") + ":Date:100",
		_("Employee") + ":Link/Employee:120",
		_("Employee Name") + "::160",
		_("Branch") + ":Link/Branch:100",
		_("Leave Type") + ":Link/Leave Type:120",
		_("Days") + ":Float:80",
		_("Status") + "::80",
	]
	data = []
	for row in leaves:
		data.append(
			[
				row.name,
				row.date,
				row.employee,
				row.employee_name,
				row.branch,
				row.type,
				row.number_of_days,
				_("Submitted") if cint(row.docstatus) == 1 else _("Draft"),
			]
		)
	return columns, data
