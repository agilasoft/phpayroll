# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe


def execute():
	if not frappe.db.table_exists("Workspace Sidebar Item"):
		return
	frappe.db.sql(
		"""
		UPDATE `tabWorkspace Sidebar Item`
		SET indent = 0
		WHERE parenttype = 'Workspace Sidebar'
			AND type = 'Section Break'
			AND label IN ('Statutory Reports', 'Time Management')
			AND indent = 1
			AND (parent = 'Payroll' OR parent LIKE 'Payroll-%%')
		"""
	)
