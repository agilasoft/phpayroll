# -*- coding: utf-8 -*-
# Copyright (c) 2024, www.belizzo.ph and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, add_days, get_datetime, time_diff_in_hours

RUN_TYPE_REGULAR = "Regular"
RUN_TYPE_13TH = "13th Month"
RUN_TYPE_SPECIAL = "Special"

THIRTEENTH_MONTH_ITEM_FIELDS = frozenset({
    "basic_pay", "overtime_pay", "holiday_pay", "night_diff_pay", "incentive", "net_sales", "cash_advance",
})


class PayrollVoucher(Document):
	def validate(self):
		if frappe.flags.get("in_migrate") or frappe.flags.get("ignore_payroll_period_lock"):
			return
		from phpayroll.ph_payroll.doctype.payroll_period.payroll_period import (
			can_bypass_payroll_period_lock,
			is_payroll_period_locked,
		)

		if not self.date_from or not self.date_to or not self.branch:
			return
		if can_bypass_payroll_period_lock():
			return
		if is_payroll_period_locked(self.branch, self.date_from, self.date_to):
			frappe.throw(
				_("This payroll period is closed. Adjust Payroll Period or ask a System Manager."),
				title=_("Payroll Locked"),
			)

@frappe.whitelist()
def run_payroll(date_from, date_to, branch, dry_run=False):
	dry_run = cint(dry_run)
	if dry_run:
		return preview_payroll(date_from, date_to, branch)

	frappe.msgprint(
		_("Running payroll from {0} to {1} for branch {2}").format(date_from, date_to, branch),
		title=_("Payroll Run Start"),
	)
	payroll_vouchers = []

	employees = frappe.get_all("Employee", filters={"status": "Active", "reporting_branch": branch})
	for employee in employees:
		voucher = get_or_create_payroll_voucher(employee.name, date_from, date_to, branch, RUN_TYPE_REGULAR)

		if voucher:
			populate_items(voucher)
			voucher.save(ignore_permissions=True)
			payroll_vouchers.append(voucher.name)

	frappe.msgprint(
		_("Payroll run completed. Vouchers: {0}").format(", ".join(payroll_vouchers) or _("none")),
		title=_("Payroll Run Complete"),
	)
	return _("Payroll run completed. Vouchers: {0}").format(", ".join(payroll_vouchers) or _("none"))


@frappe.whitelist()
def preview_payroll(date_from, date_to, branch):
	"""Compute payroll in memory per active employee; does not insert or update vouchers."""
	frappe.flags.ignore_payroll_period_lock = True
	try:
		out = []
		employees = frappe.get_all("Employee", filters={"status": "Active", "reporting_branch": branch})
		for row in employees:
			emp_doc = frappe.get_cached_doc("Employee", row.name)
			v = frappe.new_doc("Payroll Voucher")
			v.employee = row.name
			v.employee_name = emp_doc.employee_name
			v.date_from = date_from
			v.date_to = date_to
			v.branch = branch
			v.run_type = RUN_TYPE_REGULAR
			v.basic_hours = getattr(emp_doc, "basic_hours", None)
			v.hourly_rate = getattr(emp_doc, "hourly_rate", None)
			v.allow_incentive = getattr(emp_doc, "allow_incentive", None)
			populate_items(v)
			out.append(
				{
					"employee": v.employee,
					"employee_name": v.employee_name,
					"net_pay": flt(v.net_pay),
					"total_basic_pay": flt(v.total_basic_pay),
					"total_overtime_pay": flt(v.total_overtime_pay),
					"total_holiday_pay": flt(v.total_holiday_pay),
					"total_night_diff_pay": flt(getattr(v, "total_night_diff_pay", 0)),
					"tax": flt(v.tax),
				}
			)
		return out
	finally:
		frappe.flags.ignore_payroll_period_lock = False
   
@frappe.whitelist()
def recompute_payroll_voucher(voucher_name):
    voucher = frappe.get_doc("Payroll Voucher", voucher_name)
    if voucher.run_type == RUN_TYPE_13TH:
        populate_13th_month_voucher(voucher)
    else:
        populate_items(voucher)
    voucher.save(ignore_permissions=True)
    frappe.msgprint(
        _("Payroll voucher recomputed successfully. Voucher updated: {0}").format(voucher.name),
        title=_("Payroll Recompute Complete"),
    )
    return _("Payroll voucher recomputed successfully. Voucher updated: {0}").format(voucher.name)


@frappe.whitelist()
def run_13th_month(date_from, date_to, branch):
    from phpayroll.ph_payroll.doctype.payroll_settings.payroll_settings import get_defaults_for_13th_month

    enabled, _include_special, _codes = get_defaults_for_13th_month()
    if not enabled:
        frappe.throw(_("Enable 13th month in Payroll Settings."))

    frappe.msgprint(
        _("Running 13th month for {0} to {1}, branch {2}").format(date_from, date_to, branch),
        title=_("13th Month Run Start"),
    )
    payroll_vouchers = []
    employees = frappe.get_all("Employee", filters={"status": "Active", "reporting_branch": branch})
    for employee in employees:
        voucher = get_or_create_payroll_voucher(employee.name, date_from, date_to, branch, RUN_TYPE_13TH)
        if voucher:
            populate_13th_month_voucher(voucher)
            voucher.save(ignore_permissions=True)
            payroll_vouchers.append(voucher.name)

    frappe.msgprint(
        _("13th month run completed. Vouchers: {0}").format(", ".join(payroll_vouchers) or _("none")),
        title=_("13th Month Run Complete"),
    )
    return _("13th month run completed. Vouchers: {0}").format(", ".join(payroll_vouchers) or _("none"))


def get_or_create_payroll_voucher(employee, date_from, date_to, branch, run_type=RUN_TYPE_REGULAR):
    existing_vouchers = frappe.get_all(
        "Payroll Voucher",
        filters={
            "employee": employee,
            "branch": branch,
            "date_from": date_from,
            "date_to": date_to,
            "run_type": run_type,
        },
    )

    if existing_vouchers:
        existing_voucher = frappe.get_doc("Payroll Voucher", existing_vouchers[0].name)
        frappe.msgprint(
            _("Found existing voucher (same dates and run type) for Employee: {0}").format(employee),
            title=_("Voucher Exact Match"),
        )
        return existing_voucher

    overlapping_vouchers = frappe.get_all(
        "Payroll Voucher",
        filters={
            "employee": employee,
            "branch": branch,
            "run_type": run_type,
            "date_from": ["<=", date_to],
            "date_to": [">=", date_from],
        },
    )

    if overlapping_vouchers:
        frappe.msgprint(
            _("Overlapping {0} voucher for Employee: {1} in branch: {2}.").format(run_type, employee, branch),
            title=_("Voucher Overlap"),
        )
        return None

    voucher = frappe.new_doc("Payroll Voucher")
    voucher.employee = employee
    voucher.date_from = date_from
    voucher.date_to = date_to
    voucher.branch = branch
    voucher.run_type = run_type
    voucher.save(ignore_permissions=True)
    frappe.msgprint(
        _("Created new Payroll Voucher: {0} for Employee: {1}").format(voucher.name, employee),
        title=_("Payroll Voucher Creation"),
    )
    return voucher


def get_13th_month_annual_base(employee, branch, date_from, date_to, include_special, fieldnames):
    fieldnames = [f for f in (fieldnames or []) if f in THIRTEENTH_MONTH_ITEM_FIELDS]
    if not fieldnames:
        fieldnames = ["basic_pay"]
    sum_parts = ", ".join(
        "COALESCE(SUM(pi.`{0}`), 0) AS `sum_{0}`".format(f) for f in fieldnames
    )
    if include_special:
        type_clause = "pv.run_type IN ('Regular', 'Special')"
    else:
        type_clause = "pv.run_type = 'Regular'"
    sql = """
        SELECT {sums}
        FROM `tabPayroll Item` pi
        INNER JOIN `tabPayroll Voucher` pv ON pi.parent = pv.name AND pi.parenttype = 'Payroll Voucher'
        WHERE pv.employee = %(employee)s
            AND IFNULL(pv.branch, '') = IFNULL(%(branch)s, '')
            AND IFNULL(pv.docstatus, 0) < 2
            AND {type_clause}
            AND pi.date BETWEEN %(d0)s AND %(d1)s
    """.format(sums=sum_parts, type_clause=type_clause)
    rows = frappe.db.sql(
        sql,
        {
            "employee": employee,
            "branch": branch or "",
            "d0": getdate(date_from),
            "d1": getdate(date_to),
        },
        as_dict=True,
    )
    if not rows:
        return 0.0
    row = rows[0]
    return sum(flt(row.get("sum_{0}".format(f), 0)) for f in fieldnames)


def populate_13th_month_voucher(voucher):
    from phpayroll.ph_payroll.doctype.payroll_settings.payroll_settings import get_defaults_for_13th_month

    if (getattr(voucher, "run_type", None) or RUN_TYPE_REGULAR) != RUN_TYPE_13TH:
        return
    enabled, include_special, fieldnames = get_defaults_for_13th_month()
    if not enabled:
        frappe.throw(_("Enable 13th month in Payroll Settings."))

    annual = get_13th_month_annual_base(
        voucher.employee,
        voucher.branch,
        voucher.date_from,
        voucher.date_to,
        include_special,
        fieldnames,
    )
    thirteenth = flt(annual) / 12.0

    voucher.set("items", [])
    voucher.set("deductions", [])
    for _field in (
        "total_basic_pay", "total_overtime_pay", "total_holiday_pay", "total_night_diff_pay", "total_incentive",
        "taxable_income", "tax", "sss", "philhealth", "hdmf", "less_cash_advance",
        "ss_er", "ss_ee", "ss_total", "wisp_er", "wisp_ee", "ec_er",
        "ph_ee", "ph_er", "hd_ee", "hd_er", "total_contribution",
    ):
        voucher.set(_field, 0)
    voucher.thirteenth_month_pay = thirteenth
    voucher.net_pay = thirteenth

def populate_items(voucher):
    run_type = getattr(voucher, "run_type", None) or RUN_TYPE_REGULAR
    if run_type == RUN_TYPE_13TH:
        frappe.throw(
            _("Run Type is 13th Month. Use Recompute Payroll to refresh 13th month amounts.")
        )

    date_from = voucher.date_from
    date_to = voucher.date_to
    employee = voucher.employee
    branch = voucher.branch

    if not date_from or not date_to or not employee:
        frappe.throw(_("Please ensure Employee, Date From, and Date To are filled."))

    voucher.set('items', [])
    voucher.set('deductions', [])  # Clear existing deductions
    
    total_basic_pay = 0
    total_overtime_pay = 0
    total_incentive = 0
    total_holiday_pay = 0
    total_night_diff_pay = 0
    less_cash_advance = 0

    date_array = get_dates_between(date_from, date_to)
    
    for date in date_array:
        fetch_time_and_sales(employee, date, branch, voucher)

    
    for item in voucher.items:
        total_basic_pay += flt(item.basic_pay)
        total_holiday_pay += flt(item.holiday_pay)
        total_overtime_pay += flt(item.overtime_pay)
        total_night_diff_pay += flt(getattr(item, "night_diff_pay", 0))
        total_incentive += flt(item.incentive)
        less_cash_advance += flt(item.cash_advance)
    
    #Add Manual Entries
    manual_entries = frappe.get_all('Manual Payroll Entry', filters={
        'employee': employee,
        'date': ['between', [date_from, date_to]]
    }, fields=['date', 'type', 'description', 'amount'])
    
    
    manual_basic_pay = 0
    manual_overtime_pay = 0
    manual_holiday_pay = 0
    manual_cash_advance = 0
    manual_incentive = 0
    
    for entry in manual_entries:
        for item in voucher.items:
            if item.date == entry.date:
                if entry.type == 'Basic Pay':
                    item.basic_pay += entry.amount
                    manual_basic_pay += entry.amount
                elif entry.type == 'Overtime':
                    item.overtime_pay += entry.amount
                    manual_overtime_pay += entry.amount
                elif entry.type == 'Holiday Pay':
                    item.holiday_pay += entry.amount
                    manual_holiday_pay += entry.amount
                elif entry.type == 'Deduction':
                    item.cash_advance += entry.amount
                    manual_cash_advance += entry.amount
                elif entry.type == 'Others':
                    item.incentive += entry.amount
                    manual_incentive += entry.amount

    voucher.total_basic_pay = total_basic_pay + manual_basic_pay
    voucher.total_holiday_pay = total_holiday_pay + manual_holiday_pay
    voucher.total_overtime_pay = total_overtime_pay + manual_overtime_pay
    voucher.total_night_diff_pay = total_night_diff_pay
    voucher.total_incentive = total_incentive + manual_incentive
    voucher.less_cash_advance = less_cash_advance + manual_cash_advance
    
    # Set basic calculations
    net_pay = (
        total_basic_pay
        + total_holiday_pay
        + total_overtime_pay
        + total_night_diff_pay
        + total_incentive
        - less_cash_advance
        + manual_basic_pay
        + manual_holiday_pay
        + manual_overtime_pay
        + manual_incentive
        - manual_cash_advance
    )
    voucher.net_pay = net_pay  # Set the initial net pay before deductions

    # Clear prior contribution amounts so unchecked Employee flags do not leave stale values
    for _field in (
        'ss_er', 'ss_ee', 'wisp_er', 'wisp_ee', 'ec_er',
        'ph_ee', 'ph_er', 'hd_ee', 'hd_er',
    ):
        voucher.set(_field, 0)

    # Calculate contributions based on whether end of month is included in the cutoff
    if is_end_of_month_cutoff(date_to):
        calculate_end_of_month_contributions(voucher, employee, total_basic_pay)
    else:
        calculate_partial_contributions(voucher, employee, total_basic_pay)

    # Calculate total deductions
    total_sss_deduction = flt(voucher.ss_ee) + flt(voucher.wisp_ee)  # SSS total
    total_philhealth_deduction = flt(voucher.ph_ee)                   # PhilHealth
    total_hdmf_deduction = flt(voucher.hd_ee)                         # HDMF

    # Set individual deductions in voucher
    voucher.sss = total_sss_deduction
    voucher.philhealth = total_philhealth_deduction
    voucher.hdmf = total_hdmf_deduction

    # Deduct SSS, PhilHealth, and HDMF from net pay
    total_deductions = total_sss_deduction + total_philhealth_deduction + total_hdmf_deduction
    voucher.net_pay = net_pay - total_deductions  # Final net pay after statutory contributions

    from phpayroll.ph_payroll.doctype.payroll_settings.payroll_settings import get_withholding_config
    from phpayroll.ph_payroll.tax.withholding import (
        METHOD_ANNUAL_TABLE,
        METHOD_ANNUALIZED_YTD,
        compute_withholding_tax,
    )

    _wh = get_withholding_config()
    if _wh["enabled"] and _wh["method"] in (METHOD_ANNUAL_TABLE, METHOD_ANNUALIZED_YTD):
        compute_withholding_tax(voucher)
        voucher.net_pay = flt(voucher.net_pay) - flt(voucher.tax)
    elif not _wh["enabled"]:
        voucher.taxable_income = 0
        voucher.tax = 0

def get_dates_between(start_date, end_date):
    dates = []
    current_date = getdate(start_date)
    end_date = getdate(end_date)
    while current_date <= end_date:
        dates.append(current_date)
        current_date = add_days(current_date, 1)
    return dates


def get_cash_count_net_sales(branch, date):
    """Sum net_sales for branch/date. Silent 0 if Cash Count DocType/table is missing."""
    if not frappe.db.exists("DocType", "Cash Count"):
        return 0
    try:
        rows = frappe.db.sql(
            """
            SELECT COALESCE(SUM(`net_sales`), 0) AS total_amount
            FROM `tabCash Count`
            WHERE `branch` = %s AND `date` = %s
            """,
            (branch, date),
            as_dict=True,
        )
        return flt(rows[0].total_amount) if rows else 0
    except Exception:
        return 0


def fetch_time_and_sales(employee, date, branch, voucher):
    # First check if there's an Official Business record for this date
    official_business = fetch_official_business(employee, date)
    
    if official_business:
        # Use Official Business for attendance calculation
        fetch_official_business_and_populate_items(employee, date, branch, official_business, voucher)
        return

    leave_doc = fetch_leave(employee, date)
    if leave_doc:
        fetch_leave_and_populate_items(employee, date, branch, leave_doc, voucher)
        return

    from phpayroll.ph_payroll.timekeeping.resolver import resolve_worked_hours_for_day

    resolved = resolve_worked_hours_for_day(employee, date, branch, fetch_manual_attendance_time)
    br = resolved.get("time_in_branch") or branch
    fetch_cash_count_and_populate_items(
        employee,
        date,
        br,
        resolved["hours_worked"],
        resolved.get("time_in"),
        resolved.get("time_out"),
        voucher,
    )


def calculate_hours_worked(timestamp_in, timestamp_out):
    if not timestamp_in or not timestamp_out:
        return 0

    date_time_in = get_datetime(timestamp_in)
    date_time_out = get_datetime(timestamp_out)
    difference_in_hours = time_diff_in_hours(date_time_out, date_time_in)
    return round(difference_in_hours, 2)


def _time_tuple(val):
    if val is None:
        return 0, 0
    if hasattr(val, "hour"):
        return int(val.hour), int(val.minute)
    parts = str(val).split(":")
    try:
        return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
    except (ValueError, IndexError):
        return 0, 0


def compute_overtime_pay_for_day(employee, date, hourly_rate, eligible_hours_cap, default_mult):
    from phpayroll.ph_payroll.timekeeping.policy import normalize_ot_multiplier

    rows = frappe.db.sql(
        """
        SELECT ot.hours AS hours,
            COALESCE(NULLIF(ot.overtime_rate, 0), typ.rate, NULL) AS rate_src
        FROM `tabOvertime` ot
        LEFT JOIN `tabOvertime Type` typ ON typ.name = ot.overtime_type
        WHERE ot.employee = %(emp)s AND ot.date = %(d)s AND ot.docstatus = 1
        """,
        {"emp": employee, "d": date},
        as_dict=True,
    )
    if not rows:
        return 0.0, 0.0
    total_h = sum(flt(r.get("hours")) for r in rows)
    if total_h <= 0:
        return 0.0, 0.0
    cap = min(total_h, max(0.0, flt(eligible_hours_cap)))
    scale = cap / total_h if total_h else 0.0
    pay = 0.0
    for r in rows:
        h = flt(r.get("hours")) * scale
        m = normalize_ot_multiplier(r.get("rate_src"), default_mult)
        pay += h * flt(hourly_rate) * m
    return round(cap, 4), round(pay, 4)


def fetch_cash_count_and_populate_items(employee, date, branch, hours_worked, time_in, time_out, voucher):
    try:
        from phpayroll.ph_payroll.doctype.payroll_settings.payroll_settings import get_timekeeping_settings

        cfg = get_timekeeping_settings()
        net_sales = get_cash_count_net_sales(branch, date)

        basic_hours = voucher.basic_hours or 0
        hourly_rate = voucher.hourly_rate or 0
        worked_hours_for_pay = min(flt(hours_worked), basic_hours)
        basic_pay = worked_hours_for_pay * hourly_rate

        h_rate = get_holiday_rate(date)
        holiday_mult = flt(h_rate) if h_rate else 0.0
        if not holiday_mult and cint(cfg.get("apply_rest_day_sunday")):
            if getdate(date).weekday() == 6:
                holiday_mult = flt(cfg.get("rest_day_rate"))

        holiday_pay = worked_hours_for_pay * hourly_rate * holiday_mult if holiday_mult else 0

        ot_cap = max(0.0, flt(hours_worked) - basic_hours)
        default_m = flt(cfg.get("default_ot_multiplier")) or 1.25
        ot_hours, overtime_pay = compute_overtime_pay_for_day(
            employee, date, hourly_rate, ot_cap, default_m
        )

        night_diff_pay = 0.0
        if time_in and time_out and cint(cfg.get("enable_night_differential")):
            from phpayroll.ph_payroll.timekeeping.policy import count_night_hours

            sh, sm = _time_tuple(cfg.get("night_window_start"))
            eh, em = _time_tuple(cfg.get("night_window_end"))
            nh = count_night_hours(
                get_datetime(time_in), get_datetime(time_out), sh, sm, eh, em
            )
            night_diff_pay = nh * flt(hourly_rate) * flt(cfg.get("night_differential_multiplier"))

        cash_advance = fetch_cash_advance(employee, date, voucher)
        incentive = fetch_incentive(branch, net_sales)

        item = {
            "date": date,
            "time_in": time_in,
            "time_out": time_out,
            "hours_worked": hours_worked,
            "net_sales": net_sales,
            "basic_pay": basic_pay,
            "holiday_pay": holiday_pay,
            "ot_hours": ot_hours,
            "overtime_pay": overtime_pay,
            "night_diff_pay": night_diff_pay,
            "cash_advance": cash_advance,
            "incentive": incentive,
        }
        voucher.append("items", item)

    except Exception as err:
        frappe.msgprint(_("Error in payroll calculation: {0}").format(err), title=_("Error"))



def fetch_official_business(employee, date):
    """
    Fetch Official Business record for employee on a specific date
    Returns the Official Business document if found, None otherwise
    """
    try:
        ob_records = frappe.get_all('Official Business', 
            filters={
                'employee': employee, 
                'date': date,
                'docstatus': 1
            }, 
            fields=['name', 'number_of_days', 'total_additional_costs'],
            limit=1
        )
        
        if ob_records:
            return frappe.get_doc('Official Business', ob_records[0]['name'])
        return None
    except Exception as err:
        frappe.msgprint(f"Error fetching Official Business: {err}", title="Error")
        return None

def fetch_official_business_and_populate_items(employee, date, branch, official_business, voucher):
    """
    Populate payroll items based on Official Business record
    Uses number_of_days to calculate basic pay instead of hours worked
    """
    try:
        from phpayroll.ph_payroll.doctype.payroll_settings.payroll_settings import get_timekeeping_settings

        cfg = get_timekeeping_settings()
        net_sales = get_cash_count_net_sales(branch, date)

        # Basic pay computation based on Official Business number_of_days
        basic_hours = voucher.basic_hours or 0
        hourly_rate = voucher.hourly_rate or 0
        number_of_days = flt(official_business.number_of_days) or 0
        
        # Convert days to hours (assuming 1 day = basic_hours)
        # For 0.5 days, it would be basic_hours * 0.5, for 1.0 days, basic_hours * 1.0
        worked_hours_for_pay = basic_hours * number_of_days
        basic_pay = worked_hours_for_pay * hourly_rate

        h_rate = get_holiday_rate(date)
        holiday_mult = flt(h_rate) if h_rate else 0.0
        if not holiday_mult and cint(cfg.get("apply_rest_day_sunday")):
            if getdate(date).weekday() == 6:
                holiday_mult = flt(cfg.get("rest_day_rate"))
        holiday_pay = worked_hours_for_pay * hourly_rate * holiday_mult if holiday_mult else 0

        # No overtime for Official Business days
        ot_hours = 0
        overtime_pay = 0

        # Fetch cash advance (if any)
        cash_advance = fetch_cash_advance(employee, date, voucher)
        
        # Subtract Official Business additional costs from cash advance (negative cash advance)
        # This means additional costs reduce the cash advance amount
        ob_additional_costs = flt(official_business.total_additional_costs) or 0
        cash_advance -= ob_additional_costs
        
        # Add Official Business additional costs to deductions table as negative cash advance
        if official_business.additional_costs:
            for cost_item in official_business.additional_costs:
                if cost_item.amount and cost_item.amount > 0:
                    # Check if this deduction already exists to avoid duplicates
                    existing_deduction = None
                    for existing in voucher.deductions:
                        if (existing.reference_no == official_business.name and 
                            existing.date == date and
                            existing.type == 'Official Business' and
                            existing.remarks and cost_item.description in existing.remarks):
                            existing_deduction = existing
                            break
                    
                    if not existing_deduction:
                        deduction = voucher.append('deductions', {})
                        deduction.reference_no = official_business.name
                        deduction.date = date
                        deduction.type = 'Official Business'
                        # Negative amount to represent negative cash advance (reduces cash advance)
                        deduction.amount = -flt(cost_item.amount)
                        deduction.remarks = f"OB: {cost_item.description or 'Additional Cost'} (Negative Cash Advance)" + (f" - {cost_item.remarks}" if cost_item.remarks else "")

        incentive = fetch_incentive(branch, net_sales)

        # Populate item
        item = {
            'date': date,
            'time_in': None,  # No time in/out for Official Business
            'time_out': None,
            'hours_worked': worked_hours_for_pay,
            'net_sales': net_sales,
            'basic_pay': basic_pay,
            'holiday_pay': holiday_pay,
            'ot_hours': ot_hours,
            'overtime_pay': overtime_pay,
            'night_diff_pay': 0,
            'cash_advance': cash_advance,
            'incentive': incentive
        }
        voucher.append('items', item)

    except Exception as err:
        frappe.msgprint(f"Error in Official Business payroll calculation: {err}", title="Error")


def fetch_leave(employee, date):
    """Return submitted Leave for employee on date, if any."""
    try:
        leave_rows = frappe.get_all(
            "Leave",
            filters={"employee": employee, "date": date, "docstatus": 1},
            fields=["name", "number_of_days"],
            limit=1,
        )
        if leave_rows:
            return frappe.get_doc("Leave", leave_rows[0]["name"])
        return None
    except Exception as err:
        frappe.msgprint(f"Error fetching Leave: {err}", title="Error")
        return None


def fetch_leave_and_populate_items(employee, date, branch, leave_doc, voucher):
    """
    Populate payroll items from Leave (paid or unpaid). Unpaid: zero salary, row kept for audit.
    """
    try:
        from phpayroll.ph_payroll.doctype.leave.leave import leave_type_is_paid
        from phpayroll.ph_payroll.doctype.payroll_settings.payroll_settings import get_timekeeping_settings

        cfg = get_timekeeping_settings()
        net_sales = get_cash_count_net_sales(branch, date)

        basic_hours = voucher.basic_hours or 0
        hourly_rate = voucher.hourly_rate or 0
        number_of_days = flt(getattr(leave_doc, "number_of_days", None)) or 1

        paid = leave_type_is_paid(leave_doc.type)
        if paid:
            worked_hours_for_pay = basic_hours * number_of_days
            basic_pay = worked_hours_for_pay * hourly_rate
            h_rate = get_holiday_rate(date)
            holiday_mult = flt(h_rate) if h_rate else 0.0
            if not holiday_mult and cint(cfg.get("apply_rest_day_sunday")):
                if getdate(date).weekday() == 6:
                    holiday_mult = flt(cfg.get("rest_day_rate"))
            holiday_pay = worked_hours_for_pay * hourly_rate * holiday_mult if holiday_mult else 0
        else:
            worked_hours_for_pay = 0
            basic_pay = 0
            holiday_pay = 0

        ot_hours = 0
        overtime_pay = 0

        cash_advance = fetch_cash_advance(employee, date, voucher)
        incentive = fetch_incentive(branch, net_sales)

        item = {
            "date": date,
            "time_in": None,
            "time_out": None,
            "hours_worked": worked_hours_for_pay,
            "net_sales": net_sales,
            "basic_pay": basic_pay,
            "holiday_pay": holiday_pay,
            "ot_hours": ot_hours,
            "overtime_pay": overtime_pay,
            "night_diff_pay": 0,
            "cash_advance": cash_advance,
            "incentive": incentive,
        }
        voucher.append("items", item)

    except Exception as err:
        frappe.msgprint(f"Error in Leave payroll calculation: {err}", title="Error")


def fetch_overtime_hours(employee, date):
    try:
        rows = frappe.db.sql(
            """
            SELECT COALESCE(SUM(`hours`), 0) AS total_hours
            FROM `tabOvertime`
            WHERE `employee` = %s AND `date` = %s AND `docstatus` = 1
            """,
            (employee, date),
            as_dict=True,
        )
        return flt(rows[0].total_hours) if rows else 0
    except Exception as err:
        frappe.msgprint(f"Error fetching overtime hours: {err}", title="Error")
        return 0

def fetch_cash_advance(employee, date, voucher=None):
    try:
        # Use get_all (not get_list): payroll must see liquidations even when the current user
        # cannot read Cash Advance via role permissions (e.g. HR running another employee's payroll).
        parent_docs = frappe.get_all(
            "Cash Advance",
            filters={"employee": employee},
            fields=["name"],
        )

        total_cash_advance = 0
        deductions_added = 0

        for doc in parent_docs:
            liquidations = frappe.get_all(
                "Cash Advance Liquidation",
                filters={"parent": doc.name, "date": date},
                fields=["amount"],
            )

            for liquidation in liquidations:
                total_cash_advance += flt(liquidation.amount)

                # If voucher is provided, add to deductions table
                if voucher and flt(liquidation.amount) > 0:
                    ca_info = frappe.db.get_value(
                        "Cash Advance",
                        doc.name,
                        ["type", "purpose"],
                        as_dict=True,
                    )
                    if not ca_info:
                        continue

                    # Check if this deduction already exists to avoid duplicates
                    existing_deduction = None
                    for existing in voucher.deductions:
                        if (existing.reference_no == doc.name and
                                existing.date == date):
                            existing_deduction = existing
                            break

                    if not existing_deduction:
                        deduction = voucher.append('deductions', {})
                        deduction.reference_no = doc.name
                        deduction.date = date
                        deduction.type = ca_info.get("type")
                        deduction.amount = flt(liquidation.amount)
                        deduction.remarks = (
                            f"{ca_info.get('purpose') or ''} - Liquidation Amount: {flt(liquidation.amount)}"
                        )
                        deductions_added += 1
                        frappe.msgprint(f"Added deduction: {doc.name} on {date} for {liquidation.amount}", title="Debug")
        
        if voucher and deductions_added > 0:
            frappe.msgprint(f"Total deductions added for {employee} on {date}: {deductions_added}", title="Debug")
        
        return total_cash_advance
    except Exception as err:
        frappe.msgprint(f"Error fetching cash advance: {err}", title="Error")
        return 0

def fetch_cash_advance_details(employee, date):
    """
    Fetch detailed cash advance information for saving to deductions table
    """
    try:
        cash_advances = frappe.db.get_list('Cash Advance', 
            filters={'employee': employee, 'docstatus': 1}, 
            fields=['name', 'date', 'type', 'purpose', 'amount']
        )
        
        cash_advance_details = []
        for ca in cash_advances:
            # Get liquidations for this cash advance on the specific date
            liquidations = frappe.db.get_list('Cash Advance Liquidation', 
                filters={'parent': ca.name, 'date': date}, 
                fields=['date', 'amount']
            )
            
            for liquidation in liquidations:
                if flt(liquidation.amount) > 0:
                    cash_advance_details.append({
                        'reference_no': ca.name,
                        'date': liquidation.date,
                        'type': ca.type,
                        'remarks': f"{ca.purpose} - Liquidation Amount: {liquidation.amount}"
                    })
        
        return cash_advance_details
    except Exception as err:
        frappe.msgprint(f"Error fetching cash advance details: {err}", title="Error")
        return []

def populate_cash_advance_deductions(voucher, employee, date):
    """
    Populate the deductions table with cash advance details for the given date
    """
    try:
        cash_advance_details = fetch_cash_advance_details(employee, date)
        
        for detail in cash_advance_details:
            # Check if this deduction already exists to avoid duplicates
            existing_deduction = None
            for existing in voucher.deductions:
                if (existing.reference_no == detail['reference_no'] and 
                    existing.date == detail['date']):
                    existing_deduction = existing
                    break
            
            if not existing_deduction:
                deduction = voucher.append('deductions', {})
                deduction.reference_no = detail['reference_no']
                deduction.date = detail['date']
                deduction.type = detail['type']
                deduction.remarks = detail['remarks']
                
    except Exception as err:
        frappe.msgprint(f"Error populating cash advance deductions: {err}", title="Error")

def populate_all_cash_advance_deductions(voucher, employee, date_from, date_to):
    """
    Populate the deductions table with all cash advance details for the entire payroll period
    """
    try:
        frappe.msgprint(f"Starting to populate cash advance deductions for employee: {employee}, period: {date_from} to {date_to}", title="Debug")
        
        # Get all cash advances for the employee that have liquidations within the payroll period
        cash_advances = frappe.db.get_list('Cash Advance', 
            filters={'employee': employee, 'docstatus': 1}, 
            fields=['name', 'date', 'type', 'purpose', 'amount']
        )
        
        frappe.msgprint(f"Found {len(cash_advances)} cash advances for employee {employee}", title="Debug")
        
        deductions_added = 0
        for ca in cash_advances:
            # First, let's see ALL liquidations for this cash advance (without date filter)
            all_liquidations = frappe.db.get_list('Cash Advance Liquidation', 
                filters={'parent': ca.name}, 
                fields=['date', 'amount']
            )
            
            frappe.msgprint(f"Cash Advance {ca.name}: Total liquidations (all dates): {len(all_liquidations)}", title="Debug")
            
            # Show the actual dates of liquidations
            for liq in all_liquidations:
                frappe.msgprint(f"  Liquidation date: {liq.date}, amount: {liq.amount}", title="Debug")
            
            # Now get liquidations within the payroll period
            liquidations = frappe.db.get_list('Cash Advance Liquidation', 
                filters={
                    'parent': ca.name, 
                    'date': ['between', [date_from, date_to]]
                }, 
                fields=['date', 'amount']
            )
            
            frappe.msgprint(f"Cash Advance {ca.name}: Found {len(liquidations)} liquidations in period {date_from} to {date_to}", title="Debug")
            
            # Alternative approach: get all liquidations and filter manually
            if len(liquidations) == 0:
                frappe.msgprint(f"Trying alternative approach for {ca.name}...", title="Debug")
                all_liquidations_filtered = []
                for liq in all_liquidations:
                    if liq.date and date_from <= liq.date <= date_to:
                        all_liquidations_filtered.append(liq)
                        frappe.msgprint(f"  Added liquidation: {liq.date} (amount: {liq.amount})", title="Debug")
                
                if len(all_liquidations_filtered) > 0:
                    frappe.msgprint(f"Alternative approach found {len(all_liquidations_filtered)} liquidations", title="Debug")
                    liquidations = all_liquidations_filtered
            
            for liquidation in liquidations:
                if flt(liquidation.amount) > 0:
                    # Check if this deduction already exists to avoid duplicates
                    existing_deduction = None
                    for existing in voucher.deductions:
                        if (existing.reference_no == ca.name and 
                            existing.date == liquidation.date):
                            existing_deduction = existing
                            break
                    
                    if not existing_deduction:
                        deduction = voucher.append('deductions', {})
                        deduction.reference_no = ca.name
                        deduction.date = liquidation.date
                        deduction.type = ca.type
                        deduction.remarks = f"{ca.purpose} - Liquidation Amount: {liquidation.amount}"
                        deductions_added += 1
                        frappe.msgprint(f"Added deduction: {ca.name} on {liquidation.date} for {liquidation.amount}", title="Debug")
        
        frappe.msgprint(f"Total deductions added: {deductions_added}", title="Debug")
                        
    except Exception as err:
        frappe.msgprint(f"Error populating all cash advance deductions: {err}", title="Error")

@frappe.whitelist()
def test_fetch_cash_advance_with_deductions(employee, date):
    """
    Test the modified fetch_cash_advance function with deductions
    """
    try:
        # Create a test voucher
        voucher = frappe.new_doc('Payroll Voucher')
        voucher.employee = employee
        voucher.date_from = date
        voucher.date_to = date
        
        frappe.msgprint(f"Testing fetch_cash_advance for employee: {employee}, date: {date}", title="Test")
        
        # Call the modified function
        cash_advance_amount = fetch_cash_advance(employee, date, voucher)
        
        frappe.msgprint(f"Cash advance amount: {cash_advance_amount}", title="Test")
        frappe.msgprint(f"Deductions added: {len(voucher.deductions)}", title="Test")
        
        for deduction in voucher.deductions:
            frappe.msgprint(f"  - Reference: {deduction.reference_no}, Date: {deduction.date}, Type: {deduction.type}, Amount: {deduction.amount}", title="Test")
        
        return {
            'success': True,
            'cash_advance_amount': cash_advance_amount,
            'deductions_count': len(voucher.deductions),
            'deductions': [{'reference_no': d.reference_no, 'date': d.date, 'type': d.type, 'amount': d.amount} for d in voucher.deductions]
        }
        
    except Exception as err:
        frappe.msgprint(f"Error in test: {err}", title="Test Error")
        return {'success': False, 'error': str(err)}

@frappe.whitelist()
def test_specific_cash_advance():
    """
    Test the specific cash advance mentioned in the debug output
    """
    try:
        cash_advance_name = "CA000242"
        employee = "HR-EMP-00072"
        date_from = "2025-09-16"
        date_to = "2025-09-30"
        
        frappe.msgprint(f"Testing Cash Advance: {cash_advance_name}", title="Test")
        frappe.msgprint(f"Employee: {employee}, Period: {date_from} to {date_to}", title="Test")
        
        # Get all liquidations for this cash advance
        liquidations = frappe.db.get_list('Cash Advance Liquidation', 
            filters={'parent': cash_advance_name}, 
            fields=['name', 'date', 'amount', 'parent']
        )
        
        frappe.msgprint(f"Total liquidations for {cash_advance_name}: {len(liquidations)}", title="Test")
        
        for liq in liquidations:
            frappe.msgprint(f"  - Date: {liq.date}, Amount: {liq.amount}", title="Test")
        
        # Test date filtering
        filtered_liquidations = frappe.db.get_list('Cash Advance Liquidation', 
            filters={
                'parent': cash_advance_name, 
                'date': ['between', [date_from, date_to]]
            }, 
            fields=['date', 'amount']
        )
        
        frappe.msgprint(f"Liquidations in period {date_from} to {date_to}: {len(filtered_liquidations)}", title="Test")
        
        # Manual date filtering
        manual_filtered = []
        for liq in liquidations:
            if liq.date and date_from <= liq.date <= date_to:
                manual_filtered.append(liq)
                frappe.msgprint(f"  Manual filter match: {liq.date}", title="Test")
        
        frappe.msgprint(f"Manual filtering found: {len(manual_filtered)} liquidations", title="Test")
        
        return {
            'cash_advance': cash_advance_name,
            'total_liquidations': len(liquidations),
            'filtered_liquidations': len(filtered_liquidations),
            'manual_filtered': len(manual_filtered),
            'liquidations': liquidations
        }
        
    except Exception as err:
        frappe.msgprint(f"Error in test: {err}", title="Test Error")
        return {'error': str(err)}

@frappe.whitelist()
def debug_cash_advance_liquidations(cash_advance_name):
    """
    Debug function to check liquidations for a specific cash advance
    """
    try:
        # Get all liquidations for this cash advance
        liquidations = frappe.db.get_list('Cash Advance Liquidation', 
            filters={'parent': cash_advance_name}, 
            fields=['name', 'date', 'amount', 'parent']
        )
        
        frappe.msgprint(f"Cash Advance {cash_advance_name} has {len(liquidations)} liquidations:", title="Debug")
        
        for liq in liquidations:
            frappe.msgprint(f"  - Date: {liq.date}, Amount: {liq.amount}, Parent: {liq.parent}", title="Debug")
        
        return {
            'cash_advance': cash_advance_name,
            'liquidations_count': len(liquidations),
            'liquidations': liquidations
        }
        
    except Exception as err:
        frappe.msgprint(f"Error debugging liquidations: {err}", title="Error")
        return {'error': str(err)}

@frappe.whitelist()
def test_populate_deductions(voucher_name):
    """
    Test function to manually populate deductions for a specific voucher
    """
    try:
        voucher = frappe.get_doc('Payroll Voucher', voucher_name)
        employee = voucher.employee
        date_from = voucher.date_from
        date_to = voucher.date_to
        
        frappe.msgprint(f"Testing deductions population for voucher: {voucher_name}", title="Test")
        frappe.msgprint(f"Employee: {employee}, Period: {date_from} to {date_to}", title="Test")
        
        # Clear existing deductions
        voucher.set('deductions', [])
        
        # Populate deductions
        populate_all_cash_advance_deductions(voucher, employee, date_from, date_to)
        
        # Save the voucher
        voucher.save(ignore_permissions=True)
        
        frappe.msgprint(f"Test completed. Deductions count: {len(voucher.deductions)}", title="Test Results")
        
        return {
            'success': True,
            'deductions_count': len(voucher.deductions),
            'deductions': [{'reference_no': d.reference_no, 'date': d.date, 'type': d.type, 'amount': d.amount} for d in voucher.deductions]
        }
        
    except Exception as err:
        frappe.msgprint(f"Error in test: {err}", title="Test Error")
        return {'success': False, 'error': str(err)}

@frappe.whitelist()
def test_cash_advance_data(employee=None):
    """
    Test function to check if there are cash advances and liquidations in the system
    """
    try:
        # Get all cash advances
        all_cash_advances = frappe.db.get_list('Cash Advance', 
            filters={'docstatus': 1}, 
            fields=['name', 'employee', 'date', 'type', 'purpose', 'amount']
        )
        
        frappe.msgprint(f"Total Cash Advances in system: {len(all_cash_advances)}", title="Test Results")
        
        if employee:
            employee_cash_advances = frappe.db.get_list('Cash Advance', 
                filters={'employee': employee, 'docstatus': 1}, 
                fields=['name', 'date', 'type', 'purpose', 'amount']
            )
            frappe.msgprint(f"Cash Advances for employee {employee}: {len(employee_cash_advances)}", title="Test Results")
            
            for ca in employee_cash_advances:
                liquidations = frappe.db.get_list('Cash Advance Liquidation', 
                    filters={'parent': ca.name}, 
                    fields=['date', 'amount']
                )
                frappe.msgprint(f"Cash Advance {ca.name}: {len(liquidations)} liquidations", title="Test Results")
        
        return {
            'total_cash_advances': len(all_cash_advances),
            'employee_cash_advances': len(employee_cash_advances) if employee else 0
        }
        
    except Exception as err:
        frappe.msgprint(f"Error testing cash advance data: {err}", title="Error")
        return {'error': str(err)}

@frappe.whitelist()
def get_cash_advance_summary(employee, date_from, date_to):
    """
    Get a summary of cash advances for an employee within a date range
    """
    try:
        cash_advances = frappe.db.get_list('Cash Advance', 
            filters={'employee': employee, 'docstatus': 1}, 
            fields=['name', 'date', 'type', 'purpose', 'amount']
        )
        
        summary = []
        total_liquidations = 0
        
        for ca in cash_advances:
            liquidations = frappe.db.get_list('Cash Advance Liquidation', 
                filters={
                    'parent': ca.name, 
                    'date': ['between', [date_from, date_to]]
                }, 
                fields=['date', 'amount']
            )
            
            for liquidation in liquidations:
                if flt(liquidation.amount) > 0:
                    summary.append({
                        'reference_no': ca.name,
                        'date': liquidation.date,
                        'type': ca.type,
                        'purpose': ca.purpose,
                        'liquidation_amount': flt(liquidation.amount)
                    })
                    total_liquidations += flt(liquidation.amount)
        
        return {
            'cash_advances': summary,
            'total_liquidations': total_liquidations,
            'count': len(summary)
        }
        
    except Exception as err:
        frappe.msgprint(f"Error getting cash advance summary: {err}", title="Error")
        return {'cash_advances': [], 'total_liquidations': 0, 'count': 0}

def fetch_incentive(branch, net_sales):
    try:
        incentives = frappe.db.get_list('Incentive Scheme', filters={ 'branch': branch, 'amount_from': ['<=', net_sales], 'amount_to': ['>=', net_sales]}, fields=['incentive'], limit=1)
        return flt(incentives[0]['incentive']) if incentives and incentives[0]['incentive'] else 0
    except Exception as err:
        frappe.msgprint(f"Error fetching incentive: {err}", title="Error")
        return 0

def fetch_manual_attendance_time(employee, date, type, branch):
    try:
        response = frappe.db.get_list('Manual Attendance', filters={'employee': employee, 'date': date, 'type': type, 'docstatus':1}, fields=['time', 'branch'], limit=1)
        return {'time': response[0]['time'], 'branch': response[0]['branch']} if response else {'time': None, 'branch': None}
    except Exception as err:
        frappe.msgprint(f"Error fetching manual attendance time for {type}: {err}", title="Error")
        return {'time': None, 'branch': None}

def calculate_partial_contributions(voucher, employee, total_basic_pay):
    if has_hdmf_contribution(employee) == "1":
        calculate_pagibig_contributions(voucher, total_basic_pay, 'partial')
    if has_philhealth_contribution(employee) == "1":
        calculate_philhealth_contributions(voucher, total_basic_pay, 'partial')
    if has_sss_contribution(employee) == "1":
        calculate_sss_contributions(voucher, total_basic_pay, 'partial')

def calculate_end_of_month_contributions(voucher, employee, total_basic_pay):
    monthly_basic_pay = get_monthly_basic_pay_from_items(employee, voucher.date_from)
    full_month_pay = monthly_basic_pay + total_basic_pay

    if has_hdmf_contribution(employee) == "1":
        calculate_pagibig_contributions(voucher, full_month_pay, 'full', employee, voucher.date_to)
    if has_philhealth_contribution(employee) == "1":
        calculate_philhealth_contributions(voucher, full_month_pay, 'full', employee, voucher.date_to)
    if has_sss_contribution(employee) == "1":
        calculate_sss_contributions(voucher, full_month_pay, 'full', employee, voucher.date_to)
    
def calculate_sss_contributions(voucher, monthly_basic_pay, mode, employee=None, date_from=None):
    sss_table = frappe.get_doc('SSS Table', {'active': 1})
    sss_item = next((item for item in sss_table.items if item.base_from <= monthly_basic_pay <= item.base_to), None)

    if sss_item:
        # Deduct previous partial contributions if this is an end-of-month calculation
        partial_ss_ee = get_previous_month_contribution(employee, 'ss_ee', date_from) if mode == 'full' else 0
        partial_ss_er = get_previous_month_contribution(employee, 'ss_er', date_from) if mode == 'full' else 0
        partial_wisp_ee = get_previous_month_contribution(employee, 'wisp_ee', date_from) if mode == 'full' else 0
        partial_wisp_er = get_previous_month_contribution(employee, 'wisp_er', date_from) if mode == 'full' else 0
        partial_ec_er = get_previous_month_contribution(employee, 'ec_er', date_from) if mode == 'full' else 0

        # Assign values to voucher fields after deducting prior contributions
        voucher.ss_ee = flt(sss_item.ss_ee) - partial_ss_ee
        voucher.ss_er = flt(sss_item.ss_er) - partial_ss_er
        voucher.wisp_ee = flt(sss_item.wisp_ee) - partial_wisp_ee
        voucher.wisp_er = flt(sss_item.wisp_er) - partial_wisp_er
        voucher.ec_er = flt(sss_item.ec_er) - partial_ec_er
    else:
        frappe.msgprint(f"No matching SSS contribution range found for monthly basic pay: {monthly_basic_pay}", title="SSS Calculation Error")

def calculate_philhealth_contributions(voucher, basic_pay, mode, employee=None, date_from=None):
    # Fetch the active PhilHealth table document
    philhealth_table = frappe.get_doc('Philhealth Table', {'active': 1})
    
    
    
    # Find the correct item for the basic pay range
    philhealth_item = next((item for item in philhealth_table.items if item.base_from <= basic_pay <= item.base_to), None)
    
    if philhealth_item:
        # Compute the total PhilHealth contribution
        total_contribution = flt((basic_pay * (philhealth_item.rate / 100)) + philhealth_item.monthly_premium)
        
        # Calculate the employee and employer shares
        employee_share = flt(total_contribution * philhealth_item.employee_share / 100)
        employer_share = flt(total_contribution * philhealth_item.employer_share / 100)
        
        # Retrieve and deduct previous partial contributions if this is an end-of-month calculation
        partial_ph_ee = get_previous_month_contribution(employee, 'ph_ee', date_from) if mode == 'full' else 0
        partial_ph_er = get_previous_month_contribution(employee, 'ph_er', date_from) if mode == 'full' else 0
        
        # Apply deductions to the current contributions
        voucher.ph_ee = employee_share - partial_ph_ee
        voucher.ph_er = employer_share - partial_ph_er
        
    else:
        # Debug: Indicate missing contribution range
        frappe.msgprint(f"No matching PhilHealth contribution range found for basic pay: {basic_pay}", title="[ERROR] Contribution Range Not Found")



def calculate_pagibig_contributions(voucher, total_basic_pay, mode, employee=None, date_from=None):
    pagibig_table = frappe.get_doc('Pagibig Table', {'active': 1})
    pagibig_item = next((item for item in pagibig_table.items if item.base_from <= total_basic_pay <= item.base_to), None)

    if pagibig_item:
        employee_contribution = flt(total_basic_pay * (pagibig_item.employee_rate / 100) + pagibig_item.employee_fixed)
        employer_contribution = flt(total_basic_pay * (pagibig_item.employer_rate / 100) + pagibig_item.employer_fixed)

        # Deduct previous partial contributions if this is an end-of-month calculation
        partial_hd_ee = get_previous_month_contribution(employee, 'hd_ee', date_from) if mode == 'full' else 0
        partial_hd_er = get_previous_month_contribution(employee, 'hd_er', date_from) if mode == 'full' else 0

        # Assign values to voucher fields after deducting prior contributions
        voucher.hd_ee = employee_contribution - partial_hd_ee
        voucher.hd_er = employer_contribution - partial_hd_er
    else:
        frappe.msgprint(f"No matching Pagibig contribution range found for basic pay: {total_basic_pay}", title="Pagibig Calculation Error")

        
def get_previous_month_contribution(employee, contribution_field, date_from):
    """
    Retrieve the sum of contributions from previous vouchers within the same month.
    This function uses the start date (date_from) of the current voucher to avoid overlap.
    """
    first_day = frappe.utils.get_first_day(date_from)
    vouchers = frappe.get_all(
        'Payroll Voucher',
        filters={
            'employee': employee,
            'date_from': ['>=', first_day],
            'date_to': ['<', date_from]  # Up to the start date of the new voucher
        },
        fields=[contribution_field]
    )

    # Calculate the sum of the specified contribution field from previous vouchers
    total_contribution = sum(flt(voucher.get(contribution_field, 0)) for voucher in vouchers)
        
    return total_contribution

def is_end_of_month_cutoff(date_to):
    """
    Check if the payroll cutoff (date_to) falls on the last day of the month.
    """
    last_day_of_month = frappe.utils.get_last_day(date_to)
    return frappe.utils.getdate(date_to) == last_day_of_month

def has_hdmf_contribution(employee):
    """
    Check if the employee has the HDMF (Pagibig) contribution field checked.
    """
    employee_doc = frappe.get_doc('Employee', employee)
    return str(cint(employee_doc.hdmf_contribution))

def has_sss_contribution(employee):
    """
    Check if the employee has the SSS contribution field checked.
    """
    employee_doc = frappe.get_doc('Employee', employee)
    return str(cint(employee_doc.sss_contribution))

def has_philhealth_contribution(employee):
    """
    Check if the employee has PhilHealth contribution enabled.
    """
    employee_doc = frappe.get_doc('Employee', employee)
    return str(cint(employee_doc.phic_contribution))
    

def get_monthly_basic_pay_from_items(employee, date_from):
    """
    Calculate the total basic pay for the employee for the entire month
    based on daily entries in Payroll Vouchers up to the specified end-of-month date.
    """
    first_day = frappe.utils.get_first_day(date_from)
    last_day = date_from


    # Get all Payroll Voucher entries within the month for this employee
    payroll_items = frappe.get_all(
        'Payroll Voucher',
        filters={
            'employee': employee,
            'date_from': ['>=', first_day],
            'date_to': ['<=', last_day]
        },
        fields=['total_basic_pay']
    )

    # Summing up the basic pay from each Payroll Voucher entry for the month
    monthly_basic_pay = sum(flt(item.get('total_basic_pay', 0)) for item in payroll_items)


    return monthly_basic_pay

def get_holiday_rate(date):
    holiday = frappe.db.get_value('Payroll Holiday', {'date': date}, ['rate'])
    return flt(holiday) if holiday else None
