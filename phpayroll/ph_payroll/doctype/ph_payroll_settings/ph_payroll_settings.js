frappe.ui.form.on("PH Payroll Settings", {
	refresh: function (frm) {
		frm.set_intro(
			__(
				"Default is PH Payroll Voucher so existing pay runs stay valid. Switch to Frappe HR Salary Slip when ready to compute in HRMS. Historical vouchers are never deleted."
			)
		);
	},
	computation_engine: function (frm) {
		if (frm.doc.computation_engine === "Frappe HR Salary Slip") {
			frm.set_value("freeze_payroll_voucher", 1);
			if (!frm.doc.count_on_duty_as_official_business) {
				frm.set_value("count_on_duty_as_official_business", 1);
			}
			frappe.show_alert({
				message: __(
					"New Payroll Vouchers will be blocked. Use Payroll Entry and Salary Slip. On Duty Attendance Requests can be paid like Official Business."
				),
				indicator: "blue",
			});
		} else {
			frm.set_value("freeze_payroll_voucher", 0);
		}
	},
});
