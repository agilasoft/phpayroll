# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.belizzo.ph and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class PayrollSettings(Document):
	pass


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
