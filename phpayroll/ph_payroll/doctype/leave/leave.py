# -*- coding: utf-8 -*-
# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from phpayroll.ph_payroll.doctype.leave_credits.leave_credits import (
	assert_sufficient_leave_credits,
	consume_leave_credits,
	restore_leave_credits,
)


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

	def before_submit(self):
		assert_sufficient_leave_credits(self.employee, self.type, self.number_of_days)

	def on_submit(self):
		consume_leave_credits(self)

	def on_cancel(self):
		restore_leave_credits(self)
