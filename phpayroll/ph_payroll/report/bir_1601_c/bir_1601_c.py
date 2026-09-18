# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe

from phpayroll.ph_payroll.statutory_reports.files.bir_dat import bir_1601c_dat
from phpayroll.ph_payroll.statutory_reports.report_utils import data_col, money_col, parse_filters, run_aggregate


def execute(filters=None):
	data = run_aggregate(filters, month_required=True)
	columns = [
		data_col("TIN", "tin", 120),
		data_col("Employee", "employee_name", 200),
		money_col("Taxable", "taxable"),
		money_col("Tax Withheld", "tax"),
		money_col("SSS EE", "sss_ee_total"),
		money_col("PHIC EE", "ph_ee"),
		money_col("HDMF EE", "hd_ee"),
	]
	return columns, data["employees"]


@frappe.whitelist()
def export_to_dat(filters):
	filters = parse_filters(filters)
	data = run_aggregate(filters, month_required=True)
	return bir_1601c_dat(data["employer"], data["employees"], data["period_start"], data["period_end"])
