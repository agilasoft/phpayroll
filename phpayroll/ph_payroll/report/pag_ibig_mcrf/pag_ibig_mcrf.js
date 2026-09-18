frappe.query_reports["Pag-IBIG MCRF"] = {
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
			dat_method: "phpayroll.ph_payroll.report.pag_ibig_mcrf.pag_ibig_mcrf.export_to_csv",
			dat_name: function (f) {
				return (f.company || "MCRF") + "_" + f.year + String(f.month).padStart(2, "0") + ".CSV";
			},
			form: "HDMF_MCRF",
			pdf_label: __("Printable MCRF"),
		});
	},
};
