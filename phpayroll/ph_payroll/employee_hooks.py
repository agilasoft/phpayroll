# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe


def sync_reporting_branch(doc, method=None):
	"""Keep Employee.branch aligned with reporting_branch so Payroll Entry filters work."""
	if doc.get("reporting_branch") and not doc.get("branch"):
		doc.branch = doc.reporting_branch
