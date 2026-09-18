frappe.ui.form.on("Employee", {
	refresh: function (frm) {
		frm.add_custom_button(__("BIR 2316"), function () {
			frappe.prompt(
				[
					{
						fieldname: "year",
						fieldtype: "Int",
						label: __("Year"),
						reqd: 1,
						default: frappe.datetime.get_today().split("-")[0],
					},
				],
				function (values) {
					function open() {
						phpayroll.printable.preview_form({
							title: __("BIR Form 2316"),
							method: "phpayroll.ph_payroll.statutory_reports.pdf_forms.export_2316",
							args: {
								filters: {
									employee: frm.doc.name,
									year: values.year,
									company: frm.doc.company,
								},
							},
						});
					}
					if (window.phpayroll && phpayroll.printable) {
						open();
					} else {
						frappe.require("/assets/phpayroll/js/printable_pdf_preview.js", open);
					}
				},
				__("Generate BIR 2316")
			);
		});
		frm.add_custom_button(__("Generate 13th Month"), function () {
			frappe.prompt(
				[
					{
						fieldname: "year",
						fieldtype: "Int",
						label: __("Year"),
						reqd: 1,
						default: frappe.datetime.get_today().split("-")[0],
					},
				],
				function (values) {
					frappe.call({
						method: "phpayroll.ph_payroll.thirteenth_month.generate_thirteenth_month",
						args: {
							year: values.year,
							company: frm.doc.company,
							branch: frm.doc.reporting_branch,
						},
						freeze: true,
						callback: function (r) {
							if (r.message) {
								frappe.msgprint(__("Created {0} 13th-month Additional Salary records", [r.message.count]));
							}
						},
					});
				},
				__("13th Month")
			);
		});
	},
});
