frappe.ui.form.on("Salary Slip", {
	refresh: function (frm) {
		if (frm.doc.docstatus !== 0) return;
		frappe.call({
			method: "phpayroll.ph_payroll.engine.get_engine_for_company",
			args: { company: frm.doc.company },
			callback: function (r) {
				if (!(r.message && r.message.uses_hrms)) {
					frm.set_intro(
						__(
							"This company still computes payroll on PH Payroll Voucher. PH statutory overlay is not applied to this slip."
						)
					);
					return;
				}
				frm.add_custom_button(__("Recompute PH Payroll"), function () {
					frm.save();
				});
			},
		});
	},
});
