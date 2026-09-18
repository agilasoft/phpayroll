frappe.listview_settings["Payroll Voucher"] = {
	onload: function (listview) {
		frappe.call({
			method: "phpayroll.ph_payroll.engine.get_engine_for_company",
			callback: function (r) {
				const uses_hrms = r.message && r.message.uses_hrms;

				if (!uses_hrms) {
					listview.page.add_menu_item(__("Preview Payroll"), function () {
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
									method: "phpayroll.ph_payroll.doctype.payroll_voucher.payroll_voucher.preview_payroll",
									args: values,
									callback: function (res) {
										if (res.message && res.message.length) {
											const d = new frappe.ui.Dialog({
												title: __("Payroll preview (not saved)"),
												fields: [
													{
														fieldtype: "HTML",
														fieldname: "tbl",
														options:
															'<div class="small text-muted">' +
															__("Net pay is shown per employee; vouchers are not created or updated.") +
															"</div>",
													},
												],
											});
											let html =
												'<table class="table table-bordered"><thead><tr><th>Employee</th><th>Net Pay</th><th>Basic</th><th>OT</th><th>Tax</th></tr></thead><tbody>';
											res.message.forEach(function (row) {
												html +=
													"<tr><td>" +
													frappe.utils.escape_html(row.employee_name || row.employee) +
													"</td><td>" +
													row.net_pay +
													"</td><td>" +
													row.total_basic_pay +
													"</td><td>" +
													row.total_overtime_pay +
													"</td><td>" +
													row.tax +
													"</td></tr>";
											});
											html += "</tbody></table>";
											d.fields_dict.tbl.$wrapper.html(html);
											d.show();
										} else {
											frappe.msgprint(__("No preview rows (no active employees for branch?)."));
										}
									},
								});
							},
							__("Preview — Date Range and Branch"),
							__("Preview")
						);
					});

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
										listview.refresh();
									},
								});
							},
							__("Enter Date Range and Branch"),
							__("Run")
						);
					});

					listview.page.add_menu_item(__("Run 13th Month"), function () {
						frappe.prompt(
							[
								{
									fieldname: "date_from",
									fieldtype: "Date",
									label: __("Accrual / Period From"),
									reqd: 1,
								},
								{
									fieldname: "date_to",
									fieldtype: "Date",
									label: __("Accrual / Period To"),
									reqd: 1,
								},
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
									method: "phpayroll.ph_payroll.doctype.payroll_voucher.payroll_voucher.run_13th_month",
									args: values,
									callback: function (response) {
										if (response.message) {
											frappe.msgprint(response.message);
										}
										listview.refresh();
									},
								});
							},
							__("13th Month — Date Range and Branch"),
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
