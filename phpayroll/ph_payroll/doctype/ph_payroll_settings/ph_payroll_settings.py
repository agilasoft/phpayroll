# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from phpayroll.ph_payroll.constants import ENGINE_HRMS, ENGINE_LEGACY


class PHPayrollSettings(Document):
	def validate(self):
		if self.tin:
			self.tin = "".join(ch for ch in str(self.tin) if ch.isdigit())
		if self.tin_branch_code:
			self.tin_branch_code = str(self.tin_branch_code).zfill(3)
		if not self.computation_engine:
			self.computation_engine = ENGINE_HRMS if self.freeze_payroll_voucher else ENGINE_LEGACY
		# New Payroll Vouchers are blocked only after cutover to HRMS.
		self.freeze_payroll_voucher = 1 if self.computation_engine == ENGINE_HRMS else 0

	@staticmethod
	def get_settings(company=None):
		if not company:
			company = frappe.defaults.get_user_default("Company")
		if not company or not frappe.db.exists("DocType", "PH Payroll Settings"):
			return None
		name = frappe.db.get_value("PH Payroll Settings", {"company": company}, "name")
		if not name:
			return None
		return frappe.get_cached_doc("PH Payroll Settings", name)


def get_employer_profile(company):
	"""TIN/name/address from phtax BIR CAS Settings when present, else PH Payroll Settings."""
	profile = frappe._dict(
		company=company,
		tin="",
		tin_branch_code="000",
		registered_name="",
		registered_address="",
		rdo_code="",
		zip_code="",
		contact_number="",
		email="",
		sss_employer_no="",
		philhealth_pen="",
		pagibig_employer_id="",
		signatory_name="",
		signatory_title="",
	)
	if frappe.db.exists("DocType", "BIR CAS Settings"):
		try:
			from phtax.cas.doctype.bir_cas_settings.bir_cas_settings import BIRCASSettings

			cas = BIRCASSettings.get_settings(company)
			if cas:
				profile.tin = cas.tin or ""
				profile.tin_branch_code = cas.tin_branch_code or "000"
				profile.registered_name = cas.registered_name or ""
				profile.registered_address = cas.registered_address or ""
				profile.rdo_code = cas.rdo_code or ""
		except Exception:
			pass
	settings = PHPayrollSettings.get_settings(company)
	if settings:
		profile.sss_employer_no = settings.sss_employer_no or ""
		profile.philhealth_pen = settings.philhealth_pen or ""
		profile.pagibig_employer_id = settings.pagibig_employer_id or ""
		profile.signatory_name = settings.signatory_name or ""
		profile.signatory_title = settings.signatory_title or ""
		profile.zip_code = settings.zip_code or ""
		if not profile.tin:
			profile.tin = settings.tin or ""
			profile.tin_branch_code = settings.tin_branch_code or "000"
			profile.registered_name = settings.registered_name or profile.registered_name
			profile.registered_address = settings.registered_address or profile.registered_address
			profile.rdo_code = settings.rdo_code or profile.rdo_code
	if company:
		try:
			company_row = frappe.db.get_value(
				"Company", company, ["phone_no", "email", "company_name"], as_dict=True
			) or {}
		except Exception:
			company_row = {"company_name": frappe.db.get_value("Company", company, "company_name")}
		profile.contact_number = profile.contact_number or "".join(
			ch for ch in str(company_row.get("phone_no") or "") if ch.isdigit()
		)
		profile.email = profile.email or (company_row.get("email") or "")
		if not profile.registered_name:
			profile.registered_name = company_row.get("company_name") or company
	return profile
