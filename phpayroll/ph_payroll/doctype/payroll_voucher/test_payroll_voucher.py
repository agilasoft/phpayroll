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


class TestPayrollVoucher(unittest.TestCase):
	def test_holiday_rate_lookup_uses_scalar_fieldname(self):
		"""Regression: frappe.db.get_value with ['rate'] returns a tuple that flt() cannot parse."""
		scalar_rate = 1.5
		tuple_rate = (1.5,)

		self.assertEqual(_flt(scalar_rate), 1.5)
		self.assertEqual(_flt(tuple_rate), 0.0)

		holiday_mult = _flt(scalar_rate) if scalar_rate else 0.0
		broken_mult = _flt(tuple_rate) if tuple_rate else 0.0

		self.assertEqual(holiday_mult, 1.5)
		self.assertEqual(broken_mult, 0.0)


if __name__ == "__main__":
	unittest.main()
