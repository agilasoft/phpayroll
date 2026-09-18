# -*- coding: utf-8 -*-
# Copyright (c) 2025, Agilasoft Technologies Inc. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest
from types import SimpleNamespace

from phpayroll.ph_payroll.tax.withholding import (
	compute_annualized_withholding_tax_amount,
	compute_gross_taxable_from_voucher,
	compute_tax_from_bracket,
	find_bracket_row,
)


def _br(from_amt, to_amt, fixed, rate):
	return type("R", (), {"from": from_amt, "to": to_amt, "fixed": fixed, "rate": rate})()


class TestAnnualTaxTable(unittest.TestCase):
	def test_compute_tax_from_bracket(self):
		row = _br(0, 250000, 0, 0)
		self.assertEqual(compute_tax_from_bracket(row, 100000), 0)
		row2 = _br(250000, 400000, 0, 15)
		self.assertEqual(compute_tax_from_bracket(row2, 300000), (300000 - 250000) * 0.15)

	def test_find_bracket_row(self):
		items = [
			_br(0, 100, 0, 0),
			_br(101, 200, 10, 10),
		]
		table = SimpleNamespace(items=items)
		self.assertIs(find_bracket_row(table, -1), None)
		self.assertEqual(find_bracket_row(table, 50).to, 100)
		r150 = find_bracket_row(table, 150)
		self.assertEqual(getattr(r150, "from"), 101)
		r500 = find_bracket_row(table, 500)
		self.assertEqual(getattr(r500, "from"), 101)

	def test_compute_gross_taxable_from_voucher(self):
		item = SimpleNamespace(net_sales=100)
		v = SimpleNamespace(
			items=[item],
			total_basic_pay=1000,
			total_overtime_pay=100,
			total_holiday_pay=50,
			total_incentive=25,
		)
		self.assertEqual(
			compute_gross_taxable_from_voucher(v, ["basic_pay", "net_sales"]),
			1100,
		)

	def test_compute_annualized_withholding_tax_amount(self):
		# Single bracket 0-1e9: 0 + 20% over 0 => annual tax = 0.2 * projected
		items = [_br(0, 1_000_000_000, 0, 20)]
		table = SimpleNamespace(items=items)
		# 3 months, YTD incl current = 300k => projected annual = 1.2M => annual tax = 240k
		# tax due YTD = 240k * (3/12) = 60k; prior withheld 50k => 10k this period
		wh, proj = compute_annualized_withholding_tax_amount(200_000, 50_000, 100_000, 3, table)
		self.assertAlmostEqual(proj, 1_200_000.0)
		self.assertAlmostEqual(wh, 10_000.0)
		# Over-withheld prior => 0 this period
		wh2, _ = compute_annualized_withholding_tax_amount(200_000, 70_000, 100_000, 3, table)
		self.assertAlmostEqual(wh2, 0.0)
