# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors

from __future__ import unicode_literals

import csv
import io

import frappe
from frappe import _
from frappe.utils import flt


@frappe.whitelist()
def export_bir_2316_summary_csv(year, branch=None):
	"""Per-employee annual totals from submitted Regular/Special vouchers (CSV scaffold for 2316)."""
	year = int(year)
	branch_clause = ""
	params = {"y": year}
	if branch:
		branch_clause = " AND IFNULL(pv.branch,'') = %(branch)s "
		params["branch"] = branch
	rows = frappe.db.sql(
		"""
		SELECT pv.employee, e.employee_name,
			SUM(pv.total_basic_pay) AS total_basic,
			SUM(pv.total_overtime_pay) AS total_ot,
			SUM(pv.total_holiday_pay) AS total_holiday,
			SUM(IFNULL(pv.total_night_diff_pay, 0)) AS total_night,
			SUM(pv.taxable_income) AS total_taxable,
			SUM(pv.tax) AS total_tax,
			SUM(IFNULL(pv.ss_ee,0)+IFNULL(pv.wisp_ee,0)) AS total_sss_ee,
			SUM(IFNULL(pv.ph_ee,0)) AS total_ph_ee,
			SUM(IFNULL(pv.hd_ee,0)) AS total_hd_ee
		FROM `tabPayroll Voucher` pv
		LEFT JOIN `tabEmployee` e ON e.name = pv.employee
		WHERE pv.docstatus = 1
			AND YEAR(pv.date_to) = %(y)s
			AND pv.run_type IN ('Regular', 'Special')
			{branch_clause}
		GROUP BY pv.employee, e.employee_name
		ORDER BY pv.employee
		""".format(
			branch_clause=branch_clause
		),
		params,
		as_dict=True,
	)
	buf = io.StringIO()
	w = csv.writer(buf)
	w.writerow(
		[
			"employee",
			"employee_name",
			"total_basic",
			"total_ot",
			"total_holiday",
			"total_night_diff",
			"total_taxable",
			"total_tax",
			"total_sss_ee",
			"total_ph_ee",
			"total_hd_ee",
		]
	)
	for r in rows:
		w.writerow(
			[
				r.get("employee"),
				r.get("employee_name"),
				flt(r.get("total_basic")),
				flt(r.get("total_ot")),
				flt(r.get("total_holiday")),
				flt(r.get("total_night")),
				flt(r.get("total_taxable")),
				flt(r.get("total_tax")),
				flt(r.get("total_sss_ee")),
				flt(r.get("total_ph_ee")),
				flt(r.get("total_hd_ee")),
			]
		)
	frappe.response["filename"] = "bir_2316_summary_{0}.csv".format(year)
	frappe.response["filecontent"] = buf.getvalue()
	frappe.response["type"] = "download"


@frappe.whitelist()
def export_alphalist_csv(year, branch=None):
	"""Minimal alphalist-style export: same as 2316 summary with BIR-oriented column headers."""
	year = int(year)
	branch_clause = ""
	params = {"y": year}
	if branch:
		branch_clause = " AND IFNULL(pv.branch,'') = %(branch)s "
		params["branch"] = branch
	rows = frappe.db.sql(
		"""
		SELECT pv.employee,
			e.employee_name AS registered_name,
			SUM(pv.taxable_income) AS gross_comp,
			SUM(pv.tax) AS tax_withheld
		FROM `tabPayroll Voucher` pv
		LEFT JOIN `tabEmployee` e ON e.name = pv.employee
		WHERE pv.docstatus = 1
			AND YEAR(pv.date_to) = %(y)s
			AND pv.run_type IN ('Regular', 'Special')
			{branch_clause}
		GROUP BY pv.employee, e.employee_name
		ORDER BY pv.employee
		""".format(branch_clause=branch_clause),
		params,
		as_dict=True,
	)
	has_tin = frappe.db.has_column("Employee", "tin")
	buf = io.StringIO()
	w = csv.writer(buf)
	w.writerow(["tin", "registered_name", "employee", "gross_compensation", "tax_withheld"])
	for r in rows:
		emp = r.get("employee")
		tin = ""
		if has_tin and emp:
			tin = frappe.db.get_value("Employee", emp, "tin") or ""
		w.writerow(
			[
				tin,
				r.get("registered_name") or "",
				emp,
				flt(r.get("gross_comp")),
				flt(r.get("tax_withheld")),
			]
		)
	frappe.response["filename"] = "alphalist_{0}.csv".format(year)
	frappe.response["filecontent"] = buf.getvalue()
	frappe.response["type"] = "download"
