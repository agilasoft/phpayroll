import frappe
from frappe import _
from datetime import datetime, timedelta
import calendar

@frappe.whitelist()
def get_missing_entries(start_date, end_date):
	"""Get days with missing time in or time out entries"""
	try:
		employee = frappe.session.user
		
		# Get all dates in the range
		start = datetime.strptime(start_date, '%Y-%m-%d')
		end = datetime.strptime(end_date, '%Y-%m-%d')
		
		missing_entries = []
		current_date = start
		
		while current_date <= end:
			date_str = current_date.strftime('%Y-%m-%d')
			day_name = current_date.strftime('%A')
			
			# Check for time in
			time_in = frappe.db.get_value('Time In', {
				'employee': employee,
				'date': date_str
			}, 'name')
			
			# Check for time out
			time_out = frappe.db.get_value('Time Out', {
				'employee': employee,
				'date': date_str
			}, 'name')
			
			# Only include days that are missing either time in or time out
			if not time_in or not time_out:
				missing_entries.append({
					'date': date_str,
					'day_name': day_name,
					'missing_time_in': not bool(time_in),
					'missing_time_out': not bool(time_out)
				})
			
			current_date += timedelta(days=1)
		
		return missing_entries
		
	except Exception as e:
		frappe.log_error(f"Error in get_missing_entries: {str(e)}")
		return []

@frappe.whitelist()
def get_calendar_data(start_date, end_date):
	"""Get calendar data with time in/out details for each day"""
	try:
		employee = frappe.session.user
		
		# Get all dates in the range
		start = datetime.strptime(start_date, '%Y-%m-%d')
		end = datetime.strptime(end_date, '%Y-%m-%d')
		
		calendar_data = []
		current_date = start
		
		while current_date <= end:
			date_str = current_date.strftime('%Y-%m-%d')
			
			# Get time in data
			time_in_data = frappe.db.get_value('Time In', {
				'employee': employee,
				'date': date_str
			}, ['time', 'branch'], as_dict=True)
			
			# Get time out data
			time_out_data = frappe.db.get_value('Time Out', {
				'employee': employee,
				'date': date_str
			}, ['time', 'branch'], as_dict=True)
			
			# Calculate hours worked if both time in and time out exist
			hours_worked = None
			if time_in_data and time_out_data and time_in_data.time and time_out_data.time:
				time_in_dt = datetime.strptime(str(time_in_data.time), '%Y-%m-%d %H:%M:%S')
				time_out_dt = datetime.strptime(str(time_out_data.time), '%Y-%m-%d %H:%M:%S')
				hours_worked = round((time_out_dt - time_in_dt).total_seconds() / 3600, 2)
			
			calendar_data.append({
				'date': date_str,
				'time_in': time_in_data.time if time_in_data else None,
				'time_out': time_out_data.time if time_out_data else None,
				'time_in_branch': time_in_data.branch if time_in_data else None,
				'time_out_branch': time_out_data.branch if time_out_data else None,
				'hours_worked': hours_worked
			})
			
			current_date += timedelta(days=1)
		
		return calendar_data
		
	except Exception as e:
		frappe.log_error(f"Error in get_calendar_data: {str(e)}")
		return []

@frappe.whitelist()
def get_employee_timelog_summary(employee=None, start_date=None, end_date=None):
	"""Get summary of employee timelog for a date range"""
	try:
		if not employee:
			employee = frappe.session.user
		
		if not start_date:
			start_date = datetime.now().replace(day=1).strftime('%Y-%m-%d')
		if not end_date:
			end_date = datetime.now().strftime('%Y-%m-%d')
		
		# Get time in count
		time_in_count = frappe.db.count('Time In', {
			'employee': employee,
			'date': ['between', [start_date, end_date]]
		})
		
		# Get time out count
		time_out_count = frappe.db.count('Time Out', {
			'employee': employee,
			'date': ['between', [start_date, end_date]]
		})
		
		# Get total hours worked
		calendar_data = get_calendar_data(start_date, end_date)
		total_hours = sum([day.get('hours_worked', 0) for day in calendar_data if day.get('hours_worked')])
		
		return {
			'time_in_count': time_in_count,
			'time_out_count': time_out_count,
			'total_hours': round(total_hours, 2),
			'missing_entries_count': len(get_missing_entries(start_date, end_date))
		}
		
	except Exception as e:
		frappe.log_error(f"Error in get_employee_timelog_summary: {str(e)}")
		return {
			'time_in_count': 0,
			'time_out_count': 0,
			'total_hours': 0,
			'missing_entries_count': 0
		}
