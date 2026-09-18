# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Tests for printable BIR 1601-C / 1604-C / 2316 value mapping."""

from __future__ import annotations

from unittest import TestCase

from phpayroll.ph_payroll.statutory_reports.pdf_forms import (
	bir_1601c,
	bir_1604c,
	bir_2316,
	hdmf_mcrf,
	phic_rf1,
	sss_r3,
)
from phpayroll.ph_payroll.statutory_reports.pdf_forms.context import format_amount


def _employer(**overrides):
	ctx = {
		"registered_name": "Agilasoft Technologies Inc",
		"registered_address": "123 Ayala Ave, Makati 1226",
		"tin": "001234567",
		"tin_branch": "00000",
		"rdo_code": "039",
		"zip": "1226",
		"contact_number": "0281234567",
		"email": "tax@agilasoft.com",
		"signatory_name": "Jane Doe",
		"signatory_title": "President",
	}
	ctx.update(overrides)
	return ctx


class TestBirPdfFormMapping(TestCase):
	def test_1601c_maps_identity_and_tax_due(self):
		values = bir_1601c.values_from_context(
			_employer(
				year=2026,
				month=9,
				any_taxes_withheld=True,
				item_14=100000,
				item_19=5000,
				item_22=80000,
				item_25=4500,
				item_27=4500,
				item_31=4500,
				item_36=4500,
			)
		)
		self.assertEqual(values["month"], "09")
		self.assertEqual(values["year"], "2026")
		self.assertEqual(values["amended_no"], "1")
		self.assertEqual(values["taxes_yes"], "1")
		self.assertEqual(values["tin_1"], "001")
		self.assertEqual(values["tin_4"], "00000")
		self.assertEqual(values["taxpayer_name"], "AGILASOFT TECHNOLOGIES INC")
		self.assertEqual(values["item_25"], format_amount(4500))
		self.assertEqual(values["item_36"], "4,500.00")
		self.assertEqual(values["tin_p2"], "001-234-567-00000")

	def test_1604c_maps_monthly_schedule(self):
		values = bir_1604c.values_from_context(
			_employer(
				year=2026,
				sheets_attached=1,
				monthly_tax={1: 100.0, 2: 0.0, 3: 250.5, 9: 80},
			)
		)
		self.assertEqual(values["year"], "2026")
		self.assertEqual(values["amended_no"], "1")
		self.assertEqual(values["tax_jan"], "100.00")
		self.assertEqual(values["tax_mar"], "250.50")
		self.assertNotIn("tax_feb", values)
		self.assertEqual(values["tax_sep"], "80.00")
		self.assertEqual(values["tax_total"], format_amount(430.5))
		self.assertEqual(values["remit_total"], format_amount(430.5))

	def test_2316_maps_employee_and_employer(self):
		values = bir_2316.values_from_context(
			_employer(
				year=2026,
				employee_name="Santos, Juan Dela Cruz",
				employee_tin="123456789",
				employee_address="Makati City 1226",
				employee_zip="1226",
				date_of_birth="19900115",
				period_from="0101",
				period_to="1231",
				is_mwe=False,
				item_19=240000,
				item_21=180000,
				item_25a=12000,
				item_28=12000,
				item_39=180000,
				item_52=180000,
				substituted_filing=True,
			)
		)
		self.assertEqual(values["year"], "2026")
		self.assertEqual(values["ee_tin_1"], "123")
		self.assertEqual(values["er_tin_1"], "001")
		self.assertEqual(values["employee_name"], "SANTOS, JUAN DELA CRUZ")
		self.assertEqual(values["employer_name"], "AGILASOFT TECHNOLOGIES INC")
		self.assertEqual(values["main_employer"], "1")
		self.assertEqual(values["substituted_filing"], "1")
		self.assertEqual(values["item_28"], "12,000.00")
		self.assertEqual(values["period_from"], "0101")

	def test_field_layouts_have_unique_names(self):
		for mod in (bir_1601c, bir_1604c, bir_2316, sss_r3, phic_rf1, hdmf_mcrf):
			names = [field["field_name"] for field in mod.get_field_layout()]
			self.assertEqual(len(names), len(set(names)), mod.__name__)
			self.assertTrue(all(field.get("page", 0) >= 0 for field in mod.get_field_layout()))

	def test_sss_r3_maps_month_into_quarter_slot(self):
		row = {
			"sss_no": "01-2345678-9",
			"last_name": "Santos",
			"first_name": "Juan",
			"middle_name": "Dela",
			"ss_ee": 500,
			"ss_er": 1000,
			"wisp_ee": 0,
			"wisp_er": 0,
			"ec_er": 10,
		}
		values = sss_r3.values_from_context(
			_employer(year=2026, month=9, sss_employer_no="2001234567", employees=[row]),
			copies=1,
		)
		self.assertEqual(values["p0_quarter_mm"], "09")
		self.assertEqual(values["p0_quarter_yyyy"], "2026")
		self.assertEqual(values["r01_ss_no"], "0123456789")
		self.assertEqual(values["r01_ss3"], "1,500.00")
		self.assertEqual(values["r01_ec3"], "10.00")
		self.assertNotIn("r01_ss1", values)

	def test_phic_rf1_and_hdmf_mcrf_map_employees(self):
		row = {
			"phic_no": "12-345678901-2",
			"hdmf_no": "121234567890",
			"last_name": "Santos",
			"first_name": "Juan",
			"middle_name": "Dela",
			"ph_ee": 500,
			"ph_er": 500,
			"hd_ee": 100,
			"hd_er": 100,
			"basic": 20000,
		}
		phic = phic_rf1.values_from_context(
			_employer(year=2026, month=9, philhealth_pen="000123456789", employees=[row]),
			copies=1,
		)
		self.assertEqual(phic["p0_period"], "09/2026")
		self.assertEqual(phic["r01_pin"], "123456789012")
		self.assertEqual(phic["r01_ps"], "500.00")
		hdmf = hdmf_mcrf.values_from_context(
			_employer(year=2026, month=9, pagibig_employer_id="123456789012", employees=[row]),
			copies=1,
		)
		self.assertEqual(hdmf["r01_mid"], "121234567890")
		self.assertEqual(hdmf["r01_program"], "PAG-IBIG I")
		self.assertEqual(hdmf["r01_total"], "200.00")
		self.assertEqual(hdmf["p0_employer_id"], "123456789012")

	def test_hdmf_mcrf_employer_id_sits_in_value_box(self):
		layout = {field["field_name"]: field for field in hdmf_mcrf.get_field_layout()}
		field = layout["p0_employer_id"]
		self.assertGreaterEqual(field["y"], 58.32)
		self.assertLessEqual(field["y"] + field["height"], 87.02)

	def test_hdmf_mcrf_fields_stay_inside_printed_grid(self):
		layout = {field["field_name"]: field for field in hdmf_mcrf.get_field_layout()}
		self.assertGreaterEqual(layout["r01_mid"]["y"], 250.8)
		self.assertLess(layout["r01_mid"]["y"], 264.1)
		self.assertLessEqual(layout["r01_mid"]["x"] + layout["r01_mid"]["width"], 67.3)
		self.assertLessEqual(layout["r01_program"]["x"] + layout["r01_program"]["width"], 166.3)
		self.assertLessEqual(layout["r01_middle"]["x"] + layout["r01_middle"]["width"], 360.6)
		self.assertLessEqual(layout["r01_period"]["x"] + layout["r01_period"]["width"], 401.7)
		self.assertLessEqual(layout["r01_comp"]["x"] + layout["r01_comp"]["width"], 463.4)
		self.assertLessEqual(layout["r01_ee"]["x"] + layout["r01_ee"]["width"], 493.1)
		self.assertLessEqual(layout["r01_er"]["x"] + layout["r01_er"]["width"], 520.5)
		self.assertLessEqual(layout["r01_total"]["x"] + layout["r01_total"]["width"], 552.6)
		self.assertGreaterEqual(layout["p0_page_ee"]["x"], 471.5)
		self.assertLessEqual(layout["p0_page_ee"]["x"] + layout["p0_page_ee"]["width"], 493.1)
		self.assertGreaterEqual(layout["p0_address"]["x"], 180.0)
		self.assertEqual(hdmf_mcrf.ROWS_PER_PAGE, 28)
		self.assertEqual(len(hdmf_mcrf.ROW_Y), 28)
