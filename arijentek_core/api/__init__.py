from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import flt, get_first_day, get_last_day, getdate, now_datetime, nowdate

from arijentek_core.api.rate_limiter import user_rate_limit


def to_utc_iso(dt):
	if not dt:
		return None
	from zoneinfo import ZoneInfo
	from frappe.utils import get_system_timezone, get_datetime
	dt = get_datetime(dt)
	if not dt.tzinfo:
		dt = dt.replace(tzinfo=ZoneInfo(get_system_timezone()))
	return dt.astimezone(ZoneInfo("UTC")).isoformat()


def get_holiday_list_for_employee_or_company(employee: str | None, company: str | None = None) -> str | None:
	"""Retrieve the holiday list for an employee, falling back to company's default list."""
	holiday_list = None
	if employee:
		try:
			from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
			holiday_list = get_holiday_list_for_employee(employee, raise_exception=False)
		except Exception:
			pass
		if not holiday_list:
			holiday_list = frappe.db.get_value("Employee", employee, "holiday_list")

	if not holiday_list and company:
		holiday_list = frappe.db.get_value("Company", company, "default_holiday_list")

	return holiday_list


# ============ DASHBOARD ============


@frappe.whitelist()
def get_dashboard_data():
	"""Get all dashboard data in one call"""
	employee = get_current_employee()
	if not employee:
		# Return empty structure for non-employees (e.g. Administrator)
		return {
			"employee": "",
			"employee_name": frappe.session.user,
			"department": "",
			"designation": "",
			"current_month": getdate(nowdate()).strftime("%B"),
			"year": getdate(nowdate()).year,
			"last_punch": None,
			"attendance_summary": {"Present": 0, "Absent": 0, "Half Day": 0, "On Leave": 0},
			"leave_type_breakdown": {},
		}

	today = nowdate()
	current_month = getdate(today).strftime("%B")
	year = getdate(today).year

	# Get last checkin
	last_checkin = frappe.db.sql(
		"""
        SELECT name, time, log_type
        FROM `tabEmployee Checkin`
        WHERE employee = %s AND DATE(time) = %s
        ORDER BY time DESC
        LIMIT 1
    """,
		(employee, today),
		as_dict=True,
	)

	last_punch = None
	if last_checkin:
		last_punch = {
			"name": last_checkin[0].name,
			"time": to_utc_iso(last_checkin[0].time),
			"log_type": last_checkin[0].log_type,
		}

	# Get attendance summary
	first_day = get_first_day(today)
	last_day = get_last_day(today)

	summary = frappe.db.sql(
		"""
        SELECT status, COUNT(*) as count
        FROM `tabAttendance`
        WHERE employee = %s
        AND attendance_date BETWEEN %s AND %s
        AND docstatus = 1
        GROUP BY status
    """,
		(employee, first_day, last_day),
		as_dict=True,
	)

	attendance_summary = {"Present": 0, "Absent": 0, "Half Day": 0, "On Leave": 0}
	for row in summary:
		if row.status in attendance_summary:
			attendance_summary[row.status] = row.count

	# Get leave-type breakdown for "On Leave" days
	on_leave_types = frappe.db.sql(
		"""
		SELECT leave_type, COUNT(*) as count
		FROM `tabAttendance`
		WHERE employee = %s
		AND attendance_date BETWEEN %s AND %s
		AND docstatus = 1
		AND status = 'On Leave'
		GROUP BY leave_type
		""",
		(employee, first_day, last_day),
		as_dict=True,
	)
	leave_type_breakdown = {r.leave_type: r.count for r in on_leave_types}

	emp_info = (
		frappe.db.get_value(
			"Employee", employee, ["employee_name", "department", "designation"], as_dict=True
		)
		or {}
	)

	return {
		"employee": employee,
		"employee_name": emp_info.get("employee_name", ""),
		"department": emp_info.get("department", ""),
		"designation": emp_info.get("designation", ""),
		"current_month": current_month,
		"year": year,
		"last_punch": last_punch,
		"attendance_summary": attendance_summary,
		"leave_type_breakdown": leave_type_breakdown,
	}


# ============ EMPLOYEE INFO ============


@frappe.whitelist()
def get_employee_info():
	"""Get current employee details"""
	user = frappe.session.user
	employee = frappe.db.get_value(
		"Employee", {"user_id": user}, ["name", "employee_name", "department", "designation", "company"], as_dict=True
	)

	if not employee:
		return {"error": "No employee record found for this user"}

	return {
		"employee_id": employee.name,
		"employee_name": employee.employee_name,
		"department": employee.department,
		"designation": employee.designation,
		"company": employee.company,
	}


# ============ CLOCK IN/OUT ============

# Maximum shift duration in hours — auto clock-out after this
MAX_SHIFT_HOURS = 12


@frappe.whitelist()
def get_today_checkin():
	"""Get today's check-in status.

	Returns:
	  clock_in  - ISO timestamp of the single IN log (or None)
	  clock_out - ISO timestamp of the single OUT log (or None)
	  completed - True if the employee has already clocked in AND out today
	"""
	employee = get_current_employee()
	if not employee:
		return {"clock_in": None, "clock_out": None, "completed": False}

	today = nowdate()

	checkins = frappe.db.sql(
		"""
		SELECT time, log_type
		FROM `tabEmployee Checkin`
		WHERE employee = %s 
		  AND DATE(time) = %s
		  AND COALESCE(device_id, '') NOT IN ('BREAK_START', 'BREAK_END')
		ORDER BY time ASC
		""",
		(employee, today),
		as_dict=True,
	)

	if not checkins:
		return {"clock_in": None, "clock_out": None, "completed": False}

	in_log = None
	out_log = None
	for c in checkins:
		if c.log_type == "IN" and not in_log:
			in_log = c
		elif c.log_type == "OUT" and not out_log:
			out_log = c

	completed = bool(in_log and out_log)

	return {
		"clock_in": to_utc_iso(in_log.time) if in_log else None,
		"clock_out": to_utc_iso(out_log.time) if out_log else None,
		"completed": completed,
	}


@frappe.whitelist()
@user_rate_limit(limit=20, seconds=60)
def clock_in():
	"""Record clock in (once per day only) and auto-mark attendance"""
	employee = get_current_employee()
	if not employee:
		return {"success": False, "error": "Employee not found"}

	today = nowdate()

	# Check if already clocked in today
	existing_in = frappe.db.exists(
		"Employee Checkin",
		{"employee": employee, "log_type": "IN", "time": ["between", [today, f"{today} 23:59:59"]]},
	)
	if existing_in:
		return {"success": False, "error": "You have already clocked in today"}

	try:
		checkin = frappe.get_doc(
			{"doctype": "Employee Checkin", "employee": employee, "time": now_datetime(), "log_type": "IN"}
		)
		checkin.insert(ignore_permissions=True)
		frappe.db.commit()

		return {"success": True, "time": to_utc_iso(checkin.time)}
	except Exception as e:
		return {"success": False, "error": str(e)}


@frappe.whitelist()
@user_rate_limit(limit=20, seconds=60)
def clock_out():
	"""Record clock out (must have clocked in first, once per day) and auto-mark attendance"""
	employee = get_current_employee()
	if not employee:
		return {"success": False, "error": "Employee not found"}

	today = nowdate()

	# Must have clocked in today
	in_checkin = frappe.db.sql(
		"""
		SELECT time FROM `tabEmployee Checkin`
		WHERE employee = %s 
		  AND DATE(time) = %s 
		  AND log_type = 'IN'
		  AND COALESCE(device_id, '') NOT IN ('BREAK_START', 'BREAK_END')
		ORDER BY time ASC LIMIT 1
		""",
		(employee, today),
		as_dict=True,
	)
	if not in_checkin:
		return {"success": False, "error": "You must clock in before clocking out"}

	# Check if already clocked out today
	existing_out = frappe.db.sql(
		"""
		SELECT name FROM `tabEmployee Checkin`
		WHERE employee = %s 
		  AND log_type = 'OUT' 
		  AND time BETWEEN %s AND %s
		  AND COALESCE(device_id, '') NOT IN ('BREAK_START', 'BREAK_END')
		LIMIT 1
		""",
		(employee, today, f"{today} 23:59:59"),
	)
	if existing_out:
		return {"success": False, "error": "You have already clocked out today"}

	# Enforce max shift duration
	clock_in_time = in_checkin[0].time
	now = now_datetime()
	hours_worked = (now - clock_in_time).total_seconds() / 3600
	if hours_worked > MAX_SHIFT_HOURS:
		return {"success": False, "error": f"Shift exceeded {MAX_SHIFT_HOURS} hours. Please contact HR."}

	try:
		checkin = frappe.get_doc(
			{"doctype": "Employee Checkin", "employee": employee, "time": now, "log_type": "OUT"}
		)
		checkin.insert(ignore_permissions=True)
		frappe.db.commit()

		return {"success": True, "time": to_utc_iso(checkin.time)}
	except Exception as e:
		return {"success": False, "error": str(e)}


@frappe.whitelist()
@user_rate_limit(limit=20, seconds=60)
def punch(timestamp: str | None = None):
	"""Unified punch endpoint — one clock-in and one clock-out per day.

	Rules:
	  - First punch of the day → Clock IN
	  - Second punch (after IN) → Clock OUT
	  - No further punches allowed after both IN and OUT exist
	  - Cannot clock out without clocking in first
	  - Max shift duration: MAX_SHIFT_HOURS (12 hours)
	"""
	from frappe.utils import get_datetime

	employee = get_current_employee()
	if not employee:
		return {"status": "error", "error": "Employee not found"}

	# Determine punch time
	if timestamp:
		try:
			punch_time = get_datetime(timestamp)
			# Prevent future punches
			if punch_time > now_datetime():
				return {"status": "error", "error": "Cannot punch in the future"}
		except Exception:
			return {"status": "error", "error": "Invalid timestamp format"}
	else:
		punch_time = now_datetime()

	punch_date = punch_time.date()

	# Get checkins for the PUNCH DATE (not necessarily today)
	today_checkins = frappe.db.sql(
		"""
		SELECT time, log_type FROM `tabEmployee Checkin`
		WHERE employee = %s 
		  AND DATE(time) = %s
		  AND COALESCE(device_id, '') NOT IN ('BREAK_START', 'BREAK_END')
		ORDER BY time ASC
		""",
		(employee, punch_date),
		as_dict=True,
	)

	has_in = any(c.log_type == "IN" for c in today_checkins)
	has_out = any(c.log_type == "OUT" for c in today_checkins)

	# Already completed for the day
	if has_in and has_out:
		return {"status": "error", "error": f"You have already clocked in and out for {punch_date}"}

	# Determine log type
	if not has_in:
		log_type = "IN"
	elif has_in and not has_out:
		log_type = "OUT"
		# Enforce max shift duration
		in_time = next(c.time for c in today_checkins if c.log_type == "IN")

		# Calculate hours worked based on PUNCH TIME
		if isinstance(in_time, str):
			in_time = get_datetime(in_time)

		hours_worked = (punch_time - in_time).total_seconds() / 3600
		if hours_worked > MAX_SHIFT_HOURS:
			return {"status": "error", "error": f"Shift exceeded {MAX_SHIFT_HOURS} hours. Please contact HR."}
	else:
		return {"status": "error", "error": "Invalid state"}

	try:
		checkin = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": employee,
				"time": punch_time,
				"log_type": log_type,
			}
		)
		checkin.insert(ignore_permissions=True)
		frappe.db.commit()

		return {
			"status": "success",
			"log_type": log_type,
			"time": to_utc_iso(checkin.time),
		}
	except Exception as e:
		return {"status": "error", "error": str(e)}


# ============ BREAK MANAGEMENT ============


@frappe.whitelist()
@user_rate_limit(limit=20, seconds=60)
def start_break():
	"""Start a break during the current shift.

	Creates a BREAK_START Employee Checkin record.
	Only allowed if clocked in and not already on break.
	"""
	employee = get_current_employee()
	if not employee:
		return {"success": False, "error": "Employee not found"}

	today = nowdate()

	# Must be clocked in
	has_in = frappe.db.sql(
		"""
		SELECT name FROM `tabEmployee Checkin`
		WHERE employee = %s 
		  AND log_type = 'IN'
		  AND time BETWEEN %s AND %s
		  AND COALESCE(device_id, '') NOT IN ('BREAK_START', 'BREAK_END')
		LIMIT 1
		""",
		(employee, today, f"{today} 23:59:59"),
	)
	if not has_in:
		return {"success": False, "error": "You must clock in before taking a break"}

	# Already clocked out?
	has_out = frappe.db.sql(
		"""
		SELECT name FROM `tabEmployee Checkin`
		WHERE employee = %s 
		  AND log_type = 'OUT'
		  AND time BETWEEN %s AND %s
		  AND COALESCE(device_id, '') NOT IN ('BREAK_START', 'BREAK_END')
		LIMIT 1
		""",
		(employee, today, f"{today} 23:59:59"),
	)
	if has_out:
		return {"success": False, "error": "Your shift has already ended"}

	# Check if already on break (has BREAK_START but no BREAK_END)
	break_starts = frappe.db.count(
		"Employee Checkin",
		{"employee": employee, "device_id": "BREAK_START", "time": ["between", [today, f"{today} 23:59:59"]]},
	)
	break_ends = frappe.db.count(
		"Employee Checkin",
		{"employee": employee, "device_id": "BREAK_END", "time": ["between", [today, f"{today} 23:59:59"]]},
	)
	if break_starts > break_ends:
		return {"success": False, "error": "You are already on break"}

	try:
		now = now_datetime()
		checkin = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": employee,
				"time": now,
				"log_type": "OUT",  # Using OUT so it doesn't conflict with main IN/OUT
				"device_id": "BREAK_START",
			}
		)
		checkin.insert(ignore_permissions=True)
		frappe.db.commit()
		return {"success": True, "time": to_utc_iso(now)}
	except Exception as e:
		return {"success": False, "error": str(e)}


@frappe.whitelist()
@user_rate_limit(limit=20, seconds=60)
def end_break():
	"""End the current break.

	Creates a BREAK_END Employee Checkin record.
	Only allowed if currently on break.
	"""
	employee = get_current_employee()
	if not employee:
		return {"success": False, "error": "Employee not found"}

	today = nowdate()

	# Must be on break
	break_starts = frappe.db.count(
		"Employee Checkin",
		{"employee": employee, "device_id": "BREAK_START", "time": ["between", [today, f"{today} 23:59:59"]]},
	)
	break_ends = frappe.db.count(
		"Employee Checkin",
		{"employee": employee, "device_id": "BREAK_END", "time": ["between", [today, f"{today} 23:59:59"]]},
	)
	if break_starts <= break_ends:
		return {"success": False, "error": "You are not on break"}

	try:
		now = now_datetime()
		checkin = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": employee,
				"time": now,
				"log_type": "IN",
				"device_id": "BREAK_END",
			}
		)
		checkin.insert(ignore_permissions=True)
		frappe.db.commit()
		return {"success": True, "time": to_utc_iso(now)}
	except Exception as e:
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_break_status():
	"""Get break status for today: total break time and whether currently on break."""
	employee = get_current_employee()
	if not employee:
		return {"on_break": False, "total_break_minutes": 0, "break_count": 0}

	today = nowdate()

	break_logs = frappe.db.sql(
		"""
		SELECT time, device_id
		FROM `tabEmployee Checkin`
		WHERE employee = %s AND DATE(time) = %s
		AND device_id IN ('BREAK_START', 'BREAK_END')
		ORDER BY time ASC
		""",
		(employee, today),
		as_dict=True,
	)

	total_break_seconds = 0
	break_count = 0
	on_break = False
	current_break_start = None

	for log in break_logs:
		if log.device_id == "BREAK_START":
			current_break_start = log.time
			on_break = True
		elif log.device_id == "BREAK_END" and current_break_start:
			total_break_seconds += (log.time - current_break_start).total_seconds()
			break_count += 1
			current_break_start = None
			on_break = False

	# If still on break, include time since break start
	if on_break and current_break_start:
		total_break_seconds += (now_datetime() - current_break_start).total_seconds()

	return {
		"on_break": on_break,
		"total_break_minutes": round(total_break_seconds / 60, 1),
		"total_break_seconds": round(total_break_seconds),
		"break_count": break_count + (1 if on_break else 0),
		"break_start_time": to_utc_iso(current_break_start) if current_break_start and on_break else None,
	}


@frappe.whitelist()
def get_attendance_breaks(employee: str | None = None, date: str | None = None):
	"""Get BREAK_START and BREAK_END check-ins for the given employee and date."""
	if not employee:
		employee = get_current_employee()

	if not employee or not date:
		return []

	# Permission check
	from arijentek_core import get_shift_approver_employees
	permitted_employees = [e["name"] for e in get_shift_approver_employees()]
	if employee != get_current_employee() and employee not in permitted_employees:
		frappe.throw(_("Not permitted to view records for this employee"), frappe.PermissionError)

	# Fetch break logs
	logs = frappe.db.sql(
		"""
		SELECT name, time, device_id
		FROM `tabEmployee Checkin`
		WHERE employee = %s 
			AND DATE(time) = %s
			AND device_id IN ('BREAK_START', 'BREAK_END')
		ORDER BY time ASC
		""",
		(employee, date),
		as_dict=True,
	)

	breaks = []
	current_start = None
	for log in logs:
		if log.device_id == "BREAK_START":
			if current_start:
				breaks.append({
					"break_in": to_utc_iso(current_start),
					"break_out": None,
					"duration": None
				})
			current_start = log.time
		elif log.device_id == "BREAK_END":
			if current_start:
				duration = (log.time - current_start).total_seconds()
				breaks.append({
					"break_in": to_utc_iso(current_start),
					"break_out": to_utc_iso(log.time),
					"duration": round(duration / 60.0, 1) # duration in minutes
				})
				current_start = None
			else:
				breaks.append({
					"break_in": None,
					"break_out": to_utc_iso(log.time),
					"duration": None
				})
	if current_start:
		breaks.append({
			"break_in": to_utc_iso(current_start),
			"break_out": None,
			"duration": None
		})

	return breaks


# ============ LEAVE MANAGEMENT ============


@frappe.whitelist()
def get_leave_types(employee: str | None = None):
	"""Get available leave types allocated for the employee (non-LWP leave types)"""
	if not employee:
		employee = get_current_employee()
	if not employee:
		return []

	allocated_types = frappe.get_all(
		"Leave Allocation",
		filters={"employee": employee, "docstatus": 1},
		pluck="leave_type"
	)

	if not allocated_types:
		return []

	allocated_types = list(set(allocated_types))

	return frappe.get_all(
		"Leave Type",
		filters={"is_lwp": 0, "name": ["in", allocated_types]},
		pluck="name"
	)


@frappe.whitelist()
def get_holidays(
	from_date: str | None = None, to_date: str | None = None, exclude_weekly_off: str | None = None
):
	"""Get holidays for the current employee's Holiday List from ERPNext.

	Args:
		from_date: Start date (defaults to first day of current month)
		to_date: End date (defaults to last day of current month)
		exclude_weekly_off: If "1" or True, exclude Saturday/Sunday weekly-off entries
			and only return gazetted/public holidays (Jan 1, Jan 26, May 1, etc.)

	Returns list of {holiday_date, description, weekly_off} for the given date range.
	"""
	employee = get_current_employee()
	if not employee:
		return []

	company = frappe.db.get_value("Employee", employee, "company")
	holiday_list = get_holiday_list_for_employee_or_company(employee, company)
	if not holiday_list:
		return []

	today = nowdate()
	from_date = from_date or get_first_day(today)
	to_date = to_date or get_last_day(today)

	filters = {
		"parent": holiday_list,
		"holiday_date": ["between", [from_date, to_date]],
	}

	# Exclude weekly off (Sat/Sun) if requested — show only gazetted holidays
	if exclude_weekly_off in (1, "1", True, "true", "True"):
		filters["weekly_off"] = 0

	holidays = frappe.get_all(
		"Holiday",
		filters=filters,
		fields=["holiday_date", "description", "weekly_off"],
		order_by="holiday_date",
	)

	from frappe.utils import strip_html

	for h in holidays:
		dt = h.get("holiday_date")
		if hasattr(dt, "strftime"):
			h["holiday_date"] = dt.strftime("%Y-%m-%d")
		desc = h.get("description") or ""
		h["description"] = strip_html(desc).strip()

	return holidays


@frappe.whitelist()
def get_employee_holiday(employee: str, month: int, year: int) -> dict:
	"""Get holidays and weekly offs for a specific employee in a given month/year."""
	import calendar

	month = int(month)
	year = int(year)

	last_day_num = calendar.monthrange(year, month)[1]
	start_date = getdate(f"{year}-{month:02d}-01")
	end_date = getdate(f"{year}-{month:02d}-{last_day_num}")

	holiday_list = None

	# 1. Check Holiday List Assignment for Employee
	HLA = frappe.qb.DocType("Holiday List Assignment")
	hla_records = (
		frappe.qb.from_(HLA)
		.select(HLA.holiday_list)
		.where(HLA.assigned_to == employee)
		.where(HLA.from_date <= end_date)
		.where(HLA.docstatus == 1)
		.orderby(HLA.from_date, order=frappe.qb.desc)
		.limit(1)
	).run()
	if hla_records:
		holiday_list = hla_records[0][0]

	# 2. Check direct holiday_list field on Employee doctype
	if not holiday_list:
		holiday_list = frappe.db.get_value("Employee", employee, "holiday_list")

	# Get employee's company
	company = frappe.db.get_value("Employee", employee, "company")

	# 3. Check Holiday List Assignment for Company
	if not holiday_list and company:
		hla_records = (
			frappe.qb.from_(HLA)
			.select(HLA.holiday_list)
			.where(HLA.assigned_to == company)
			.where(HLA.from_date <= end_date)
			.where(HLA.docstatus == 1)
			.orderby(HLA.from_date, order=frappe.qb.desc)
			.limit(1)
		).run()
		if hla_records:
			holiday_list = hla_records[0][0]

	# 4. Check default_holiday_list field on Company doctype
	if not holiday_list and company:
		holiday_list = frappe.db.get_value("Company", company, "default_holiday_list")

	# Query holidays
	holidays = {}
	if holiday_list:
		holiday_records = frappe.get_all(
			"Holiday",
			filters={
				"parent": holiday_list,
				"holiday_date": ["between", [start_date, end_date]],
			},
			fields=["holiday_date", "description", "weekly_off"],
		)
		for h in holiday_records:
			dt = h.holiday_date
			date_str = dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else str(dt)
			holidays[date_str] = {
				"description": h.description or "Holiday",
				"weekly_off": bool(h.weekly_off),
			}

	return holidays


# Standard leave balance categories (order for display)
LEAVE_BALANCE_CATEGORIES = [
	"Casual Leave",
	"Sick Leave",
	"Earned Leave",
	"Regional Holidays",
]


def _get_earned_leave_balance(employee, today):
	"""Calculate earned leave: 1 day per 20 working days since date of joining, minus used.

	Bug 4 fix:
	- Half Day attendance now counts as 0.5 working days (was 1)
	- Uses current leave period (calendar year) for calculation
	- Properly accounts for used earned leave
	"""
	date_of_joining = frappe.db.get_value("Employee", employee, "date_of_joining")
	if not date_of_joining:
		return 0

	date_of_joining = getdate(date_of_joining)
	today_d = getdate(today)
	if date_of_joining > today_d:
		return 0

	# Count Present days as 1.0 and Half Day as 0.5
	present_result = frappe.db.sql(
		"""
		SELECT COUNT(DISTINCT attendance_date) as days
		FROM `tabAttendance`
		WHERE employee = %s
		AND docstatus = 1
		AND attendance_date BETWEEN %s AND %s
		AND status = 'Present'
		""",
		(employee, date_of_joining, today_d),
		as_dict=True,
	)
	present_days = flt(present_result[0].days) if present_result else 0

	half_day_result = frappe.db.sql(
		"""
		SELECT COUNT(DISTINCT attendance_date) as days
		FROM `tabAttendance`
		WHERE employee = %s
		AND docstatus = 1
		AND attendance_date BETWEEN %s AND %s
		AND status = 'Half Day'
		""",
		(employee, date_of_joining, today_d),
		as_dict=True,
	)
	half_days = flt(half_day_result[0].days) if half_day_result else 0

	# Total working days: Present counts as 1, Half Day as 0.5
	working_days = present_days + (half_days * 0.5)

	# Earned = floor(working_days / 20)
	earned = int(working_days // 20)

	# Minus earned leave already taken (Approved Leave Applications)
	used_result = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(total_leave_days), 0) as used
		FROM `tabLeave Application`
		WHERE employee = %s
		AND leave_type = 'Earned Leave'
		AND status = 'Approved'
		AND docstatus = 1
		""",
		(employee,),
		as_dict=True,
	)
	used = flt(used_result[0].used) if used_result else 0

	balance = earned - used
	return max(0, balance)


@frappe.whitelist()
def get_leave_balance():
	"""Get leave balance for leave types allocated to the employee."""
	employee = get_current_employee()
	if not employee:
		return []

	from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on

	today = nowdate()
	balance_map = {}

	# Get allocated leave types for the employee
	allocated_types = get_leave_types(employee)

	# Get balances from ERPNext for allocated leave types
	for leave_type in allocated_types:
		if leave_type == "Earned Leave":
			balance_map[leave_type] = _get_earned_leave_balance(employee, today)
		else:
			try:
				latest_alloc = frappe.db.get_value(
					"Leave Allocation",
					{"employee": employee, "leave_type": leave_type, "docstatus": 1},
					["from_date", "to_date", "new_leaves_allocated"],
					order_by="from_date desc",
					as_dict=True,
				)
				if latest_alloc:
					allocated = flt(latest_alloc.new_leaves_allocated)
					approved_result = frappe.db.sql(
						"""
						SELECT COALESCE(SUM(total_leave_days), 0) as approved_days
						FROM `tabLeave Application`
						WHERE employee = %s
						AND leave_type = %s
						AND status = 'Approved'
						AND docstatus = 1
						AND (
							from_date BETWEEN %s AND %s
							OR to_date BETWEEN %s AND %s
						)
						""",
						(
							employee,
							leave_type,
							latest_alloc.from_date,
							latest_alloc.to_date,
							latest_alloc.from_date,
							latest_alloc.to_date,
						),
						as_dict=True,
					)
					approved = flt(approved_result[0].approved_days) if approved_result else 0.0
					balance_map[leave_type] = max(0.0, allocated - approved)
				else:
					balance_map[leave_type] = 0
			except Exception:
				balance_map[leave_type] = 0

	return [{"leave_type": k, "balance": flt(v)} for k, v in balance_map.items()]


@frappe.whitelist()
@user_rate_limit(limit=10, seconds=60)
def apply_leave(leave_type: str, from_date: str, to_date: str, half_day: int = 0, reason: str = "", name: str = None):
	"""Submit or edit leave application.

	Auto-creates a Leave Allocation for the calendar year if one does
	not already exist, so employees can apply without HR manually
	setting up allocations first.
	"""
	employee = get_current_employee()
	if not employee:
		return {"success": False, "error": "Employee not found"}

	# Ensure a submitted Leave Allocation covers the requested dates
	_ensure_leave_allocation(employee, leave_type, from_date, to_date)

	try:
		if name:
			# Edit mode
			leave = frappe.get_doc("Leave Application", name)
			if leave.employee != employee:
				return {"success": False, "error": "Not authorized to edit this leave application"}
			if leave.status != "Open" or leave.docstatus != 0:
				return {"success": False, "error": "Cannot edit a leave application that is already processed or submitted"}

			leave.leave_type = leave_type
			leave.from_date = from_date
			leave.to_date = to_date
			leave.half_day = half_day
			leave.description = reason
			leave.save(ignore_permissions=True)
		else:
			# Create mode
			leave = frappe.get_doc(
				{
					"doctype": "Leave Application",
					"employee": employee,
					"leave_type": leave_type,
					"from_date": from_date,
					"to_date": to_date,
					"half_day": half_day,
					"description": reason,
					"status": "Open",
				}
			)
			leave.insert(ignore_permissions=True)

		frappe.db.commit()

		# Notify Manager (only on creation)
		if not name:
			try:
				from arijentek_core.api.notifications import notify_leave_application

				notify_leave_application(leave)
			except Exception:
				# Don't fail the application if notification fails
				pass

		return {"success": True, "name": leave.name}
	except Exception as e:
		msg = str(e)
		# Strip noisy traceback bits
		if "ValidationError" in msg and ":" in msg:
			msg = msg.split(":")[-1].strip()
		return {"success": False, "error": msg}


@frappe.whitelist()
def get_leave_applications():
	"""Get employee's leave applications"""
	employee = get_current_employee()
	if not employee:
		return []

	apps = frappe.get_all(
		"Leave Application",
		filters={"employee": employee},
		fields=["name", "leave_type", "from_date", "to_date", "total_leave_days", "status", "half_day", "description"],
		order_by="creation desc",
		limit=20,
	)

	# Convert to plain dicts with string dates (handle Frappe Document objects)
	result = []
	for app in apps:
		app_dict = dict(app) if hasattr(app, "__dict__") else app
		# Convert date objects to ISO strings
		if hasattr(app_dict.get("from_date"), "isoformat"):
			app_dict["from_date"] = app_dict["from_date"].isoformat()
		if hasattr(app_dict.get("to_date"), "isoformat"):
			app_dict["to_date"] = app_dict["to_date"].isoformat()
		result.append(app_dict)

	return result


@frappe.whitelist()
def cancel_leave(leave_application: str):
	employee = get_current_employee()
	if not employee:
		return {"success": False, "error": "Employee not found"}

	try:
		leave = frappe.get_doc("Leave Application", leave_application)

		if leave.employee != employee:
			return {"success": False, "error": "Not authorized"}

		if leave.status != "Open":
			return {"success": False, "error": "Cannot cancel - leave already processed"}

		leave.status = "Cancelled"
		leave.save(ignore_permissions=True)
		frappe.db.commit()

		return {"success": True}
	except Exception as e:
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def delete_leave(leave_application: str):
	employee = get_current_employee()
	if not employee:
		return {"success": False, "error": "Employee not found"}

	try:
		leave = frappe.get_doc("Leave Application", leave_application)

		if leave.employee != employee:
			return {"success": False, "error": "Not authorized"}

		if leave.status != "Open" or leave.docstatus != 0:
			return {"success": False, "error": "Cannot delete - leave already processed or submitted"}

		frappe.delete_doc("Leave Application", leave_application, ignore_permissions=True)
		frappe.db.commit()

		return {"success": True}
	except Exception as e:
		return {"success": False, "error": str(e)}


# ============ PAYSLIPS ============


@frappe.whitelist()
def get_salary_slips():
	"""Get employee's salary slips"""
	employee = get_current_employee()
	if not employee:
		return []

	slips = frappe.get_all(
		"Salary Slip",
		filters={"employee": employee, "docstatus": 1},
		fields=["name", "start_date", "end_date", "net_pay", "gross_pay"],
		order_by="start_date desc",
		limit=12,
	)

	for slip in slips:
		slip["month"] = getdate(slip["start_date"]).strftime("%B")
		slip["year"] = getdate(slip["start_date"]).year

	return slips


@frappe.whitelist(allow_guest=False)
def download_payslip(name: str):
	"""Download salary slip PDF using simplified template."""
	from arijentek_core.payroll.payslip_generator import download_payslip_pdf

	return download_payslip_pdf(name)


@frappe.whitelist()
@user_rate_limit(limit=10, seconds=60)
def delete_my_payslip(name: str):
	"""Delete a salary slip owned by the current employee."""
	from arijentek_core.payroll.payslip_generator import delete_my_payslip as _delete

	return _delete(name)


@frappe.whitelist()
def can_delete_salary_slip():
	"""Check if the current user has permission to delete Salary Slips."""
	return frappe.has_permission("Salary Slip", "delete")


@frappe.whitelist()
def generate_payroll(month: int | None = None, year: int | None = None):
	"""Generate salary slips for a month. Requires HR Manager or Payroll Entry create permission.

	month: 1-12, year: e.g. 2026. Defaults to previous month.
	"""
	user = frappe.session.user
	if not (frappe.has_permission("Payroll Entry", "create") or "HR Manager" in frappe.get_roles(user)):
		return {"success": False, "error": "Not authorized to generate payroll"}

	from frappe.utils import get_first_day, get_last_day, getdate

	from arijentek_core.payroll.payslip_generator import generate_payroll_for_month

	today = getdate()
	year = int(year) if year else today.year
	month = int(month) if month else (today.month - 1 if today.month > 1 else 12)
	if month < 1:
		month = 12
		year -= 1

	try:
		result = generate_payroll_for_month(month=month, year=year, submit=True)
		return {
			"success": result.get("success", False),
			"payroll_entry": result.get("created_slips", []),
			"message": result.get("message", ""),
			"total_created": result.get("total_created", 0),
			"total_failed": result.get("total_failed", 0),
			"failed_employees": result.get("failed_employees", []),
		}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Payroll Generation Error")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_payslip_details(name: str):
	"""Get detailed payslip information including attendance breakdown."""
	from arijentek_core.payroll.payslip_generator import get_payslip_details as _get_payslip_details

	return _get_payslip_details(name)


@frappe.whitelist()
def get_payroll_preview(month: int | None = None, year: int | None = None):
	employee = get_current_employee()
	if not employee:
		return {"error": "Employee not found"}

	from arijentek_core.payroll.calculator import get_payroll_preview as _get_payroll_preview

	today = getdate()
	year = int(year) if year else today.year
	month = int(month) if month else (today.month - 1 if today.month > 1 else 12)
	if month < 1:
		month = 12
		year -= 1

	return _get_payroll_preview(employee, month, year)


@frappe.whitelist()
def get_payroll_dashboard():
	"""Get payroll dashboard data for the current employee."""
	employee = get_current_employee()
	if not employee:
		return {"error": "Employee not found"}

	from arijentek_core.payroll.payslip_generator import get_payroll_dashboard_data

	return get_payroll_dashboard_data(employee)


@frappe.whitelist()
@user_rate_limit(limit=5, seconds=60)
def generate_my_payslip(month: int | None = None, year: int | None = None):
	"""Generate a payslip for the current employee.

	All employees can generate their own payslips. This is a self-service feature.
	Security: Only generates for the current logged-in employee, not arbitrary employees.
	"""
	employee = get_current_employee()
	if not employee:
		return {"success": False, "error": "Employee not found"}

	# Input validation
	try:
		today = getdate()
		year = int(year) if year else today.year
		month = int(month) if month else (today.month - 1 if today.month > 1 else 12)

		# Validate month and year ranges
		if not (1 <= month <= 12):
			return {"success": False, "error": "Invalid month. Must be between 1 and 12"}

		if not (2020 <= year <= 2030):
			return {"success": False, "error": "Invalid year. Must be between 2020 and 2030"}

		# Adjust for previous month if needed
		if month < 1:
			month = 12
			year -= 1

		# Check if the selected month and year is in the future
		if year > today.year or (year == today.year and month > today.month):
			return {
				"success": False,
				"error": _("Cannot generate payslip for a future date.")
			}
	except (ValueError, TypeError) as e:
		return {"success": False, "error": f"Invalid month or year: {e!s}"}

	# Import and call the payslip generator
	from frappe.utils import get_first_day, get_last_day

	from arijentek_core.payroll.payslip_generator import PayslipGenerator

	try:
		# Get pay period dates
		start_date = get_first_day(f"{year}-{month:02d}-01")
		end_date = get_last_day(f"{year}-{month:02d}-01")

		# Check if Salary Slip already exists for this employee in the selected period
		existing_slip = frappe.db.exists(
			"Salary Slip",
			{
				"employee": employee,
				"start_date": start_date,
				"end_date": end_date,
				"docstatus": ["!=", 2],
			}
		)
		if existing_slip:
			return {
				"success": False,
				"error": _("Salary Slip already generated for the selected month and year: {0}").format(existing_slip),
			}

		# Get company
		company = frappe.db.get_value("Employee", employee, "company")
		if not company:
			company = frappe.defaults.get_user_default("company")

		# Generate payslip
		generator = PayslipGenerator(company, start_date, end_date)
		slip = generator.generate_payslip(employee, submit=True)

		if slip:
			return {
				"success": True,
				"salary_slip": slip.name,
				"gross_pay": slip.gross_pay,
				"net_pay": slip.net_pay,
				"message": _("Salary Slip created successfully"),
			}
		else:
			error_msg = (
				generator.failed_employees[0]["error"] if generator.failed_employees else "Unknown error"
			)
			return {"success": False, "error": error_msg}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), f"Payslip Generation Error - {employee}")
		return {"success": False, "error": f"Failed to generate payslip: {e!s}"}


# ============ ATTENDANCE SUMMARY & RECORDS ============


@frappe.whitelist()
def get_attendance_summary():
	"""Get attendance summary for current month"""
	employee = get_current_employee()
	if not employee:
		return {}

	today = getdate(nowdate())
	first_day = get_first_day(today)
	last_day = get_last_day(today)

	summary = frappe.db.sql(
		"""
        SELECT status, COUNT(*) as count
        FROM `tabAttendance`
        WHERE employee = %s
        AND attendance_date BETWEEN %s AND %s
        AND docstatus = 1
        GROUP BY status
    """,
		(employee, first_day, last_day),
		as_dict=True,
	)

	result = {"present": 0, "absent": 0, "half_day": 0}
	for row in summary:
		if row.status == "Present":
			result["present"] = row.count
		elif row.status == "Absent":
			result["absent"] = row.count
		elif row.status == "Half Day":
			result["half_day"] = row.count

	return result


def calculate_break_hours(logs, in_time, out_time, attendance_date, current_today_str, current_now):
	"""Calculate break hours for an employee on a specific attendance date based on check-ins."""
	from datetime import timedelta
	from frappe.utils import get_datetime

	in_datetime = get_datetime(in_time) if in_time else None
	out_datetime = get_datetime(out_time) if out_time else None

	if not in_datetime:
		return 0.0

	if not out_datetime:
		if str(attendance_date) == current_today_str:
			out_datetime = current_now
		else:
			out_datetime = in_datetime + timedelta(hours=12)

	total_break_seconds = 0
	current_break_start = None

	for log in logs:
		log_time = get_datetime(log.time)
		if log_time < in_datetime or log_time > out_datetime:
			continue

		if log.device_id == "BREAK_START":
			current_break_start = log_time
		elif log.device_id == "BREAK_END" and current_break_start:
			total_break_seconds += (log_time - current_break_start).total_seconds()
			current_break_start = None

	if current_break_start and out_datetime > current_break_start:
		total_break_seconds += (out_datetime - current_break_start).total_seconds()

	return round(total_break_seconds / 3600.0, 2)


@frappe.whitelist()
def get_attendance_records(month: int | None = None, year: int | None = None, employee_id: str | None = None):
	"""Get attendance records for a given month/year (defaults to current month).

	Returns list of records with date, status, working_hours, in_time, out_time
	plus a summary count.
	"""
	import calendar
	from arijentek_core import get_shift_approver_employees

	permitted_employees = [e["name"] for e in get_shift_approver_employees()]

	if employee_id == "all":
		if not permitted_employees:
			return {"records": [], "summary": {"Present": 0, "Absent": 0, "Half Day": 0, "On Leave": 0}}
	elif employee_id:
		if employee_id != get_current_employee() and employee_id not in permitted_employees:
			frappe.throw(_("Not permitted to view attendance records for this employee"), frappe.PermissionError)
		employee = employee_id
	else:
		employee = get_current_employee()

	today = getdate(nowdate())
	month = int(month) if month else today.month
	year = int(year) if year else today.year

	last_day = calendar.monthrange(year, month)[1]
	start_date = getdate(f"{year}-{month:02d}-01")
	end_date = getdate(f"{year}-{month:02d}-{last_day}")

	if employee_id == "all":
		records = frappe.db.sql(
			"""
			SELECT 
				a.name, a.attendance_date, a.status, a.working_hours, a.in_time, a.out_time, 
				a.employee, e.employee_name
			FROM `tabAttendance` a
			LEFT JOIN `tabEmployee` e ON a.employee = e.name
			WHERE a.employee IN ({})
				AND a.attendance_date BETWEEN %s AND %s
				AND a.docstatus = 1
			ORDER BY a.attendance_date ASC, e.employee_name ASC
			""".format(", ".join(["%s"] * len(permitted_employees))),
			(*permitted_employees, start_date, end_date),
			as_dict=True,
		)
	else:
		if not employee:
			return {"records": [], "summary": {}}
		records = frappe.db.sql(
			"""
			SELECT 
				a.name, a.attendance_date, a.status, a.working_hours, a.in_time, a.out_time, 
				a.employee, e.employee_name
			FROM `tabAttendance` a
			LEFT JOIN `tabEmployee` e ON a.employee = e.name
			WHERE a.employee = %s
				AND a.attendance_date BETWEEN %s AND %s
				AND a.docstatus = 1
			ORDER BY a.attendance_date ASC
			""",
			(employee, start_date, end_date),
			as_dict=True,
		)

	summary = {"Present": 0, "Absent": 0, "Half Day": 0, "On Leave": 0}

	# Fetch all break check-ins for these employees in this period to calculate break hours
	emp_ids = list(set(r.employee for r in records if r.employee))
	break_logs_by_employee = {}
	if emp_ids:
		from frappe.utils import add_days
		checkin_start = add_days(start_date, -1)
		checkin_end = add_days(end_date, 2)
		break_logs = frappe.db.sql(
			"""
			SELECT employee, time, device_id
			FROM `tabEmployee Checkin`
			WHERE employee IN %(employees)s
				AND device_id IN ('BREAK_START', 'BREAK_END')
				AND time BETWEEN %(start)s AND %(end)s
			ORDER BY time ASC
			""",
			{
				"employees": emp_ids,
				"start": checkin_start,
				"end": checkin_end
			},
			as_dict=True
		)
		for log in break_logs:
			if log.employee not in break_logs_by_employee:
				break_logs_by_employee[log.employee] = []
			break_logs_by_employee[log.employee].append(log)

	result_records = []
	from frappe.utils import get_datetime, now_datetime
	current_now = now_datetime()
	current_today_str = str(nowdate())

	for r in records:
		if r.status in summary:
			summary[r.status] += 1

		# Calculate break hours
		logs = break_logs_by_employee.get(r.employee, [])
		break_hours = calculate_break_hours(
			logs=logs,
			in_time=r.in_time,
			out_time=r.out_time,
			attendance_date=r.attendance_date,
			current_today_str=current_today_str,
			current_now=current_now
		)

		result_records.append(
			{
				"name": r.name,
				"date": str(r.attendance_date),
				"status": r.status,
				"working_hours": round(flt(r.working_hours), 2),
				"break_hours": break_hours,
				"in_time": str(r.in_time) if r.in_time else None,
				"out_time": str(r.out_time) if r.out_time else None,
				"employee": r.employee,
				"employee_name": r.employee_name,
			}
		)

	return {
		"records": result_records,
		"summary": summary,
		"period": {"start": str(start_date), "end": str(end_date), "month": month, "year": year},
	}


# ============ ROSTER ============


@frappe.whitelist()
def get_roster_data(month: int | None = None, year: int | None = None, employee: str | None = None):
	"""Get roster data for the current employee's department/team.

	Returns a grid of employees x dates with shift assignments,
	attendance status, holidays, and weekly offs.
	"""
	import calendar

	current_employee = get_current_employee()
	if not current_employee:
		return {"employees": [], "dates": [], "holidays": []}

	today = getdate(nowdate())
	month = int(month) if month else today.month
	year = int(year) if year else today.year

	# Check if current user is a manager (active reports) based on reports_to, leave_approver, shift_request_approver
	reports = frappe.get_all(
		"Employee",
		filters={"status": "Active"},
		or_filters={
			"shift_request_approver": frappe.session.user
		},
		pluck="name",
	)

	user_roles = frappe.get_roles(frappe.session.user)
	is_system_user = "System Manager" in user_roles

	allowed_employees = [current_employee] + reports if reports else []

	filters = {"status": "Active"}
	if employee:
		# If a specific employee filter is selected, check permission
		if is_system_user:
			filters["name"] = employee
		elif reports and employee in allowed_employees:
			filters["name"] = employee
		elif employee == current_employee:
			filters["name"] = employee
		else:
			return {"employees": [], "dates": [], "holidays": []}
	else:
		# No specific employee chosen
		if is_system_user:
			# System user has unrestricted access (defaults to showing active employees)
			pass
		elif reports:
			# Manager defaults to showing themselves and their reporting employees
			filters["name"] = ["in", allowed_employees]
		else:
			# Regular employee with restricted permissions only shows their own details
			filters["name"] = current_employee

	employees = frappe.get_all(
		"Employee",
		filters=filters,
		fields=["name", "employee_name", "designation", "default_shift", "company", "holiday_list"],
		order_by="employee_name",
		limit=50,
	)

	# Date range for the month
	last_day_num = calendar.monthrange(year, month)[1]
	start_date = getdate(f"{year}-{month:02d}-01")
	end_date = getdate(f"{year}-{month:02d}-{last_day_num}")

	# Resolve holiday list and load holidays for the logged-in employee (used for column weekends)
	logged_in_holidays = get_employee_holiday(current_employee, month, year)

	# Generate dates list using logged-in user's weekends
	dates = []
	current = start_date
	while current <= end_date:
		date_str = str(current)
		is_weekend = False
		if date_str in logged_in_holidays:
			is_weekend = logged_in_holidays[date_str].get("weekly_off", False)

		dates.append(
			{
				"date": date_str,
				"day": current.day,
				"weekday": current.strftime("%a"),
				"is_weekend": is_weekend,
			}
		)
		current = frappe.utils.add_days(current, 1)

	# Get attendance for all employees in the period
	emp_names = [e.name for e in employees]
	attendance = {}
	if emp_names:
		att_records = frappe.db.sql(
			"""
			SELECT employee, attendance_date, status, working_hours
			FROM `tabAttendance`
			WHERE employee IN %s
			AND attendance_date BETWEEN %s AND %s
			AND docstatus = 1
			""",
			(emp_names, start_date, end_date),
			as_dict=True,
		)
		for att in att_records:
			key = f"{att.employee}_{att.attendance_date}"
			attendance[key] = {
				"status": att.status,
				"hours": round(flt(att.working_hours), 1),
			}

	# Build roster grid using employee-specific holiday lists
	roster = []
	for emp in employees:
		emp_dates = []
		emp_holidays = get_employee_holiday(emp.name, month, year)

		for d in dates:
			key = f"{emp.name}_{d['date']}"
			att = attendance.get(key)
			holiday = emp_holidays.get(d["date"])

			if att:
				status = att["status"]
			elif holiday:
				status = "WO" if holiday["weekly_off"] else "H"
			else:
				status = "-"  # No details = hyphen

			emp_dates.append(
				{
					"date": d["date"],
					"status": status,
					"hours": att["hours"] if att else 0,
					"is_weekend": d["is_weekend"],
				}
			)

		roster.append(
			{
				"employee": emp.name,
				"employee_name": emp.employee_name,
				"designation": emp.designation or "",
				"shift": emp.default_shift or "General",
				"dates": emp_dates,
			}
		)

	return {
		"employees": roster,
		"dates": dates,
		"holidays": logged_in_holidays,
		"period": {"month": month, "year": year},
	}


# ============ ISSUES ============


@frappe.whitelist()
def create_issue(issue_type: str, description: str):
	employee = get_current_employee()
	if not employee:
		return {"success": False, "error": "Employee not found"}

	try:
		# Using HD Ticket (Frappe Helpdesk) or Issue
		doctype = "HD Ticket" if frappe.db.exists("DocType", "HD Ticket") else "Issue"

		doc = frappe.get_doc(
			{
				"doctype": doctype,
				"subject": f"[{issue_type}] Issue from Employee Portal",
				"description": description,
				"raised_by": frappe.session.user,
			}
		)
		doc.insert(ignore_permissions=True)
		frappe.db.commit()

		return {"success": True, "ticket": doc.name}
	except Exception as e:
		return {"success": False, "error": str(e)}


# ============ REPORTING / MANAGER ============


@frappe.whitelist()
def get_reporting_info():
	"""Get reporting manager and leave approver details for the current employee."""
	employee = get_current_employee()
	if not employee:
		return {}

	emp = frappe.get_doc("Employee", employee)
	result = {}

	if emp.reports_to:
		try:
			manager = frappe.get_doc("Employee", emp.reports_to)
			result["reporting_manager"] = {
				"name": manager.name,
				"employee_name": manager.employee_name,
				"designation": manager.designation or "",
				"department": manager.department or "",
				"user_id": manager.user_id or "",
			}
		except Exception:
			pass

	if emp.leave_approver:
		try:
			approver_emp = frappe.db.get_value(
				"Employee",
				{"user_id": emp.leave_approver},
				["name", "employee_name", "designation"],
				as_dict=True,
			)
			result["leave_approver"] = {
				"user_id": emp.leave_approver,
				"employee_name": approver_emp.employee_name if approver_emp else emp.leave_approver,
				"designation": approver_emp.designation if approver_emp else "",
			}
		except Exception:
			pass

	return result


# ============ SESSION ============


@frappe.whitelist(allow_guest=True)
def get_session_info():  # nosemgrep: guest access required for session detection on SPA load
	"""Return session information for the current user.

	Called by the Vue SPA on startup to determine:
	- Whether the user is logged in
	- Their full name, employee ID, designation, department
	- Whether they have desk access (System User)
	"""
	user = frappe.session.user

	if user == "Guest":
		return {
			"user": "Guest",
			"is_logged_in": False,
			"has_desk_access": False,
		}

	employee = get_current_employee()
	emp_data = {}
	if employee:
		emp_data = (
			frappe.db.get_value(
				"Employee",
				employee,
				["employee_name", "department", "designation"],
				as_dict=True,
			)
			or {}
		)

	user_type = frappe.db.get_value("User", user, "user_type") or ""

	has_desk_access = user_type == "System User"
	if has_desk_access:
		# Feature 3: If user ONLY has Employee and Employee Self Service roles,
		# hide the Open Desk button.
		roles = [r for r in frappe.get_roles(user) if r not in ["All", "Guest"]]
		if set(roles).issubset({"Employee", "Employee Self Service"}):
			has_desk_access = False

	has_payroll_permission = frappe.has_permission(  # nosemgrep: return value IS used in the or-expression
		"Payroll Entry", "create"
	) or "HR Manager" in frappe.get_roles(user)

	# Check if is manager (has direct reports or is leave/shift approver)
	is_manager = False
	if employee:
		has_reports = frappe.get_all(
			"Employee",
			filters={"status": "Active"},
			or_filters={
				"leave_approver": user,
				"expense_approver": user,
				"shift_request_approver": user,
			},
			limit=1,
			pluck="name",
		)
		is_manager = bool(has_reports)

	return {
		"user": user,
		"full_name": emp_data.get("employee_name") or frappe.utils.get_fullname(user),
		"is_logged_in": True,
		"has_desk_access": has_desk_access,
		"has_payroll_permission": bool(has_payroll_permission),
		"is_manager": is_manager,
		"is_system_manager": "System Manager" in frappe.get_roles(user),
		"employee": employee,
		"employee_name": emp_data.get("employee_name", ""),
		"department": emp_data.get("department", ""),
		"designation": emp_data.get("designation", ""),
	}


# ============ LEAVE ALLOCATION HELPER ============


def _ensure_leave_allocation(employee, leave_type, from_date, to_date):
	"""Create a Leave Allocation for the calendar year if none covers the dates.

	This lets employees apply for leave even if HR hasn't manually created
	allocations.  The allocation uses the Leave Type's ``max_leaves_allowed``
	(falls back to 12 days per year).
	"""
	# Already covered?
	covered = frappe.db.sql(
		"""
		SELECT name FROM `tabLeave Allocation`
		WHERE employee = %s AND leave_type = %s
		AND from_date <= %s AND to_date >= %s
		AND docstatus = 1
		LIMIT 1
		""",
		(employee, leave_type, from_date, to_date),
	)
	if covered:
		return

	year = getdate(from_date).year
	lt_doc = frappe.get_doc("Leave Type", leave_type)
	max_leaves = lt_doc.max_leaves_allowed or 12

	try:
		alloc = frappe.get_doc(
			{
				"doctype": "Leave Allocation",
				"employee": employee,
				"leave_type": leave_type,
				"from_date": f"{year}-01-01",
				"to_date": f"{year}-12-31",
				"new_leaves_allocated": max_leaves,
			}
		)
		alloc.insert(ignore_permissions=True)
		alloc.submit()
		frappe.db.commit()
	except Exception as e:
		# Might fail if an overlapping allocation already exists — that's OK,
		# the Leave Application validation will catch it with a clearer message.
		frappe.log_error(f"Leave Allocation Error: {e}", "Leave Allocation Auto-Create")
		frappe.db.rollback()


# ============ HELPERS ============


def get_current_employee():
	"""Get employee ID for current user"""
	return frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")


# ============ PAYROLL SETUP ============


@frappe.whitelist()
def setup_payroll_components():
	"""Setup default salary components for Indian payroll. Requires HR Manager role."""
	user = frappe.session.user
	if not ("HR Manager" in frappe.get_roles(user) or frappe.has_permission("Salary Component", "create")):
		return {"success": False, "error": "Not authorized to setup payroll components"}

	from arijentek_core.payroll.setup import create_default_salary_components

	try:
		result = create_default_salary_components()
		return {"success": True, **result}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Payroll Setup Error")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_payroll_setup_status():
	"""Get payroll setup status for the company."""
	from arijentek_core.payroll.setup import get_payroll_setup_status as _get_status

	return _get_status()


@frappe.whitelist()
def setup_payroll_for_company():
	"""Complete payroll setup for the company. Requires HR Manager role."""
	user = frappe.session.user
	if not ("HR Manager" in frappe.get_roles(user) or frappe.has_permission("Salary Structure", "create")):
		return {"success": False, "error": "Not authorized to setup payroll"}

	from arijentek_core.payroll.setup import setup_payroll_for_company as _setup

	try:
		result = _setup()
		return {"success": True, **result}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Payroll Setup Error")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_payroll_summary(month: int | None = None, year: int | None = None):
	"""Get payroll summary for the company. Requires HR Manager or Payroll permission."""
	user = frappe.session.user
	if not (frappe.has_permission("Salary Slip", "read") or "HR Manager" in frappe.get_roles(user)):
		return {"error": "Not authorized"}

	from arijentek_core.payroll.automation import get_payroll_summary as _get_summary

	today = getdate()
	year = int(year) if year else today.year
	month = int(month) if month else (today.month - 1 if today.month > 1 else 12)
	if month < 1:
		month = 12
		year -= 1

	return _get_summary(month=month, year=year)


# ============ MANAGER FEATURES ============


@frappe.whitelist()
def get_team_leaves(status=None, from_date=None, to_date=None, employee=None):
	"""Get pending leave applications for employees reporting to the current user with optional filters"""
	current_employee = get_current_employee()
	if not current_employee:
		return []

	user_roles = frappe.get_roles(frappe.session.user)
	if "System Manager" in user_roles or "HR Manager" in user_roles:
		reports = frappe.get_all(
			"Employee",
			filters={"status": "Active"},
			pluck="name",
		)
	else:
		# Find active employees where current user is the leave approver
		reports = frappe.get_all(
			"Employee",
			filters={"status": "Active", "leave_approver": frappe.session.user},
			pluck="name",
		)

	if not reports:
		return []

	filters = {"docstatus": ["<", 2]}

	if employee:
		if employee in reports:
			filters["employee"] = employee
		else:
			return []
	else:
		filters["employee"] = ["in", reports]

	if status:
		if status == "Draft" or status == "Open":
			filters["status"] = "Open"
			filters["docstatus"] = 0
		else:
			filters["status"] = status

	if from_date and to_date:
		filters["from_date"] = ["between", [from_date, to_date]]
	elif from_date:
		filters["from_date"] = [">=", from_date]
	elif to_date:
		filters["from_date"] = ["<=", to_date]

	apps = frappe.get_all(
		"Leave Application",
		filters=filters,
		fields=[
			"name",
			"employee",
			"employee_name",
			"leave_type",
			"from_date",
			"to_date",
			"total_leave_days",
			"description",
			"creation",
			"status",
		],
		order_by="creation desc",
	)

	return apps


@frappe.whitelist()
def process_leave(leave_application: str, status: str, rejection_reason: str | None = None):
	"""Approve or Reject a leave application.

	Bug 3 fix: Ensures leave balance is deducted on approval by properly
	submitting the Leave Application with ignore_permissions, and creates
	'On Leave' attendance records for the approved leave dates.
	"""
	if status not in ["Approved", "Rejected"]:
		return {"success": False, "error": "Invalid status"}

	employee = get_current_employee()
	if not employee:
		return {"success": False, "error": "Employee not found"}

	try:
		doc = frappe.get_doc("Leave Application", leave_application)

		# Verify permission: Current user must be the leave approver or have HR/System Manager role
		emp_approvers = frappe.db.get_value(
			"Employee",
			doc.employee,
			["leave_approver"],
			as_dict=True
		) or {}
		user_roles = frappe.get_roles()

		is_approver = (
			frappe.session.user == emp_approvers.get("leave_approver")
		)

		if not is_approver and "System Manager" not in user_roles and "HR Manager" not in user_roles:
			return {"success": False, "error": "Not authorized to process this application"}

		if doc.status != "Open":
			return {"success": False, "error": "Application is not Open"}

		if status == "Approved":
			doc.status = "Approved"
			doc.flags.ignore_permissions = True
			doc.submit()  # HRMS Leave Application submit deducts leave balance
			frappe.db.commit()

			# Create "On Leave" attendance for each leave day
			_create_on_leave_attendance(doc)

		else:
			doc.status = "Rejected"
			doc.flags.ignore_permissions = True
			doc.save(ignore_permissions=True)
			frappe.db.commit()

		# Notify Employee
		try:
			from arijentek_core.api.notifications import notify_leave_status

			notify_leave_status(doc)
		except Exception:
			pass

		return {"success": True}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Leave Process Error")
		msg = str(e)
		# Clean up error message for the user
		if ":" in msg and len(msg) > 100:
			msg = msg.split(":")[-1].strip()[:200]
		return {"success": False, "error": msg}


def _create_on_leave_attendance(leave_doc):
	"""Create 'On Leave' attendance records for each day of an approved leave.

	This ensures the attendance calendar shows leave days correctly
	and the leave count is reflected in attendance summaries.
	"""
	from frappe.utils import add_days as _add_days

	try:
		current = getdate(leave_doc.from_date)
		end = getdate(leave_doc.to_date)

		while current <= end:
			# Skip if attendance already exists
			existing = frappe.db.exists(
				"Attendance",
				{"employee": leave_doc.employee, "attendance_date": current, "docstatus": ["!=", 2]},
			)
			if not existing:
				att = frappe.new_doc("Attendance")
				att.update(
					{
						"employee": leave_doc.employee,
						"attendance_date": current,
						"status": "On Leave",
						"leave_type": leave_doc.leave_type,
					}
				)
				att.flags.ignore_permissions = True
				att.insert(ignore_permissions=True)
				att.submit()

			current = _add_days(current, 1)

		frappe.db.commit()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "On Leave Attendance Creation Error")
