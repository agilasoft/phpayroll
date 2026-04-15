# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = filters or {}
	year = filters.get("year")
	month = filters.get("month")
	branch = filters.get("branch")
	if not year or not month:
		frappe.throw(_("Year and Month are required."))

	params = {"y": int(year), "m": int(month)}
	branch_clause = ""
	if branch:
		branch_clause = " AND IFNULL(pv.branch,'') = %(branch)s "
		params["branch"] = branch

	rows = frappe.db.sql(
		"""
		SELECT pv.name, pv.employee, pv.employee_name, pv.branch, pv.date_to,
			IFNULL(pv.ss_ee,0)+IFNULL(pv.wisp_ee,0) AS sss_ee,
			IFNULL(pv.ph_ee,0) AS ph_ee,
			IFNULL(pv.hd_ee,0) AS hd_ee,
			IFNULL(pv.ss_er,0)+IFNULL(pv.wisp_er,0)+IFNULL(pv.ec_er,0) AS sss_er_side,
			IFNULL(pv.ph_er,0) AS ph_er,
			IFNULL(pv.hd_er,0) AS hd_er
		FROM `tabPayroll Voucher` pv
		WHERE pv.docstatus = 1
			AND YEAR(pv.date_to) = %(y)s
			AND MONTH(pv.date_to) = %(m)s
			AND pv.run_type IN ('Regular', 'Special')
			{0}
		ORDER BY pv.employee
		""".format(
			branch_clause
		),
		params,
		as_dict=True,
	)

	columns = [
		_("Voucher") + ":Link/Payroll Voucher:140",
		_("Employee") + ":Link/Employee:120",
		_("Employee Name") + "::160",
		_("Branch") + ":Link/Branch:100",
		_("Date To") + ":Date:100",
		_("SSS EE") + ":Currency:100",
		_("PhilHealth EE") + ":Currency:100",
		_("HDMF EE") + ":Currency:100",
		_("SSS ER+EC") + ":Currency:100",
		_("PhilHealth ER") + ":Currency:100",
		_("HDMF ER") + ":Currency:100",
	]
	data = []
	for r in rows:
		data.append(
			[
				r.name,
				r.employee,
				r.employee_name,
				r.branch,
				r.date_to,
				flt(r.sss_ee),
				flt(r.ph_ee),
				flt(r.hd_ee),
				flt(r.sss_er_side),
				flt(r.ph_er),
				flt(r.hd_er),
			]
		)
	return columns, data
