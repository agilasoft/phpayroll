# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import unittest

from phpayroll.ph_payroll.timekeeping.policy import apply_worked_hours_policy, normalize_ot_multiplier


class TestTimekeepingPolicy(unittest.TestCase):
	def test_normalize_ot_multiplier(self):
		self.assertAlmostEqual(normalize_ot_multiplier(125, 1.25), 1.25)
		self.assertAlmostEqual(normalize_ot_multiplier(1.5, 1.25), 1.5)
		self.assertAlmostEqual(normalize_ot_multiplier(None, 1.25), 1.25)

	def test_apply_worked_hours_policy(self):
		cfg = {
			"time_rounding_minutes": 15,
			"time_minimum_paid_hours": 0,
			"unpaid_break_minutes_per_day": 60,
			"unpaid_break_apply_after_hours": 5,
		}
		# 8.02 rounds to 8h, then 60 min unpaid break applies (8 >= 5)
		self.assertEqual(apply_worked_hours_policy(8.02, cfg), 7.0)
		cfg2 = dict(cfg)
		cfg2["time_minimum_paid_hours"] = 4
		self.assertEqual(apply_worked_hours_policy(0.5, cfg2), 4.0)


if __name__ == "__main__":
	unittest.main()
