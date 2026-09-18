# -*- coding: utf-8 -*-
# Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class AnnualTaxTable(Document):
	def validate(self):
		items = sorted(self.get("items") or [], key=lambda x: flt(getattr(x, "from", 0)))
		prev_to = None
		for i, row in enumerate(items, start=1):
			rf = flt(getattr(row, "from", 0))
			rt = flt(getattr(row, "to", 0))
			if rt < rf:
				frappe.throw(_("Row {0}: To must be greater than or equal to From.").format(i))
			if prev_to is not None and rf <= prev_to:
				frappe.throw(_("Row {0}: Tax brackets overlap or are not strictly increasing.").format(i))
			prev_to = rt
