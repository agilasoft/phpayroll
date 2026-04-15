# -*- coding: utf-8 -*-
"""Time policy from Payroll Settings: rounding, minimum paid hours, break deduction."""

from __future__ import unicode_literals

from frappe.utils import cint, flt


def apply_worked_hours_policy(gross_hours, cfg):
	"""Return adjusted hours after rounding, minimum-if-clocked-in, and unpaid break."""
	h = flt(gross_hours)
	if h <= 0:
		return 0.0

	rm = cint(cfg.get("time_rounding_minutes") or 0)
	if rm > 0:
		step = rm / 60.0
		h = round(h / step) * step
		h = round(h, 4)

	mn = flt(cfg.get("time_minimum_paid_hours") or 0)
	if mn > 0 and h > 0 and h < mn:
		h = mn

	br = cint(cfg.get("unpaid_break_minutes_per_day") or 0)
	th = flt(cfg.get("unpaid_break_apply_after_hours") or 0)
	if br > 0 and h > 0:
		if th <= 0 or h >= th:
			h -= br / 60.0
	if h < 0:
		h = 0.0
	return round(h, 4)


def normalize_ot_multiplier(rate_value, default_mult):
	"""Overtime Type rate: values > 2 treated as percent (125 -> 1.25)."""
	r = flt(rate_value)
	if r <= 0:
		return flt(default_mult) if default_mult else 1.25
	if r > 2.0:
		return r / 100.0
	return r


def count_night_hours(dt_in, dt_out, start_h, start_m, end_h, end_m):
	"""Return hours where local time falls in [start, end) possibly crossing midnight."""
	if not dt_in or not dt_out or dt_in >= dt_out:
		return 0.0
	from datetime import timedelta

	start_m = cint(start_h) * 60 + cint(start_m)
	end_m = cint(end_h) * 60 + cint(end_m)
	crosses = start_m > end_m
	night_minutes = 0
	cur = dt_in
	step = timedelta(minutes=1)
	while cur < dt_out:
		m = cur.hour * 60 + cur.minute
		if crosses:
			in_win = m >= start_m or m < end_m
		else:
			in_win = start_m <= m < end_m
		if in_win:
			night_minutes += 1
		cur += step
	return round(night_minutes / 60.0, 4)
