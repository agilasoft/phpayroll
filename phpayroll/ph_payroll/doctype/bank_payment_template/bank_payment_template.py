# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors

from __future__ import unicode_literals

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class BankPaymentTemplate(Document):
	def validate(self):
		if not (self.column_map or "").strip():
			frappe.throw(_("Column Map is required."), title=_("Bank Payment Template"))
		try:
			parsed = json.loads(self.column_map)
		except ValueError:
			frappe.throw(_("Column Map must be valid JSON."), title=_("Bank Payment Template"))
		if not isinstance(parsed, list) or not parsed:
			frappe.throw(_("Column Map must be a non-empty JSON array."), title=_("Bank Payment Template"))


ALLOWED_BANK_COLUMNS = frozenset(
	{"employee", "employee_name", "branch", "net_pay", "voucher", "date_to", "taxable_income", "tax"}
)


def row_values_from_voucher(voucher_name, keys):
	v = frappe.get_doc("Payroll Voucher", voucher_name)
	out = []
	for k in keys:
		if k not in ALLOWED_BANK_COLUMNS:
			out.append("")
		elif k == "employee":
			out.append(v.employee or "")
		elif k == "employee_name":
			out.append(v.employee_name or "")
		elif k == "branch":
			out.append(v.branch or "")
		elif k == "net_pay":
			out.append(str(flt(v.net_pay)))
		elif k == "voucher":
			out.append(v.name)
		elif k == "date_to":
			out.append(str(v.date_to or ""))
		elif k == "taxable_income":
			out.append(str(flt(v.taxable_income)))
		elif k == "tax":
			out.append(str(flt(v.tax)))
		else:
			out.append("")
	return out


@frappe.whitelist()
def export_payroll_bank_file(template_code, voucher_names):
	if isinstance(voucher_names, str):
		voucher_names = json.loads(voucher_names)
	doc = frappe.get_doc("Bank Payment Template", template_code)
	keys = json.loads(doc.column_map)
	delim = doc.delimiter or ","
	if delim == "\\t":
		delim = "\t"
	lines = []
	if doc.include_header:
		lines.append(delim.join(keys))
	for name in voucher_names:
		if not frappe.db.exists("Payroll Voucher", name):
			continue
		vals = row_values_from_voucher(name, keys)
		lines.append(delim.join(vals))
	content = "\n".join(lines)
	frappe.response["filename"] = "{0}_payroll_export.csv".format(template_code)
	frappe.response["filecontent"] = content
	frappe.response["type"] = "download"
