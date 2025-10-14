frappe.pages['my-timelog'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'My Timelog',
		single_column: true
	});

	// Load CSS
	frappe.require('/assets/phpayroll/css/my_timelog.css');

	// Create dashboard layout
	create_timelog_dashboard(page);
}

function create_timelog_dashboard(page) {
	// Create main container
	let dashboard_container = $(`
		<div class="timelog-dashboard">
			<div class="dashboard-header">
				<h3>Time Log Dashboard</h3>
				<div class="date-range-picker">
					<input type="date" id="start-date" class="form-control" style="width: 150px; display: inline-block;">
					<span style="margin: 0 10px;">to</span>
					<input type="date" id="end-date" class="form-control" style="width: 150px; display: inline-block;">
					<button class="btn btn-primary btn-sm" onclick="refreshDashboard()" style="margin-left: 10px;">Refresh</button>
				</div>
			</div>
			<div class="dashboard-content">
				<div class="left-sidebar">
					<div class="missing-entries-section">
						<h4>Missing Time Entries</h4>
						<div id="missing-entries-cards" class="missing-cards-container">
							<div class="loading-spinner">Loading...</div>
						</div>
					</div>
				</div>
				<div class="right-calendar">
					<div class="calendar-section">
						<h4>Time Log Calendar</h4>
						<div id="calendar-container">
							<div class="loading-spinner">Loading calendar...</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	`);

	page.main.append(dashboard_container);

	// Set default date range (current month)
	let today = new Date();
	let firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
	let lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
	
	$('#start-date').val(formatDate(firstDay));
	$('#end-date').val(formatDate(lastDay));

	// Load initial data
	loadDashboardData();
}

function formatDate(date) {
	return date.getFullYear() + '-' + 
		   String(date.getMonth() + 1).padStart(2, '0') + '-' + 
		   String(date.getDate()).padStart(2, '0');
}

function loadDashboardData() {
	let startDate = $('#start-date').val();
	let endDate = $('#end-date').val();
	
	// Load missing entries
	loadMissingEntries(startDate, endDate);
	
	// Load calendar data
	loadCalendarData(startDate, endDate);
}

function loadMissingEntries(startDate, endDate) {
	frappe.call({
		method: 'phpayroll.ph_payroll.page.my_timelog.my_timelog.get_missing_entries',
		args: {
			start_date: startDate,
			end_date: endDate
		},
		callback: function(r) {
			if (r.message) {
				displayMissingEntries(r.message);
			}
		}
	});
}

function loadCalendarData(startDate, endDate) {
	frappe.call({
		method: 'phpayroll.ph_payroll.page.my_timelog.my_timelog.get_calendar_data',
		args: {
			start_date: startDate,
			end_date: endDate
		},
		callback: function(r) {
			if (r.message) {
				displayCalendar(r.message);
			}
		}
	});
}

function displayMissingEntries(missingEntries) {
	let container = $('#missing-entries-cards');
	container.empty();
	
	if (missingEntries.length === 0) {
		container.html('<div class="no-missing-entries">No missing time entries found!</div>');
		return;
	}
	
	missingEntries.forEach(function(entry) {
		let card = $(`
			<div class="missing-entry-card">
				<div class="card-header">
					<h5>${entry.date}</h5>
					<span class="day-name">${entry.day_name}</span>
				</div>
				<div class="card-body">
					<div class="missing-info">
						${entry.missing_time_in ? '<span class="missing-badge time-in-missing">Missing Time In</span>' : ''}
						${entry.missing_time_out ? '<span class="missing-badge time-out-missing">Missing Time Out</span>' : ''}
					</div>
					<div class="card-actions">
						<button class="btn btn-sm btn-primary" onclick="createTimeEntry('${entry.date}', 'Time In')" ${!entry.missing_time_in ? 'disabled' : ''}>
							Add Time In
						</button>
						<button class="btn btn-sm btn-secondary" onclick="createTimeEntry('${entry.date}', 'Time Out')" ${!entry.missing_time_out ? 'disabled' : ''}>
							Add Time Out
						</button>
					</div>
				</div>
			</div>
		`);
		container.append(card);
	});
}

function displayCalendar(calendarData) {
	let container = $('#calendar-container');
	container.empty();
	
	// Create calendar grid
	let calendar = $(`
		<div class="calendar-grid">
			<div class="calendar-header">
				<div class="calendar-nav">
					<button class="btn btn-sm" onclick="navigateCalendar(-1)">← Previous</button>
					<span class="current-month"></span>
					<button class="btn btn-sm" onclick="navigateCalendar(1)">Next →</button>
				</div>
			</div>
			<div class="calendar-body">
				<div class="calendar-days-header">
					<div>Sun</div><div>Mon</div><div>Tue</div><div>Wed</div><div>Thu</div><div>Fri</div><div>Sat</div>
				</div>
				<div class="calendar-days" id="calendar-days"></div>
			</div>
		</div>
	`);
	
	container.append(calendar);
	updateCurrentMonth();
	renderCalendarDays(calendarData);
}

function renderCalendarDays(calendarData) {
	let daysContainer = $('#calendar-days');
	daysContainer.empty();
	
	// Get current month and year
	let startDate = new Date($('#start-date').val());
	let currentMonth = startDate.getMonth();
	let currentYear = startDate.getFullYear();
	
	// Get first day of month and number of days
	let firstDay = new Date(currentYear, currentMonth, 1);
	let lastDay = new Date(currentYear, currentMonth + 1, 0);
	let daysInMonth = lastDay.getDate();
	let startingDayOfWeek = firstDay.getDay();
	
	// Add empty cells for days before month starts
	for (let i = 0; i < startingDayOfWeek; i++) {
		daysContainer.append('<div class="calendar-day empty"></div>');
	}
	
	// Add days of the month
	for (let day = 1; day <= daysInMonth; day++) {
		let dateStr = formatDate(new Date(currentYear, currentMonth, day));
		let dayData = calendarData.find(d => d.date === dateStr);
		
		let dayElement = $(`
			<div class="calendar-day ${dayData ? 'has-data' : ''}" data-date="${dateStr}">
				<div class="day-number">${day}</div>
				${dayData ? `
					<div class="time-entries">
						${dayData.time_in ? `<div class="time-entry time-in">In: ${formatTime(dayData.time_in)}</div>` : ''}
						${dayData.time_out ? `<div class="time-entry time-out">Out: ${formatTime(dayData.time_out)}</div>` : ''}
						${dayData.hours_worked ? `<div class="hours-worked">${dayData.hours_worked}h</div>` : ''}
					</div>
				` : ''}
			</div>
		`);
		
		daysContainer.append(dayElement);
	}
}

function formatTime(datetime) {
	if (!datetime) return '';
	let date = new Date(datetime);
	return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

function createTimeEntry(date, type) {
	frappe.new_doc(type === 'Time In' ? 'Time In' : 'Time Out', {
		date: date,
		employee: frappe.user.name
	});
}

function refreshDashboard() {
	loadDashboardData();
}

function updateCurrentMonth() {
	let startDate = new Date($('#start-date').val());
	let monthNames = ["January", "February", "March", "April", "May", "June",
		"July", "August", "September", "October", "November", "December"];
	let monthName = monthNames[startDate.getMonth()];
	let year = startDate.getFullYear();
	$('.current-month').text(`${monthName} ${year}`);
}

function navigateCalendar(direction) {
	let startDate = new Date($('#start-date').val());
	let newDate = new Date(startDate.getFullYear(), startDate.getMonth() + direction, 1);
	
	$('#start-date').val(formatDate(newDate));
	
	let endDate = new Date(newDate.getFullYear(), newDate.getMonth() + 1, 0);
	$('#end-date').val(formatDate(endDate));
	
	loadDashboardData();
}

// Make functions globally available
window.refreshDashboard = refreshDashboard;
window.createTimeEntry = createTimeEntry;
window.navigateCalendar = navigateCalendar;