frappe.query_reports["BIR 1604-C"] = {
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
			fieldname: "branch",
			label: __("Branch"),
			fieldtype: "Link",
			options: "Branch",
		},
	],
	onload: function (report) {
		phpayroll_report_buttons(report, {
			dat_method: "phpayroll.ph_payroll.report.bir_1604_c.bir_1604_c.export_to_dat",
			dat_name: function (f) {
				return "H1604C_" + f.year + ".DAT";
			},
			form: "1604C",
			pdf_label: __("Printable 1604-C"),
		});
	},
};
