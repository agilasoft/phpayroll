frappe.ui.form.on('Payroll Voucher', {
    refresh: function(frm) {
        if (frm.doc.docstatus === 0) {
            frm.page.add_menu_item(__('Recompute Payroll'), function() {
                frappe.confirm(__('Are you sure you want to recompute this payroll voucher?'),
                    function() {
                        frappe.call({
                            method: 'phpayroll.ph_payroll.doctype.payroll_voucher.payroll_voucher.recompute_payroll_voucher',
                            args: {
                                voucher_name: frm.doc.name
                                },
                            callback: function(response) {
                                if (response.message) {
                                    frm.reload_doc();
                                    frappe.msgprint(__('Payroll voucher recomputed successfully.'));
                                }
                            }
                        });
                    }
                );
            });
        }
    }
});
