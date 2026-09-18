# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Seed Salary Components, PH structure, and Salary Slip custom fields when HRMS is installed."""

from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from phpayroll.ph_payroll.constants import (
	COMPONENT_ABBR,
	DEDUCTION_COMPONENTS,
	EARNING_COMPONENTS,
	EMPLOYER_COMPONENTS,
	PH_SALARY_STRUCTURE,
	WITHHOLDING_TAX,
)


def hrms_available():
	return frappe.db.exists("DocType", "Salary Component")


def setup_hrms_overlay():
	if not hrms_available():
		return
	ensure_salary_components()
	ensure_salary_structure()
	ensure_salary_slip_fields()


def ensure_salary_components():
	specs = []
	for name in EARNING_COMPONENTS:
		specs.append((name, "Earning", 0, 0, name != "13th Month"))
	for name in DEDUCTION_COMPONENTS:
		is_tax = name == WITHHOLDING_TAX
		specs.append((name, "Deduction", 0, int(is_tax), 0))
	for name in EMPLOYER_COMPONENTS:
		specs.append((name, "Employer Contribution", 1, 1, 0))

	for name, ctype, statistical, do_not_include, tax_applicable in specs:
		if frappe.db.exists("Salary Component", name):
			continue
		doc = frappe.new_doc("Salary Component")
		doc.salary_component = name
		doc.salary_component_abbr = COMPONENT_ABBR.get(name, name[:5].upper())
		doc.type = ctype
		doc.depends_on_payment_days = 0
		doc.statistical_component = statistical
		doc.do_not_include_in_total = do_not_include if ctype != "Employer Contribution" else 1
		doc.is_tax_applicable = tax_applicable if ctype == "Earning" else 0
		doc.remove_if_zero_valued = 0
		doc.amount = 0
		doc.insert(ignore_permissions=True)


def _preferred_company():
	company = frappe.defaults.get_global_default("company")
	if company and frappe.db.exists("Company", company):
		return company
	ph = frappe.get_all(
		"Company",
		filters={"country": "Philippines"},
		pluck="name",
		order_by="name",
		limit=1,
	)
	if ph:
		return ph[0]
	companies = frappe.get_all("Company", pluck="name", order_by="name", limit=1)
	return companies[0] if companies else None


def ensure_salary_structure(company=None):
	if frappe.db.exists("Salary Structure", PH_SALARY_STRUCTURE):
		return
	company = company or _preferred_company()
	if not company:
		return
	doc = frappe.new_doc("Salary Structure")
	doc.name = PH_SALARY_STRUCTURE
	doc.company = company
	doc.is_active = "Yes"
	doc.payroll_frequency = "Bimonthly"
	doc.currency = frappe.get_cached_value("Company", company, "default_currency") or "PHP"
	for name in EARNING_COMPONENTS:
		doc.append(
			"earnings",
			{
				"salary_component": name,
				"abbr": COMPONENT_ABBR[name],
				"amount": 0,
				"depends_on_payment_days": 0,
			},
		)
	for name in DEDUCTION_COMPONENTS:
		doc.append(
			"deductions",
			{
				"salary_component": name,
				"abbr": COMPONENT_ABBR[name],
				"amount": 0,
				"depends_on_payment_days": 0,
			},
		)
	if hasattr(doc, "employer_contributions") or True:
		try:
			for name in EMPLOYER_COMPONENTS:
				doc.append(
					"employer_contributions",
					{
						"salary_component": name,
						"abbr": COMPONENT_ABBR[name],
						"amount": 0,
					},
				)
		except Exception:
			pass
	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True)
	try:
		doc.submit()
	except Exception:
		frappe.log_error(title="PH Salary Structure submit failed")


def ensure_salary_slip_fields():
	fields = [
		dict(
			fieldname="ph_statutory_section",
			label="PH Statutory",
			fieldtype="Section Break",
			insert_after="rounded_total",
			collapsible=1,
		),
		dict(fieldname="ss_ee", label="SS EE", fieldtype="Currency", insert_after="ph_statutory_section", read_only=1),
		dict(fieldname="ss_er", label="SS ER", fieldtype="Currency", insert_after="ss_ee", read_only=1),
		dict(fieldname="wisp_ee", label="WISP EE", fieldtype="Currency", insert_after="ss_er", read_only=1),
		dict(fieldname="wisp_er", label="WISP ER", fieldtype="Currency", insert_after="wisp_ee", read_only=1),
		dict(fieldname="ec_er", label="EC ER", fieldtype="Currency", insert_after="wisp_er", read_only=1),
		dict(fieldname="ph_statutory_col", fieldtype="Column Break", insert_after="ec_er"),
		dict(fieldname="ph_ee", label="PH EE", fieldtype="Currency", insert_after="ph_statutory_col", read_only=1),
		dict(fieldname="ph_er", label="PH ER", fieldtype="Currency", insert_after="ph_ee", read_only=1),
		dict(fieldname="hd_ee", label="HD EE", fieldtype="Currency", insert_after="ph_er", read_only=1),
		dict(fieldname="hd_er", label="HD ER", fieldtype="Currency", insert_after="hd_ee", read_only=1),
		dict(fieldname="taxable_income", label="Taxable Income", fieldtype="Currency", insert_after="hd_er", read_only=1),
		dict(fieldname="tax", label="Withholding Tax", fieldtype="Currency", insert_after="taxable_income", read_only=1),
		dict(fieldname="total_basic_pay", label="Total Basic Pay", fieldtype="Currency", insert_after="tax", read_only=1),
	]
	create_custom_fields({"Salary Slip": fields}, ignore_validate=True, update=True)
