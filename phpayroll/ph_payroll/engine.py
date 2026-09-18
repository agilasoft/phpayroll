# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Company-level switch: legacy Payroll Voucher vs Frappe HR Salary Slip."""

from __future__ import annotations

import frappe
from frappe import _

from phpayroll.ph_payroll.constants import ENGINE_HRMS, ENGINE_LEGACY
from phpayroll.ph_payroll.doctype.ph_payroll_settings.ph_payroll_settings import PHPayrollSettings


def get_computation_engine(company=None):
	"""Return ENGINE_LEGACY (default) or ENGINE_HRMS."""
	if not company:
		company = frappe.defaults.get_user_default("Company")
	settings = PHPayrollSettings.get_settings(company) if company else None
	if settings:
		engine = settings.get("computation_engine")
		if engine:
			return engine
		# Pre-cutover freeze flag means they already moved off Payroll Voucher.
		if settings.get("freeze_payroll_voucher"):
			return ENGINE_HRMS
	return ENGINE_LEGACY


def uses_hrms_payroll(company=None):
	return get_computation_engine(company) == ENGINE_HRMS


def uses_legacy_payroll(company=None):
	return not uses_hrms_payroll(company)


def company_for_employee(employee):
	return frappe.db.get_value("Employee", employee, "company") if employee else None


def assert_legacy_payroll(company=None, employee=None):
	company = company or company_for_employee(employee)
	if uses_hrms_payroll(company):
		frappe.throw(
			_(
				"Payroll computation is set to Frappe HR Salary Slip for this company. "
				"Use Payroll Entry / Salary Slip. Change PH Payroll Settings to "
				"PH Payroll Voucher only for legacy cutovers."
			)
		)


def assert_hrms_payroll(company=None, employee=None):
	company = company or company_for_employee(employee)
	if uses_legacy_payroll(company):
		frappe.throw(
			_(
				"Payroll computation is set to PH Payroll Voucher (legacy) for this company. "
				"Existing Payroll Vouchers stay valid. Switch PH Payroll Settings to "
				"Frappe HR Salary Slip when you are ready to run payroll in HRMS."
			)
		)


@frappe.whitelist()
def get_engine_for_company(company=None):
	company = company or frappe.defaults.get_user_default("Company")
	engine = get_computation_engine(company)
	return {
		"company": company,
		"engine": engine,
		"uses_hrms": engine == ENGINE_HRMS,
		"uses_legacy": engine == ENGINE_LEGACY,
	}
