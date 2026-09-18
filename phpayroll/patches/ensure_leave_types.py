# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe

DEFAULT_LEAVE_TYPES = (
	("Sick", "Sick leave"),
	("Vacation", "Vacation leave"),
	("Magna Carta", "Magna Carta leave"),
)


def execute():
	if not frappe.db.table_exists("tabLeave Type"):
		return

	for type_name, description in DEFAULT_LEAVE_TYPES:
		if frappe.db.exists("Leave Type", type_name):
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Leave Type",
				"type_name": type_name,
				"description": description or "",
			}
		)
		doc.insert(ignore_permissions=True)

	if not frappe.db.exists("Leave Type", "Vacation"):
		return

	if frappe.db.table_exists("tabLeave Credit Line"):
		frappe.db.sql(
			"""
			UPDATE `tabLeave Credit Line`
			SET leave_type = %s
			WHERE (leave_type IS NULL OR leave_type = '')
				AND parenttype = 'Leave Credits'
			""",
			("Vacation",),
		)
