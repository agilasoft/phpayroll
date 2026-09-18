# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

from __future__ import annotations

import json

import frappe
from frappe import _

from phpayroll.ph_payroll.statutory_reports.aggregator import aggregate_employees


def parse_filters(filters):
	if isinstance(filters, str):
		filters = json.loads(filters or "{}")
	return frappe._dict(filters or {})


def require_company_year(filters, month_required=False):
	if not filters.get("company"):
		frappe.throw(_("Please select Company"))
	if not filters.get("year"):
		frappe.throw(_("Please select Year"))
	if month_required and not filters.get("month"):
		frappe.throw(_("Please select Month"))


def money_col(label, field, width=120):
	return {"label": _(label), "fieldname": field, "fieldtype": "Currency", "width": width}


def data_col(label, field, width=140):
	return {"label": _(label), "fieldname": field, "fieldtype": "Data", "width": width}


def run_aggregate(filters, month_required=False):
	filters = parse_filters(filters)
	require_company_year(filters, month_required=month_required)
	return aggregate_employees(
		filters.company,
		filters.year,
		month=filters.month if month_required or filters.get("month") else None,
		branch=filters.get("branch"),
	)
