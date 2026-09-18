import frappe

from phpayroll.ph_payroll.statutory_reports.files.sss_r3 import sss_r3_dat
from phpayroll.ph_payroll.statutory_reports.report_utils import data_col, money_col, parse_filters, run_aggregate


def execute(filters=None):
	data = run_aggregate(filters, month_required=True)
	columns = [
		data_col("SSS No", "sss_no", 120),
		data_col("Employee", "employee_name", 200),
		money_col("SS EE", "ss_ee"),
		money_col("SS ER", "ss_er"),
		money_col("EC", "ec_er"),
		money_col("WISP EE", "wisp_ee"),
		money_col("WISP ER", "wisp_er"),
	]
	return columns, data["employees"]


@frappe.whitelist()
def export_to_dat(filters):
	filters = parse_filters(filters)
	data = run_aggregate(filters, month_required=True)
	return sss_r3_dat(data["employer"], data["employees"], filters.year, filters.month)
