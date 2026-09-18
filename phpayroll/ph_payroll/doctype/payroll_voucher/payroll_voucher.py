# -*- coding: utf-8 -*-
# Copyright (c) 2024, www.belizzo.ph and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from phpayroll.ph_payroll.earnings import compute_period_pay
from phpayroll.ph_payroll.statutory import apply_statutory_to_doc, calculate_statutory


class PayrollVoucher(Document):
	pass


def enforce_freeze(doc, method=None):
	from phpayroll.ph_payroll.engine import uses_hrms_payroll

	company = frappe.db.get_value("Employee", doc.employee, "company") if doc.employee else None
	if uses_hrms_payroll(company) and doc.is_new():
		frappe.throw(
			_("Payroll computation is on Frappe HR Salary Slip. Use Salary Slip / Payroll Entry for new pay runs.")
		)


@frappe.whitelist()
def run_payroll(date_from, date_to, branch):
	from phpayroll.ph_payroll.engine import assert_legacy_payroll

	assert_legacy_payroll()
	frappe.msgprint(f"Running payroll from {date_from} to {date_to} for branch {branch}", title="Payroll Run Start")
	payroll_vouchers = []

	employees = frappe.get_all("Employee", filters={"status": "Active", "reporting_branch": branch})
	if employees:
		assert_legacy_payroll(frappe.db.get_value("Employee", employees[0].name, "company"))
	for employee in employees:
		voucher = get_or_create_payroll_voucher(employee.name, date_from, date_to, branch)
		if voucher:
			populate_items(voucher)
			voucher.save(ignore_permissions=True)
			payroll_vouchers.append(voucher.name)

	frappe.msgprint(
		f"Payroll run completed successfully. Vouchers created/updated: {', '.join(payroll_vouchers)}",
		title="Payroll Run Complete",
	)
	return f"Payroll run completed successfully. Vouchers created/updated: {', '.join(payroll_vouchers)}"


@frappe.whitelist()
def recompute_payroll_voucher(voucher_name):
	voucher = frappe.get_doc("Payroll Voucher", voucher_name)
	populate_items(voucher)
	voucher.save(ignore_permissions=True)
	frappe.msgprint(
		f"Payroll voucher recomputed successfully. Voucher updated: {voucher.name}",
		title="Payroll Recompute Complete",
	)
	return f"Payroll voucher recomputed successfully. Voucher updated: {voucher.name}"


def get_or_create_payroll_voucher(employee, date_from, date_to, branch):
	existing_vouchers = frappe.get_all(
		"Payroll Voucher",
		filters={
			"employee": employee,
			"branch": branch,
			"date_from": date_from,
			"date_to": date_to,
		},
	)
	if existing_vouchers:
		return frappe.get_doc("Payroll Voucher", existing_vouchers[0].name)

	overlapping_vouchers = frappe.get_all(
		"Payroll Voucher",
		filters={
			"employee": employee,
			"branch": branch,
			"date_from": ["<=", date_to],
			"date_to": [">=", date_from],
		},
	)
	if overlapping_vouchers:
		frappe.msgprint(
			f"Found overlapping vouchers for Employee: {employee} in branch: {branch}. Cannot create/update voucher due to overlap.",
			title="Voucher Overlap",
		)
		return None

	voucher = frappe.new_doc("Payroll Voucher")
	voucher.employee = employee
	voucher.date_from = date_from
	voucher.date_to = date_to
	voucher.branch = branch
	voucher.save(ignore_permissions=True)
	return voucher


def populate_items(voucher):
	if not voucher.date_from or not voucher.date_to or not voucher.employee:
		frappe.throw(_("Please ensure Employee, Date From, and Date To are filled."))

	totals = compute_period_pay(
		voucher.employee,
		voucher.date_from,
		voucher.date_to,
		branch=voucher.branch,
		voucher=voucher,
	)
	voucher.total_basic_pay = totals.total_basic_pay
	voucher.total_holiday_pay = totals.total_holiday_pay
	voucher.total_overtime_pay = totals.total_overtime_pay
	voucher.total_incentive = totals.total_incentive
	voucher.less_cash_advance = totals.less_cash_advance

	other_taxable = (
		flt(totals.total_overtime_pay) + flt(totals.total_holiday_pay) + flt(totals.total_incentive)
	)
	stat = calculate_statutory(
		voucher.employee,
		totals.total_basic_pay,
		voucher.date_from,
		voucher.date_to,
		other_taxable=other_taxable,
		source="payroll_voucher",
	)
	apply_statutory_to_doc(voucher, stat)
	voucher.net_pay = flt(totals.gross) - flt(totals.less_cash_advance) - flt(stat.sss) - flt(stat.philhealth) - flt(stat.hdmf) - flt(stat.tax)
	voucher.save(ignore_permissions=True)
