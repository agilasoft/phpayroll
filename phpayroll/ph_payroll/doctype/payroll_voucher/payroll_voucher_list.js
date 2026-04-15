// payroll_voucher_list.js

frappe.listview_settings['Payroll Voucher'] = {
    onload: function(listview) {
        listview.page.add_menu_item(__('Preview Payroll'), function() {
            frappe.prompt([
                {'fieldname': 'date_from', 'fieldtype': 'Date', 'label': __('Date From'), 'reqd': 1},
                {'fieldname': 'date_to', 'fieldtype': 'Date', 'label': __('Date To'), 'reqd': 1},
                {
                    'fieldname': 'branch',
                    'fieldtype': 'Link',
                    'label': __('Branch'),
                    'options': 'Branch',
                    'reqd': 1
                }
            ], function(values) {
                frappe.call({
                    method: 'phpayroll.ph_payroll.doctype.payroll_voucher.payroll_voucher.preview_payroll',
                    args: {
                        date_from: values.date_from,
                        date_to: values.date_to,
                        branch: values.branch
                    },
                    callback: function(r) {
                        if (r.message && r.message.length) {
                            const d = new frappe.ui.Dialog({
                                title: __('Payroll preview (not saved)'),
                                fields: [{
                                    fieldtype: 'HTML',
                                    fieldname: 'tbl',
                                    options: '<div class="small text-muted">' + __('Net pay is shown per employee; vouchers are not created or updated.') + '</div>'
                                }]
                            });
                            let html = '<table class="table table-bordered"><thead><tr><th>Employee</th><th>Net Pay</th><th>Basic</th><th>OT</th><th>Tax</th></tr></thead><tbody>';
                            r.message.forEach(function(row) {
                                html += '<tr><td>' + frappe.utils.escape_html(row.employee_name || row.employee) + '</td><td>' + row.net_pay + '</td><td>' + row.total_basic_pay + '</td><td>' + row.total_overtime_pay + '</td><td>' + row.tax + '</td></tr>';
                            });
                            html += '</tbody></table>';
                            d.fields_dict.tbl.$wrapper.html(html);
                            d.show();
                        } else {
                            frappe.msgprint(__('No preview rows (no active employees for branch?).'));
                        }
                    }
                });
            }, __('Preview — Date Range and Branch'), __('Preview'));
        });

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
                        listview.refresh();
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
