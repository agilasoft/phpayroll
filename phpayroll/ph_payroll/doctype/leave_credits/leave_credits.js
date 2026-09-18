// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Leave Credits', {
	refresh(frm) {
		frm.set_df_property('balance', 'read_only', 1);
	},
});
