# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe


def execute():
    if not frappe.db.has_column("Payroll Voucher", "run_type"):
        return
    frappe.db.sql(
        """
        UPDATE `tabPayroll Voucher`
        SET run_type = 'Regular'
        WHERE IFNULL(run_type, '') = ''
        """
    )
