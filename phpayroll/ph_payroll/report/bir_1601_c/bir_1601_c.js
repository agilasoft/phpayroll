frappe.query_reports["BIR 1601-C"] = {
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
			dat_method: "phpayroll.ph_payroll.report.bir_1601_c.bir_1601_c.export_to_dat",
			dat_name: function (f) {
				return "1601C_" + f.month + f.year + ".DAT";
			},
			form: "1601C",
			pdf_label: __("Printable 1601-C"),
		});
	},
};
