// payroll_voucher_list.js

frappe.listview_settings['Payroll Voucher'] = {
    onload: function(listview) {
        listview.page.add_menu_item(__('Run Payroll'), function() {
            frappe.prompt([
                {'fieldname': 'date_from', 'fieldtype': 'Date', 'label': 'Date From', 'reqd': 1},
                {'fieldname': 'date_to', 'fieldtype': 'Date', 'label': 'Date To', 'reqd': 1},
                {
                    'fieldname': 'branch', 
                    'fieldtype': 'Link', 
                    'label': 'Branch', 
                    'options': 'Branch', 
                    'reqd': 1
                }
            ], function(values){
                frappe.call({
                    method: 'phpayroll.ph_payroll.doctype.payroll_voucher.payroll_voucher.run_payroll',
                    args: {
                        date_from: values.date_from,
                        date_to: values.date_to,
                        branch: values.branch
                    },
                    callback: function(response) {
                        if(response.message) {
                            frappe.msgprint(response.message);
                        }
                    }
                });
            }, __('Enter Date Range and Branch'), __('Run'));
        });

        listview.page.add_menu_item(__('Run 13th Month'), function() {
            frappe.prompt([
                {'fieldname': 'date_from', 'fieldtype': 'Date', 'label': __('Accrual / Period From'), 'reqd': 1},
                {'fieldname': 'date_to', 'fieldtype': 'Date', 'label': __('Accrual / Period To'), 'reqd': 1},
                {
                    'fieldname': 'branch',
                    'fieldtype': 'Link',
                    'label': __('Branch'),
                    'options': 'Branch',
                    'reqd': 1
                }
            ], function(values) {
                frappe.call({
                    method: 'phpayroll.ph_payroll.doctype.payroll_voucher.payroll_voucher.run_13th_month',
                    args: {
                        date_from: values.date_from,
                        date_to: values.date_to,
                        branch: values.branch
                    },
                    callback: function(response) {
                        if (response.message) {
                            frappe.msgprint(response.message);
                        }
                        listview.refresh();
                    }
                });
            }, __('13th Month — Date Range and Branch'), __('Run'));
        });
    }
};
