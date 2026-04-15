# -*- coding: utf-8 -*-
# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class ManualAttendance(Document):
	def validate(self):
		if not self.employee or not self.date:
			return
		d = getdate(self.date)
		emp = self.employee
		if frappe.get_all(
			"Official Business",
			filters={"employee": emp, "date": d, "docstatus": 1},
			limit=1,
		) or frappe.get_all("Leave", filters={"employee": emp, "date": d, "docstatus": 1}, limit=1):
			if "System Manager" not in frappe.get_roles():
				frappe.throw(
					_(
						"This date has submitted Official Business or Leave. Only System Manager may add Manual Attendance."
					),
					title=_("Manual Attendance"),
				)
