frappe.query_reports["PhilHealth RF-1"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "year",
			label: __("Year"),
			fieldtype: "Int",
			default: frappe.datetime.get_today().split("-")[0],
			reqd: 1,
		},
		{
			fieldname: "month",
			label: __("Month"),
			fieldtype: "Int",
			default: parseInt(frappe.datetime.get_today().split("-")[1], 10),
			reqd: 1,
		},
		{
			fieldname: "branch",
			label: __("Branch"),
			fieldtype: "Link",
			options: "Branch",
		},
	],
	onload: function (report) {
		phpayroll_report_buttons(report, {
			dat_method: "phpayroll.ph_payroll.report.philhealth_rf_1.philhealth_rf_1.export_to_csv",
			dat_name: function (f) {
				return "PHIC_RF1_" + f.month + f.year + ".CSV";
			},
			form: "PHIC_RF1",
			pdf_label: __("Printable RF-1"),
		});
	},
};
