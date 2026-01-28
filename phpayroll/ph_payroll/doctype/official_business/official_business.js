// Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Official Business', {
	refresh: function(frm) {
		// Delay calculation to ensure form is fully loaded
		setTimeout(function() {
			calculate_total_additional_costs(frm);
		}, 100);
	},
	
	additional_costs: function(frm) {
		calculate_total_additional_costs(frm);
	}
});

frappe.ui.form.on('Official Business Additional Cost', {
	amount: function(frm, cdt, cdn) {
		calculate_total_additional_costs(frm);
	},
	
	additional_costs_remove: function(frm) {
		calculate_total_additional_costs(frm);
	}
});

function calculate_total_additional_costs(frm) {
	if (!frm || !frm.doc) {
		return;
	}
	
	let total = 0;
	if (frm.doc.additional_costs) {
		frm.doc.additional_costs.forEach(function(row) {
			if (row.amount) {
				total += flt(row.amount);
			}
		});
	}
	
	// Set the value directly and refresh the field
	frm.doc.total_additional_costs = total;
	frm.refresh_field('total_additional_costs');
}
