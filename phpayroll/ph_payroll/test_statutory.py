# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import unittest

import frappe

from phpayroll.ph_payroll.statutory import annual_tax_from_brackets
from phpayroll.ph_payroll.statutory_reports.files.bir_dat import encode_row, strip_tin


class TestStatutory(unittest.TestCase):
	def test_annual_tax_zero_bracket(self):
		items = [frappe._dict({"from": 0, "to": 250000, "fixed": 0, "rate": 0})]
		self.assertEqual(annual_tax_from_brackets(200000, items), 0)

	def test_annual_tax_second_bracket(self):
		items = [
			frappe._dict({"from": 0, "to": 250000, "fixed": 0, "rate": 0}),
			frappe._dict({"from": 250000, "to": 400000, "fixed": 0, "rate": 15}),
		]
		# 300000 -> 15% of 50000 = 7500
		self.assertEqual(annual_tax_from_brackets(300000, items), 7500)

	def test_strip_tin(self):
		self.assertEqual(strip_tin("123-456-789-000"), "123456789000")

	def test_encode_row(self):
		self.assertEqual(encode_row("H", ["a", 1.2]), "H,a,1.20")
