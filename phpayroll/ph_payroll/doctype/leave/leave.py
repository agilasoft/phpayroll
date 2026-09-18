# -*- coding: utf-8 -*-
# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from phpayroll.ph_payroll.doctype.leave_blackout_period.leave_blackout_period import leave_date_in_blackout
from phpayroll.ph_payroll.doctype.leave_credits.leave_credits import (
	assert_sufficient_leave_credits,
	consume_leave_credits,
	restore_leave_credits,
)


def leave_type_is_paid(leave_type_name):
	if not leave_type_name:
		return True
	v = frappe.db.get_value("Leave Type", leave_type_name, "is_paid")
	if v is None:
		return True
	return cint(v) == 1


class Leave(Document):
	def validate(self):
		if self.type and not frappe.db.exists("Leave Type", self.type):
			frappe.throw(_("Leave Type {0} is not valid.").format(self.type), title=_("Leave"))
		if self.number_of_days in (None, ""):
			self.number_of_days = 1
		d = flt(self.number_of_days)
		if d <= 0:
			frappe.throw(_("Number of Days must be greater than zero."), title=_("Leave"))
		if d > 1:
			frappe.throw(
				_("Number of Days cannot exceed 1 for a single leave date. Create another row for additional days."),
				title=_("Leave"),
			)
		blk = leave_date_in_blackout(self.date, self.branch)
		if blk and "System Manager" not in frappe.get_roles():
			frappe.throw(
				_("Leave is blocked for this date ({0}).").format(blk.get("description") or blk.get("name")),
				title=_("Leave Blackout"),
			)

	def before_submit(self):
		if leave_type_is_paid(self.type):
			assert_sufficient_leave_credits(self.employee, self.type, self.number_of_days)

	def on_submit(self):
		if leave_type_is_paid(self.type):
			consume_leave_credits(self)

	def on_cancel(self):
		if leave_type_is_paid(self.type):
			restore_leave_credits(self)
