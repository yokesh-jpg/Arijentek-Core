import frappe
from frappe import _
from frappe.utils import now_datetime, nowdate

from arijentek_core.api.rate_limiter import user_rate_limit

ATTENDANCE_RATE_LIMIT = 10
ATTENDANCE_RATE_LIMIT_SECONDS = 60
MAX_SHIFT_HOURS = 12


@frappe.whitelist()
@user_rate_limit(limit=ATTENDANCE_RATE_LIMIT, seconds=ATTENDANCE_RATE_LIMIT_SECONDS)
def punch(employee: str | None = None, timestamp: str | None = None):
	"""Punch endpoint with enforcement: one IN + one OUT per day, 12hr max."""
	employee = _validate_and_get_employee(employee)
	timestamp = _validate_timestamp(timestamp)
	today = nowdate()

	# Get today's checkins
	today_checkins = frappe.db.sql(
		"""
		SELECT time, log_type FROM `tabEmployee Checkin`
		WHERE employee = %s 
		  AND DATE(time) = %s
		  AND COALESCE(device_id, '') NOT IN ('BREAK_START', 'BREAK_END')
		ORDER BY time ASC
		""",
		(employee, today),
		as_dict=True,
	)

	has_in = any(c.log_type == "IN" for c in today_checkins)
	has_out = any(c.log_type == "OUT" for c in today_checkins)

	if has_in and has_out:
		frappe.throw(_("You have already clocked in and out today"))

	if not has_in:
		log_type = "IN"
	elif has_in and not has_out:
		log_type = "OUT"
		# Enforce max shift duration
		in_time = next(c.time for c in today_checkins if c.log_type == "IN")
		hours_worked = (timestamp - in_time).total_seconds() / 3600
		if hours_worked > MAX_SHIFT_HOURS:
			frappe.throw(_(f"Shift exceeded {MAX_SHIFT_HOURS} hours. Please contact HR."))
	else:
		frappe.throw(_("Invalid state"))

	checkin = frappe.get_doc(
		{
			"doctype": "Employee Checkin",
			"employee": employee,
			"time": timestamp,
			"log_type": log_type,
			"device_id": "Web/Manual",
		}
	)
	checkin.insert()
	frappe.db.commit()

	return {"status": "success", "log_type": log_type, "time": str(timestamp), "employee": employee}


@frappe.whitelist()
@user_rate_limit(limit=ATTENDANCE_RATE_LIMIT, seconds=ATTENDANCE_RATE_LIMIT_SECONDS)
def get_status(employee: str | None = None):
	employee = _validate_and_get_employee(employee)

	last_checkin = frappe.db.get_all(
		"Employee Checkin",
		filters={"employee": employee},
		fields=["log_type", "time"],
		order_by="time desc",
		limit=1,
	)

	return {
		"last_log": {"log_type": last_checkin[0].get("log_type"), "time": str(last_checkin[0].get("time"))}
		if last_checkin
		else None
	}


def _validate_and_get_employee(employee=None):
	if employee:
		employee = str(employee).strip()[:50]
		if not frappe.db.exists("Employee", employee):
			frappe.throw(_("Invalid employee"))
		return employee

	employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
	if not employee:
		frappe.throw(_("Employee not found for this user"))
	return employee


def _validate_timestamp(timestamp=None):
	if timestamp:
		try:
			if isinstance(timestamp, str):
				from frappe.utils import get_datetime

				timestamp = get_datetime(timestamp)
			now = now_datetime()
			max_future_seconds = 5
			if (timestamp - now).total_seconds() > max_future_seconds:
				timestamp = now
			return timestamp
		except Exception:
			return now_datetime()
	return now_datetime()


@frappe.whitelist()
def get_dashboard_data():
	"""Get dashboard data for employee"""
	employee = _validate_and_get_employee()

	today = frappe.utils.nowdate()
	month_start = frappe.utils.get_first_day(frappe.utils.nowdate())

	attendance_summary = frappe.db.sql(
		"""
		SELECT status, COUNT(*) as count
		FROM `tabAttendance`
		WHERE employee = %s
			AND attendance_date BETWEEN %s AND %s
			AND docstatus = 1
		GROUP BY status
	""",
		(employee, month_start, today),
		as_dict=True,
	)

	summary = {"Present": 0, "Absent": 0, "Half Day": 0, "On Leave": 0}
	for att in attendance_summary:
		summary[att.status] = att.count

	last_punch = frappe.db.get_all(
		"Employee Checkin",
		filters={"employee": employee},
		fields=["log_type", "time"],
		order_by="time desc",
		limit=1,
	)

	last_punch_data = None
	if last_punch:
		last_punch_data = {"log_type": last_punch[0].log_type, "time": str(last_punch[0].time)}

	return {
		"employee": employee,
		"attendance_summary": summary,
		"last_punch": last_punch_data,
		"current_month": frappe.utils.now_datetime().strftime("%B"),
		"year": frappe.utils.now_datetime().year,
	}


@frappe.whitelist()
def get_attendance_records(month: int | None = None, year: int | None = None):
	employee = _validate_and_get_employee()

	today = frappe.utils.getdate(frappe.utils.nowdate())
	month = int(month) if month else today.month
	year = int(year) if year else today.year

	import calendar

	last_day = calendar.monthrange(year, month)[1]
	start_date = frappe.utils.getdate(f"{year}-{month:02d}-01")
	end_date = frappe.utils.getdate(f"{year}-{month:02d}-{last_day}")

	records = frappe.db.sql(
		"""
		SELECT attendance_date, status, working_hours, in_time, out_time
		FROM `tabAttendance`
		WHERE employee = %s
			AND attendance_date BETWEEN %s AND %s
			AND docstatus = 1
		ORDER BY attendance_date
	""",
		(employee, start_date, end_date),
		as_dict=True,
	)

	return {
		"records": [
			{"date": str(r.attendance_date), "status": r.status, "hours": r.working_hours or 0}
			for r in records
		],
		"period": {"start": str(start_date), "end": str(end_date)},
	}


@frappe.whitelist()
def get_attendance_status():
	"""Get attendance status choices dynamically from DocType metadata"""
	meta = frappe.get_meta("Attendance")
	field = meta.get_field("status")
	if field and field.options:
		return [opt.strip() for opt in field.options.split("\n") if opt.strip()]
	return ["Present", "Absent", "Half Day", "On Leave"]


def add_employee_checkins(employee, time, log_type):
	"""Insert an Employee Checkin record with skip_auto_attendance=1."""
	checkin = frappe.new_doc("Employee Checkin")
	checkin.employee = employee
	checkin.time = time
	checkin.log_type = log_type
	checkin.device_id = "Manual"
	checkin.skip_auto_attendance = 1
	checkin.insert(ignore_permissions=True)
	return checkin


def can_add_attendance(employee, date, status, id=None):
	"""Validate if attendance can be added or updated."""
	from frappe.utils import getdate

	# 1. Check if employee exists and is active
	emp_status = frappe.db.get_value("Employee", employee, "status")
	if not emp_status:
		return False, _("Employee {0} does not exist").format(employee)
	if emp_status == "Inactive":
		return False, _("Cannot mark attendance for an Inactive employee {0}").format(employee)

	# 2. Check if date is before joining date
	joining_date = frappe.db.get_value("Employee", employee, "date_of_joining")
	if joining_date and getdate(date) < getdate(joining_date):
		return False, _("Attendance date {0} cannot be less than employee's joining date {1}").format(date, joining_date)

	# 3. Check for duplicate record
	filters = {
		"employee": employee,
		"attendance_date": date,
		"docstatus": ["!=", 2],
	}
	if id:
		filters["name"] = ["!=", id]

	duplicate = frappe.db.exists("Attendance", filters)
	if duplicate:
		return False, _("Attendance for employee {0} is already marked for date {1}").format(employee, date)

	return True, ""


@frappe.whitelist()
def manual_attendance(employee, date, status, in_time=None, out_time=None, id=None):
	"""Manually mark attendance and record checkins if times are provided."""
	import datetime
	from frappe.utils import get_datetime

	# Check permissions
	from arijentek_core import get_shift_approver_employees
	permitted = [e["name"] for e in get_shift_approver_employees()]
	has_global_permission = frappe.has_permission("Attendance", "write") or frappe.has_permission("Attendance", "create")
	if employee not in permitted and not has_global_permission:
		frappe.throw(_("Not permitted to create or modify Attendance records"), frappe.PermissionError)

	# Safety Healing Check: If the passed ID is cancelled (docstatus == 2), heal it to the active replacement
	if id and frappe.db.get_value("Attendance", id, "docstatus") == 2:
		active_replacement = frappe.db.exists(
			"Attendance", {"employee": employee, "attendance_date": date, "docstatus": ["!=", 2]}
		)
		id = active_replacement or None

	# Run core validations
	allowed, message = can_add_attendance(employee, date, status, id=id)
	if not allowed:
		frappe.throw(message)

	existing = id if id else frappe.db.exists(
		"Attendance", {"employee": employee, "attendance_date": date, "docstatus": ["!=", 2]}
	)

	existing_doc = frappe.get_doc("Attendance", existing) if existing else None

	in_datetime = None
	out_datetime = None

	# 1. Create IN checkin if in_time is provided
	if in_time and str(in_time).strip():
		in_datetime = get_datetime(f"{date} {in_time}:00")
		if not existing_doc or not existing_doc.in_time:
			add_employee_checkins(employee, in_datetime, "IN")
		else:
			in_datetime = existing_doc.in_time

	# 2. Create OUT checkin if out_time is provided
	if out_time and str(out_time).strip():
		out_datetime = get_datetime(f"{date} {out_time}:00")
		# if in_datetime and out_datetime < in_datetime:
		# 	# Overnight shift logic: add 1 day to out_datetime
		# 	out_datetime += datetime.timedelta(days=1)
		
		if not existing_doc or not existing_doc.out_time:
			add_employee_checkins(employee, out_datetime, "OUT")
		else:
			out_datetime = existing_doc.out_time

	# 3. Calculate working hours
	working_hours = 0.0
	if in_datetime and out_datetime:
		diff_seconds = (out_datetime - in_datetime).total_seconds()
		working_hours = round(diff_seconds / 3600.0, 2)

	# 4. Create or update Attendance record
	attendance_data = {
		"doctype": "Attendance",
		"employee": employee,
		"attendance_date": date,
		"status": status,
		"working_hours": working_hours,
		"in_time": in_datetime,
		"out_time": out_datetime,
	}

	if existing:
		existing_doc = frappe.get_doc("Attendance", existing)
		if existing_doc.docstatus == 1:
			existing_doc.flags.ignore_permissions = True
			existing_doc.cancel()
			
			new_attendance = frappe.new_doc("Attendance")
			new_attendance.update(attendance_data)
			new_attendance.insert(ignore_permissions=True)
			new_attendance.flags.ignore_permissions = True
			new_attendance.submit()
			attendance_name = new_attendance.name
		else:
			existing_doc.update(attendance_data)
			existing_doc.save(ignore_permissions=True)
			existing_doc.flags.ignore_permissions = True
			existing_doc.submit()
			attendance_name = existing_doc.name
	else:
		attendance = frappe.new_doc("Attendance")
		attendance.update(attendance_data)
		attendance.insert(ignore_permissions=True)
		attendance.flags.ignore_permissions = True
		attendance.submit()
		attendance_name = attendance.name

	frappe.db.commit()
	return {"status": "success", "attendance": attendance_name}


def can_delete(name):
	"""Check if an attendance record can be deleted."""
	if not name:
		return False, _("Attendance ID is required")

	if not frappe.db.exists("Attendance", name):
		return False, _("Attendance record {0} not found").format(name)

	doc = frappe.get_doc("Attendance", name)

	# Permission check: the user must have permission to delete Attendance or be a manager of this employee
	from arijentek_core import get_shift_approver_employees
	permitted = [e["name"] for e in get_shift_approver_employees()]
	if doc.employee not in permitted and not frappe.has_permission("Attendance", "delete", doc):
		return False, _("You do not have permission to delete this attendance record")

	# Check for submitted salary slip covering the attendance date
	salary_slip_exists = frappe.db.exists(
		"Salary Slip",
		{
			"employee": doc.employee,
			"start_date": ["<=", doc.attendance_date],
			"end_date": [">=", doc.attendance_date],
			"docstatus": 1,
		}
	)
	if salary_slip_exists:
		return False, _("Cannot delete attendance because Salary Slip {0} is already submitted for this period.").format(salary_slip_exists)

	return True, ""


@frappe.whitelist()
def delete_attendance(name):
	"""Delete an Attendance record after performing validations."""
	allowed, message = can_delete(name)
	if not allowed:
		return {"status": "failed", "message": message}

	doc = frappe.get_doc("Attendance", name)
	if doc.docstatus == 1:
		doc.flags.ignore_permissions = True
		doc.cancel()

	frappe.delete_doc("Attendance", name, ignore_permissions=True)
	frappe.db.commit()

	return {"status": "success", "message": _("Attendance record deleted successfully")}


@frappe.whitelist()
def create_attendance_request(from_date, to_date, reason, explanation=None):
	"""Create an Attendance Request as draft."""
	employee = _validate_and_get_employee()

	if not from_date or not to_date or not reason:
		return {"status": "failed", "message": _("From Date, To Date and Reason are mandatory fields.")}

	# Perform validations
	valid, message = validate_attendance_request(employee, from_date, to_date)
	if not valid:
		return {"status": "failed", "message": message}

	company = frappe.db.get_value("Employee", employee, "company")
	if not company:
		return {"status": "failed", "message": _("Company not found for employee {0}").format(employee)}

	doc = frappe.get_doc(
		{
			"doctype": "Attendance Request",
			"employee": employee,
			"company": company,
			"from_date": from_date,
			"to_date": to_date,
			"reason": reason,
			"explanation": explanation,
			"docstatus": 0, # Draft
		}
	)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()

	return {"status": "success", "name": doc.name}


def validate_attendance_request(employee, from_date, to_date):
	from frappe.utils import getdate

	# 1. Check active employee
	status = frappe.db.get_value("Employee", employee, "status")
	if not status:
		return False, _("Employee record not found.")
	if status == "Inactive":
		return False, _("Cannot request attendance for an Inactive Employee.")

	# 2. Date range validation (from_date <= to_date)
	try:
		fd = getdate(from_date)
		td = getdate(to_date)
	except Exception:
		return False, _("Invalid date format.")

	if fd > td:
		return False, _("To date cannot be less than from date.")

	from frappe.utils import nowdate
	today = getdate(nowdate())
	if fd > today or td > today:
		return False, _("Future dates not allowed.")

	# 3. Date of joining and Relieving date checks
	date_of_joining, relieving_date = frappe.db.get_value(
		"Employee", employee, ["date_of_joining", "relieving_date"]
	)
	if date_of_joining and fd < getdate(date_of_joining):
		return False, _("From date cannot be less than employee's joining date ({0}).").format(frappe.utils.format_date(date_of_joining))
	if relieving_date and td > getdate(relieving_date):
		return False, _("To date cannot be greater than employee's relieving date ({0}).").format(frappe.utils.format_date(relieving_date))

	# 4. Overlap check with existing Attendance Requests
	overlapping = frappe.db.get_all(
		"Attendance Request",
		filters={
			"employee": employee,
			"docstatus": ["<", 2],
			"to_date": [">=", from_date],
			"from_date": ["<=", to_date],
		},
		fields=["name"],
		limit=1,
	)
	if overlapping:
		return False, _("An overlapping Attendance Request ({0}) already exists for this period.").format(overlapping[0].name)

	return True, ""


@frappe.whitelist()
def get_team_attendance_requests(status=None, from_date=None, to_date=None, employee=None):
	"""Get pending attendance requests for manager/system manager with optional filters"""
	user = frappe.session.user
	user_roles = frappe.get_roles(user)

	filters = {}

	# Determine employee list permission
	if "System Manager" in user_roles or "HR Manager" in user_roles:
		if employee:
			filters["employee"] = employee
	else:
		from arijentek_core import get_shift_approver_employees
		permitted = [e["name"] for e in get_shift_approver_employees()]
		if not permitted:
			return []
		if employee:
			if employee in permitted:
				filters["employee"] = employee
			else:
				return []
		else:
			filters["employee"] = ["in", permitted]

	# Map status filter to docstatus
	if status == "Draft" or status == "Open" or status == "Pending":
		filters["docstatus"] = 0
	elif status == "Approved":
		filters["docstatus"] = 1
	elif status == "Rejected":
		filters["docstatus"] = 2
	else:
		# All statuses (Draft, Submitted, Cancelled) -> docstatus < 3
		filters["docstatus"] = ["<", 3]

	# Date filters checking overlap with request range
	if from_date and to_date:
		filters["from_date"] = ["between", [from_date, to_date]]
	elif from_date:
		filters["from_date"] = [">=", from_date]
	elif to_date:
		filters["from_date"] = ["<=", to_date]

	requests = frappe.get_all(
		"Attendance Request",
		filters=filters,
		fields=[
			"name",
			"employee",
			"employee_name",
			"from_date",
			"to_date",
			"reason",
			"explanation",
			"creation",
			"docstatus",
		],
		order_by="creation desc",
	)

	# Format dates to string
	for r in requests:
		r["from_date"] = str(r["from_date"]) if r["from_date"] else ""
		r["to_date"] = str(r["to_date"]) if r["to_date"] else ""
		r["creation"] = str(r["creation"]) if r["creation"] else ""
		# Map docstatus to status string for frontend compatibility
		if r["docstatus"] == 0:
			r["status"] = "Open"
		elif r["docstatus"] == 1:
			r["status"] = "Approved"
		elif r["docstatus"] == 2:
			r["status"] = "Rejected"

	return requests


@frappe.whitelist()
def process_attendance_request(name, action):
	"""Approve or Reject an attendance request"""
	user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if "System Manager" not in user_roles and "HR Manager" not in user_roles:
		doc = frappe.get_doc("Attendance Request", name)
		from arijentek_core import get_shift_approver_employees
		permitted = [e["name"] for e in get_shift_approver_employees()]
		if doc.employee not in permitted:
			return {"status": "failed", "message": _("Not authorized to process this request.")}

	try:
		doc = frappe.get_doc("Attendance Request", name)
		if doc.docstatus != 0:
			return {"status": "failed", "message": _("Only Draft requests can be processed.")}

		if action == "Approve":
			doc.flags.ignore_permissions = True
			doc.submit()
			frappe.db.commit()
		elif action == "Reject":
			frappe.db.set_value("Attendance Request", name, "docstatus", 2)
			frappe.db.commit()
		else:
			return {"status": "failed", "message": _("Invalid action.")}
	except Exception as e:
		frappe.db.rollback()
		return {"status": "failed", "message": str(e)}

	return {"status": "success"}


@frappe.whitelist()
def get_my_attendance_requests(status=None, from_date=None, to_date=None):
	"""Get attendance requests for the current logged-in employee."""
	employee = _validate_and_get_employee()

	filters = {"employee": employee}

	# Map status filter to docstatus
	if status == "Open" or status == "Draft" or status == "Pending":
		filters["docstatus"] = 0
	elif status == "Approved":
		filters["docstatus"] = 1
	elif status == "Rejected":
		filters["docstatus"] = 2
	else:
		filters["docstatus"] = ["<", 3]

	# Date filters
	if from_date and to_date:
		filters["from_date"] = ["between", [from_date, to_date]]
	elif from_date:
		filters["from_date"] = [">=", from_date]
	elif to_date:
		filters["from_date"] = ["<=", to_date]

	requests = frappe.get_all(
		"Attendance Request",
		filters=filters,
		fields=[
			"name",
			"employee",
			"employee_name",
			"from_date",
			"to_date",
			"reason",
			"explanation",
			"creation",
			"docstatus",
		],
		order_by="creation desc",
	)

	# Format dates and map docstatus to status string
	for r in requests:
		r["from_date"] = str(r["from_date"]) if r["from_date"] else ""
		r["to_date"] = str(r["to_date"]) if r["to_date"] else ""
		r["creation"] = str(r["creation"]) if r["creation"] else ""
		if r["docstatus"] == 0:
			r["status"] = "Open"
		elif r["docstatus"] == 1:
			r["status"] = "Approved"
		elif r["docstatus"] == 2:
			r["status"] = "Rejected"

	return requests


@frappe.whitelist()
def update_attendance_request(name, from_date=None, to_date=None, reason=None, explanation=None):
	"""Update a draft Attendance Request owned by the current employee."""
	employee = _validate_and_get_employee()

	if not name:
		return {"status": "failed", "message": _("Attendance Request name is required.")}

	if not frappe.db.exists("Attendance Request", name):
		return {"status": "failed", "message": _("Attendance Request {0} not found.").format(name)}

	doc = frappe.get_doc("Attendance Request", name)

	# Ownership check
	if doc.employee != employee:
		return {"status": "failed", "message": _("You can only edit your own attendance requests.")}

	# Only draft requests can be edited
	if doc.docstatus != 0:
		return {"status": "failed", "message": _("Only Open/Draft requests can be edited.")}

	# Update fields if provided
	update_from = from_date or str(doc.from_date)
	update_to = to_date or str(doc.to_date)

	# Validate dates
	valid, message = validate_attendance_request_for_update(employee, update_from, update_to, name)
	if not valid:
		return {"status": "failed", "message": message}

	if from_date:
		doc.from_date = from_date
	if to_date:
		doc.to_date = to_date
	if reason:
		doc.reason = reason
	if explanation is not None:
		doc.explanation = explanation

	doc.save(ignore_permissions=True)
	frappe.db.commit()

	return {"status": "success", "name": doc.name}


def validate_attendance_request_for_update(employee, from_date, to_date, exclude_name=None):
	"""Validate attendance request dates for update, excluding the current request from overlap check."""
	from frappe.utils import getdate, nowdate

	# 1. Check active employee
	status = frappe.db.get_value("Employee", employee, "status")
	if not status:
		return False, _("Employee record not found.")
	if status == "Inactive":
		return False, _("Cannot request attendance for an Inactive Employee.")

	# 2. Date range validation
	try:
		fd = getdate(from_date)
		td = getdate(to_date)
	except Exception:
		return False, _("Invalid date format.")

	if fd > td:
		return False, _("To date cannot be less than from date.")

	today = getdate(nowdate())
	if fd > today or td > today:
		return False, _("Future dates not allowed.")

	# 3. Date of joining and Relieving date checks
	date_of_joining, relieving_date = frappe.db.get_value(
		"Employee", employee, ["date_of_joining", "relieving_date"]
	)
	if date_of_joining and fd < getdate(date_of_joining):
		return False, _("From date cannot be less than employee's joining date ({0}).").format(
			frappe.utils.format_date(date_of_joining)
		)
	if relieving_date and td > getdate(relieving_date):
		return False, _("To date cannot be greater than employee's relieving date ({0}).").format(
			frappe.utils.format_date(relieving_date)
		)

	# 4. Overlap check (excluding current request)
	overlap_filters = {
		"employee": employee,
		"docstatus": ["<", 2],
		"to_date": [">=", from_date],
		"from_date": ["<=", to_date],
	}
	if exclude_name:
		overlap_filters["name"] = ["!=", exclude_name]

	overlapping = frappe.db.get_all(
		"Attendance Request",
		filters=overlap_filters,
		fields=["name"],
		limit=1,
	)
	if overlapping:
		return False, _("An overlapping Attendance Request ({0}) already exists for this period.").format(
			overlapping[0].name
		)

	return True, ""


@frappe.whitelist()
def delete_attendance_request(name):
	"""Delete a draft Attendance Request owned by the current employee."""
	employee = _validate_and_get_employee()

	if not name:
		return {"status": "failed", "message": _("Attendance Request name is required.")}

	if not frappe.db.exists("Attendance Request", name):
		return {"status": "failed", "message": _("Attendance Request {0} not found.").format(name)}

	doc = frappe.get_doc("Attendance Request", name)

	# Ownership check
	if doc.employee != employee:
		return {"status": "failed", "message": _("You can only delete your own attendance requests.")}

	# Only draft requests can be deleted
	if doc.docstatus != 0:
		return {"status": "failed", "message": _("Only Open/Draft requests can be deleted.")}

	frappe.delete_doc("Attendance Request", name, ignore_permissions=True)
	frappe.db.commit()

	return {"status": "success", "message": _("Attendance request deleted successfully.")}
