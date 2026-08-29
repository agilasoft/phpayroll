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


def _compute_daily_basic_and_holiday_pay(
	hours_worked,
	basic_hours,
	hourly_rate,
	holiday_mult,
	is_declared_holiday,
):
	"""Mirror payroll_voucher.compute_daily_basic_and_holiday_pay without frappe."""
	hours_worked = _flt(hours_worked)
	basic_hours = _flt(basic_hours)
	hourly_rate = _flt(hourly_rate)
	holiday_mult = _flt(holiday_mult)

	if hours_worked > 0:
		payable_hours = min(hours_worked, basic_hours) if basic_hours else hours_worked
		basic_pay = payable_hours * hourly_rate
		holiday_pay = payable_hours * hourly_rate * holiday_mult if holiday_mult else 0.0
		return hours_worked, basic_pay, holiday_pay

	if is_declared_holiday and basic_hours > 0 and hourly_rate > 0:
		day_pay = basic_hours * hourly_rate
		return basic_hours, 0.0, day_pay

	return hours_worked, 0.0, 0.0


class TestHolidayRateLookup(unittest.TestCase):
	def test_scalar_rate_converts_to_float(self):
		"""Regression: frappe.db.get_value with ['rate'] returns a tuple that flt() cannot parse."""
		self.assertEqual(_flt(1.5), 1.5)
		self.assertEqual(_flt((1.5,)), 0.0)


class TestUnworkedHolidayPay(unittest.TestCase):
	def test_unworked_declared_holiday_pays_one_full_day(self):
		display_hours, basic_pay, holiday_pay = _compute_daily_basic_and_holiday_pay(
			0, 8, 100, 1.0, True
		)
		self.assertEqual(display_hours, 8)
		self.assertEqual(basic_pay, 0.0)
		self.assertEqual(holiday_pay, 800.0)

	def test_worked_holiday_includes_premium(self):
		display_hours, basic_pay, holiday_pay = _compute_daily_basic_and_holiday_pay(
			8, 8, 100, 1.0, True
		)
		self.assertEqual(display_hours, 8)
		self.assertEqual(basic_pay, 800.0)
		self.assertEqual(holiday_pay, 800.0)

	def test_non_holiday_without_hours_pays_nothing(self):
		display_hours, basic_pay, holiday_pay = _compute_daily_basic_and_holiday_pay(
			0, 8, 100, 0, False
		)
		self.assertEqual(display_hours, 0)
		self.assertEqual(basic_pay, 0.0)
		self.assertEqual(holiday_pay, 0.0)


if __name__ == "__main__":
	unittest.main()
