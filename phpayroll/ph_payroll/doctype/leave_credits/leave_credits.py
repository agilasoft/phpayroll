# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class LeaveCredits(Document):
	def validate(self):
		for row in self.entries or []:
			if not row.leave_type:
				frappe.throw(
					_("Leave Type is required on each ledger row."),
					title=_("Leave Credits"),
				)
			if not frappe.db.exists("Leave Type", row.leave_type):
				frappe.throw(
					_("Leave Type {0} does not exist.").format(row.leave_type),
					title=_("Leave Credits"),
				)
		self.balance = sum(flt(row.days) for row in (self.entries or []))


def get_leave_credit_balance(employee, leave_type):
	"""Sum of ledger days for the employee and Leave Type (Leave Credits name == employee)."""
	if not employee or not leave_type or not frappe.db.exists("Leave Credits", employee):
		return 0.0
	rows = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(days), 0) AS bal
		FROM `tabLeave Credit Line`
		WHERE parent = %s AND parenttype = 'Leave Credits'
			AND leave_type = %s
		""",
		(employee, leave_type),
	)
	return flt(rows[0][0]) if rows else 0.0


def get_or_create_leave_credits(employee):
	if frappe.db.exists("Leave Credits", employee):
		return frappe.get_doc("Leave Credits", employee)
	doc = frappe.get_doc({"doctype": "Leave Credits", "employee": employee})
	doc.insert(ignore_permissions=True)
	return doc


def _leave_type_label(leave_type):
	if not leave_type:
		return ""
	return frappe.db.get_value("Leave Type", leave_type, "type_name") or leave_type


def assert_sufficient_leave_credits(employee, leave_type, days_needed):
	if not leave_type:
		frappe.throw(_("Leave Type is required."), title=_("Leave Credits"))
	bal = get_leave_credit_balance(employee, leave_type)
	if bal < flt(days_needed):
		frappe.throw(
			_(
				"Insufficient {0} leave credits. Required: {1} day(s), available: {2}."
			).format(_leave_type_label(leave_type), flt(days_needed, 2), flt(bal, 2)),
			title=_("Leave Credits"),
		)


def consume_leave_credits(leave_doc):
	days = flt(leave_doc.number_of_days)
	leave_type = leave_doc.type
	if days <= 0 or not leave_type:
		return
	if frappe.db.sql(
		"""
		SELECT name FROM `tabLeave Credit Line`
		WHERE parent = %s AND parenttype = 'Leave Credits'
			AND reference_doctype = 'Leave' AND reference_name = %s AND entry_type = 'Leave'
		LIMIT 1
		""",
		(leave_doc.employee, leave_doc.name),
	):
		return
	lc = get_or_create_leave_credits(leave_doc.employee)
	lc.append(
		"entries",
		{
			"posting_date": leave_doc.date,
			"entry_type": "Leave",
			"leave_type": leave_type,
			"days": -days,
			"reference_doctype": "Leave",
			"reference_name": leave_doc.name,
			"remarks": _("Paid leave — deducted from leave credits"),
		},
	)
	lc.save(ignore_permissions=True)


def restore_leave_credits(leave_doc):
	days = flt(leave_doc.number_of_days)
	leave_type = leave_doc.type
	if days <= 0 or not leave_type:
		return
	lc = get_or_create_leave_credits(leave_doc.employee)
	lc.append(
		"entries",
		{
			"posting_date": leave_doc.date,
			"entry_type": "Reversal",
			"leave_type": leave_type,
			"days": days,
			"reference_doctype": "Leave",
			"reference_name": leave_doc.name,
			"remarks": _("Leave cancelled — credits restored"),
		},
	)
	lc.save(ignore_permissions=True)
