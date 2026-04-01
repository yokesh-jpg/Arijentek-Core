"""
Daily Attendance Module
========================

End-of-day scheduled task that ensures:
1. Weekly off / Holiday days are marked as Present (WO) for all active employees
2. Working days with no checkin are marked as Absent
3. Runs daily via scheduler_events in hooks.py

This fixes the bug where:
- Employees not clocked on working days are left with no attendance (should be Absent)
- Weekly off (WO) days are not marked as Present
"""

from datetime import date as date_type

import frappe
from frappe.utils import add_days, get_first_day, get_last_day, getdate, today


def mark_daily_attendance():
	"""Mark attendance for all active employees for yesterday.

	Called daily by scheduler. Processes yesterday because today's
	attendance may still be in progress (employee hasn't clocked out yet).
	"""
	yesterday = add_days(today(), -1)
	_mark_attendance_for_date(getdate(yesterday))


def mark_attendance_for_month(month=None, year=None):
	"""Backfill attendance for an entire month.

	Useful for correcting historical data.
	Called manually via:
	  bench execute arijentek_core.attendance.daily_attendance.mark_attendance_for_month --kwargs '{"month":3,"year":2026}'
	"""
	today_d = getdate(today())
	month = int(month) if month else today_d.month
	year = int(year) if year else today_d.year

	first_day = get_first_day(f"{year}-{month:02d}-01")
	last_day = get_last_day(f"{year}-{month:02d}-01")

	current = getdate(first_day)
	end = getdate(last_day)

	# Don't process future dates
	if end > today_d:
		end = add_days(today_d, -1)

	while current <= end:
		_mark_attendance_for_date(current)
		current = add_days(current, 1)

	frappe.db.commit()


def _mark_attendance_for_date(att_date):
	"""Process attendance for all active employees on a given date."""
	employees = frappe.get_all(
		"Employee",
		filters={"status": "Active"},
		fields=["name", "employee_name", "holiday_list", "default_shift", "company"],
	)

	for emp in employees:
		try:
			_process_employee_date(emp, att_date)
		except Exception:
			frappe.log_error(
				frappe.get_traceback(),
				f"Daily Attendance Error for {emp.name} on {att_date}",
			)

	frappe.db.commit()


def _process_employee_date(emp, att_date):
	"""Process a single employee for a single date."""
	# Skip if attendance already exists (submitted and not cancelled)
	existing = frappe.db.exists(
		"Attendance",
		{"employee": emp.name, "attendance_date": att_date, "docstatus": ["!=", 2]},
	)
	if existing:
		return

	# Check if date is a holiday or weekly off
	is_holiday, is_weekly_off, holiday_desc = _is_holiday_or_weekly_off(emp, att_date)

	# Check if there's an approved leave for this date
	has_leave = frappe.db.exists(
		"Leave Application",
		{
			"employee": emp.name,
			"status": "Approved",
			"docstatus": 1,
			"from_date": ["<=", att_date],
			"to_date": [">=", att_date],
		},
	)

	if has_leave:
		# Leave Application submit already creates "On Leave" attendance in HRMS
		# Don't create duplicate
		return

	if is_weekly_off or is_holiday:
		# Weekly off or holiday → mark as Present (day off, not absent)
		_create_attendance(
			employee=emp.name,
			date=att_date,
			status="Present",
			working_hours=0,
			leave_type=None,
			remarks=holiday_desc or ("Weekly Off" if is_weekly_off else "Holiday"),
		)
	else:
		# Working day with no clock-in → Absent
		_create_attendance(
			employee=emp.name,
			date=att_date,
			status="Absent",
			working_hours=0,
			leave_type=None,
			remarks="No clock-in recorded",
		)


def _is_holiday_or_weekly_off(emp, att_date):
	"""Check if a date is a holiday or weekly off for the employee.

	Returns (is_holiday, is_weekly_off, description).
	"""
	# Get employee's holiday list
	holiday_list = emp.get("holiday_list")
	if not holiday_list:
		# Try to get from company
		try:
			from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee

			holiday_list = get_holiday_list_for_employee(emp.name, raise_exception=False)
		except ImportError, Exception:
			pass

	if not holiday_list:
		# No holiday list — check day of week (Sat/Sun as default weekly off)
		day_of_week = getdate(att_date).weekday()  # 0=Mon, 6=Sun
		if day_of_week in (5, 6):  # Saturday, Sunday
			return True, True, "Weekly Off (Saturday)" if day_of_week == 5 else "Weekly Off (Sunday)"
		return False, False, None

	# Check holiday list for this date
	holiday = frappe.db.get_value(
		"Holiday",
		{"parent": holiday_list, "holiday_date": att_date},
		["description", "weekly_off"],
		as_dict=True,
	)

	if holiday:
		return True, bool(holiday.weekly_off), holiday.description or "Holiday"

	return False, False, None


def _create_attendance(employee, date, status, working_hours=0, leave_type=None, remarks=None):
	"""Create and submit an attendance record."""
	try:
		attendance = frappe.new_doc("Attendance")
		attendance.update(
			{
				"employee": employee,
				"attendance_date": date,
				"status": status,
				"working_hours": working_hours,
				"doctype": "Attendance",
			}
		)
		if leave_type:
			attendance.leave_type = leave_type
		if remarks:
			# Use the custom_field or company, whichever is available
			if hasattr(attendance, "remarks"):
				attendance.remarks = remarks

		attendance.insert(ignore_permissions=True)
		attendance.flags.ignore_permissions = True
		attendance.submit()
	except frappe.DuplicateEntryError:
		# Race condition — another process created it
		pass
	except Exception:
		frappe.log_error(
			frappe.get_traceback(),
			f"Create Attendance Error for {employee} on {date}",
		)
