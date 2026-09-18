# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.utils import flt

from phpayroll.ph_payroll.constants import (
	BASIC_PAY,
	CASH_ADVANCE,
	EC_ER,
	HOLIDAY_PAY,
	INCENTIVE,
	OVERTIME_PAY,
	PAGIBIG_EE,
	PAGIBIG_ER,
	PHILHEALTH_EE,
	PHILHEALTH_ER,
	SSS_EE,
	SSS_ER,
	THIRTEENTH_MONTH,
	WISP_EE,
	WISP_ER,
	WITHHOLDING_TAX,
)
from phpayroll.ph_payroll.earnings import compute_period_pay
from phpayroll.ph_payroll.statutory import apply_statutory_to_doc, calculate_statutory

try:
	from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip
except Exception:  # pragma: no cover - hrms not installed on site yet
	from frappe.model.document import Document as SalarySlip


class PHSalarySlip(SalarySlip):
	def calculate_net_pay(self, skip_tax_breakup_computation=True):
		if getattr(self, "salary_structure", None) and hasattr(super(), "calculate_net_pay"):
			super().calculate_net_pay(skip_tax_breakup_computation=True)
		self.apply_ph_payroll()
		if hasattr(self, "set_precision_for_component_amounts"):
			self.set_precision_for_component_amounts()
		if hasattr(self, "set_net_pay"):
			self.set_net_pay()

	def apply_regional_deductions(self):
		# India TDS skipped; PH statutory applied in apply_ph_payroll after totals exist.
		return

	def apply_ph_payroll(self):
		from phpayroll.ph_payroll.engine import uses_legacy_payroll

		if uses_legacy_payroll(self.company):
			return
		if not self.employee or not self.start_date or not self.end_date:
			return
		branch = frappe.db.get_value("Employee", self.employee, "reporting_branch")
		earnings = compute_period_pay(self.employee, self.start_date, self.end_date, branch=branch)
		self.total_basic_pay = earnings.total_basic_pay
		self.set_component_amount("earnings", BASIC_PAY, earnings.total_basic_pay)
		self.set_component_amount("earnings", OVERTIME_PAY, earnings.total_overtime_pay)
		self.set_component_amount("earnings", HOLIDAY_PAY, earnings.total_holiday_pay)
		self.set_component_amount("earnings", INCENTIVE, earnings.total_incentive)
		self.set_component_amount("deductions", CASH_ADVANCE, earnings.less_cash_advance)

		thirteenth = self.component_amount("earnings", THIRTEENTH_MONTH)
		other_taxable = (
			flt(earnings.total_overtime_pay)
			+ flt(earnings.total_holiday_pay)
			+ flt(earnings.total_incentive)
		)
		stat = calculate_statutory(
			self.employee,
			earnings.total_basic_pay,
			self.start_date,
			self.end_date,
			other_taxable=other_taxable,
			thirteenth_month=thirteenth,
			source="salary_slip",
		)
		apply_statutory_to_doc(self, stat)
		self.set_component_amount("deductions", SSS_EE, flt(stat.ss_ee) + flt(stat.wisp_ee))
		self.set_component_amount("deductions", WISP_EE, 0)
		self.set_component_amount("deductions", PHILHEALTH_EE, stat.ph_ee)
		self.set_component_amount("deductions", PAGIBIG_EE, stat.hd_ee)
		self.set_component_amount("deductions", WITHHOLDING_TAX, stat.tax)
		self.set_component_amount("earnings", SSS_ER, 0)
		self.set_employer_amount(SSS_ER, stat.ss_er)
		self.set_employer_amount(WISP_ER, stat.wisp_er)
		self.set_employer_amount(EC_ER, stat.ec_er)
		self.set_employer_amount(PHILHEALTH_ER, stat.ph_er)
		self.set_employer_amount(PAGIBIG_ER, stat.hd_er)

		if hasattr(self, "get_component_totals"):
			self.gross_pay = self.get_component_totals("earnings", depends_on_payment_days=0)

	def component_amount(self, table, name):
		for row in self.get(table) or []:
			if row.salary_component == name:
				return flt(row.amount)
		return 0

	def set_component_amount(self, table, name, amount):
		amount = flt(amount)
		for row in self.get(table) or []:
			if row.salary_component == name:
				row.amount = amount
				row.default_amount = amount
				return
		if amount == 0:
			return
		self.append(
			table,
			{
				"salary_component": name,
				"amount": amount,
				"default_amount": amount,
				"depends_on_payment_days": 0,
			},
		)

	def set_employer_amount(self, name, amount):
		amount = flt(amount)
		table = "employer_contributions" if self.meta.has_field("employer_contributions") else None
		if not table:
			return
		self.set_component_amount(table, name, amount)
