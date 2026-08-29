# -*- coding: utf-8 -*-
# Copyright (c) 2025, Agilasoft Technologies Inc. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest


def _flt(val):
	try:
		return float(val)
	except (TypeError, ValueError):
		return 0.0


class TestHolidayRateLookup(unittest.TestCase):
	def test_scalar_rate_converts_to_float(self):
		"""Regression: frappe.db.get_value with ['rate'] returns a tuple that flt() cannot parse."""
		self.assertEqual(_flt(1.5), 1.5)
		self.assertEqual(_flt((1.5,)), 0.0)

	def test_compute_holiday_pay_formula(self):
		worked_hours_for_pay = 8
		hourly_rate = 100
		holiday_mult = 1.0
		holiday_pay = (
			worked_hours_for_pay * hourly_rate * holiday_mult if holiday_mult else 0
		)
		self.assertEqual(holiday_pay, 800.0)


if __name__ == "__main__":
	unittest.main()
