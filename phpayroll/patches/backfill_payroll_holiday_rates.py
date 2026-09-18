# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe.utils import flt


def execute():
	if not frappe.db.table_exists("tabPayroll Holiday"):
		return

	rows = frappe.db.sql(
		"""
		SELECT ph.name, ph.holiday_type, ph.rate, ht.rate AS type_rate
		FROM `tabPayroll Holiday` ph
		LEFT JOIN `tabHoliday Type` ht ON ht.name = ph.holiday_type
		WHERE IFNULL(ph.rate, 0) = 0 AND IFNULL(ht.rate, 0) > 0
		""",
		as_dict=True,
	)
	for row in rows:
		frappe.db.set_value("Payroll Holiday", row.name, "rate", flt(row.type_rate))
