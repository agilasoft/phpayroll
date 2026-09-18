# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document


class Attendance(Document):
	def validate(self):
		if not (self.punches or []):
			frappe.throw(_("Add at least one punch row."), title=_("Attendance"))
