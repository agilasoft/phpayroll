# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class LeaveBlackoutPeriod(Document):
	def validate(self):
		if getdate(self.date_from) > getdate(self.date_to):
			frappe.throw(_("Date From cannot be after Date To."), title=_("Leave Blackout Period"))


def leave_date_in_blackout(leave_date, branch):
	if not frappe.db.exists("DocType", "Leave Blackout Period"):
		return None
	d = getdate(leave_date)
	b = branch or ""
	rows = frappe.db.sql(
		"""
		SELECT name, description FROM `tabLeave Blackout Period`
		WHERE `date_from` <= %(d)s AND `date_to` >= %(d)s
			AND (`branch` IS NULL OR `branch` = '' OR `branch` = %(b)s)
		LIMIT 1
		""",
		{"d": d, "b": b},
		as_dict=True,
	)
	return rows[0] if rows else None
