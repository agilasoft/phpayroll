# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe

from phpayroll.ph_payroll.constants import ENGINE_HRMS, ENGINE_LEGACY


def execute():
	if not frappe.db.exists("DocType", "PH Payroll Settings"):
		return
	if not frappe.db.has_column("PH Payroll Settings", "computation_engine"):
		return
	frappe.db.sql(
		"""
		UPDATE `tabPH Payroll Settings`
		SET computation_engine = %s
		WHERE IFNULL(computation_engine, '') = '' AND IFNULL(freeze_payroll_voucher, 0) = 1
		""",
		ENGINE_HRMS,
	)
	frappe.db.sql(
		"""
		UPDATE `tabPH Payroll Settings`
		SET computation_engine = %s
		WHERE IFNULL(computation_engine, '') = ''
		""",
		ENGINE_LEGACY,
	)
	if frappe.db.has_column("PH Payroll Settings", "count_on_duty_as_official_business"):
		frappe.db.sql(
			"""
			UPDATE `tabPH Payroll Settings`
			SET count_on_duty_as_official_business = 1
			WHERE computation_engine = %s
			""",
			ENGINE_HRMS,
		)
