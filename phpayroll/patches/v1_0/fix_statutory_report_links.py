# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe

REPORTS = (
	"BIR 1601-C",
	"BIR 1604-C",
	"SSS R-3",
	"PhilHealth RF-1",
	"Pag-IBIG MCRF",
)


def execute():
	_fix_report_ref_doctypes()
	_fix_workspace_shortcuts()
	_fix_sidebar()


def _fix_report_ref_doctypes():
	if not frappe.db.table_exists("Report"):
		return
	for name in REPORTS:
		if not frappe.db.exists("Report", name):
			continue
		if frappe.db.get_value("Report", name, "ref_doctype"):
			continue
		frappe.db.set_value("Report", name, "ref_doctype", "Employee", update_modified=False)


def _fix_workspace_shortcuts():
	if not frappe.db.table_exists("Workspace Shortcut"):
		return
	frappe.db.sql(
		"""
		UPDATE `tabWorkspace Shortcut`
		SET report_ref_doctype = 'Employee'
		WHERE parenttype = 'Workspace'
			AND type = 'Report'
			AND link_to IN %(reports)s
			AND IFNULL(report_ref_doctype, '') = ''
		""",
		{"reports": REPORTS},
	)


def _fix_sidebar():
	if not frappe.db.table_exists("Workspace Sidebar Item"):
		return
	frappe.db.sql(
		"""
		UPDATE `tabWorkspace Sidebar Item`
		SET link_type = 'DocType'
		WHERE parenttype = 'Workspace Sidebar'
			AND type = 'Section Break'
			AND label = 'Statutory Reports'
			AND link_type = 'Report'
			AND IFNULL(link_to, '') = ''
		"""
	)
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
