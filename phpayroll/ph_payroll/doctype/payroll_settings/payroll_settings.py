# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.belizzo.ph and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt


class PayrollSettings(Document):
	pass


def get_timekeeping_settings():
	"""Defaults for time rounding, breaks, OT fallback, rest day, night differential."""
	doc = frappe.get_single("Payroll Settings")
	return {
		"time_rounding_minutes": cint(getattr(doc, "time_rounding_minutes", None)),
		"time_minimum_paid_hours": flt(getattr(doc, "time_minimum_paid_hours", None)),
		"default_ot_multiplier": flt(getattr(doc, "default_ot_multiplier", None)) or 1.25,
		"unpaid_break_minutes_per_day": cint(getattr(doc, "unpaid_break_minutes_per_day", None)),
		"unpaid_break_apply_after_hours": flt(getattr(doc, "unpaid_break_apply_after_hours", None)),
		"apply_rest_day_sunday": cint(getattr(doc, "apply_rest_day_sunday", None)),
		"rest_day_rate": flt(getattr(doc, "rest_day_rate", None)),
		"enable_night_differential": cint(getattr(doc, "enable_night_differential", None)),
		"night_window_start": getattr(doc, "night_window_start", None),
		"night_window_end": getattr(doc, "night_window_end", None),
		"night_differential_multiplier": flt(getattr(doc, "night_differential_multiplier", None)),
	}


def get_withholding_config():
	"""Return dict for income tax: enabled, method, deduct_contributions, default_tax_table, tax_base_codes."""
	doc = frappe.get_single("Payroll Settings")
	codes = []
	for row in doc.get("tax_base_income_items") or []:
		if row.get("income_component"):
			codes.append(row.income_component)
	if not codes:
		codes = ["basic_pay", "overtime_pay", "holiday_pay", "night_diff_pay", "incentive"]
	return {
		"enabled": cint(getattr(doc, "income_tax_enabled", None)),
		"method": getattr(doc, "withholding_method", None) or "Annual_Table_Per_Cycle",
		"deduct_contributions": cint(getattr(doc, "deduct_contributions_from_tax_base", None)),
		"default_tax_table": getattr(doc, "default_annual_tax_table", None) or None,
		"tax_base_codes": codes,
		"annualized_month_basis": getattr(doc, "annualized_month_basis", None) or "Calendar_Month_of_Date_To",
		"annualized_use_date_of_joining": cint(getattr(doc, "annualized_use_date_of_joining", None)),
	}


def get_defaults_for_13th_month():
	"""Return (enabled: bool, include_special: bool, component_codes: list of str)."""
	doc = frappe.get_single("Payroll Settings")
	enabled = bool(doc.enable_13th_month)
	include_special = bool(doc.include_special_in_13th_month_base)
	codes = []
	for row in doc.get("thirteenth_month_income_items") or []:
		if row.income_component:
			codes.append(row.income_component)
	if not codes:
		codes = ["basic_pay"]
	return enabled, include_special, codes
