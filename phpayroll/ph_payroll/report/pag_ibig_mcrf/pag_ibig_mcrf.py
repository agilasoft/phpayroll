import frappe

from phpayroll.ph_payroll.statutory_reports.files.hdmf_mcrf import pagibig_mcrf_csv
from phpayroll.ph_payroll.statutory_reports.report_utils import data_col, money_col, parse_filters, run_aggregate


def execute(filters=None):
	data = run_aggregate(filters, month_required=True)
	columns = [
		data_col("MID", "hdmf_no", 120),
		data_col("Employee", "employee_name", 200),
		money_col("EE", "hd_ee"),
		money_col("ER", "hd_er"),
	]
	return columns, data["employees"]


@frappe.whitelist()
def export_to_csv(filters):
	filters = parse_filters(filters)
	data = run_aggregate(filters, month_required=True)
	return pagibig_mcrf_csv(data["employer"], data["employees"], filters.year, filters.month)
