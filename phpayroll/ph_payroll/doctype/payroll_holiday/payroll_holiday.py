# -*- coding: utf-8 -*-
# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class PayrollHoliday(Document):
	def validate(self):
		if self.holiday_type and not flt(self.rate):
			type_rate = frappe.db.get_value("Holiday Type", self.holiday_type, "rate")
			if type_rate is not None:
				self.rate = flt(type_rate)
