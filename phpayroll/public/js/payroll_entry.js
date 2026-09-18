frappe.ui.form.on("Payroll Entry", {
	refresh: function (frm) {
		frappe.call({
			method: "phpayroll.ph_payroll.engine.get_engine_for_company",
			args: { company: frm.doc.company },
			callback: function (r) {
				if (!(r.message && r.message.uses_hrms)) {
					frm.set_intro(
						__(
							"This company still computes payroll on PH Payroll Voucher. Switch PH Payroll Settings to Frappe HR Salary Slip to run pay here."
						)
					);
					return;
				}
				frm.add_custom_button(__("Prepare PH Assignments"), function () {
					frappe.call({
						method: "phpayroll.ph_payroll.payroll_run.prepare_payroll_entry",
						args: { payroll_entry: frm.doc.name },
						freeze: true,
						callback: function (res) {
							if (res.message) {
								frappe.show_alert({ message: __("Assignments ready"), indicator: "green" });
							}
						},
					});
				});
				frm.add_custom_button(__("Create PH Salary Slips"), function () {
					frappe.prompt(
						[
							{
								fieldname: "branch",
								fieldtype: "Link",
								options: "Branch",
								label: __("Reporting Branch"),
								reqd: 1,
							},
						],
						function (values) {
							frappe.call({
								method: "phpayroll.ph_payroll.payroll_run.prepare_salary_slips",
								args: {
									date_from: frm.doc.start_date,
									date_to: frm.doc.end_date,
									branch: values.branch,
									company: frm.doc.company,
								},
								freeze: true,
								callback: function (res) {
									if (res.message) {
										frappe.msgprint(__("Created / updated {0} salary slips", [res.message.count]));
									}
								},
							});
						},
						__("PH Payroll by Branch")
					);
				});
			},
		});
	},
});
