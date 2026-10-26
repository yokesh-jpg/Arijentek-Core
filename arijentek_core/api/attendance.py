"""
Attendance API - Roster management and Clock In/Out functionality
"""

import datetime
from zoneinfo import ZoneInfo

import frappe
from frappe import _
from frappe.utils import (
	add_days,
	flt,
	get_first_day,
	get_last_day,
	getdate,
	now_datetime,
	nowdate,
	time_diff_in_hours,
)


def get_employee_now_datetime(employee_id=None) -> datetime.datetime:
	"""
	Return the current datetime in the employee's timezone, or fallback to system timezone.
	"""
	user_tz = None
	if employee_id:
		user_id = frappe.db.get_value("Employee", employee_id, "user_id")
		if user_id:
			user_tz = frappe.db.get_value("User", user_id, "time_zone")

	if not user_tz:
		# Fallback to current session user
		user_tz = frappe.db.get_value("User", frappe.session.user, "time_zone")

	if user_tz:
		try:
			return datetime.datetime.now(ZoneInfo(user_tz)).replace(tzinfo=None)
		except Exception:
			pass

	return now_datetime()


def calculate_hours(start_time, end_time):
	"""
	Calculate hours between two datetime/timedelta values.

	Returns 0 if either value is None.
	"""
	if not start_time or not end_time:
		return 0
	diff = end_time - start_time
	total_seconds = diff.total_seconds()
	return round(max(0.0, total_seconds / 3600), 2)


def calculate_completed_shift_hours(logs):
	"""
	Calculate total hours from the day's first clock-in to the last clock-out,
	subtracting any break durations.

	Does NOT include ongoing session time — only completed pairs count.

	Args:
	    logs: list of check-in logs for today, ordered by time asc

	Returns:
	    tuple (total_hours, total_seconds)
	"""
	first_in_time = None
	last_out_time = None

	for log in logs:
		if log.log_type == "IN" and first_in_time is None:
			first_in_time = log.time

	for log in reversed(logs):
		if log.log_type == "OUT":
			last_out_time = log.time
			break

	if first_in_time and last_out_time and last_out_time >= first_in_time:
		total_span_seconds = max(0, int((last_out_time - first_in_time).total_seconds()))

		# Calculate total break duration
		break_seconds = 0
		break_start_time = None
		for log in logs:
			note = _extract_log_note(log)
			if log.log_type == "OUT" and note == "Break Start":
				break_start_time = log.time
			elif log.log_type == "IN" and note == "Break End" and break_start_time is not None:
				effective_break_end = min(log.time, last_out_time)
				if effective_break_end > break_start_time:
					break_seconds += max(0, int((effective_break_end - break_start_time).total_seconds()))
				break_start_time = None

		# Subtract breaks from total span
		net_seconds = max(0, total_span_seconds - break_seconds)
		net_hours = round(net_seconds / 3600.0, 2)
		return net_hours, net_seconds

	return 0.0, 0



def _get_default_working_hours(employment_type: str | None) -> int:
	"""Return default shift length based on employment type."""
	employment_type = (employment_type or "").lower()
	if "part" in employment_type:
		return 4
	return 8


def _normalize_break_note(note: str | None) -> str | None:
	"""Normalize supported break marker values."""
	normalized = (note or "").strip().lower()
	if normalized == "break start":
		return "Break Start"
	if normalized == "break end":
		return "Break End"
	return None


def _build_device_id(note: str | None = None) -> str:
	"""Store portal break markers on device_id since Employee Checkin has no note field."""
	break_note = _normalize_break_note(note)
	if break_note:
		return f"HRMS Portal - {break_note}"
	return "HRMS Portal"


def _extract_log_note(log) -> str | None:
	"""Derive a synthetic note from available Employee Checkin fields."""
	if not log:
		return None

	device_id = str(getattr(log, "device_id", None) or log.get("device_id") or "")
	device_id_lower = device_id.lower()
	if "break start" in device_id_lower:
		return "Break Start"
	if "break end" in device_id_lower:
		return "Break End"
	return None


def _is_break_start_log(log) -> bool:
	"""Return True when a log marks the start of a break."""
	return bool(log and log.log_type == "OUT" and _extract_log_note(log) == "Break Start")


def _is_recent_duplicate(log_time, employee_id=None, threshold_seconds: int = 5) -> bool:
	"""Treat repeat submissions within a few seconds as duplicate actions."""
	if not log_time:
		return False
	current_time = get_employee_now_datetime(employee_id)
	return abs((current_time - log_time).total_seconds()) <= threshold_seconds


@frappe.whitelist()
def is_auto_attendance_disabled() -> bool:
	"""
	Check whether automatic attendance creation is disabled in HR Settings.
	"""
	try:
		return bool(frappe.utils.cint(frappe.db.get_single_value("HR Settings", "disable_auto_attendance")))
	except Exception:
		return False


def _mark_breaks_for_date(sorted_checkins):
	"""
	Mark checkins between first IN and last OUT as Break.

	For a single day's checkins already sorted by time ascending:
	- Find the first IN and last OUT.
	- Any checkin strictly between those two indices gets log_type set to "Break".

	Returns the list (mutated in place).
	"""
	first_in_idx = None
	last_out_idx = None
	for i, ln in enumerate(sorted_checkins):
		if ln.log_type == "IN" and first_in_idx is None:
			first_in_idx = i
		if ln.log_type == "OUT":
			last_out_idx = i

	if first_in_idx is None or last_out_idx is None or first_in_idx > last_out_idx:
		return sorted_checkins

	for i, ln in enumerate(sorted_checkins):
		if i > first_in_idx and i < last_out_idx:
			ln.log_type = "Break"
			ln.break_label = "Break"

	return sorted_checkins


def get_today_shifts(employee_id, for_date=None):
	if not for_date:
		for_date = get_employee_now_datetime(employee_id).date()
	# Check for active shift assignments
	assignments = frappe.get_all(
		"Shift Assignment",
		filters={
			"employee": employee_id,
			"docstatus": 1,
			"status": "Active",
			"start_date": ("<=", for_date),
		},
		fields=["shift_type", "end_date"],
	)

	active_assignments = []
	for a in assignments:
		if not a.end_date or getdate(a.end_date) >= getdate(for_date):
			active_assignments.append(a)

	if not active_assignments:
		return []

	# Load shift types and sort by start_time
	shift_types = []
	for a in active_assignments:
		st = frappe.get_cached_value("Shift Type", a.shift_type, ["name", "start_time", "end_time"], as_dict=True)
		if st:
			shift_types.append(st)

	shift_types.sort(key=lambda x: x.start_time)
	return shift_types


@frappe.whitelist()
def get_employee_roster(employee_id: str | None = None):
	"""
	Get employee's roster/shift configuration.

	Args:
	    employee_id: Employee ID (optional, defaults to current user's employee)

	Returns:
	    Dict with roster configuration including working hours
	"""
	if not employee_id:
		employee_id = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")

	if not employee_id:
		frappe.throw(_("No employee record found for current user"))

	today = get_employee_now_datetime(employee_id).date()
	employment_type = frappe.db.get_value("Employee", employee_id, "employment_type") or "Full-time"

	# Get today's shifts ordered by start time
	shifts = get_today_shifts(employee_id, today)
	if shifts:
		# Query today's checkins to see if any is currently active (checked in)
		logs = frappe.get_all(
			"Employee Checkin",
			filters={"employee": employee_id, "time": [">=", today]},
			fields=["log_type", "shift"],
			order_by="time asc",
		)
		active_shift_name = None
		if logs:
			last_log = logs[-1]
			if last_log.log_type == "IN":
				active_shift_name = last_log.shift

		active_shift = None
		if active_shift_name:
			for s in shifts:
				if s.name == active_shift_name:
					active_shift = s
					break
		if not active_shift:
			# Find the first shift that doesn't have an OUT log
			completed_shifts = {l.shift for l in logs if l.log_type == "OUT"}
			for s in shifts:
				if s.name not in completed_shifts:
					active_shift = s
					break
		if not active_shift:
			active_shift = shifts[-1]

		return {
			"has_roster": True,
			"employment_type": employment_type,
			"shift_type": active_shift.name,
			"shift_name": active_shift.name,
			"start_time": str(active_shift.start_time) if active_shift.start_time else None,
			"end_time": str(active_shift.end_time) if active_shift.end_time else None,
			"working_hours": calculate_hours(active_shift.start_time, active_shift.end_time) or 8,
		}

	# No shift assignment - check employment type for default hours
	default_hours = _get_default_working_hours(employment_type)

	return {
		"has_roster": False,
		"employment_type": employment_type,
		"working_hours": default_hours,
		"shift_type": None,
		"shift_name": "Standard Hours",
		"start_time": "09:00:00",
		"end_time": "17:00:00" if default_hours == 8 else "13:00:00",
	}


@frappe.whitelist()
def get_current_employee():
	"""
	Get the current user's employee record.

	Returns:
	    Employee basic info or None
	"""
	employee = frappe.db.get_value(
		"Employee",
		{"user_id": frappe.session.user, "status": "Active"},
		["name", "employee_name", "employment_type", "department", "designation", "company", "image"],
		as_dict=True,
	)

	if not employee:
		return None

	# Get roster info
	roster = get_employee_roster(employee.name)
	employee.roster = roster

	# Get today's check-in status
	today_checkin = get_today_checkin_status(employee.name)
	employee.today_checkin = today_checkin

	# Check if current user may load the Frappe Desk — the desk tier only
	# (services.permissions.DESK_ROLES); plain System Manager / HR Manager
	# holders are SPA-only and must not see a dead "Desk" link in the portal.
	from arijentek_core.services.permissions import DESK_ROLES

	user = frappe.session.user
	roles = frappe.get_roles(user)
	employee["has_desk_access"] = user == "Administrator" or bool(set(roles) & DESK_ROLES)

	return employee


def _link_missing_out_shifts(employee_id, for_date):
	"""
	Heals shift-less OUT check-in logs by attributing them to the shift of the preceding IN log.
	"""
	logs = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": employee_id,
			"time": ["Between", [f"{for_date} 00:00:00", f"{for_date} 23:59:59"]],
		},
		fields=["name", "log_type", "shift"],
		order_by="time asc",
	)

	current_shift = None
	for log in logs:
		if log.log_type == "IN":
			if log.shift:
				current_shift = log.shift
		elif log.log_type == "OUT":
			if not log.shift and current_shift:
				frappe.db.set_value("Employee Checkin", log.name, "shift", current_shift, update_modified=False)
				log.shift = current_shift
			current_shift = None


@frappe.whitelist()
def get_today_checkin_status(employee_id: str | None = None, skip_roster: bool = False, for_date: str | None = None):
	"""
	Get today's check-in status for an employee.

	Args:
	    employee_id: Employee ID (optional, defaults to current user)
	    skip_roster: Skip roster lookup for faster response
	    for_date: Target date to check status for (optional, defaults to today)

	Returns:
	    Dict with check-in status and logs
	"""
	if not employee_id:
		employee_id = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")

	if not employee_id:
		return {"checked_in": False, "logs": []}

	today = getdate(for_date) if for_date else get_employee_now_datetime(employee_id).date()
	_link_missing_out_shifts(employee_id, today)

	# Fetch absolute latest log to check if they are currently clocked in (active session)
	last_db_log = frappe.db.get_value(
		"Employee Checkin",
		{"employee": employee_id},
		["name", "log_type", "time", "latitude", "longitude", "device_id", "shift"],
		order_by="time desc",
		as_dict=True
	)

	start_date = today
	if last_db_log and last_db_log.log_type == "IN" and last_db_log.time:
		# If they clocked in yesterday (up to 24h ago) and haven't clocked out, start query from the check-in date
		last_checkin_date = last_db_log.time.date()
		if last_checkin_date < today and (get_employee_now_datetime(employee_id) - last_db_log.time).total_seconds() < 86400:
			# But only if attendance has not already been submitted for that date
			if not frappe.db.exists("Attendance", {"employee": employee_id, "attendance_date": last_checkin_date, "docstatus": ("!=", 2)}):
				start_date = last_checkin_date

	# Get check-in logs starting from start_date
	logs = frappe.get_all(
		"Employee Checkin",
		filters={"employee": employee_id, "time": [">=", start_date]},
		fields=["name", "log_type", "time", "latitude", "longitude", "device_id", "shift"],
		order_by="time asc",
	)

	# Fallback to single/standard shift logic
	checked_in = False
	last_log = None
	if logs:
		last_log = logs[-1]
		checked_in = last_log.log_type == "IN"

	total_hours, total_seconds = calculate_completed_shift_hours(logs)

	current_session_seconds = 0
	if checked_in and last_log:
		current_session_seconds = max(0, int((get_employee_now_datetime(employee_id) - last_log.time).total_seconds()))

	working_hours_target = 8
	overtime = 0
	active_shift_name = None
	if not skip_roster:
		roster = get_employee_roster(employee_id)
		working_hours_target = roster.get("working_hours", 8)
		overtime = max(0, total_hours - working_hours_target)
		active_shift_name = roster.get("shift_type")
	else:
		overtime = max(0, total_hours - working_hours_target)

	is_on_break = _is_break_start_log(last_log)

	current_break_seconds = 0
	if is_on_break and last_log:
		current_break_seconds = max(0, int((get_employee_now_datetime(employee_id) - last_log.time).total_seconds()))

	return {
		"checked_in": checked_in,
		"is_on_break": is_on_break,
		"is_still_checked_in": checked_in,
		"is_overnight_shift": False,
		"last_log_type": last_log.log_type if last_log else None,
		"last_log_time": str(last_log.time) if last_log else None,
		"last_log_note": _extract_log_note(last_log),
		"total_hours_today": round(total_hours, 2),
		"total_seconds_today": total_seconds + current_session_seconds,
		"current_session_seconds": current_session_seconds,
		"current_break_seconds": current_break_seconds,
		"overtime_hours": round(overtime, 2),
		"working_hours_target": working_hours_target,
		"logs": [
			{
				"log_type": l.log_type,
				"time": str(l.time),
				"device_id": l.device_id,
				"note": _extract_log_note(l),
			}
			for l in logs
		],
		"shifts": [],
		"active_shift_name": active_shift_name,
	}


def _get_active_timesheet(employee_id: str, for_date=None) -> "str | None":
	"""
	Return the name of today's open (draft) Timesheet for the employee.
	Returns None if no active timesheet exists.
	"""
	if not for_date:
		for_date = get_employee_now_datetime(employee_id).date()
	return frappe.db.get_value(
		"Timesheet",
		{
			"employee": employee_id,
			"start_date": for_date,
			"docstatus": 0,
		},
		"name",
	)


def create_timesheet(employee_id: str, start_time) -> str:
	"""
	Create a new draft Timesheet with an initial open time-log row.

	The first row uses activity_type='Attendance', from_time=start_time, and
	leaves to_time blank to indicate the session is still active.

	Args:
	    employee_id: Employee name/ID
	    start_time:  datetime – the clock-in time (from_time of the first row)

	Returns:
	    Name of the created Timesheet document.

	Raises:
	    frappe.ValidationError: if a draft Timesheet already exists for the day.
	"""
	for_date = start_time.date() if hasattr(start_time, "date") else getdate(start_time)

	# Guard: prevent duplicate open timesheets for the same day
	existing = _get_active_timesheet(employee_id, for_date)
	if existing:
		frappe.throw(
			_(
				"A Timesheet ({0}) is already open for today. "
				"Please contact HR."
			).format(existing),
			frappe.ValidationError,
		)

	company = frappe.db.get_value("Employee", employee_id, "company")
	ts = frappe.get_doc(
		{
			"doctype": "Timesheet",
			"employee": employee_id,
			"company": company,
			"start_date": for_date,
			"time_logs": [
				{
					"activity_type": "Attendance",
					"from_time": start_time,
					"to_time": None,
					"hours": 0,
					"completed": 0,
				}
			],
		}
	)
	ts.insert(ignore_permissions=True)
	frappe.db.commit()
	return ts.name


def start_timesheet_log(timesheet_name: str, start_time) -> None:
	"""
	Append a new open time-log row to an existing draft Timesheet.

	Called after a break ends to resume tracking time in the same Timesheet
	document for the day.

	Args:
	    timesheet_name: Name of the Timesheet to append to
	    start_time:     datetime – the break-end / resume time
	"""
	ts = frappe.get_doc("Timesheet", timesheet_name)
	ts.append(
		"time_logs",
		{
			"activity_type": "Attendance",
			"from_time": start_time,
			"to_time": None,
			"hours": 0,
			"completed": 0,
		},
	)
	ts.save(ignore_permissions=True)
	frappe.db.commit()


def end_timesheet_log(timesheet_name: str, end_time, submit: bool = False) -> None:
	"""
	Close the latest open time-log row on an existing Timesheet.

	Hours are rounded to 2 decimal places so short sessions (e.g. 15 min)
	are recorded as 0.25 hrs.

	Args:
	    timesheet_name: Timesheet to update
	    end_time:       datetime – the stop / break-start time
	    submit:         If True, submit the Timesheet (docstatus→1) after saving.
	                    Pass True only on final Clock Out.

	Raises:
	    frappe.ValidationError: if no open row is found in the Timesheet.
	"""
	ts = frappe.get_doc("Timesheet", timesheet_name)

	# Find the last row that has no to_time (the currently active row)
	open_row = None
	for row in reversed(ts.time_logs):
		if not row.to_time:
			open_row = row
			break

	if not open_row:
		frappe.throw(
			_(
				"No open time-log row found in Timesheet {0}. "
				"Please contact HR."
			).format(timesheet_name),
			frappe.ValidationError,
		)

	open_row.to_time = end_time
	diff_seconds = max(0, (end_time - open_row.from_time).total_seconds())
	open_row.hours = round(diff_seconds / 3600, 2)

	ts.save(ignore_permissions=True)
	if submit:
		ts.submit()  # docstatus → 1

	frappe.db.commit()


@frappe.whitelist()
def clock_in(latitude: float | None = None, longitude: float | None = None, notes: str | None = None, shift: str | None = None):
	"""
	Record employee check-in with location.

	Args:
	    latitude: GPS latitude (optional)
	    longitude: GPS longitude (optional)
	    notes: Additional notes (optional)
	    shift: Explicit shift type name (optional)

	Returns:
	    Dict with success status and check-in details
	"""
	employee_id = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")

	if not employee_id:
		return {"success": False, "message": _("No employee record found for current user")}

	# Check last log status
	last_log = frappe.db.get_value(
		"Employee Checkin",
		{"employee": employee_id},
		["name", "log_type", "time"],
		order_by="time desc",
		as_dict=True,
	)

	if last_log and last_log.log_type == "IN":
		# Check if it's from today
		today = get_employee_now_datetime(employee_id).date()
		if getdate(last_log.time) == today:
			if _is_recent_duplicate(last_log.time, employee_id):
				status = get_today_checkin_status(employee_id)
				return {
					"success": True,
					"checkin_id": last_log.name,
					"time": str(last_log.time),
					"message": _("Already checked in."),
					"status": status,
				}
			return {"success": False, "message": _("Already checked in today. Please check out first.")}

	if not shift:
		roster = get_employee_roster(employee_id)
		if roster.get("has_roster"):
			shift = roster.get("shift_type") or roster.get("shift_name")

	# Create check-in record
	is_break = notes and "Break" in notes
	try:
		checkin = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": employee_id,
				"log_type": "IN",
				"time": get_employee_now_datetime(employee_id),
				"device_id": _build_device_id(notes),
				"latitude": latitude,
				"longitude": longitude,
				"skip_auto_attendance": 1 if (is_break or is_auto_attendance_disabled()) else 0,
			}
		)
		checkin.insert(ignore_permissions=True)

		if shift:
			checkin.db_set("shift", shift)
			checkin.shift = shift

		# Timesheet Integration
		try:
			timesheet_enabled = frappe.utils.cint(frappe.db.get_single_value("HR Settings", "timesheet_with_clockin"))
		except Exception:
			timesheet_enabled = 0

		if timesheet_enabled:
			is_break_end = notes == "Break End"
			if is_break_end:
				timesheet_name = _get_active_timesheet(employee_id, checkin.time.date())
				if timesheet_name:
					start_timesheet_log(timesheet_name, checkin.time)
				else:
					create_timesheet(employee_id, checkin.time)
			elif not is_break:
				create_timesheet(employee_id, checkin.time)

		# Auto-generate Attendance record on Clock In if "Make Present while Clock Out" is disabled
		is_break = notes and "Break" in notes
		if not is_break and not is_auto_attendance_disabled():
			try:
				mark_present = frappe.utils.cint(
					frappe.db.get_single_value("HR Settings", "mark_present_on_clock_out")
				)
			except Exception:
				mark_present = 0

			if not mark_present:
				_process_auto_attendance(employee_id)
			else:
				today_date = checkin.time.date()
				existing_att = frappe.db.get_value(
					"Attendance",
					{"employee": employee_id, "attendance_date": today_date, "docstatus": ("!=", 2)},
					["name", "status", "in_time"],
					as_dict=True,
				)
				if existing_att:
					updates = {"in_time": checkin.time, "out_time": None}
					if existing_att.status == "On Leave":
						updates["status"] = "Present"
					frappe.db.set_value("Attendance", existing_att.name, updates, update_modified=True)
					frappe.db.commit()

		# Return full status so the portal timer can stay accurate after clock actions.
		status = get_today_checkin_status(employee_id)

		return {
			"success": True,
			"checkin_id": checkin.name,
			"time": str(checkin.time),
			"message": _("Checked in successfully at {0}").format(checkin.time.strftime("%H:%M")),
			"status": status,
		}
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error("HRMS Clock-in Failed", frappe.get_traceback())
		return {"success": False, "message": _("Failed to clock in: {0}").format(str(e))}


@frappe.whitelist()
def clock_out(latitude: float | None = None, longitude: float | None = None, notes: str | None = None, shift: str | None = None):
	"""
	Record employee check-out and calculate hours.

	Args:
	    latitude: GPS latitude (optional)
	    longitude: GPS longitude (optional)
	    notes: Additional notes (optional)
	    shift: Explicit shift type name (optional)

	Returns:
	    Dict with success status, check-out details, and hours worked
	"""
	employee_id = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")

	if not employee_id:
		return {"success": False, "message": _("No employee record found for current user")}

	# Check last log status
	last_log = frappe.db.get_value(
		"Employee Checkin",
		{"employee": employee_id},
		["log_type", "time", "name"],
		order_by="time desc",
		as_dict=True,
	)

	if not last_log or last_log.log_type == "OUT":
		if last_log and last_log.log_type == "OUT" and _is_recent_duplicate(last_log.time, employee_id):
			status = get_today_checkin_status(employee_id)
			return {
				"success": True,
				"checkout_id": last_log.name,
				"time": str(last_log.time),
				"hours_this_session": 0,
				"message": _("Already checked out."),
				"status": status,
			}
		return {"success": False, "message": _("No active check-in found. Please check in first.")}

	is_break = notes and "Break" in notes

	# Mis-punch guard: an OUT within a minute of the IN is nearly always a
	# double-tap (the portal's clock widget confirms under-a-minute check-outs;
	# the server rejects them outright). Uses the same tz-aware comparison as
	# _is_recent_duplicate. Break start actions are exempt.
	if last_log.log_type == "IN" and not is_break:
		elapsed_since_in = (get_employee_now_datetime(employee_id) - last_log.time).total_seconds()
		if 0 <= elapsed_since_in < 60:
			return {
				"success": False,
				"message": _("Checked out {0}s after check-in. Mis-punch guard: please wait a minute and try again.").format(
					int(elapsed_since_in)
				),
			}
	try:
		checkout = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": employee_id,
				"log_type": "OUT",
				"time": get_employee_now_datetime(employee_id),
				"device_id": _build_device_id(notes),
				"latitude": latitude,
				"longitude": longitude,
				"skip_auto_attendance": 1 if (is_break or is_auto_attendance_disabled()) else 0,
			}
		)
		checkout.insert(ignore_permissions=True)

		if shift:
			checkout.db_set("shift", shift)
			checkout.shift = shift

		# Timesheet Integration
		try:
			timesheet_enabled = frappe.utils.cint(frappe.db.get_single_value("HR Settings", "timesheet_with_clockin"))
		except Exception:
			timesheet_enabled = 0

		if timesheet_enabled:
			is_break_start = notes == "Break Start"
			timesheet_name = _get_active_timesheet(employee_id, checkout.time.date())
			if timesheet_name:
				if is_break_start:
					end_timesheet_log(timesheet_name, checkout.time, submit=False)
				elif not is_break:
					end_timesheet_log(timesheet_name, checkout.time, submit=True)

		# Calculate hours for this session
		hours_worked = time_diff_in_hours(checkout.time, last_log.time)

		# Auto-generate or update Attendance record on Clock Out to set out_time and working_hours
		is_break = notes and "Break" in notes
		if not is_break and not is_auto_attendance_disabled():
			_process_auto_attendance(employee_id)

		# Return full status so the portal timer can stay accurate after clock actions.
		status = get_today_checkin_status(employee_id)

		return {
			"success": True,
			"checkout_id": checkout.name,
			"time": str(checkout.time),
			"hours_this_session": round(hours_worked, 2),
			"message": _("Checked out successfully. Hours this session: {0}").format(round(hours_worked, 2)),
			"status": status,
		}
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error("HRMS Clock-out Failed", frappe.get_traceback())
		return {"success": False, "message": _("Failed to clock out: {0}").format(str(e))}

def calculate_late_early(employee_id, for_date, first_in_time, last_out_time):
	"""
	Calculate whether the employee was late or left early based on their shift.
	Returns (late_entry, early_exit) as 1 or 0.
	"""
	late_entry = 0
	early_exit = 0

	shifts = get_today_shifts(employee_id, for_date)
	if not shifts:
		return 0, 0

	try:
		# Get full shift details including grace periods
		shift = frappe.get_cached_value("Shift Type", shifts[0].name,
			["start_time", "end_time", "late_entry_grace_period", "early_exit_grace_period"], as_dict=True)

		if not shift:
			return 0, 0

		# first_in_time and last_out_time are datetime objects
		# shift.start_time and shift.end_time are timedeltas
		if first_in_time and shift.start_time:
			in_time_delta = datetime.timedelta(hours=first_in_time.hour, minutes=first_in_time.minute, seconds=first_in_time.second)
			grace = datetime.timedelta(minutes=shift.get("late_entry_grace_period") or 0)
			if in_time_delta > (shift.start_time + grace):
				late_entry = 1

		if last_out_time and shift.end_time:
			out_time_delta = datetime.timedelta(hours=last_out_time.hour, minutes=last_out_time.minute, seconds=last_out_time.second)
			grace = datetime.timedelta(minutes=shift.get("early_exit_grace_period") or 0)
			if out_time_delta < (shift.end_time - grace):
				early_exit = 1
	except Exception:
		frappe.log_error("calculate_late_early failed", frappe.get_traceback())

	return late_entry, early_exit



def _process_auto_attendance(employee_id, for_date=None):
	"""
	Process check-in logs and create/update Attendance records, supporting multiple shifts and overnight work.
	"""
	if is_auto_attendance_disabled():
		return
	if not for_date:
		# Called during Clock Out. Isolate current shift by walking BACKWARDS from latest log.
		recent_logs = frappe.get_all(
			"Employee Checkin",
			filters={"employee": employee_id},
			fields=["name", "log_type", "time", "device_id"],
			order_by="time desc",
			limit=30,
		)

		if not recent_logs:
			return

		shift_logs_reversed = []
		for log in recent_logs:
			shift_logs_reversed.append(log)
			# Stop as soon as we hit the shift's initial clock-in log
			if log.log_type == "IN" and _extract_log_note(log) != "Break End":
				break

		logs = list(reversed(shift_logs_reversed))
		if not logs:
			return

		# Determine attendance date from the shift's initial clock-in time
		first_in_log = next((l for l in logs if l.log_type == "IN"), None)
		if not first_in_log:
			return
		for_date = first_in_log.time.date()

	else:
		# Called for a specific date (e.g. historical re-processing or admin trigger)
		for_date = getdate(for_date)
		_link_missing_out_shifts(employee_id, for_date)

		# Fetch logs starting from for_date 00:00:00 up to for_date + 1 day 23:59:59
		start_dt = f"{for_date} 00:00:00"
		end_dt = f"{add_days(for_date, 1)} 23:59:59"

		all_logs = frappe.get_all(
			"Employee Checkin",
			filters={
				"employee": employee_id,
				"time": ["Between", [start_dt, end_dt]],
			},
			fields=["name", "log_type", "time", "device_id"],
			order_by="time asc",
		)

		if not all_logs:
			return

		# Find the first IN on for_date
		start_idx = None
		for i, l in enumerate(all_logs):
			if l.log_type == "IN" and l.time.date() == for_date:
				start_idx = i
				break

		if start_idx is None:
			return

		shift_logs = []
		for l in all_logs[start_idx:]:
			shift_logs.append(l)
			if l.log_type == "OUT" and _extract_log_note(l) != "Break Start":
				break

		logs = shift_logs

	if not logs:
		return

	# Find today's first clock-in time
	first_in_time = None
	for log in logs:
		if log.log_type == "IN":
			first_in_time = log.time
			break

	# Find today's last clock-out time (which is the check-out currently being created)
	last_out_time = None
	for log in reversed(logs):
		if log.log_type == "OUT":
			last_out_time = log.time
			break

	if not first_in_time:
		return

	if last_out_time and last_out_time < first_in_time:
		return

	total_working_hours = 0.0
	if last_out_time:
		# Calculate total span (hours employee spent in company)
		total_span_seconds = max(0, int((last_out_time - first_in_time).total_seconds()))

		# Calculate total break duration (all break start to break end pairs)
		break_seconds = 0
		break_start_time = None
		for log in logs:
			note = _extract_log_note(log)
			if log.log_type == "OUT" and note == "Break Start":
				break_start_time = log.time
			elif log.log_type == "IN" and note == "Break End" and break_start_time is not None:
				effective_break_end = min(log.time, last_out_time)
				if effective_break_end > break_start_time:
					break_seconds += max(0, int((effective_break_end - break_start_time).total_seconds()))
				break_start_time = None

		# Total working hours = total span - break duration
		net_seconds = max(0, total_span_seconds - break_seconds)
		total_working_hours = round(net_seconds / 3600.0, 2)

	# Determine shift type
	shifts = get_today_shifts(employee_id, for_date)
	shift_type = None
	if shifts:
		shift_type = shifts[0].name
	else:
		roster = get_employee_roster(employee_id)
		shift_type = roster.get("shift_type")

	# Attendance status is directly Present for clocked employee (no absent status)
	status = "Present"

	existing = frappe.db.get_value(
		"Attendance",
		{"employee": employee_id, "attendance_date": for_date, "docstatus": ("!=", 2)},
		["name", "status", "working_hours", "docstatus", "shift", "in_time", "out_time"],
		as_dict=True,
	)

	late_entry = 0
	early_exit = 0
	if shifts:
		late_entry, early_exit = calculate_late_early(employee_id, for_date, first_in_time, last_out_time)

	if existing:
		# Update if there's any difference in status, working hours, shift, in_time, or out_time
		if (
			existing.status != status
			or (last_out_time and round(flt(existing.working_hours), 2) != round(flt(total_working_hours), 2))
			or (shift_type and existing.shift != shift_type)
			or existing.in_time != first_in_time
			or (last_out_time and existing.out_time != last_out_time)
			or (not last_out_time and existing.out_time is not None)
		):
			try:
				update_values = {
					"status": status,
					"in_time": first_in_time,
					"late_entry": late_entry,
				}
				if last_out_time:
					update_values["working_hours"] = round(total_working_hours, 2)
					update_values["out_time"] = last_out_time
					update_values["early_exit"] = early_exit
				else:
					update_values["out_time"] = None
				if shift_type:
					update_values["shift"] = shift_type

				frappe.db.set_value("Attendance", existing.name, update_values, update_modified=True)
				frappe.db.commit()
			except Exception:
				frappe.log_error("Failed to update existing attendance during auto-attendance update", frappe.get_traceback())
		return

	try:
		doc_values = {
			"doctype": "Attendance",
			"employee": employee_id,
			"attendance_date": for_date,
			"status": status,
			"working_hours": round(total_working_hours, 2) if last_out_time else 0.0,
			"in_time": first_in_time,
			"late_entry": late_entry,
		}
		if last_out_time:
			doc_values["out_time"] = last_out_time
			doc_values["early_exit"] = early_exit
		if shift_type:
			doc_values["shift"] = shift_type

		attendance_doc = frappe.get_doc(doc_values)
		attendance_doc.insert(ignore_permissions=True)
		attendance_doc.submit()
		frappe.db.commit()
	except Exception:
		frappe.log_error("Auto-Attendance Creation Failed", frappe.get_traceback())


def _build_attendance_records(records):
	"""Convert raw Attendance rows to the API response shape, applying the
	lazy On Leave + in_time -> Present fix and looking up employee names.
	Returns (records, summary)."""
	summary = {"Present": 0, "Absent": 0, "Half Day": 0, "On Leave": 0}
	result_records = []
	for r in records:
		rec_status = r.status
		if r.in_time and rec_status == "On Leave":
			rec_status = "Present"
			try:
				frappe.db.set_value("Attendance", r.name, "status", "Present", update_modified=True)
				frappe.db.commit()
			except Exception:
				pass

		if rec_status in summary:
			summary[rec_status] += 1
		employee_name = ""
		if r.employee:
			employee_name = frappe.db.get_value("Employee", r.employee, "employee_name")
		result_records.append(
			{
				"name": r.name,
				"date": str(r.attendance_date),
				"status": rec_status,
				"working_hours": round(flt(r.working_hours), 2),
				"in_time": str(r.in_time) if r.in_time else None,
				"out_time": str(r.out_time) if r.out_time else None,
				"employee": r.employee or "",
				"employee_name": employee_name or "",
			}
		)
	return result_records, summary


@frappe.whitelist()
def get_attendance_history(employee_id: str | None = None, month=None, year=None, days: int = 30, status: str | None = None, start_date: str | None = None, end_date: str | None = None, override_employee_id: str | None = None, page: int = 1, page_size: int = 0):
	"""
	Get attendance history for an employee from the Attendance table.

	Args:
	    employee_id: Employee ID (optional, defaults to current user)
	    month: Month number (optional, defaults to current month if year also provided)
	    year: Year number (optional, defaults to current year if month also provided)
	    days: Number of days to look back (default 30, used if month/year not provided)
	    status: Filter by attendance status (Present, Absent, Half Day, On Leave, Weekend)
	    start_date: Filter start date (YYYY-MM-DD format)
	    end_date: Filter end date (YYYY-MM-DD format)
	    override_employee_id: Employee ID to filter by (optional, for admin view).
	        If empty, returns attendance for ALL employees.
	    page: Page number (1-based; used when page_size > 0).
	    page_size: Rows per page (0 = no limit / legacy, returns all records).

	Returns:
	    When page_size == 0 (legacy): Dict with 'records' list
	    (date, status, working_hours, in_time, out_time, employee, employee_name)
	    and a 'summary' count by status (for single-employee view).
	    When page_size > 0: Dict with 'data' (the page), 'total', 'page',
	    'page_size', and 'summary' (count by status over the full filtered set).
	"""
	if not employee_id:
		employee_id = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")

	# Determine date range based on month/year or days fallback
	if month and year:
		requested_date = getdate(f"{year}-{month}-01")
		start_date = get_first_day(requested_date)
		end_date = get_last_day(requested_date)
	elif start_date and end_date:
		start_date = getdate(start_date)
		end_date = getdate(end_date)
	else:
		# No date filter — return all records (All Time)
		start_date = None
		end_date = None

	# Decide whether to query all employees or a single one
	filters = ["docstatus = 1"]
	params = []

	# Enforce permission check
	from arijentek_core.api.roster import get_employee_list
	permitted_employees = [e["name"] for e in get_employee_list()]

	if override_employee_id or override_employee_id == "":
		if override_employee_id == "":
			if not is_global_attendance_manager():
				if permitted_employees:
					filters.append("employee IN ({})".format(", ".join(["%s"] * len(permitted_employees))))
					params.extend(permitted_employees)
				else:
					return {"records": [], "summary": {"Present": 0, "Absent": 0, "Half Day": 0, "On Leave": 0}}
		else:
			if override_employee_id not in permitted_employees:
				frappe.throw(_("Not permitted to view attendance for this employee"), frappe.PermissionError)
			filters.append("employee = %s")
			params.append(override_employee_id)
	else:
		# override_employee_id is None: if employee_id is specified (e.g. self dashboard query)
		if employee_id not in permitted_employees:
			frappe.throw(_("Not permitted to view attendance for this employee"), frappe.PermissionError)
		filters.append("employee = %s")
		params.append(employee_id)

	if start_date and end_date:
		filters.append("attendance_date BETWEEN %s AND %s")
		params.extend([start_date, end_date])

	if status and status not in ["All", ""]:
		filters.append("status = %s")
		params.append(status)

	where_clause = " AND ".join(filters)

	# Server-side paging: page_size > 0. The total and the summary come from
	# the full filtered set (COUNT and GROUP BY), so they are not affected
	# by which page is being returned.
	if page_size > 0:
		total = frappe.db.sql(
			"SELECT COUNT(*) AS count FROM `tabAttendance` WHERE {}".format(where_clause),
			params,
			as_dict=True,
		)[0].count

		summary = {"Present": 0, "Absent": 0, "Half Day": 0, "On Leave": 0}
		for row in frappe.db.sql(
			"SELECT status, COUNT(*) AS count FROM `tabAttendance` WHERE {} GROUP BY status".format(where_clause),
			params,
			as_dict=True,
		):
			if row.status in summary:
				summary[row.status] = row.count

		offset = (max(1, page) - 1) * page_size
		records = frappe.db.sql(
			"""
			SELECT name, attendance_date, status, working_hours, in_time, out_time, employee
			FROM `tabAttendance`
			WHERE {}
			ORDER BY name DESC, attendance_date DESC
			LIMIT %s OFFSET %s
			""".format(where_clause),
			params + [page_size, offset],
			as_dict=True,
		)
		result_records, _ = _build_attendance_records(records)
		return {
			"data": result_records,
			"total": total,
			"page": page,
			"page_size": page_size,
			"summary": summary,
		}

	# Legacy: no limit, return all records.
	records = frappe.db.sql(
		"""
		SELECT name, attendance_date, status, working_hours, in_time, out_time, employee
		FROM `tabAttendance`
		WHERE {}
		ORDER BY name DESC, attendance_date DESC
		""".format(where_clause),
		params,
		as_dict=True,
	)

	result_records, summary = _build_attendance_records(records)

	return {"records": result_records, "summary": summary}


# ---------------------------------------------------------------------------
# Dashboard card APIs (leave balance, holidays, working days)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_leave_balance(employee: str | None = None):
	"""
	Return total available leave days for the dashboard card.

	If *employee* is supplied that employee is used; otherwise the
	current session user is resolved to an Employee record.

	Returns an integer / float representing the sum of ``balance_leaves``
	across all active leave types for the current fiscal year.
	"""
	if not employee:
		employee = frappe.db.get_value(
			"Employee", {"user_id": frappe.session.user, "status": "Active"}, "name"
		)
	if not employee:
		return 0

	# Use HRMS helper so allocation logic (carried-forward, max
	# carried forward, etc.) stays consistent with the rest of HRMS.
	from hrms.hr.doctype.leave_application.leave_application import get_leave_details

	date = getdate(nowdate())
	leave_details = get_leave_details(employee, date)
	allocation = leave_details.get("leave_allocation", {})

	total_balance = 0.0
	for details in allocation.values():
		total_balance += details.get("remaining_leaves", 0)

	return round(total_balance, 1)


@frappe.whitelist()
def get_attendance_summary(month=None, year=None):
	"""Get attendance summary for specified month/year (defaults to current month)"""
	employee = get_current_employee()
	if not employee:
		return {}
	employee_name = employee if isinstance(employee, str) else employee.get("name")

	# Default to current month if not specified
	requested_date = getdate(nowdate())
	if month and year:
		requested_date = getdate(f"{year}-{month}-01")

	today = requested_date
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
		(employee_name, first_day, last_day),
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


@frappe.whitelist()
def get_monthly_attendance_stats(employee_id: str | None = None, month=None, year=None):
	"""
	Get monthly attendance statistics for the specified month/year (defaults to current month).

	Returns:
	    Dict with:
	        - working_days: int — total working days in month (excl. weekends + holidays)
	        - present_days: int — days marked Present/Half Day in Attendance table
	        - total_days: int — total calendar days in the month
	"""
	from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee

	if not employee_id:
		employee_id = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")

	if not employee_id:
		return {"working_days": 0, "present_days": 0, "total_days": 0}

	# Default to current month if not specified
	requested_date = getdate()
	if month and year:
		requested_date = getdate(f"{year}-{month}-01")

	today = requested_date
	first_day = get_first_day(today)
	last_day = getdate(get_last_day(today))

	# Total calendar days in month
	total_days = (last_day - first_day).days + 1

	# Fetch holidays for this month from employee's holiday list
	holiday_list = get_holiday_list_for_employee(employee_id, raise_exception=False)
	holiday_dates = set()
	if holiday_list:
		holidays = frappe.get_all(
			"Holiday",
			filters={"parent": holiday_list, "holiday_date": ["between", [str(first_day), str(last_day)]]},
			fields=["holiday_date"],
		)
		holiday_dates = {str(h.holiday_date) for h in holidays}

	# Count working days (exclude Sat/Sun + holidays)
	working_days = 0
	current = first_day
	import datetime as _dt
	while current <= last_day:
		str_date = str(current)
		if current.weekday() < 5 and str_date not in holiday_dates:
			working_days += 1
		current += _dt.timedelta(days=1)

	# Count present days from Attendance table
	present_rows = frappe.db.sql(
		"""
		SELECT COUNT(*)
		FROM `tabAttendance`
		WHERE employee = %s
			AND attendance_date BETWEEN %s AND %s
			AND docstatus = 1
			AND status IN ('Present', 'Half Day')
		""",
		(employee_id, str(first_day), str(last_day)),
		as_list=True,
	)
	present_days = present_rows[0][0] if present_rows else 0

	return {
		"working_days": working_days,
		"present_days": present_days,
		"total_days": total_days,
	}


@frappe.whitelist()
def get_holidays(start_date: str, end_date: str):
	"""
	Get holidays between start_date and end_date.

	Args:
	    start_date: Start date (YYYY-MM-DD format)
	    end_date: End date (YYYY-MM-DD format)

	Returns:
	    List of holidays with date, description, and weekly_off flag
	"""
	from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee

	employee_id = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
	if not employee_id:
		return []

	holiday_list = get_holiday_list_for_employee(employee_id, raise_exception=False)
	holidays = []

	if holiday_list:
		holidays = frappe.get_all(
			"Holiday",
			filters={"parent": holiday_list, "holiday_date": ["between", [start_date, end_date]]},
			fields=["holiday_date", "description", "weekly_off"],
		)

	return holidays


@frappe.whitelist()
def get_leave_applications(month=None, year=None):
	"""
	Get leave applications for the specified month/year.

	Args:
	    month: Month number (optional, defaults to current month)
	    year: Year number (optional, defaults to current year)

	Returns:
	    List of leave applications with date, leave_type, and status
	"""
	employee_id = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
	if not employee_id:
		return []

	today = getdate()
	if not month or not year:
		month = today.month
		year = today.year

	start_date = getdate(f"{year}-{month}-01")
	end_date = getdate(get_last_day(start_date))

	leaves = frappe.get_all(
		"Leave Application",
		filters={
			"employee": employee_id,
			"docstatus": 1,
			"from_date": ["<=", end_date],
			"to_date": [">=", start_date],
		},
		fields=["name", "leave_type", "from_date", "to_date", "status", "total_leave_days"],
		order_by="from_date asc",
	)

	return [
		{
			"name": l.name,
			"leave_type": l.leave_type,
			"from_date": str(l.from_date),
			"to_date": str(l.to_date),
			"status": l.status,
			"total_leave_days": l.total_leave_days,
		}
		for l in leaves
	]


# ---------------------------------------------------------------------------
# Attendance Grid API
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_attendance_grid(year: int | str | None = None, month: int | str | None = None, employee_id: str | None = None):
	"""
	Get attendance grid data for all (or a specific) employee(s) for a given month.

	Returns a nested structure:
	{
	    "employees": [{"name": "EMP-001", "employee_name": "John Doe"}, ...],
	    "days_in_month": 30,
	    "grid": [
	        {
	            "employee": "EMP-001",
	            "employee_name": "John Doe",
	            "days": [
	                {"date": "2026-05-01", "status": "Present", "in_time": "...", "out_time": "...", "working_hours": 8.5, "is_working_day": true},
	                ...
	            ]
	        },
	        ...
	    ]
	}
	"""
	from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee

	if not year or not month:
		today = getdate()
		year = today.year
		month = today.month

	first_day = getdate(f"{year}-{month}-01")
	last_day = getdate(get_last_day(first_day))
	days_in_month = last_day.day

	# Determine which employees to include
	from arijentek_core.api.roster import get_employee_list
	permitted_employees = [e["name"] for e in get_employee_list()]

	if employee_id:
		if employee_id not in permitted_employees:
			frappe.throw(_("Not permitted to view attendance grid for this employee"), frappe.PermissionError)
		employee_ids = [employee_id]
	else:
		# get_all bypasses employee_query_conditions — drop platform staff
		# from the grid roster explicitly.
		from arijentek_core.services.internal_access import get_internal_employee_names

		grid_filters = {"status": "Active"}
		internal = get_internal_employee_names()
		if internal:
			grid_filters["name"] = ["not in", internal]
		if is_global_attendance_manager():
			employees = frappe.get_all(
				"Employee",
				filters=grid_filters,
				fields=["name", "employee_name"],
				order_by="employee_name asc",
			)
			employee_ids = [e.name for e in employees]
		else:
			active_permitted = frappe.get_all(
				"Employee",
				filters={"name": ["in", permitted_employees], "status": "Active"},
				fields=["name"],
				order_by="employee_name asc",
			)
			employee_ids = [e.name for e in active_permitted]

	# Fetch all holidays for employees (use a common holiday list approach)
	# We'll resolve per-employee since holiday lists vary
	holiday_cache = {}

	# Fetch all attendance records for the month for these employees
	attendance_records = []
	if employee_ids:
		attendance_records = frappe.db.sql(
			"""
			SELECT name, attendance_date, status, working_hours, in_time, out_time, employee
			FROM `tabAttendance`
			WHERE docstatus = 1
			AND employee IN ({placeholders})
			AND attendance_date BETWEEN %s AND %s
			ORDER BY employee, attendance_date
			""".format(placeholders=", ".join(["%s"] * len(employee_ids))),
			(*employee_ids, first_day, last_day),
			as_dict=True,
		)

	# Build a lookup: (employee, date_str) → attendance record
	attendance_lookup = {}
	for r in attendance_records:
		key = (r.employee, str(r.attendance_date))
		attendance_lookup[key] = {
			"name": r.name,
			"status": r.status,
			"working_hours": round(flt(r.working_hours), 2),
			"in_time": str(r.in_time) if r.in_time else None,
			"out_time": str(r.out_time) if r.out_time else None,
		}

	# Fetch approved leave applications for the month for these employees
	leave_records = []
	if employee_ids:
		leave_records = frappe.db.sql(
			"""
			SELECT employee, from_date, to_date, leave_type, status
			FROM `tabLeave Application`
			WHERE docstatus = 1
			AND employee IN ({placeholders})
			AND from_date <= %s
			AND to_date >= %s
			ORDER BY employee, from_date
			""".format(placeholders=", ".join(["%s"] * len(employee_ids))),
			(*employee_ids, last_day, first_day),
			as_dict=True,
		)

	# Build leave date sets: employee → set of date strings
	leave_date_sets = {}
	for l in leave_records:
		if l.status != "Approved":
			continue
		if l.employee not in leave_date_sets:
			leave_date_sets[l.employee] = set()
		cd = getdate(l.from_date)
		while cd <= getdate(l.to_date):
			leave_date_sets[l.employee].add(str(cd))
			cd = add_days(cd, 1)

	# Build grid data
	grid = []
	for emp_id in employee_ids:
		# Get employee's holiday list
		holiday_list_name = frappe.db.get_value("Employee", emp_id, "holiday_list")
		holiday_dates = set()
		if holiday_list_name and holiday_list_name not in holiday_cache:
			holidays = frappe.get_all(
				"Holiday",
				filters={"parent": holiday_list_name, "holiday_date": ["between", [str(first_day), str(last_day)]]},
				fields=["holiday_date"],
			)
			holiday_cache[holiday_list_name] = {str(h.holiday_date) for h in holidays}
		if holiday_list_name:
			holiday_dates = holiday_cache.get(holiday_list_name, set())

		leave_dates = leave_date_sets.get(emp_id, set())

		# Get employee name
		emp_name = ""
		for r in attendance_records:
			if r.employee == emp_id:
				emp_name = frappe.db.get_value("Employee", emp_id, "employee_name")
				break
		if not emp_name:
			emp_name = frappe.db.get_value("Employee", emp_id, "employee_name")

		days_data = []
		for day in range(1, days_in_month + 1):
			current_date = getdate(f"{year}-{month}-{day:02d}")
			date_str = str(current_date)
			is_on_leave = date_str in leave_dates

			attendance = attendance_lookup.get((emp_id, date_str))

			if attendance:
				status = attendance["status"]
				if attendance.get("in_time") and status == "On Leave":
					status = "Present"
				is_working_day = True
			elif is_on_leave:
				status = "On Leave"
				is_working_day = False
			else:
				status = ""
				is_working_day = True

			days_data.append({
				"date": date_str,
				"status": status,
				"in_time": attendance["in_time"] if attendance else None,
				"out_time": attendance["out_time"] if attendance else None,
				"working_hours": attendance["working_hours"] if attendance else 0,
				"is_working_day": is_working_day,
				"attendance_name": attendance["name"] if attendance else None,
			})

		grid.append({
			"employee": emp_id,
			"employee_name": emp_name,
			"days": days_data,
		})

	# Filter by status if provided (for the frontend filter — applied on the grid)
	# We return all data; filtering is done client-side for grid UX

	return {
		"employees": [{"name": emp_id, "employee_name": g["employee_name"]} for g in grid],
		"days_in_month": days_in_month,
		"first_day": str(first_day),
		"last_day": str(last_day),
		"grid": grid,
	}


# ---------------------------------------------------------------------------
# Mark attendance (manual attendance marking via employee portal)
# ---------------------------------------------------------------------------
# Permission helpers
# ---------------------------------------------------------------------------


@frappe.whitelist()
def can_mark_attendance():
	"""
	Check if the current user has 'create' permission on the Attendance DocType,
	or if they are an 'HR Manager' or 'System Manager' or have 'submit' permission on 'Attendance'.

	Returns:
	    bool: True if user can create Attendance records, False otherwise.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles or frappe.has_permission("Attendance", "submit") or frappe.has_permission("Attendance", "create"):
		return True
	return False


@frappe.whitelist()
def can_manage_attendance():
	"""
	Check if the current user can view other employees' attendance data
	(e.g. HR managers, supervisors).

	Uses 'write' permission as the gate — any user with write access can
	read and manage attendance records beyond their own.

	Returns:
	    bool: True if user can view other employees' data, False otherwise.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	return bool(frappe.has_permission("Attendance", "write"))


@frappe.whitelist()
def can_view_attendance():
	"""
	Check if the current user can read the Attendance DocType.

	Used to gate the visibility of the employee filter dropdown.
	Any user with read permission can see attendance records (they will
	be auto-filtered by User Permissions on the server side).

	Returns:
	    bool: True if user can view Attendance, False otherwise.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	return bool(frappe.has_permission("Attendance", "read"))


@frappe.whitelist()
def mark_attendance(
	employee_id: str | None = None,
	date: str | None = None,
	status: str = "Present",
	in_time: str | None = None,
	out_time: str | None = None,
):
	"""
	Manually mark attendance for an employee on a specific date.

	Only users with 'create' permission on the Attendance DocType can call this.
	Returns the name of the created Attendance record.

	Args:
	    employee_id: Employee ID (optional, defaults to current user's employee)
	    date: Attendance date in YYYY-MM-DD format (optional, defaults to today)
	    status: Present, Absent, or Half Day (default: Present)
	    in_time: Clock In time in HH:MM format (optional)
	    out_time: Clock Out time in HH:MM format (optional)

	Returns:
	    dict: {"name": "<attendance_name>", "date": "<date>", "status": "<status>"}

	Raises:
	    frappe.ValidationError: If attendance is already marked, on a holiday, or on approved leave.
	"""
	from frappe.utils import getdate, today

	if not employee_id:
		employee_id = frappe.db.get_value(
			"Employee", {"user_id": frappe.session.user, "status": "Active"}, "name"
		)
	if not employee_id:
		return {"success": False, "message": _("No employee record found for current user")}

	if not can_write_employee_attendance(employee_id):
		return {"success": False, "message": _("You do not have permission to mark attendance for this employee")}

	if not date:
		date = today()
	else:
		parsed = getdate(date)
		# getdate("0000-00-00") or getdate("") can return a zero/invalid date
		if not parsed or parsed.year < 1 or parsed.month < 1 or parsed.month > 12:
			frappe.throw(_("Invalid date: {0}").format(date))
		date = str(parsed)

	status = status or "Present"

	# Check if already marked
	existing = frappe.db.get_value(
		"Attendance",
		{"employee": employee_id, "attendance_date": date, "docstatus": ("!=", 2)},
		["name", "status"],
		as_dict=True,
	)
	if existing:
		return {
			"success": False,
			"message": _("Attendance has already been marked as {0} for this date.").format(
				existing.status
			),
		}

	# Get shift assignment for the date to capture shift details
	shift_info = {}
	shift_assignments = frappe.get_all(
		"Shift Assignment",
		filters={
			"employee": employee_id,
			"docstatus": 1,
			"start_date": ("<=", date),
			"end_date": (">=", date),
		},
		fields=["shift_type"],
		limit=1,
	)
	if shift_assignments:
		shift_type = frappe.db.get_value(
			"Shift Type", shift_assignments[0].shift_type, ["start_time", "end_time"], as_dict=True
		)
		if shift_type:
			shift_info["shift"] = shift_assignments[0].shift_type
			shift_info["in_time"] = shift_type.start_time
			shift_info["out_time"] = shift_type.end_time

	attendance_date = getdate(date)
	# Defensive: getdate can return zero datetime for bad inputs
	if not attendance_date or attendance_date.year < 1 or attendance_date.month < 1:
		attendance_date = getdate()

	# Create IN checkin if in_time is provided
	in_datetime = None
	if in_time and str(in_time).strip():
		from frappe.utils import get_datetime
		in_datetime = get_datetime(f"{date} {in_time}:00")
		if not frappe.db.exists("Employee Checkin", {"employee": employee_id, "time": in_datetime, "log_type": "IN"}):
			checkin = frappe.get_doc({
				"doctype": "Employee Checkin",
				"employee": employee_id,
				"log_type": "IN",
				"time": in_datetime,
				"device_id": "Manual Entry",
				"skip_auto_attendance": 1,
			})
			checkin.insert(ignore_permissions=True)

	# Create OUT checkin if out_time is provided
	out_datetime = None
	if out_time and str(out_time).strip():
		from frappe.utils import get_datetime
		out_datetime = get_datetime(f"{date} {out_time}:00")
		if not frappe.db.exists("Employee Checkin", {"employee": employee_id, "time": out_datetime, "log_type": "OUT"}):
			checkout = frappe.get_doc({
				"doctype": "Employee Checkin",
				"employee": employee_id,
				"log_type": "OUT",
				"time": out_datetime,
				"device_id": "Manual Entry",
				"skip_auto_attendance": 1,
			})
			checkout.insert(ignore_permissions=True)

	# Calculate working hours
	working_hours = 0.0
	if in_datetime and out_datetime:
		diff_seconds = (out_datetime - in_datetime).total_seconds()
		working_hours = round(diff_seconds / 3600.0, 2)

	doc = frappe.get_doc({
		"doctype": "Attendance",
		"employee": employee_id,
		"attendance_date": attendance_date,
		"status": status,
		"working_hours": working_hours,
		"in_time": in_datetime,
		"out_time": out_datetime,
	})
	if shift_info.get("shift"):
		doc.shift = shift_info["shift"]
	try:
		doc.insert(ignore_permissions=True)
		doc.submit()
		frappe.db.commit()
		return {"name": doc.name, "date": doc.attendance_date, "status": doc.status}
	except Exception as e:
		frappe.db.rollback()
		return {"success": False, "message": str(e)}


# ---------------------------------------------------------------------------
# Get attendance record by ID (for edit dialog)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_attendance(name: str):
	"""
	Get an Attendance record by its name.

	Returns the fields needed to populate the edit dialog.

	Args:
	    name: Attendance record name

	Returns:
	    Dict with employee, attendance_date, status (and other Attendance fields)
	"""
	if not name:
		return {}

	return frappe.get_value(
		"Attendance",
		name,
		[
			"name",
			"employee",
			"employee_name",
			"attendance_date",
			"status",
			"in_time",
			"out_time",
			"working_hours",
			"shift",
			"company",
			"department",
		],
		as_dict=True,
	)


# ---------------------------------------------------------------------------
# Get attendance detail by name (for grid cell pop-up)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_attendance_detail(attendance_name: str):
	"""
	Get full Attendance record details by name.

	Returns the complete Attendance DocType fields plus employee info.

	Args:
	    attendance_name: Name of the Attendance record

	Returns:
	    Dict with Attendance fields and employee details
	"""
	if not attendance_name:
		return {}

	attendance = frappe.get_value(
		"Attendance",
		attendance_name,
		[
			"name",
			"employee",
			"employee_name",
			"attendance_date",
			"status",
			"in_time",
			"out_time",
			"working_hours",
			"shift",
			"company",
			"department",
			"leave_type",
			"late_entry",
			"early_exit",
			"half_day_status",
			"overtime_type",
			"standard_working_hours",
			"actual_overtime_duration",
		],
		as_dict=True,
	)

	if not attendance:
		return {}

	# Add employee details
	employee = frappe.get_value(
		"Employee",
		attendance.employee,
		[
			"name",
			"employee_name",
			"department",
			"company",
			"branch",
			"grade",
			"holiday_list",
		],
		as_dict=True,
	)

	# Get shift type details if shift is set
	shift_details = {}
	if attendance.shift:
		shift = frappe.get_value(
			"Shift Type",
			attendance.shift,
			["name", "shift_name", "start_time", "end_time", "validation_rule"],
			as_dict=True,
		)
		if shift:
			shift_details = shift

	return {
		**attendance,
		"employee": employee,
		"shift_details": shift_details,
	}


@frappe.whitelist()
def update_attendance(
	attendance_name: str,
	status: str,
	in_time: str | None = None,
	out_time: str | None = None,
	late_entry: int = 0,
	early_exit: int = 0,
):
	attendance_details = frappe.db.get_value(
		"Attendance", attendance_name, ["employee", "attendance_date"], as_dict=True
	)
	if not attendance_details:
		return {"success": False, "message": _("Attendance record not found")}

	employee = attendance_details.employee
	date = str(attendance_details.attendance_date) if attendance_details.attendance_date else None

	if not employee or not can_write_employee_attendance(employee):
		return {"success": False, "message": _("You do not have permission to edit attendance")}

	# Create IN checkin if in_time is provided
	in_datetime = None
	if in_time and str(in_time).strip():
		from frappe.utils import get_datetime
		in_datetime = get_datetime(f"{date} {in_time}:00")
		if not frappe.db.exists("Employee Checkin", {"employee": employee, "time": in_datetime, "log_type": "IN"}):
			checkin = frappe.get_doc({
				"doctype": "Employee Checkin",
				"employee": employee,
				"log_type": "IN",
				"time": in_datetime,
				"device_id": "Manual Entry",
				"skip_auto_attendance": 1,
			})
			checkin.insert(ignore_permissions=True)

	# Create OUT checkin if out_time is provided
	out_datetime = None
	if out_time and str(out_time).strip():
		from frappe.utils import get_datetime
		out_datetime = get_datetime(f"{date} {out_time}:00")
		if not frappe.db.exists("Employee Checkin", {"employee": employee, "time": out_datetime, "log_type": "OUT"}):
			checkout = frappe.get_doc({
				"doctype": "Employee Checkin",
				"employee": employee,
				"log_type": "OUT",
				"time": out_datetime,
				"device_id": "Manual Entry",
				"skip_auto_attendance": 1,
			})
			checkout.insert(ignore_permissions=True)

	# Calculate working hours
	working_hours = 0.0
	if in_datetime and out_datetime:
		diff_seconds = (out_datetime - in_datetime).total_seconds()
		working_hours = round(diff_seconds / 3600.0, 2)

	# Directly update the submitted record in the database keeping same ID
	frappe.db.set_value(
		"Attendance",
		attendance_name,
		{
			"status": status,
			"in_time": in_datetime,
			"out_time": out_datetime,
			"working_hours": working_hours,
			"late_entry": late_entry,
			"early_exit": early_exit,
		},
		update_modified=True,
	)
	frappe.db.commit()

	return {"name": attendance_name, "date": date, "status": status}


@frappe.whitelist()
def delete_attendance(attendance_name: str):
	employee = frappe.db.get_value("Attendance", attendance_name, "employee")
	if not employee or not can_write_employee_attendance(employee):
		return {"success": False, "message": _("You do not have permission to delete attendance")}

	doc = frappe.get_doc("Attendance", attendance_name)

	if doc.docstatus == 1:
		doc.cancel()

	frappe.delete_doc("Attendance", attendance_name, ignore_permissions=True)
	frappe.db.commit()
	return {"success": True}


@frappe.whitelist()
def get_employee_checkins(
	employee_id: str | None = None,
	month: str | None = None,
	year: str | None = None,
	day: str | None = None,
	override_employee_id: str | None = None,
	start_date: str | None = None,
	end_date: str | None = None,
	page: int = 1,
	page_size: int = 0,
):
	"""
	Get all check-in/out logs, optionally filtered by date and employee.

	Args:
	    employee_id: Employee ID (optional, defaults to current user's employee)
	    month: Filter by month number (optional)
	    year: Filter by year (optional)
	    day: Filter by day of month (optional)
	    override_employee_id: Admin filter — specific employee or empty for all.
	    start_date: Filter start date (YYYY-MM-DD format)
	    end_date: Filter end date (YYYY-MM-DD format)
	    page: Page number (1-based; used when page_size > 0).
	    page_size: Rows per page (0 = no limit / legacy, returns all records).

	Returns:
	    When page_size == 0 (legacy): List of check-in logs with name, log_type,
	    time, device_id, latitude, longitude, shift.
	    When page_size > 0: Dict with 'data' (the page), 'total', 'page',
	    'page_size'.
	"""
	# Admin mode: override_employee_id controls who to filter
	from arijentek_core.api.roster import get_employee_list
	permitted_employees = [e["name"] for e in get_employee_list()]

	if override_employee_id or override_employee_id == "":
		if override_employee_id == "":
			if is_global_attendance_manager():
				filters = {}
			else:
				filters = {"employee": ["in", permitted_employees]}
		else:
			if override_employee_id not in permitted_employees:
				frappe.throw(_("Not permitted to view check-ins for this employee"), frappe.PermissionError)
			filters = {"employee": override_employee_id}
	else:
		if not employee_id:
			employee_id = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
		if not employee_id:
			frappe.throw(_("No employee record found for current user"))
		if employee_id not in permitted_employees:
			frappe.throw(_("Not permitted to view check-ins for this employee"), frappe.PermissionError)
		filters = {"employee": employee_id}

	# Build date range if start_date/end_date provided, or month/year provided
	if start_date and end_date:
		filters["time"] = ["between", [f"{start_date} 00:00:00", f"{end_date} 23:59:59"]]
	elif month or year:
		year = int(year) if year else getdate().year
		month = int(month) if month else getdate().month
		start_date_val = getdate(f"{year}-{month:02d}-01")
		end_date_val = getdate(get_last_day(start_date_val))

		if day:
			day = int(day)
			start_date_val = getdate(f"{year}-{month:02d}-{day:02d}")
			end_date_val = start_date_val

		filters["time"] = ["between", [start_date_val, end_date_val]]

	# Server-side paging: page_size > 0 limits the query; 0 = legacy (all rows).
	logs = frappe.get_all(
		"Employee Checkin",
		filters=filters,
		fields=["name", "log_type", "time", "device_id", "latitude", "longitude", "shift", "employee"],
		order_by="name desc",
		limit_page_length=page_size if page_size > 0 else 0,
		limit_start=(max(1, page) - 1) * page_size if page_size > 0 else 0,
	)

	# Resolve employee names for returned logs
	emp_names = {}
	return_logs = []
	for log in logs:
		emp = log.employee
		if emp not in emp_names:
			emp_names[emp] = frappe.db.get_value("Employee", emp, "employee_name")
		return_logs.append({
			"name": log.name,
			"employee": emp,
			"employee_name": emp_names[emp],
			"log_type": log.log_type,
			"time": str(log.time),
			"device_id": log.device_id,
			"latitude": log.latitude,
			"longitude": log.longitude,
			"shift": log.shift,
		})

	if page_size > 0:
		# Total comes from the full filtered set (same filters), so it is
		# not affected by which page is being returned.
		total = frappe.db.count("Employee Checkin", filters=filters)
		return {
			"data": return_logs,
			"total": total,
			"page": page,
			"page_size": page_size,
		}

	return return_logs


def is_global_attendance_manager():
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles or "HR User" in roles:
		return True
	from frappe.desk.reportview import get_match_cond
	mcond = get_match_cond("Employee", as_condition=True)
	if not mcond:
		return True
	return False


def can_write_employee_attendance(employee_id):
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	# If they have global create/write permission on Attendance, they are allowed
	if frappe.has_permission("Attendance", "create") or frappe.has_permission("Attendance", "write"):
		return True
	# Otherwise, check if the employee is in their permitted list
	from arijentek_core.api.roster import get_employee_list
	permitted_employees = [e["name"] for e in get_employee_list()]
	if employee_id in permitted_employees:
		return True
	return False


@frappe.whitelist()
def get_employee_list_for_attendance():
	"""
	Return a list of employees for the attendance page.
	Accessible if the user is an 'HR Manager' or 'System Manager' or has 'submit' permission on 'Attendance' doctype.
	Otherwise, returns an empty list.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)

	if "HR Manager" in roles or "System Manager" in roles or frappe.has_permission("Attendance", "submit"):
		from arijentek_core.services.internal_access import get_internal_employee_names

		filters = {"status": ["in", ["Active", "Suspended"]]}
		internal = get_internal_employee_names()
		if internal:
			filters["name"] = ["not in", internal]
		return frappe.get_all(
			"Employee",
			filters=filters,
			fields=["name", "employee_name"],
			order_by="employee_name asc",
		)
	return []


@frappe.whitelist()
def can_delete_checkin():
	"""
	Check if the current user has 'delete' permission on the Employee Checkin DocType.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Employee Checkin", "delete"):
		return True

	return False


@frappe.whitelist()
def delete_employee_checkin(checkin_name: str):
	"""
	Delete employee checkin record.
	"""
	if not can_delete_checkin():
		return {"success": False, "message": _("You do not have permission to delete employee checkins")}

	frappe.delete_doc("Employee Checkin", checkin_name, ignore_permissions=True)
	frappe.db.commit()

	return {"success": True}


def _extract_frappe_message():
	"""
	Helper to extract human-readable error messages from frappe.message_log.
	Handles both plain strings, JSON message objects, and tabular warning messages.
	"""
	if frappe.message_log:
		try:
			import json
			last_msg = json.loads(frappe.message_log[-1])
			if isinstance(last_msg, dict) and "message" in last_msg:
				msg = last_msg["message"]
				if isinstance(msg, list) and len(msg) > 1 and isinstance(msg[0], list):
					# Table format: [[Date, Reason, Action], ...]
					table_msgs = []
					for row in msg[1:]:
						if len(row) >= 2:
							table_msgs.append(f"{row[1]} on {row[0]}")
					if table_msgs:
						return ", ".join(table_msgs)
				if isinstance(msg, str):
					return msg
		except Exception:
			pass
	return None


@frappe.whitelist()
def create_attendance_request(date, explanation=None, employee=None):
	"""
	Create an Attendance Request for the given employee (or current user).
	"""
	if not date:
		return {"success": False, "message": _("Date is required.")}

	if not employee:
		employee = frappe.db.get_value(
			"Employee",
			{"user_id": frappe.session.user, "status": "Active"},
			"name"
		)

	if not employee:
		return {"success": False, "message": _("Active Employee record not found.")}

	company = frappe.db.get_value("Employee", employee, "company")

	# Create Attendance Request
	from erpnext.setup.doctype.employee.employee import is_holiday
	include_holidays = 1 if is_holiday(employee, date) else 0

	doc = frappe.get_doc({
		"doctype": "Attendance Request",
		"employee": employee,
		"company": company,
		"from_date": date,
		"to_date": date,  # Same as selected from date because it is mandatory
		"reason": "On Duty",  # Reason (on duty because our client employees won't be do work from home)
		"explanation": explanation,
		"include_holidays": include_holidays,
	})

	# Auto-populate shift if possible
	try:
		doc.validate_shifts()
	except Exception:
		pass

	try:
		# Run date validation for duplicate requests/attendance
		validate_attendance_request(doc)

		# Insert bypassing standard validation (which would block on leave/holiday)
		doc.flags.ignore_validate = True
		doc.insert()
	except Exception as e:
		frappe.db.rollback()
		msg = _extract_frappe_message() or str(e)
		frappe.clear_messages()
		return {"success": False, "message": msg}

	try:
		from arijentek_core.api.notifications import notify_approvers
		title = "New Attendance Request"
		body = f"{doc.employee_name} has requested attendance (ID: {doc.name})."
		notify_approvers(doc, title, body, module="hrm", route="/attendance?tab=requests")
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Attendance Request Creation Notification Error")

	return {"success": True, "name": doc.name}


def validate_attendance_request(doc, method=None):
	"""
	Backend validation on Attendance Request:
	If on the specific date the user is present, stop and tell 'You are already present on the selected date.'
	"""
	from_date = getdate(doc.from_date)
	to_date = getdate(doc.to_date)

	curr_date = from_date
	while curr_date <= to_date:
		# Check if employee has an Attendance record on curr_date with status == "Present"
		existing_attendance = frappe.db.exists(
			"Attendance",
			{
				"employee": doc.employee,
				"attendance_date": curr_date,
				"status": "Present",
				"docstatus": ("!=", 2),
			}
		)
		if existing_attendance:
			frappe.throw(_("You are already present on the selected date."))

		# Check if employee already has an Attendance Request for curr_date
		existing_request = frappe.db.exists(
			"Attendance Request",
			{
				"employee": doc.employee,
				"from_date": ("<=", curr_date),
				"to_date": (">=", curr_date),
				"docstatus": ("in", [0, 1]),
				"name": ("!=", doc.name if doc.name else ""),
			}
		)
		if existing_request:
			frappe.throw(_("Attendance request already available for the selected date."))

		curr_date = add_days(curr_date, 1)


@frappe.whitelist()
def get_attendance_requests(employee_id=None, status=None, start_date=None, end_date=None, page: int = 1, page_size: int = 0):
	"""
	Fetch attendance requests based on permissions and filters.

	`page_size` > 0 returns a single page (LIMIT/OFFSET) plus the total of the
	full filtered set; `page_size` = 0 keeps the legacy behaviour (all rows).
	"""
	permitted_employees = [e["name"] for e in get_employee_list_for_attendance()]

	# If the user doesn't have permission to see other employees' attendance (empty list),
	# they can ONLY see their own attendance requests
	if not permitted_employees:
		user_employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user, "status": "Active"}, "name")
		if not user_employee:
			return []
		permitted_employees = [user_employee]

	# Build filters
	filters = {}

	# Employee filter
	if employee_id:
		if employee_id in permitted_employees:
			filters["employee"] = employee_id
		else:
			return []  # No permission
	else:
		filters["employee"] = ["in", permitted_employees]

	# Status filter mapping to docstatus
	# docstatus: 0 = Draft, 1 = Approved (Submitted), 2 = Rejected (Cancelled)
	if status:
		if status == "Draft":
			filters["docstatus"] = 0
		elif status == "Approved":
			filters["docstatus"] = 1
		elif status == "Rejected":
			filters["docstatus"] = 2
	else:
		filters["docstatus"] = ["in", [0, 1, 2]]

	# Date range filter
	if start_date and end_date:
		filters["from_date"] = [">=", start_date]
		filters["to_date"] = ["<=", end_date]

	# Server-side paging: page_size > 0 limits the query; 0 = legacy (all rows).
	requests = frappe.get_all(
		"Attendance Request",
		filters=filters,
		fields=["name", "employee", "employee_name", "from_date", "to_date", "reason", "explanation", "docstatus", "owner"],
		order_by="creation desc",
		limit_page_length=page_size if page_size > 0 else 0,
		limit_start=(max(1, page) - 1) * page_size if page_size > 0 else 0,
	)

	# Inject can_approve flag
	can_approve = frappe.has_permission("Attendance Request", "submit")
	for r in requests:
		r["can_approve"] = can_approve

	if page_size > 0:
		# Total comes from the full filtered set (same filters), so it is
		# not affected by which page is being returned.
		total = frappe.db.count("Attendance Request", filters=filters)
		return {
			"data": requests,
			"total": total,
			"page": page,
			"page_size": page_size,
		}

	return requests


@frappe.whitelist()
def update_attendance_request(request_name, date, explanation=None):
	"""
	Update the date and explanation of a draft Attendance Request.
	"""
	if not request_name:
		return {"success": False, "message": _("Attendance Request name is required.")}
	if not date:
		return {"success": False, "message": _("Date is required.")}

	doc = frappe.get_doc("Attendance Request", request_name)
	if doc.docstatus != 0:
		return {"success": False, "message": _("Only draft Attendance Requests can be edited.")}

	has_submit_perm = frappe.has_permission("Attendance Request", "submit")
	if doc.owner != frappe.session.user and not has_submit_perm:
		return {"success": False, "message": _("You don't have permission to edit this request.")}

	# Update fields
	doc.from_date = date
	doc.to_date = date
	doc.explanation = explanation

	try:
		# Run date validation
		validate_attendance_request(doc)

		doc.flags.ignore_validate = True
		doc.save()
	except Exception as e:
		frappe.db.rollback()
		msg = _extract_frappe_message() or str(e)
		frappe.clear_messages()
		return {"success": False, "message": msg}

	return {"success": True}


@frappe.whitelist()
def delete_attendance_request(request_name):
	"""
	Delete a draft Attendance Request.
	"""
	if not request_name:
		frappe.throw(_("Attendance Request name is required."))

	doc = frappe.get_doc("Attendance Request", request_name)

	has_submit_perm = frappe.has_permission("Attendance Request", "submit")
	is_creator = doc.owner == frappe.session.user

	if not has_submit_perm and not (is_creator and doc.docstatus == 0):
		return {"success": False, "message": _("You don't have permission to delete this request")}

	if has_submit_perm and doc.docstatus == 1:
		if not frappe.has_permission("Attendance Request", "delete"):
			return {"success": False, "message": _("You need explicit Delete permission to delete an approved Attendance Request")}

	if doc.docstatus == 1:
		doc.flags.ignore_permissions = True
		doc.cancel()

	doc.delete(ignore_permissions=True)
	return {"success": True, "message": "Deleted"}


@frappe.whitelist()
def approve_attendance_request(request_name):
	"""
	Approve (submit) an Attendance Request.
	"""
	frappe.only_for(["HR Manager", "System Manager", "Leave Approver"])
	if not request_name:
		frappe.throw(_("Attendance Request name is required."))

	doc = frappe.get_doc("Attendance Request", request_name)

	# Manually create/update the attendance record to be "Present"
	attendance = frappe.db.exists(
		"Attendance",
		{
			"employee": doc.employee,
			"attendance_date": doc.from_date,
			"docstatus": ("!=", 2),
		}
	)

	if attendance:
		frappe.db.set_value("Attendance", attendance, {
			"status": "Present",
			"attendance_request": doc.name
		})
	else:
		att_doc = frappe.new_doc("Attendance")
		att_doc.employee = doc.employee
		att_doc.attendance_date = doc.from_date
		att_doc.shift = doc.shift
		att_doc.company = doc.company
		att_doc.attendance_request = doc.name
		att_doc.status = "Present"
		att_doc.insert(ignore_permissions=True)
		att_doc.submit()

	doc.db_set("docstatus", 1)
	doc.status = "Approved"

	try:
		from arijentek_core.api.notifications import notify_owner
		title = "Attendance Request Approved"
		body = f"Your attendance request (ID: {doc.name}) has been Approved."
		notify_owner(doc, title, body, module="hrm", route="/attendance?tab=requests")
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Attendance Request Status Notification Error")

	return {"success": True}

@frappe.whitelist()
def reject_attendance_request(request_name):
	"""
	Reject (cancel/mark docstatus = 2) an Attendance Request.
	"""
	frappe.only_for(["HR Manager", "System Manager", "Leave Approver"])
	if not request_name:
		frappe.throw(_("Attendance Request name is required."))

	doc = frappe.get_doc("Attendance Request", request_name)
	if doc.docstatus == 0:
		doc.db_set("docstatus", 2)
	elif doc.docstatus == 1:
		# Manually cancel linked attendance records
		attendance_list = frappe.get_all(
			"Attendance",
			filters={"employee": doc.employee, "attendance_request": doc.name, "docstatus": 1},
			fields=["name"]
		)
		for att in attendance_list:
			try:
				att_obj = frappe.get_doc("Attendance", att.name)
				att_obj.cancel()
			except Exception:
				# Force set docstatus of Attendance to 2 if standard cancel fails
				frappe.db.set_value("Attendance", att.name, "docstatus", 2)
		doc.db_set("docstatus", 2)

	doc.status = "Rejected"

	try:
		from arijentek_core.api.notifications import notify_owner
		title = "Attendance Request Rejected"
		body = f"Your attendance request (ID: {doc.name}) has been Rejected."
		notify_owner(doc, title, body, module="hrm", route="/attendance?tab=requests")
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Attendance Request Status Notification Error")
	return {"success": True}

@frappe.whitelist()
def get_bulk_attendance_filters():
	"""
	Returns the list of active Departments, Designations, and Shift Types to populate the dropdowns in the bulk attendance popup.
	"""
	if not can_mark_attendance():
		frappe.throw(_("Not permitted to access bulk attendance"), frappe.PermissionError)

	departments = frappe.get_all("Department", filters={"disabled": 0}, fields=["name"], order_by="name asc")
	designations = frappe.get_all("Designation", fields=["name"], order_by="name asc")
	shifts = frappe.get_all("Shift Type", filters={"docstatus": ["<", 2]}, fields=["name"], order_by="name asc")

	return {
		"departments": [d.name for d in departments],
		"designations": [d.name for d in designations],
		"shifts": [s.name for s in shifts]
	}

@frappe.whitelist()
def get_employees_for_bulk_attendance(
	date: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	department: str | None = None,
	designation: str | None = None,
):
	"""
	Returns a list of active employees filtered by department and designation.
	Performs a lookup with the Attendance doctype to check if attendance records already exist for the given date or date range.
	"""
	if not can_mark_attendance():
		frappe.throw(_("Not permitted to access bulk attendance"), frappe.PermissionError)

	if not date and not (from_date and to_date):
		frappe.throw(_("Date or Date Range is required"))

	start_d = getdate(from_date or date)
	end_d = getdate(to_date or date)

	if (end_d - start_d).days > 31:
		frappe.throw(_("Date range cannot exceed 31 days"))

	filters = {"status": ["in", ["Active", "Suspended"]]}
	if department:
		filters["department"] = department
	if designation:
		filters["designation"] = designation
	# get_all bypasses employee_query_conditions — platform staff never
	# appear in bulk-attendance marking (or its counts).
	from arijentek_core.services.internal_access import get_internal_employee_names

	internal = get_internal_employee_names()
	if internal:
		filters["name"] = ["not in", internal]

	employees = frappe.get_all(
		"Employee",
		filters=filters,
		fields=["name", "employee_name", "department", "designation"],
		order_by="employee_name asc",
	)

	if not employees:
		return []

	employee_names = [e.name for e in employees]

	if from_date and to_date and from_date != to_date:
		attendances = frappe.get_all(
			"Attendance",
			filters={
				"attendance_date": ["between", [str(start_d), str(end_d)]],
				"employee": ["in", employee_names],
				"docstatus": 1,
			},
			fields=["employee", "status", "attendance_date"],
		)
		att_map = {}
		for a in attendances:
			if a.employee not in att_map:
				att_map[a.employee] = []
			att_map[a.employee].append(a)

		result = []
		for emp in employees:
			records = att_map.get(emp.name, [])
			emp_dict = dict(emp)
			emp_dict["existing_count"] = len(records)
			emp_dict["attendance_status"] = f"{len(records)} marked" if records else None
			emp_dict["attendance_name"] = None
			result.append(emp_dict)
		return result
	else:
		single_date = str(start_d)
		attendances = frappe.get_all(
			"Attendance",
			filters={"attendance_date": single_date, "employee": ["in", employee_names], "docstatus": 1},
			fields=["employee", "status", "name as attendance_name"],
		)
		att_map = {a.employee: {"status": a.status, "attendance_name": a.attendance_name} for a in attendances}

		result = []
		for emp in employees:
			att_info = att_map.get(emp.name, {})
			emp_dict = dict(emp)
			emp_dict["existing_count"] = 1 if att_info.get("status") else 0
			emp_dict["attendance_status"] = att_info.get("status")
			emp_dict["attendance_name"] = att_info.get("attendance_name")
			result.append(emp_dict)
		return result


def _get_employee_holiday_dates(employee: str, start_date: str, end_date: str) -> set:
	"""Fetch set of holiday date strings (YYYY-MM-DD) for an employee within date range."""
	from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee

	holiday_list = get_holiday_list_for_employee(employee, raise_exception=False)
	if not holiday_list:
		return set()

	holidays = frappe.get_all(
		"Holiday",
		filters={"parent": holiday_list, "holiday_date": ["between", [start_date, end_date]]},
		fields=["holiday_date"],
	)
	return {str(h.holiday_date) for h in holidays}


@frappe.whitelist()
def mark_bulk_attendance(data: str):
	"""
	Accepts JSON data for employee attendance updates.
	Supports single date records or range data with avoid_holidays option.
	Iterates through employees and dates. Creates or updates Attendance records.
	"""
	if not can_mark_attendance():
		frappe.throw(_("Not permitted to mark bulk attendance"), frappe.PermissionError)

	try:
		import json
		parsed_data = json.loads(data)
	except Exception:
		frappe.throw(_("Invalid JSON data provided"))

	records_to_process = []

	if isinstance(parsed_data, dict) and "employees" in parsed_data:
		# Range-based bulk payload format
		employees = parsed_data.get("employees", [])
		from_date = parsed_data.get("from_date")
		to_date = parsed_data.get("to_date")
		status = parsed_data.get("status")
		shift = parsed_data.get("shift")
		late_entry = parsed_data.get("late_entry", 0)
		early_exit = parsed_data.get("early_exit", 0)
		avoid_holidays = bool(parsed_data.get("avoid_holidays", False))

		if not employees or not from_date or not to_date or not status:
			frappe.throw(_("Missing required fields for bulk attendance range submission"))

		start_d = getdate(from_date)
		end_d = getdate(to_date)
		if (end_d - start_d).days > 31:
			frappe.throw(_("Date range cannot exceed 31 days"))

		# Generate date list
		date_list = []
		curr = start_d
		while curr <= end_d:
			date_list.append(str(curr))
			curr = add_days(curr, 1)

		for emp_id in employees:
			emp_holidays = set()
			if avoid_holidays:
				emp_holidays = _get_employee_holiday_dates(emp_id, str(start_d), str(end_d))

			for d_str in date_list:
				if avoid_holidays and d_str in emp_holidays:
					continue
				records_to_process.append({
					"employee": emp_id,
					"date": d_str,
					"status": status,
					"shift": shift,
					"late_entry": late_entry,
					"early_exit": early_exit,
				})
	elif isinstance(parsed_data, list):
		# Standard record list payload format
		for record in parsed_data:
			emp_id = record.get("employee")
			from_d = record.get("from_date") or record.get("date")
			to_d = record.get("to_date") or record.get("date")
			status = record.get("status")
			shift = record.get("shift")
			late_entry = record.get("late_entry", 0)
			early_exit = record.get("early_exit", 0)
			avoid_holidays = bool(record.get("avoid_holidays", False))

			if not emp_id or not from_d or not status:
				continue

			if from_d and to_d and from_d != to_d:
				start_d = getdate(from_d)
				end_d = getdate(to_d)
				if (end_d - start_d).days > 31:
					frappe.throw(_("Date range cannot exceed 31 days"))

				emp_holidays = set()
				if avoid_holidays:
					emp_holidays = _get_employee_holiday_dates(emp_id, str(start_d), str(end_d))

				curr = start_d
				while curr <= end_d:
					d_str = str(curr)
					if not (avoid_holidays and d_str in emp_holidays):
						records_to_process.append({
							"employee": emp_id,
							"date": d_str,
							"status": status,
							"shift": shift,
							"late_entry": late_entry,
							"early_exit": early_exit,
						})
					curr = add_days(curr, 1)
			else:
				d_str = str(getdate(from_d))
				emp_holidays = set()
				if avoid_holidays:
					emp_holidays = _get_employee_holiday_dates(emp_id, d_str, d_str)
				if not (avoid_holidays and d_str in emp_holidays):
					records_to_process.append({
						"employee": emp_id,
						"date": d_str,
						"status": status,
						"shift": shift,
						"late_entry": late_entry,
						"early_exit": early_exit,
					})
	else:
		frappe.throw(_("Data format not supported"))

	created_count = 0
	updated_count = 0

	shift_times = {}

	for record in records_to_process:
		employee = record.get("employee")
		att_date = record.get("date")
		status = record.get("status")

		if not employee or not att_date or not status:
			continue

		shift = record.get("shift")
		late_entry = record.get("late_entry", 0)
		early_exit = record.get("early_exit", 0)

		# Fetch shift times if not cached
		if shift and shift not in shift_times:
			shift_doc = frappe.db.get_value("Shift Type", shift, ["start_time", "end_time"], as_dict=True)
			if shift_doc:
				shift_times[shift] = shift_doc
			else:
				shift_times[shift] = None

		in_time = None
		out_time = None
		if shift and shift_times.get(shift):
			st = shift_times[shift].get("start_time")
			et = shift_times[shift].get("end_time")
			if st is not None:
				in_time = f"{att_date} {st}"
			if et is not None:
				if st is not None and et < st:
					from datetime import timedelta
					next_day = getdate(att_date) + timedelta(days=1)
					out_time = f"{next_day} {et}"
				else:
					out_time = f"{att_date} {et}"

		# Check if existing submitted attendance
		existing = frappe.db.exists("Attendance", {"employee": employee, "attendance_date": att_date, "docstatus": 1})

		if existing:
			current_status = frappe.db.get_value("Attendance", existing, "status")
			if current_status == "On Leave":
				employee_name = frappe.db.get_value("Employee", employee, "employee_name") or employee
				frappe.throw(
					_("Cannot update attendance because {0} is already on leave on {1}. Please delete the leave application and the attendance entry first.").format(employee_name, att_date)
				)

			update_values = {
				"status": status,
				"late_entry": late_entry,
				"early_exit": early_exit,
			}
			if shift:
				update_values["shift"] = shift
			if in_time:
				update_values["in_time"] = in_time
			if out_time:
				update_values["out_time"] = out_time

			frappe.db.set_value("Attendance", existing, update_values)
			updated_count += 1
		else:
			created_count += 1
			new_doc = frappe.get_doc({
				"doctype": "Attendance",
				"employee": employee,
				"attendance_date": att_date,
				"status": status,
				"late_entry": late_entry,
				"early_exit": early_exit,
			})
			if shift:
				new_doc.shift = shift
			if in_time:
				new_doc.in_time = in_time
			if out_time:
				new_doc.out_time = out_time

			new_doc.insert(ignore_permissions=True)
			new_doc.submit()

	return {"success": True, "created": created_count, "updated": updated_count}

@frappe.whitelist()
def can_user_delete():
	roles = frappe.get_roles()
	is_manager = "HR Manager" in roles or "System Manager" in roles
	return bool(is_manager or frappe.has_permission("Attendance", "delete"))

@frappe.whitelist()
def can_user_edit():
	roles = frappe.get_roles()
	is_manager = "HR Manager" in roles or "System Manager" in roles
	return bool(is_manager or frappe.has_permission("Attendance", "write") or frappe.has_permission("Attendance", "amend"))

@frappe.whitelist()
def get_attendance_break_logs(employee_id, attendance_date):
	"""
	Fetch break logs for an employee on a specific date.
	Returns list of dicts: [{"break_in": str/datetime, "break_out": str/datetime, "duration": str, "is_ongoing": bool}]
	"""
	start_dt = f"{attendance_date} 00:00:00"
	end_dt = f"{attendance_date} 23:59:59"

	checkins = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": employee_id,
			"time": ["between", [start_dt, end_dt]],
			"docstatus": ["<", 2]
		},
		fields=["name", "time", "log_type", "device_id"],
		order_by="time asc"
	)

	if not checkins:
		return []

	first_in_idx = None
	last_out_idx = None
	for i, c in enumerate(checkins):
		if c.log_type == "IN" and first_in_idx is None:
			first_in_idx = i
		if c.log_type == "OUT":
			last_out_idx = i

	break_logs = []
	break_start = None

	for i, c in enumerate(checkins):
		note = _extract_log_note(c)
		is_explicit_break_start = (c.log_type == "OUT" and note == "Break Start")
		is_explicit_break_end = (c.log_type == "IN" and note == "Break End")

		is_implicit_break_start = (
			c.log_type == "OUT"
			and first_in_idx is not None
			and last_out_idx is not None
			and first_in_idx < i < last_out_idx
		)
		is_implicit_break_end = (
			c.log_type == "IN"
			and first_in_idx is not None
			and last_out_idx is not None
			and first_in_idx < i <= last_out_idx
			and break_start is not None
		)

		if (is_explicit_break_start or is_implicit_break_start) and break_start is None:
			break_start = c.time
		elif (is_explicit_break_end or is_implicit_break_end) and break_start is not None:
			break_end = c.time
			duration_secs = int((break_end - break_start).total_seconds())
			mins = max(0, duration_secs // 60)
			hrs = mins // 60
			rem_mins = mins % 60
			if hrs > 0:
				dur_str = f"{hrs}h {rem_mins}m"
			else:
				dur_str = f"{rem_mins}m"

			break_logs.append({
				"break_in": str(break_start),
				"break_out": str(break_end),
				"duration": dur_str,
				"is_ongoing": False
			})
			break_start = None

	if break_start is not None:
		break_logs.append({
			"break_in": str(break_start),
			"break_out": None,
			"duration": "On Break",
			"is_ongoing": True
		})

	return break_logs


@frappe.whitelist()
def get_attendance_details(attendance_id):
	"""
	Fetch details for a single Attendance record, including break logs.
	"""
	if not attendance_id:
		frappe.throw(_("Attendance ID is required"))

	att = frappe.get_doc("Attendance", attendance_id)

	can_delete = can_user_delete()
	can_edit = can_user_edit()
	break_logs = get_attendance_break_logs(att.employee, att.attendance_date)

	return {
		"attendance_id": att.name,
		"employee": att.employee,
		"employee_name": att.employee_name,
		"date": att.attendance_date,
		"status": att.status,
		"in_time": att.in_time,
		"out_time": att.out_time,
		"working_hours": att.working_hours,
		"shift": att.shift,
		"late_entry": att.late_entry,
		"early_exit": att.early_exit,
		"docstatus": att.docstatus,
		"can_edit": can_edit,
		"can_delete": can_delete,
		"break_logs": break_logs,
	}

@frappe.whitelist()
def can_create_attendance():
	"""
	Returns True if the current user has permission to create an Attendance.
	This is true for 'HR Manager', 'System Manager', or users with explicit create permissions on the 'Attendance' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Attendance", "create"):
		return True

	return False

@frappe.whitelist()
def can_read_attendance():
	"""
	Returns True if the current user has permission to read an Attendance.
	This is true for 'HR Manager', 'System Manager', or users with explicit read permissions on the 'Attendance' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Attendance", "read"):
		return True

	return False

@frappe.whitelist()
def can_edit_attendance():
	"""
	Returns True if the current user has permission to edit an Attendance.
	This is true for 'HR Manager', 'System Manager', or users with explicit edit permissions on the 'Attendance' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Attendance", "write"):
		return True

	return False

@frappe.whitelist()
def can_delete_attendance():
	"""
	Returns True if the current user has permission to delete an Attendance.
	This is true for 'HR Manager', 'System Manager', or users with explicit delete permissions on the 'Attendance' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Attendance", "delete"):
		return True

	return False

@frappe.whitelist()
def can_create_employee_checkin():
	"""
	Returns True if the current user has permission to create an Employee Checkin.
	This is true for 'HR Manager', 'System Manager', or users with explicit create permissions on the 'Employee Checkin' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Employee Checkin", "create"):
		return True

	return False

@frappe.whitelist()
def can_read_employee_checkin():
	"""
	Returns True if the current user has permission to read an Employee Checkin.
	This is true for 'HR Manager', 'System Manager', or users with explicit read permissions on the 'Employee Checkin' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Employee Checkin", "read"):
		return True

	return False

@frappe.whitelist()
def can_edit_employee_checkin():
	"""
	Returns True if the current user has permission to edit an Employee Checkin.
	This is true for 'HR Manager', 'System Manager', or users with explicit edit permissions on the 'Employee Checkin' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Employee Checkin", "write"):
		return True

	return False

@frappe.whitelist()
def can_delete_employee_checkin():
	"""
	Returns True if the current user has permission to delete an Employee Checkin.
	This is true for 'HR Manager', 'System Manager', or users with explicit delete permissions on the 'Employee Checkin' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Employee Checkin", "delete"):
		return True

	return False

@frappe.whitelist()
def can_create_attendance_request():
	"""
	Returns True if the current user has permission to create an Attendance Request.
	This is true for 'HR Manager', 'System Manager', or users with explicit create permissions on the 'Attendance Request' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Attendance Request", "create"):
		return True

	return False

@frappe.whitelist()
def can_read_attendance_request():
	"""
	Returns True if the current user has permission to read an Attendance Request.
	This is true for 'HR Manager', 'System Manager', or users with explicit read permissions on the 'Attendance Request' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Attendance Request", "read"):
		return True

	return False

@frappe.whitelist()
def can_edit_attendance_request():
	"""
	Returns True if the current user has permission to edit an Attendance Request.
	This is true for 'HR Manager', 'System Manager', or users with explicit edit permissions on the 'Attendance Request' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Attendance Request", "write"):
		return True

	return False

@frappe.whitelist()
def can_delete_attendance_request():
	"""
	Returns True if the current user has permission to delete an Attendance Request.
	This is true for 'HR Manager', 'System Manager', or users with explicit delete permissions on the 'Attendance Request' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Attendance Request", "delete"):
		return True

	return False

@frappe.whitelist()
def can_submit_attendance_request():
	"""
	Returns True if the current user has permission to submit/approve an Attendance Request.
	This is true for 'HR Manager', 'System Manager', or users with explicit submit permissions on the 'Attendance Request' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Attendance Request", "submit"):
		return True

	return False


@frappe.whitelist()
def can_read_timesheet():
	"""
	Returns True if the current user has permission to read a Timesheet.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Timesheet", "read"):
		return True
	return False

@frappe.whitelist()
def can_create_timesheet():
	"""
	Returns True if the current user has permission to create a Timesheet.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Timesheet", "create"):
		return True
	return False

@frappe.whitelist()
def can_edit_timesheet():
	"""
	Returns True if the current user has permission to edit a Timesheet.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Timesheet", "write"):
		return True
	return False

@frappe.whitelist()
def can_delete_timesheet():
	"""
	Returns True if the current user has permission to delete a Timesheet.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Timesheet", "delete"):
		return True
	return False


@frappe.whitelist()
def get_time_sheet_list(search_text=None, employee=None, include_void=False, page=1, page_size=0):
	"""
	Fetch a list of Timesheets.
	Supports searching by Timesheet ID (name), filtering by employee,
	optional inclusion of Cancelled (void) rows, and server-side pagination.
	`page_size = 0` returns the full list (legacy, no pagination).
	"""
	filters = {}
	if search_text:
		filters["name"] = ["like", f"%{search_text}%"]

	if not include_void:
		filters["status"] = ["!=", "Cancelled"]

	if can_manage_timesheets():
		if employee:
			filters["employee"] = employee
	else:
		current_employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user, "status": "Active"}, "name")
		if not current_employee:
			if page_size > 0:
				return {"data": [], "total": 0, "page": page, "page_size": page_size}
			return []
		filters["employee"] = current_employee

	timesheets = frappe.get_list(
		"Timesheet",
		filters=filters,
		fields=["name", "employee", "employee_name", "status", "start_date", "end_date", "total_hours"],
		order_by="creation desc",
		limit_page_length=page_size if page_size > 0 else 0,
		limit_start=(max(1, page) - 1) * page_size if page_size > 0 else 0
	)

	if page_size > 0:
		total = frappe.db.count("Timesheet", filters=filters)
		return {"data": timesheets, "total": total, "page": page, "page_size": page_size}
	return timesheets


@frappe.whitelist()
def get_timesheet_list_details(name):
	"""
	Fetch full details of a Timesheet, including child logs.
	"""
	return frappe.get_doc("Timesheet", name).as_dict()


@frappe.whitelist()
def get_activity_type():
	"""
	Fetch all Activity Types.
	"""
	return frappe.get_list("Activity Type", fields=["name"])


@frappe.whitelist()
def save_timesheet(employee, start_date, time_logs, name=None, submit=False):
	"""
	Create or edit a Timesheet document.
	Supports amending submitted Timesheets with atomic cancel & amend and rollback on failure.
	"""
	import json
	from frappe.utils import cint, flt

	if isinstance(time_logs, str):
		time_logs = json.loads(time_logs)

	do_submit = cint(submit) == 1

	try:
		if name:
			old_doc = frappe.get_doc("Timesheet", name)
			if old_doc.docstatus == 2:
				frappe.throw(_("Cannot edit a cancelled Timesheet."))

			if old_doc.docstatus == 1:
				# Step 1: Cancel the submitted Timesheet
				old_doc.cancel()

				# Step 2: Create amended draft copy
				new_doc = frappe.copy_doc(old_doc, ignore_no_copy=False)
				new_doc.amended_from = old_doc.name
				new_doc.employee = employee
				new_doc.start_date = start_date
				new_doc.set("time_logs", [])

				for row in time_logs:
					new_doc.append(
						"time_logs",
						{
							"activity_type": row.get("activity_type"),
							"from_time": row.get("from_time"),
							"to_time": row.get("to_time"),
							"hours": flt(row.get("hours")),
							"description": row.get("description"),
							"completed": row.get("completed", 0),
						},
					)

				# Step 3: Save amended timesheet
				new_doc.save()

				# Step 4: Submit if requested
				if do_submit:
					new_doc.submit()

				frappe.db.commit()
				return new_doc.name

			# Draft Timesheet: edit in place
			ts = old_doc
			ts.employee = employee
			ts.start_date = start_date
			ts.set("time_logs", [])
		else:
			company = frappe.db.get_value("Employee", employee, "company")
			ts = frappe.new_doc("Timesheet")
			ts.employee = employee
			ts.company = company
			ts.start_date = start_date

		for row in time_logs:
			ts.append(
				"time_logs",
				{
					"activity_type": row.get("activity_type"),
					"from_time": row.get("from_time"),
					"to_time": row.get("to_time"),
					"hours": flt(row.get("hours")),
					"description": row.get("description"),
					"completed": row.get("completed", 0),
				},
			)

		ts.save()
		if do_submit:
			ts.submit()

		frappe.db.commit()
		return ts.name
	except Exception as e:
		frappe.db.rollback()
		msg = _extract_frappe_message() or str(e)
		frappe.clear_messages()
		msg = frappe.utils.strip_html_tags(msg)
		frappe.throw(msg)


@frappe.whitelist()
def can_manage_timesheets():
	"""
	Returns True if the current user is HR Manager, System Manager, or Administrator.
	"""
	user = frappe.session.user
	if user == "Administrator":
		return True
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	return False


@frappe.whitelist()
def delete_timesheet(name):
	"""
	Cancel and delete a Timesheet document with transaction safety.
	"""
	try:
		ts = frappe.get_doc("Timesheet", name)
		if ts.docstatus == 1:
			ts.cancel()
		frappe.delete_doc("Timesheet", name)
		frappe.db.commit()
		return {"success": True}
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(message=frappe.get_traceback(), title="Failed to delete Timesheet")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def submit_timesheet(name):
	"""
	Submit a Timesheet document with transaction safety.
	"""
	try:
		ts = frappe.get_doc("Timesheet", name)
		ts.submit()
		frappe.db.commit()
		return {"success": True}
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(message=frappe.get_traceback(), title="Failed to submit Timesheet")
		return {"success": False, "error": str(e)}



@frappe.whitelist()
def get_float_precision():
	"""Returns float precision from system settings."""
	return frappe.db.get_single_value("System Settings", "float_precision") or 2


@frappe.whitelist()
def export_monthly_attendance_sheet(from_date=None, to_date=None, month=None, employee=None, department=None, branch=None, export=False, pdf=False, late_entry=None, early_exit=None):
	"""
	Export or generate PDF for Monthly Attendance Sheet report with flexible date range (from_date to to_date).
	"""
	import calendar
	import datetime

	import frappe
	from frappe import _
	from frappe.utils import cint, getdate, now_datetime
	from frappe.utils.pdf import get_pdf
	from frappe.utils.xlsxutils import build_xlsx_response

	from arijentek_core.api.reports import get_monthly_attendance_report

	res = get_monthly_attendance_report(from_date=from_date, to_date=to_date, month=month, employee=employee, department=department, branch=branch, late_entry=late_entry, early_exit=early_exit)

	is_export = cint(export) if isinstance(export, (int, str)) and str(export).isdigit() else frappe.parse_json(export)
	is_pdf = cint(pdf) if isinstance(pdf, (int, str)) and str(pdf).isdigit() else frappe.parse_json(pdf)

	if is_export:
		columns = res.get("columns", [])
		data = res.get("data", [])
		xlsx_data = [[c["label"] for c in columns]]
		for row in data:
			xlsx_data.append([row.get(c["fieldname"], "") for c in columns])
		return build_xlsx_response(xlsx_data, "Monthly_Attendance_Sheet")

	if is_pdf:
		columns = res.get("columns", [])
		data = res.get("data", [])

		start_d = res.get("start_date") or from_date
		end_d = res.get("end_date") or to_date
		month_label = f"{start_d} to {end_d}" if start_d and end_d else (month or "Attendance Sheet")

		# Extract Day Columns dynamically from returned columns
		day_columns = []
		for c in columns:
			fn = c["fieldname"]
			if fn.startswith("day_"):
				# Label is e.g. "1 Wed" or "15 Thu"
				parts = c["label"].split(" ")
				day_num = parts[0] if parts else fn.replace("day_", "")
				day_abbr = parts[1] if len(parts) > 1 else ""
				day_columns.append({
					"day_num": day_num,
					"day_abbr": day_abbr,
					"fieldname": fn
				})

		company_name = frappe.db.get_single_value("Global Defaults", "default_company") or "Company"

		context = {
			"report_title": _("Monthly Attendance Sheet"),
			"company_name": company_name,
			"month_label": month_label,
			"selected_department": department,
			"selected_branch": branch,
			"selected_employee": employee,
			"generated_on": now_datetime().strftime("%Y-%m-%d %H:%M"),
			"columns": columns,
			"day_columns": day_columns,
			"data": data
		}

		html_content = frappe.render_template("arijentek_core/templates/reports/monthly_attendance_sheet.html", context)

		pdf_options = {
			"page-size": "A4",
			"orientation": "Landscape",
			"margin-top": "10mm",
			"margin-bottom": "10mm",
			"margin-left": "8mm",
			"margin-right": "8mm",
			"encoding": "UTF-8"
		}

		pdf_binary = get_pdf(html_content, options=pdf_options)

		safe_month_label = month_label.replace(' ', '_').replace('/', '-')
		frappe.local.response.filename = f"Monthly_Attendance_Sheet_{safe_month_label}.pdf"
		frappe.local.response.filecontent = pdf_binary
		frappe.local.response.type = "pdf"
		return

	return res


report_mark_attendance_list = export_monthly_attendance_sheet


@frappe.whitelist()
def report_daily_timesheet_summary(from_date=None, to_date=None, employee=None, department=None, designation=None, export=False, pdf=False):
	import frappe
	from frappe import _
	from frappe.utils import cint, flt, now_datetime, nowdate
	from frappe.utils.pdf import get_pdf

	from arijentek_core.api.reports import get_daily_timesheet_summary_report

	res = get_daily_timesheet_summary_report(
		from_date=from_date,
		to_date=to_date,
		employee=employee,
		department=department,
		designation=designation,
		export=export
	)

	is_pdf = cint(pdf) if isinstance(pdf, (int, str)) and str(pdf).isdigit() else frappe.parse_json(pdf)

	if is_pdf:
		data = res.get("data", []) if isinstance(res, dict) else []
		columns = res.get("columns", []) if isinstance(res, dict) else []

		company_name = frappe.db.get_single_value("Global Defaults", "default_company") or "Company"

		# Format Date Range Label
		if from_date and to_date:
			date_range_label = f"{from_date} to {to_date}"
		elif from_date:
			date_range_label = from_date
		elif to_date:
			date_range_label = to_date
		else:
			date_range_label = nowdate()

		total_hours = round(sum(flt(r.get("hours", 0)) for r in data), 2)

		# Pre-format time_span for template rendering
		for r in data:
			ft = str(r.get("from_time") or "")
			tt = str(r.get("to_time") or "")
			f_time = ft.split(" ")[-1] if " " in ft else ft
			t_time = tt.split(" ")[-1] if " " in tt else tt
			r["time_span"] = f"{f_time} - {t_time}" if (f_time and t_time) else "-"

		context = {
			"report_title": _("Daily Timesheet Summary"),
			"company_name": company_name,
			"date_range_label": date_range_label,
			"selected_department": department,
			"selected_designation": designation,
			"selected_employee": employee,
			"generated_on": now_datetime().strftime("%Y-%m-%d %H:%M"),
			"columns": columns,
			"data": data,
			"total_hours": total_hours
		}

		html_content = frappe.render_template("arijentek_core/templates/reports/daily_timesheet_summary.html", context)

		pdf_options = {
			"page-size": "A4",
			"orientation": "Landscape",
			"margin-top": "10mm",
			"margin-bottom": "10mm",
			"margin-left": "8mm",
			"margin-right": "8mm",
			"encoding": "UTF-8"
		}

		pdf_binary = get_pdf(html_content, options=pdf_options)

		frappe.local.response.filename = f"Daily_Timesheet_Summary_{from_date or 'report'}.pdf"
		frappe.local.response.filecontent = pdf_binary
		frappe.local.response.type = "pdf"
		return

	return res

def mark_daily_attendance():
	"""
	Scheduled entry point for attendance processing.
	Calculates the target date based on 15 hours ago using system time and processes attendance for all employees.
	"""
	if is_auto_attendance_disabled():
		return
	target_date = (now_datetime() - datetime.timedelta(hours=15)).date()
	_mark_attendance_for_date(target_date)

def _mark_attendance_for_date(date):
	"""
	Find all active employees and process their attendance for the given date.
	"""
	employees = frappe.get_all("Employee", filters={"status": "Active"}, pluck="name")
	for employee in employees:
		try:
			_process_employee_date(employee, date)
		except Exception:
			frappe.log_error("Auto Attendance Error", f"Failed for {employee} on {date}\n{frappe.get_traceback()}")
	frappe.db.commit()

def _process_employee_date(employee_id, date):
	"""
	Determine and create missing attendance records for an employee on a specific date.
	Checks that at least 15 hours have elapsed since clock-in (or date start) before marking attendance.
	"""
	if is_auto_attendance_disabled():
		return
	from frappe.utils import get_datetime

	# 1. Check if Attendance already exists
	existing_att = frappe.db.get_value(
		"Attendance",
		{"employee": employee_id, "attendance_date": date, "docstatus": ("!=", 2)},
		["name", "in_time", "out_time", "status"],
		as_dict=True,
	)

	if existing_att:
		# If out_time exists, employee clocked out properly
		if existing_att.out_time:
			return

		# If only in_time exists (employee forgot to clock out)
		if existing_att.in_time:
			current_time = get_employee_now_datetime(employee_id)
			time_diff = (current_time - existing_att.in_time).total_seconds() / 3600.0
			if time_diff <= 15:
				return  # Shift might still be active within 15 hours

			# More than 15 hours elapsed with no out_time -> mark as Absent
			if existing_att.status != "Absent":
				frappe.db.set_value(
					"Attendance",
					existing_att.name,
					{"status": "Absent", "working_hours": 0.0},
					update_modified=True,
				)
				frappe.db.commit()
		return

	# 2. Check if it's a Holiday or Weekly Off
	holiday_list = frappe.db.get_value("Employee", employee_id, "holiday_list")
	if not holiday_list:
		company = frappe.db.get_value("Employee", employee_id, "company")
		if company:
			holiday_list = frappe.db.get_value("Company", company, "default_holiday_list")

	if holiday_list:
		try:
			from erpnext.setup.doctype.holiday_list.holiday_list import is_holiday
			if is_holiday(holiday_list, date):
				return # Ignore making entry for holidays
		except Exception:
			pass

	# 3. Check if On Leave
	if frappe.db.exists("Leave Application", {
		"employee": employee_id,
		"docstatus": 1,
		"status": "Approved",
		"from_date": ("<=", date),
		"to_date": (">=", date)
	}):
		return # On leave, skip

	current_time = get_employee_now_datetime(employee_id)

	# 4. Check if employee clocked in ("IN" log) on this date
	first_log = frappe.db.get_value(
		"Employee Checkin",
		{
			"employee": employee_id,
			"time": ["Between", [f"{date} 00:00:00", f"{date} 23:59:59"]],
			"log_type": "IN"
		},
		["time", "shift"],
		order_by="time asc",
		as_dict=True
	)

	if first_log:
		time_diff = (current_time - first_log.time).total_seconds() / 3600.0
		if time_diff <= 15:
			return # Avoid marking attendance if clock-in is within 15 hours, shift might still be active
	else:
		# No clock-in log on this date. Ensure 15 hours have passed since the start of this date before marking absent.
		date_start = get_datetime(f"{date} 00:00:00")
		hours_since_start = (current_time - date_start).total_seconds() / 3600.0
		if hours_since_start <= 15:
			return # Date start is within 15 hours, do not mark absent yet

	doc_vals = {
		"doctype": "Attendance",
		"employee": employee_id,
		"attendance_date": date,
		"status": "Absent",
		"working_hours": 0.0
	}

	if first_log:
		doc_vals["in_time"] = first_log.time
		if first_log.shift:
			doc_vals["shift"] = first_log.shift

	attendance_doc = frappe.get_doc(doc_vals)
	attendance_doc.insert(ignore_permissions=True)
	attendance_doc.submit()


@frappe.whitelist()
def get_active_sessions_for_reconciliation():
	if not can_mark_attendance():
		frappe.throw(_("Not permitted to access this resource"), frappe.PermissionError)

	from frappe.utils import add_to_date, get_datetime, getdate, now

	now_local = get_datetime(now())
	time_limit = add_to_date(now_local, hours=-36)

	logs = frappe.db.sql("""
		SELECT 
			ec.employee, 
			e.employee_name,
			ec.time, 
			ec.log_type, 
			ec.name as checkin_name,
			ec.shift,
			e.department,
			e.designation
		FROM 
			`tabEmployee Checkin` ec
		INNER JOIN 
			`tabEmployee` e ON ec.employee = e.name
		INNER JOIN (
			SELECT employee, MAX(time) as max_time 
			FROM `tabEmployee Checkin` 
			GROUP BY employee
		) latest ON ec.employee = latest.employee AND ec.time = latest.max_time
		LEFT JOIN
			`tabAttendance` a ON ec.employee = a.employee AND DATE(ec.time) = a.attendance_date AND a.docstatus < 2
		WHERE 
			ec.log_type = 'IN' 
			AND ec.time >= %(time_limit)s
			AND e.status = 'Active'
			AND (a.name IS NULL OR a.out_time IS NULL OR a.out_time < ec.time)
		ORDER BY 
			ec.time ASC
	""", {"time_limit": time_limit}, as_dict=True)

	result = []

	for log in logs:
		emp_now = get_employee_now_datetime(log.employee)
		delta = emp_now - log.time
		elapsed_hours = max(0.0, delta.total_seconds() / 3600.0)

		# Flag those who have checked in for a long time (> 12 hours) and might have forgot to clock out
		forgot_to_clock_out = elapsed_hours > 12.0

		result.append({
			"employee": log.employee,
			"employee_name": log.employee_name,
			"checkin_time": log.time,
			"elapsed_hours": round(elapsed_hours, 1),
			"forgot_to_clock_out": forgot_to_clock_out,
			"shift": log.shift,
			"department": log.department,
			"designation": log.designation,
			"date": str(getdate(log.time))
		})

	return result


@frappe.whitelist()
def reconcile_active_sessions(data: str):
	if not can_mark_attendance():
		frappe.throw(_("Not permitted to reconcile attendance"), frappe.PermissionError)

	import json

	from frappe.utils import add_to_date, get_datetime, getdate

	try:
		records = json.loads(data)
	except Exception:
		frappe.throw(_("Invalid JSON data provided"))

	if not isinstance(records, list):
		records = [records]

	for rec in records:
		employee = rec.get("employee")
		date = rec.get("date")
		status = rec.get("status")
		checkin_time = rec.get("checkin_time")
		checkout_time = rec.get("checkout_time")
		shift = rec.get("shift")

		if not employee or not date or not status:
			continue

		out_dt = None
		if checkout_time:
			out_dt = get_datetime(checkout_time)
		elif checkin_time:
			ci_dt = get_datetime(checkin_time)
			out_dt = add_to_date(ci_dt, hours=9)

		working_hours = 0.0
		if checkin_time and out_dt:
			ci_dt = get_datetime(checkin_time)
			working_hours = round((out_dt - ci_dt).total_seconds() / 3600.0, 2)

		# 1. Create or Update Attendance
		existing = frappe.db.exists("Attendance", {"employee": employee, "attendance_date": date, "docstatus": ["<", 2]})
		if existing:
			frappe.db.set_value("Attendance", existing, {
				"status": status,
				"shift": shift,
				"out_time": out_dt,
				"working_hours": working_hours,
			})
		else:
			att_doc = frappe.get_doc({
				"doctype": "Attendance",
				"employee": employee,
				"attendance_date": date,
				"status": status,
				"shift": shift,
				"in_time": get_datetime(checkin_time) if checkin_time else None,
				"out_time": out_dt,
				"working_hours": working_hours,
			})
			att_doc.insert(ignore_permissions=True)
			att_doc.submit()

		# 2. Close check-in session by creating synthetic OUT log
		out_dt = None
		if checkout_time:
			out_dt = get_datetime(checkout_time)
		elif checkin_time:
			ci_dt = get_datetime(checkin_time)
			out_dt = add_to_date(ci_dt, hours=9)

		if out_dt:
			if not frappe.db.exists("Employee Checkin", {"employee": employee, "time": out_dt, "log_type": "OUT"}):
				checkin_doc = frappe.get_doc({
					"doctype": "Employee Checkin",
					"employee": employee,
					"time": out_dt,
					"log_type": "OUT",
					"device_id": "Portal Reconciler",
					"shift": shift,
					"skip_auto_attendance": 1
				})
				checkin_doc.insert(ignore_permissions=True)

			# Timesheet Integration - Close timesheet if enabled
			try:
				timesheet_enabled = frappe.utils.cint(frappe.db.get_single_value("HR Settings", "timesheet_with_clockin"))
			except Exception:
				timesheet_enabled = 0

			if timesheet_enabled:
				timesheet_name = _get_active_timesheet(employee, out_dt.date())
				if timesheet_name:
					end_timesheet_log(timesheet_name, out_dt, submit=True)

	return {"success": True}

# ---------------------------------------------------------------------------
# Attendance Request Report API
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_attendance_request_filter_options():
	"""
	Returns filter options for the Attendance Request report.
	"""
	# Get visible employees for the current user
	employees = []
	try:
		visible_employees = get_employee_list_for_attendance()
		if visible_employees:
			employees = [
				{"id": e["name"], "name": f"{e['name']} - {e.get('employee_name', '')}"}
				for e in visible_employees
			]
	except Exception:
		pass

	return {
		"employees": employees
	}


@frappe.whitelist()
def report_attendance_request_list(from_date=None, to_date=None, employee=None, status=None, export=False, pdf=False):
	"""
	Returns attendance requests for the report.
	"""
	import frappe
	from frappe import _
	from frappe.utils import cint, now_datetime
	from frappe.utils.pdf import get_pdf
	from frappe.utils.xlsxutils import build_xlsx_response

	# Verify permissions (basic check)
	if not frappe.has_permission("Attendance Request", "read"):
		frappe.throw(_("You do not have permission to view Attendance Requests"))

	conditions = ["1=1"]
	params = {}

	if employee:
		conditions.append("employee = %(employee)s")
		params["employee"] = employee

	if from_date and to_date:
		conditions.append("from_date <= %(to_date)s AND to_date >= %(from_date)s")
		params["from_date"] = from_date
		params["to_date"] = to_date

	if status:
		status = str(status).upper()
		if status == "DRAFT":
			conditions.append("docstatus = 0")
		elif status in ("SUBMITTED", "APPROVED"):
			conditions.append("docstatus = 1")
		elif status in ("REJECTED", "CANCELLED"):
			conditions.append("docstatus = 2")

	query = f"""
		SELECT
			name, employee, employee_name, from_date, to_date, half_day, reason, explanation, docstatus
		FROM `tabAttendance Request`
		WHERE {" AND ".join(conditions)}
		ORDER BY creation DESC
	"""

	data = frappe.db.sql(query, params, as_dict=True)

	columns = [
		{"label": "Request ID", "fieldname": "name"},
		{"label": "Employee ID", "fieldname": "employee"},
		{"label": "Employee Name", "fieldname": "employee_name"},
		{"label": "From Date", "fieldname": "from_date"},
		{"label": "To Date", "fieldname": "to_date"},
		{"label": "Half Day", "fieldname": "half_day"},
		{"label": "Reason", "fieldname": "reason"},
		{"label": "Explanation", "fieldname": "explanation"},
		{"label": "Status", "fieldname": "status"},
	]

	# Format data
	for row in data:
		if row.get("from_date"):
			row["from_date"] = str(row["from_date"])
		if row.get("to_date"):
			row["to_date"] = str(row["to_date"])

		row["half_day"] = "Yes" if row.get("half_day") else "No"

		ds = row.get("docstatus", 0)
		if ds == 0:
			row["status"] = "Draft"
		elif ds == 1:
			row["status"] = "Approved"
		else:
			row["status"] = "Cancelled"

	is_export = cint(export) if isinstance(export, (int, str)) and str(export).isdigit() else frappe.parse_json(export)
	is_pdf = cint(pdf) if isinstance(pdf, (int, str)) and str(pdf).isdigit() else frappe.parse_json(pdf)

	if is_export:
		xlsx_data = [[c["label"] for c in columns]]
		for row in data:
			xlsx_data.append([row.get(c["fieldname"], "") for c in columns])
		return build_xlsx_response(xlsx_data, "Attendance_Request_Report")

	if is_pdf:
		company_name = frappe.db.get_single_value("Global Defaults", "default_company") or "Company"

		date_range = "All Dates"
		if from_date and to_date:
			date_range = f"{from_date} to {to_date}"

		context = {
			"report_title": _("Attendance Request Report"),
			"company_name": company_name,
			"date_range": date_range,
			"selected_employee": employee,
			"selected_status": status,
			"generated_on": now_datetime().strftime("%Y-%m-%d %H:%M"),
			"columns": columns,
			"data": data
		}

		html_content = frappe.render_template("arijentek_core/templates/reports/attendance_request_report.html", context)

		pdf_options = {
			"page-size": "A4",
			"orientation": "Landscape",
			"margin-top": "10mm",
			"margin-bottom": "10mm",
			"margin-left": "8mm",
			"margin-right": "8mm",
			"encoding": "UTF-8"
		}

		pdf_binary = get_pdf(html_content, options=pdf_options)

		safe_date_range = date_range.replace(' ', '_').replace('/', '-')
		frappe.local.response.filename = f"Attendance_Requests_{safe_date_range}.pdf"
		frappe.local.response.filecontent = pdf_binary
		frappe.local.response.type = "pdf"
		return

	return {
		"columns": columns,
		"data": data
	}

# ---------------------------------------------------------------------------
# Attendance Without Clock In/Out Report API
# ---------------------------------------------------------------------------

@frappe.whitelist()
def report_attendance_no_clock_list(from_date=None, to_date=None, employee=None, forgot_clock_out=False, export=False, pdf=False):
	"""
	Returns attendance entries that have missing clock in/out or specifically forgot clock out (in_time present, out_time missing).
	"""
	import frappe
	from frappe import _
	from frappe.utils import cint, now_datetime
	from frappe.utils.pdf import get_pdf
	from frappe.utils.xlsxutils import build_xlsx_response

	# Verify permissions
	if not frappe.has_permission("Attendance", "read"):
		frappe.throw(_("You do not have permission to view Attendance records"))

	is_forgot = cint(forgot_clock_out) if isinstance(forgot_clock_out, (int, str)) and str(forgot_clock_out).isdigit() else frappe.parse_json(forgot_clock_out)

	conditions = ["docstatus < 2"]
	if is_forgot:
		conditions.append("(in_time IS NOT NULL AND in_time != '' AND (out_time IS NULL OR out_time = ''))")
	else:
		conditions.append("((in_time IS NULL OR in_time = '') OR (out_time IS NULL OR out_time = ''))")

	params = {}


	if employee:
		conditions.append("employee = %(employee)s")
		params["employee"] = employee

	if from_date and to_date:
		conditions.append("attendance_date <= %(to_date)s AND attendance_date >= %(from_date)s")
		params["from_date"] = from_date
		params["to_date"] = to_date

	query = f"""
		SELECT
			name, employee, employee_name, attendance_date, in_time, out_time, status, shift
		FROM `tabAttendance`
		WHERE {" AND ".join(conditions)}
		ORDER BY attendance_date DESC, employee ASC
	"""

	data = frappe.db.sql(query, params, as_dict=True)

	columns = [
		{"label": "ID", "fieldname": "name"},
		{"label": "Employee ID", "fieldname": "employee"},
		{"label": "Employee Name", "fieldname": "employee_name"},
		{"label": "Date", "fieldname": "attendance_date"},
		{"label": "In Time", "fieldname": "in_time"},
		{"label": "Out Time", "fieldname": "out_time"},
		{"label": "Status", "fieldname": "status"},
		{"label": "Shift", "fieldname": "shift"},
	]

	# Format data
	for row in data:
		if row.get("attendance_date"):
			row["attendance_date"] = str(row["attendance_date"])
		if row.get("in_time"):
			row["in_time"] = str(row["in_time"])
		if row.get("out_time"):
			row["out_time"] = str(row["out_time"])

	is_export = cint(export) if isinstance(export, (int, str)) and str(export).isdigit() else frappe.parse_json(export)
	is_pdf = cint(pdf) if isinstance(pdf, (int, str)) and str(pdf).isdigit() else frappe.parse_json(pdf)

	if is_export:
		xlsx_data = [[c["label"] for c in columns]]
		for row in data:
			xlsx_data.append([row.get(c["fieldname"], "") for c in columns])
		return build_xlsx_response(xlsx_data, "Attendance_Without_Clock")

	if is_pdf:
		company_name = frappe.db.get_single_value("Global Defaults", "default_company") or "Company"

		date_range = "All Dates"
		if from_date and to_date:
			date_range = f"{from_date} to {to_date}"

		context = {
			"report_title": _("Attendance Without Clock"),
			"company_name": company_name,
			"date_range": date_range,
			"selected_employee": employee,
			"generated_on": now_datetime().strftime("%Y-%m-%d %H:%M"),
			"columns": columns,
			"data": data
		}

		html_content = frappe.render_template("arijentek_core/templates/reports/attendance_no_clock_report.html", context)

		pdf_options = {
			"page-size": "A4",
			"orientation": "Portrait",
			"margin-top": "10mm",
			"margin-bottom": "10mm",
			"margin-left": "8mm",
			"margin-right": "8mm",
			"encoding": "UTF-8"
		}

		pdf_binary = get_pdf(html_content, options=pdf_options)

		safe_date_range = date_range.replace(' ', '_').replace('/', '-')
		frappe.local.response.filename = f"Attendance_Without_Clock_{safe_date_range}.pdf"
		frappe.local.response.filecontent = pdf_binary
		frappe.local.response.type = "pdf"
		return

	return {
		"columns": columns,
		"data": data
	}



