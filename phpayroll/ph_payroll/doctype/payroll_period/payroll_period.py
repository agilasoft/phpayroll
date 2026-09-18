# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime


class PayrollPeriod(Document):
	def validate(self):
		if getdate(self.date_from) > getdate(self.date_to):
			frappe.throw(_("Date From cannot be after Date To."), title=_("Payroll Period"))

	def before_save(self):
		if self.is_closed and not self.closed_on:
			self.closed_on = now_datetime()
			self.closed_by = frappe.session.user
		if not self.is_closed:
			self.closed_on = None
			self.closed_by = None


def is_payroll_period_locked(branch, date_from, date_to):
	if frappe.flags.get("ignore_payroll_period_lock"):
		return False
	if not frappe.db.exists("DocType", "Payroll Period"):
		return False
	df, dt = getdate(date_from), getdate(date_to)
	b = branch or ""
	rows = frappe.db.sql(
		"""
		SELECT name FROM `tabPayroll Period`
		WHERE `is_closed` = 1
			AND `date_from` <= %(dt)s
			AND `date_to` >= %(df)s
			AND (`branch` IS NULL OR `branch` = '' OR `branch` = %(branch)s)
		""",
		{"df": df, "dt": dt, "branch": b},
	)
	return bool(rows)


def can_bypass_payroll_period_lock():
	if frappe.session.user == "Administrator":
		return True
	roles = frappe.get_roles(frappe.session.user)
	return "System Manager" in roles
