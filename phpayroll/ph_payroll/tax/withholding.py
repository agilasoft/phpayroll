# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.belizzo.ph and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint, flt, fmt_money, getdate

METHOD_ANNUAL_TABLE = "Annual_Table_Per_Cycle"
METHOD_ANNUALIZED_YTD = "Annualized_YTD"
METHOD_MANUAL_ONLY = "Manual_Only"

MONTH_BASIS_CALENDAR = "Calendar_Month_of_Date_To"
MONTH_BASIS_PAY_PERIODS = "Pay_Period_Count_YTD"

TAX_BASE_VOUCHER_TOTALS = {
	"basic_pay": "total_basic_pay",
	"overtime_pay": "total_overtime_pay",
	"holiday_pay": "total_holiday_pay",
	"night_diff_pay": "total_night_diff_pay",
	"incentive": "total_incentive",
}

ALLOWED_TAX_BASE_CODES = frozenset(TAX_BASE_VOUCHER_TOTALS.keys()) | frozenset({"net_sales"})


def _child_items(parent, fieldname):
	if hasattr(parent, "get"):
		return parent.get(fieldname) or []
	return getattr(parent, fieldname, None) or []


def _flt_field(obj, fieldname):
	if hasattr(obj, "get"):
		return flt(obj.get(fieldname))
	return flt(getattr(obj, fieldname, 0))


def compute_gross_taxable_from_voucher(voucher, codes):
	"""Sum configured income components for the voucher period (voucher totals + item net_sales)."""
	gross = 0.0
	items = _child_items(voucher, "items")
	for code in codes:
		if code not in ALLOWED_TAX_BASE_CODES:
			continue
		if code in TAX_BASE_VOUCHER_TOTALS:
			gross += _flt_field(voucher, TAX_BASE_VOUCHER_TOTALS[code])
		elif code == "net_sales":
			gross += sum(flt(getattr(row, "net_sales", 0) or 0) for row in items)
	return gross


def find_bracket_row(table_doc, taxable_amount):
	"""Return the Annual Tax Table Item row for taxable_amount, or None."""
	items = sorted(_child_items(table_doc, "items"), key=lambda r: flt(getattr(r, "from", 0)))
	if not items:
		return None
	t = flt(taxable_amount)
	if t <= 0:
		return None
	for row in items:
		rf = flt(getattr(row, "from", 0))
		rt = flt(getattr(row, "to", 0))
		if rf <= t <= rt:
			return row
	if t > flt(getattr(items[-1], "to", 0)):
		return items[-1]
	if t < flt(getattr(items[0], "from", 0)):
		return items[0]
	return None


def compute_tax_from_bracket(row, taxable_amount):
	"""BIR-style: fixed + (taxable - from) * rate/100 on the marginal band."""
	if not row:
		return 0.0
	base = flt(taxable_amount) - flt(getattr(row, "from", 0))
	excess = base if base > 0 else 0.0
	return flt(getattr(row, "fixed", 0)) + excess * flt(getattr(row, "rate", 0)) / 100.0


def resolve_annual_tax_table(employee_doc, default_name):
	"""Pick Annual Tax Table: employee override, then Payroll Settings default, else sole active."""
	name = employee_doc.get("annual_tax_table") or default_name
	if name:
		doc = frappe.get_doc("Annual Tax Table", name)
		if not cint(doc.active):
			frappe.throw(
				_("Annual Tax Table {0} is not active.").format(frappe.bold(name)),
				title=_("Withholding Tax"),
			)
		return doc

	active = frappe.get_all("Annual Tax Table", filters={"active": 1}, pluck="name")
	if not active:
		frappe.throw(
			_(
				"No active Annual Tax Table. Create one in Annual Tax Table or set Default Annual Tax Table in Payroll Settings."
			),
			title=_("Withholding Tax"),
		)
	if len(active) == 1:
		return frappe.get_doc("Annual Tax Table", active[0])
	if default_name:
		doc = frappe.get_doc("Annual Tax Table", default_name)
		if not cint(doc.active):
			frappe.throw(
				_("Payroll Settings Default Annual Tax Table {0} is not active.").format(frappe.bold(default_name)),
				title=_("Withholding Tax"),
			)
		return doc
	frappe.throw(
		_(
			"Multiple active Annual Tax Tables. Set Default Annual Tax Table in Payroll Settings, or keep only one active."
		),
		title=_("Withholding Tax"),
	)


def _ytd_conditions(voucher, year):
	conditions = [
		"employee = %(employee)s",
		"YEAR(date_to) = %(year)s",
		"IFNULL(branch, '') = %(branch)s",
		"run_type IN ('Regular', 'Special')",
		"docstatus != 2",
	]
	params = {
		"employee": voucher.employee,
		"year": year,
		"branch": voucher.branch or "",
	}
	if voucher.name:
		conditions.append("name != %(vname)s")
		params["vname"] = voucher.name
	return conditions, params


def get_ytd_taxable_and_tax_withheld(voucher):
	"""Sum taxable_income and tax from other vouchers in the same year (excludes this voucher if named)."""
	year = getdate(voucher.date_to).year
	conditions, params = _ytd_conditions(voucher, year)
	sql = """
		SELECT COALESCE(SUM(taxable_income), 0), COALESCE(SUM(tax), 0)
		FROM `tabPayroll Voucher`
		WHERE {where}
	""".format(where=" AND ".join(conditions))
	row = frappe.db.sql(sql, params)
	if not row:
		return 0.0, 0.0
	return flt(row[0][0]), flt(row[0][1])


def get_pay_period_count_including_current(voucher):
	"""Number of Regular/Special payroll vouchers in the calendar year of date_to, including this run."""
	year = getdate(voucher.date_to).year
	conditions, params = _ytd_conditions(voucher, year)
	sql = "SELECT COUNT(*) FROM `tabPayroll Voucher` WHERE {where}".format(where=" AND ".join(conditions))
	cnt = frappe.db.sql(sql, params)
	n = int(cnt[0][0]) if cnt else 0
	return max(1, n + 1)


def months_elapsed_for_annualized(voucher, employee_doc, cfg):
	"""Months factor n for projected annual = (YTD_incl / n) * 12."""
	dt = getdate(voucher.date_to)
	basis = cfg.get("annualized_month_basis") or MONTH_BASIS_CALENDAR

	if basis == MONTH_BASIS_PAY_PERIODS:
		return get_pay_period_count_including_current(voucher)

	respect_join = cint(cfg.get("annualized_use_date_of_joining"))
	join_raw = employee_doc.get("date_of_joining") if respect_join else None
	if join_raw:
		jd = getdate(join_raw)
		if jd <= dt:
			year = dt.year
			if jd.year < year:
				start_year, start_month = year, 1
			elif jd.year == year:
				start_year, start_month = jd.year, jd.month
			else:
				start_year, start_month = year, 1
			n = (dt.year - start_year) * 12 + (dt.month - start_month) + 1
			return max(1, n)

	return max(1, dt.month)


def compute_annualized_withholding_tax_amount(
	prior_taxable_ytd, prior_tax_withheld, current_period_taxable, months_elapsed, table_doc
):
	"""
	Pure math: projected annual income, full-year tax from table, prorated YTD due, minus prior withheld.
	Returns (withholding_for_this_period, projected_annual_income).
	"""
	n = max(1, int(months_elapsed))
	ytd_incl = flt(prior_taxable_ytd) + flt(current_period_taxable)
	projected_annual = (ytd_incl / float(n)) * 12.0

	row = find_bracket_row(table_doc, projected_annual)
	if not row:
		return None, projected_annual

	annual_tax = compute_tax_from_bracket(row, projected_annual)
	tax_due_ytd = annual_tax * (float(n) / 12.0)
	wh = tax_due_ytd - flt(prior_tax_withheld)
	return max(0.0, flt(wh)), projected_annual


def compute_withholding_tax(voucher):
	"""
	Set voucher.taxable_income and voucher.tax from Payroll Settings + Annual Tax Table.
	Call after SSS/PhilHealth/HDMF so net_pay can be reduced by tax; caller adjusts net_pay.
	"""
	from phpayroll.ph_payroll.doctype.payroll_settings.payroll_settings import get_withholding_config

	cfg = get_withholding_config()
	if not cfg["enabled"]:
		return

	method = cfg["method"]
	if method == METHOD_MANUAL_ONLY:
		return
	if method not in (METHOD_ANNUAL_TABLE, METHOD_ANNUALIZED_YTD):
		return

	run_type = getattr(voucher, "run_type", None) or "Regular"
	if run_type == "13th Month":
		return

	employee = frappe.get_cached_doc("Employee", voucher.employee)
	codes = [c for c in cfg["tax_base_codes"] if c in ALLOWED_TAX_BASE_CODES]
	gross = compute_gross_taxable_from_voucher(voucher, codes)

	taxable = gross
	if cfg["deduct_contributions"]:
		taxable -= (
			flt(voucher.ss_ee)
			+ flt(voucher.wisp_ee)
			+ flt(voucher.ph_ee)
			+ flt(voucher.hd_ee)
		)
	taxable = max(0.0, flt(taxable))

	voucher.taxable_income = taxable

	if cint(employee.get("is_mwe")) or cint(employee.get("withholding_tax_exempt")):
		voucher.tax = 0.0
		return

	if taxable <= 0:
		voucher.tax = 0.0
		return

	table = resolve_annual_tax_table(employee, cfg["default_tax_table"])

	if method == METHOD_ANNUAL_TABLE:
		row = find_bracket_row(table, taxable)
		if not row:
			frappe.throw(
				_("Annual Tax Table {0} has no brackets.").format(frappe.bold(table.name)),
				title=_("Withholding Tax"),
			)
		voucher.tax = compute_tax_from_bracket(row, taxable)
		return

	# Annualized_YTD
	prior_taxable, prior_tax = get_ytd_taxable_and_tax_withheld(voucher)
	n = months_elapsed_for_annualized(voucher, employee, cfg)
	wh, projected = compute_annualized_withholding_tax_amount(
		prior_taxable, prior_tax, taxable, n, table
	)
	if wh is None:
		frappe.throw(
			_("Annual Tax Table {0} has no brackets (projected annual taxable: {1}).").format(
				frappe.bold(table.name), frappe.bold(fmt_money(projected))
			),
			title=_("Withholding Tax"),
		)
	voucher.tax = wh
