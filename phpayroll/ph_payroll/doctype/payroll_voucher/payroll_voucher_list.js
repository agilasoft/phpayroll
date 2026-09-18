frappe.listview_settings["Payroll Voucher"] = {
	onload: function (listview) {
		frappe.call({
			method: "phpayroll.ph_payroll.engine.get_engine_for_company",
			callback: function (r) {
				const uses_hrms = r.message && r.message.uses_hrms;
				if (!uses_hrms) {
					listview.page.add_menu_item(__("Run Payroll"), function () {
						frappe.prompt(
							[
								{ fieldname: "date_from", fieldtype: "Date", label: __("Date From"), reqd: 1 },
								{ fieldname: "date_to", fieldtype: "Date", label: __("Date To"), reqd: 1 },
								{
									fieldname: "branch",
									fieldtype: "Link",
									label: __("Branch"),
									options: "Branch",
									reqd: 1,
								},
							],
							function (values) {
								frappe.call({
									method: "phpayroll.ph_payroll.doctype.payroll_voucher.payroll_voucher.run_payroll",
									args: values,
									callback: function (response) {
										if (response.message) {
											frappe.msgprint(response.message);
										}
									},
								});
							},
							__("Enter Date Range and Branch"),
							__("Run")
						);
					});
				}
				listview.page.add_menu_item(__("Create Salary Slips"), function () {
					if (!uses_hrms) {
						frappe.msgprint(
							__(
								"Payroll computation is still on PH Payroll Voucher. Switch PH Payroll Settings to Frappe HR Salary Slip to create Salary Slips."
							)
						);
						return;
					}
					frappe.prompt(
						[
							{ fieldname: "date_from", fieldtype: "Date", label: __("Date From"), reqd: 1 },
							{ fieldname: "date_to", fieldtype: "Date", label: __("Date To"), reqd: 1 },
							{
								fieldname: "branch",
								fieldtype: "Link",
								label: __("Branch"),
								options: "Branch",
								reqd: 1,
							},
						],
						function (values) {
							frappe.call({
								method: "phpayroll.ph_payroll.payroll_run.prepare_salary_slips",
								args: values,
								callback: function (res) {
									if (res.message) {
										frappe.msgprint(__("Created / updated {0} salary slips", [res.message.count]));
									}
								},
							});
						},
						__("Salary Slips by Branch"),
						__("Create")
					);
				});
			},
		});
	},
};
