# -*- coding: utf-8 -*-
"""Placeholder for biometric / device attendance import (CSV/API). Extend as needed."""

from __future__ import unicode_literals

import frappe
from frappe import _


@frappe.whitelist()
def log_biometric_import_stub(message=None):
	"""Reserved hook for third-party punch import; logs intent only."""
	frappe.logger("phpayroll").info(_("Biometric import stub: {0}").format(message or ""))
	return {"ok": True, "message": _("No import performed — implement device mapping here.")}
