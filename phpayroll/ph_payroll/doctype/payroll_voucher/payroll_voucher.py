# -*- coding: utf-8 -*-
# Copyright (c) 2024, www.belizzo.ph and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, add_days, get_datetime, time_diff_in_hours

class PayrollVoucher(Document):
    pass

@frappe.whitelist()
def run_payroll(date_from, date_to, branch):
    frappe.msgprint(f"Running payroll from {date_from} to {date_to} for branch {branch}", title="Payroll Run Start")
    payroll_vouchers = []

    employees = frappe.get_all('Employee', filters={'status': 'Active', 'reporting_branch': branch})
    for employee in employees:
        voucher = get_or_create_payroll_voucher(employee.name, date_from, date_to, branch)
        
        if voucher:
            populate_items(voucher)
            voucher.save(ignore_permissions=True)
            payroll_vouchers.append(voucher.name)

    frappe.msgprint(f"Payroll run completed successfully. Vouchers created/updated: {', '.join(payroll_vouchers)}", title="Payroll Run Complete")
    return f"Payroll run completed successfully. Vouchers created/updated: {', '.join(payroll_vouchers)}"
   
@frappe.whitelist()
def recompute_payroll_voucher(voucher_name):
    # Load the document using the passed voucher name
    voucher = frappe.get_doc('Payroll Voucher', voucher_name)

    # Populate items and save the document
    populate_items(voucher)
    voucher.save(ignore_permissions=True)

    # Return a message indicating success
    frappe.msgprint(f"Payroll voucher recomputed successfully. Voucher updated: {voucher.name}", title="Payroll Recompute Complete")
    return f"Payroll voucher recomputed successfully. Voucher updated: {voucher.name}"
    
def get_or_create_payroll_voucher(employee, date_from, date_to, branch):
    # First, check for existing vouchers with exact date matches
    existing_vouchers = frappe.get_all('Payroll Voucher', filters={
        'employee': employee,
        'branch': branch,
        'date_from': date_from,
        'date_to': date_to
    })

    if existing_vouchers:
        existing_voucher = frappe.get_doc('Payroll Voucher', existing_vouchers[0].name)
        frappe.msgprint(f"Found existing voucher with exact date range for Employee: {employee} in branch: {branch}. Updating the existing voucher.", title="Voucher Exact Match")
        return existing_voucher

    # Next, check for overlapping vouchers
    overlapping_vouchers = frappe.get_all('Payroll Voucher', filters={
        'employee': employee,
        'branch': branch,
        'date_from': ['<=', date_to],
        'date_to': ['>=', date_from]
    })

    if overlapping_vouchers:
        frappe.msgprint(f"Found overlapping vouchers for Employee: {employee} in branch: {branch}. Cannot create/update voucher due to overlap.", title="Voucher Overlap")
        return None

    # If no exact match or overlap, create a new voucher
    voucher = frappe.new_doc('Payroll Voucher')
    voucher.employee = employee
    voucher.date_from = date_from
    voucher.date_to = date_to
    voucher.branch = branch
    voucher.save(ignore_permissions=True)
    frappe.msgprint(f"Created new Payroll Voucher: {voucher.name} for Employee: {employee}", title="Payroll Voucher Creation")
    return voucher

def populate_items(voucher):
    date_from = voucher.date_from
    date_to = voucher.date_to
    employee = voucher.employee
    branch = voucher.branch

    if not date_from or not date_to or not employee:
        frappe.throw(_('Please ensure Employee, Date From, and Date To are filled.'))

    voucher.set('items', [])
    voucher.set('deductions', [])  # Clear existing deductions
    
    total_basic_pay = 0
    total_overtime_pay = 0
    total_incentive = 0
    total_holiday_pay = 0
    less_cash_advance = 0

    date_array = get_dates_between(date_from, date_to)
    
    for date in date_array:
        fetch_time_and_sales(employee, date, branch, voucher)

    
    for item in voucher.items:
        total_basic_pay += flt(item.basic_pay)
        total_holiday_pay += flt(item.holiday_pay)
        total_overtime_pay += flt(item.overtime_pay)
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
    voucher.total_incentive = total_incentive + manual_incentive
    voucher.less_cash_advance = less_cash_advance + manual_cash_advance
    
    # Set basic calculations
    net_pay = total_basic_pay + total_holiday_pay + total_overtime_pay + total_incentive - less_cash_advance + manual_basic_pay + manual_holiday_pay + manual_overtime_pay + manual_incentive - manual_cash_advance
    voucher.net_pay = net_pay  # Set the initial net pay before deductions

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
    voucher.net_pay = net_pay - total_deductions  # Final net pay after deductions


    # Save the voucher with updated values
    voucher.save(ignore_permissions=True) 
    
def get_dates_between(start_date, end_date):
    dates = []
    current_date = getdate(start_date)
    end_date = getdate(end_date)
    while current_date <= end_date:
        dates.append(current_date)
        current_date = add_days(current_date, 1)
    return dates

def fetch_time_and_sales(employee, date, branch, voucher):
    time_in, time_out, time_in_branch, manual_time_in, manual_time_out = None, None, None, None, None

    try:
        time_in_response = frappe.db.get_value('Time In', {'employee': employee, 'date': date}, ['time', 'branch'])
        if time_in_response:
            time_in, time_in_branch = time_in_response

        time_out_response = frappe.db.get_value('Time Out', {'employee': employee, 'date': date}, 'time')
        if time_out_response:
            time_out = time_out_response

        if not time_in:
            manual_time_in = fetch_manual_attendance_time(employee, date, 'Time In', branch)
            time_in = manual_time_in['time']
            if not time_in_branch:
                time_in_branch = manual_time_in['branch']

        if not time_out:
            manual_time_out = fetch_manual_attendance_time(employee, date, 'Time Out', branch)
            time_out = manual_time_out['time']

    except Exception as err:
        frappe.msgprint(f"Error fetching time records: {err}", title="Error")

    fetch_cash_count_and_populate_items(employee, date, time_in_branch, calculate_hours_worked(time_in, time_out), time_in, time_out, voucher)

def calculate_hours_worked(timestamp_in, timestamp_out):
    if not timestamp_in or not timestamp_out:
        return 0

    date_time_in = get_datetime(timestamp_in)
    date_time_out = get_datetime(timestamp_out)
    difference_in_hours = time_diff_in_hours(date_time_out, date_time_in)
    return round(difference_in_hours, 2)

def fetch_cash_count_and_populate_items(employee, date, branch, hours_worked, time_in, time_out, voucher):
    try:
        net_sales = 0  # Default value

        # Safely check if the Cash Count doctype exists
        try:
            frappe.get_meta("Cash Count", cached=True)
            # If exists, proceed to get the cash count data
            cash_counts = frappe.db.get_list(
                'Cash Count',
                filters={'branch': branch, 'date': date},
                fields=['sum(net_sales) as total_amount']
            )
            if cash_counts and cash_counts[0].get('total_amount'):
                net_sales = cash_counts[0]['total_amount']
        except frappe.DoesNotExistError:
            net_sales = 0
        except Exception as e:
            net_sales = 0

        # Basic pay computation
        basic_hours = voucher.basic_hours or 0
        hourly_rate = voucher.hourly_rate or 0
        worked_hours_for_pay = min(hours_worked, basic_hours)
        basic_pay = worked_hours_for_pay * hourly_rate

        # Holiday pay
        holiday_rate = get_holiday_rate(date)
        holiday_pay = worked_hours_for_pay * hourly_rate * holiday_rate if holiday_rate else 0

        # Overtime
        ot_hours_fetched = fetch_overtime_hours(employee, date)
        ot_difference = hours_worked - basic_hours
        ot_hours = min(ot_hours_fetched, max(ot_difference, 0))
        overtime_pay = ot_hours * hourly_rate * 1.25

        # Other compensations
        cash_advance = fetch_cash_advance(employee, date, voucher)
        incentive = fetch_incentive(branch, net_sales)

        # Populate item
        item = {
            'date': date,
            'time_in': time_in,
            'time_out': time_out,
            'hours_worked': hours_worked,
            'net_sales': net_sales,
            'basic_pay': basic_pay,
            'holiday_pay': holiday_pay,
            'ot_hours': ot_hours,
            'overtime_pay': overtime_pay,
            'cash_advance': cash_advance,
            'incentive': incentive
        }
        voucher.append('items', item)

    except Exception as err:
        frappe.msgprint(f"Error in payroll calculation: {err}", title="Error")



def fetch_overtime_hours(employee, date):
    try:
        ot_response = frappe.db.get_list('Overtime', filters={'employee': employee, 'date': date, 'docstatus':1}, fields=['sum(hours) as total_hours'])
        return flt(ot_response[0]['total_hours']) if ot_response and ot_response[0]['total_hours'] else 0
    except Exception as err:
        frappe.msgprint(f"Error fetching overtime hours: {err}", title="Error")
        return 0

def fetch_cash_advance(employee, date, voucher=None):
    try:
        parent_docs = frappe.db.get_list('Cash Advance', filters={'employee': employee}, fields=['name'])
        
        total_cash_advance = 0
        deductions_added = 0
        
        for doc in parent_docs:
            liquidations = frappe.db.get_list('Cash Advance Liquidation', filters={'parent': doc.name, 'date': date}, fields=['amount'])
            
            for liquidation in liquidations:
                total_cash_advance += flt(liquidation.amount)
                
                # If voucher is provided, add to deductions table
                if voucher and liquidation.amount > 0:
                    # Get cash advance details
                    ca_doc = frappe.get_doc('Cash Advance', doc.name)
                    
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
                        deduction.type = ca_doc.type
                        deduction.amount = liquidation.amount
                        deduction.remarks = f"{ca_doc.purpose} - Liquidation Amount: {liquidation.amount}"
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
                if liquidation.amount > 0:
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
                if liquidation.amount > 0:
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
                if liquidation.amount > 0:
                    summary.append({
                        'reference_no': ca.name,
                        'date': liquidation.date,
                        'type': ca.type,
                        'purpose': ca.purpose,
                        'liquidation_amount': liquidation.amount
                    })
                    total_liquidations += liquidation.amount
        
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
    return str(employee_doc.sss_contribution)

def has_sss_contribution(employee):
    """
    Check if the employee has the SSS contribution field checked.
    """
    employee_doc = frappe.get_doc('Employee', employee)
    return str(employee_doc.sss_contribution)

def has_philhealth_contribution(employee):
    """
    Check if the employee has PhilHealth contribution enabled.
    """
    employee_doc = frappe.get_doc('Employee', employee)
    return str(employee_doc.sss_contribution)
    

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
