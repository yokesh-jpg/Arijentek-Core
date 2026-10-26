"""
Roster API - Shift assignment queries for employee portal.
"""

from calendar import monthrange
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import add_days, getdate, time_diff_in_hours

from arijentek_core.api.attendance import calculate_completed_shift_hours, calculate_hours, get_employee_roster


@frappe.whitelist()
def get_next_three_days_roster(employee_id=None):
	"""
	Return the next 3 days' shift roster starting from tomorrow (excludes today).

	Fetches active Shift Assignment records that cover tomorrow through
	today+3, resolves the Shift Type details, and returns a lightweight
	list suitable for the dashboard "Upcoming Roster" card.

	Returns list of dicts:
	    [
	        {
	            "date": "YYYY-MM-DD",
	            "day_name": "Monday",
	            "day_short": "Mon",
	            "shift_name": "Morning Shift",
	            "start_time": "08:00:00",
	            "end_time": "16:30:00",
	            "is_off": False,
	        },
	        ...
	    ]

	    Days with no shift assignment show shift_name="Yet to assign", is_off=False.
	"""
	if not employee_id:
		employee_id = frappe.db.get_value(
			"Employee", {"user_id": frappe.session.user, "status": "Active"}, "name"
		)
	if not employee_id:
		frappe.throw(_("No employee record found for current user"))

	today = getdate()
	# Skip today — start from tomorrow
	start = add_days(today, 1)
	ends = add_days(today, 3)

	# Fetch active shift assignments that overlap [tomorrow .. today+3]
	assignments = frappe.get_all(
		"Shift Assignment",
		filters={
			"employee": employee_id,
			"docstatus": 1,
			"start_date": ("<=", ends),
			"end_date": (">=", start),
		},
		fields=["name", "shift_type", "start_date", "end_date"],
		order_by="start_date asc",
	)

	# Batch-resolve Shift Type records
	shift_names = list({a.shift_type for a in assignments if a.shift_type})
	shift_map = {}
	if shift_names:
		shifts = frappe.get_all(
			"Shift Type",
			filters={"name": ("in", shift_names)},
			fields=["name", "start_time", "end_time"],
		)
		shift_map = {s.name: s for s in shifts}

	# Build next-3-days list
	result = []
	cursor = today
	day_labels = {}
	for i in range(3):
		day_labels[str(cursor)] = cursor.strftime("%A")
		cursor = add_days(cursor, 1)

	assigned_by_date = {}
	for a in assignments:
		a_start = getdate(a.start_date)
		a_end = getdate(a.end_date) if a.end_date else a_start
		d = a_start
		while d <= a_end and d <= ends:
			assigned_by_date.setdefault(str(d), []).append(a)
			d = add_days(d, 1)

	# Build day labels for the 3-day window
	for i in range(3):
		d = add_days(start, i)
		day_labels[str(d)] = d.strftime("%A")

	for i in range(3):
		d = add_days(start, i)
		date_str = str(d)
		shift = None
		is_off = True

		for a in assigned_by_date.get(date_str, []):
			st = shift_map.get(a.shift_type)
			if st:
				shift = {
					"shift_name": st.name,
					"start_time": str(st.start_time) if st.start_time else None,
					"end_time": str(st.end_time) if st.end_time else None,
				}
				is_off = False
				break

		result.append({
			"date": date_str,
			"day_name": day_labels.get(date_str, d.strftime("%A")),
			"day_short": d.strftime("%a"),
			"shift_name": shift["shift_name"] if shift else "Yet to assign",
			"start_time": shift["start_time"] if shift else None,
			"end_time": shift["end_time"] if shift else None,
			"is_off": is_off,
		})

	return result


# ---------------------------------------------------------------------------
# Shift Request CRUD (Request Change feature for Roster)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_shift_types():
	"""Return all Shift Type names for the dropdown."""
	types = frappe.get_all(
		"Shift Type",
		fields=["name"],
		order_by="name asc",
	)
	return types


@frappe.whitelist()
def get_shift_requests(employee_id=None):
	"""Return all Shift Request documents the current user is permitted to see, ordered by creation desc."""
	visible_employees = get_employee_list()
	if not visible_employees:
		return []

	employee_names = [e["name"] for e in visible_employees]

	# Fetch shift requests for these visible employees
	requests = frappe.db.sql(
		f"""
		SELECT
			name, employee, shift_type, from_date, to_date, status, approver, docstatus, creation
		FROM `tabShift Request`
		WHERE docstatus < 2
		AND employee IN ({', '.join(['%s'] * len(employee_names))})
		ORDER BY creation DESC
		""",
		tuple(employee_names),
		as_dict=True,
	)

	roles = frappe.get_roles(frappe.session.user)
	is_hr_or_sys_manager = "HR Manager" in roles or "System Manager" in roles

	for r in requests:
		if r.employee:
			r["employee_name"] = frappe.db.get_value("Employee", r.employee, "employee_name")

		can_approve = False
		if is_hr_or_sys_manager:
			can_approve = True
		elif r.approver == frappe.session.user:
			can_approve = True
		else:
			dept = frappe.db.get_value("Employee", r.employee, "department")
			shift_approver = frappe.db.get_value("Employee", r.employee, "shift_request_approver")

			approvers = []
			if dept:
				approvers_res = frappe.db.sql(
					"""select approver from `tabDepartment Approver` where parent = %s and parentfield = 'shift_request_approver'""",
					(dept),
				)
				approvers = [row[0] for row in approvers_res]
			if shift_approver:
				approvers.append(shift_approver)

			if frappe.session.user in approvers:
				can_approve = True

		r["can_approve"] = can_approve

	return requests


@frappe.whitelist()
def get_shift_requests_list(page=1, page_size=10, status=None, employee=None):
	"""
	Return paginated Shift Request documents the current user is permitted to see,
	ordered by creation desc.

	Parameters:
	    page: 1-based page number (default 1)
	    page_size: rows per page (default 10)
	    status: optional filter — 'Draft' | 'Approved' | 'Rejected'
	    employee: optional filter — employee name

	Returns:
	    dict: {'data': [...], 'total': int, 'page': int, 'page_size': int}
	"""
	visible_employees = get_employee_list()
	if not visible_employees:
		return {"data": [], "total": 0, "page": page, "page_size": page_size}

	employee_names = [e["name"] for e in visible_employees]

	# Build the WHERE clause (shared by the COUNT and the page SELECT)
	conditions = [
		"docstatus < 2",
		"employee IN ({})".format(", ".join(["%s"] * len(employee_names))),
	]
	params = list(employee_names)

	if status:
		conditions.append("status = %s")
		params.append(status)
	if employee:
		conditions.append("employee = %s")
		params.append(employee)

	where_clause = " AND ".join(conditions)

	# Count total matching rows
	total_row = frappe.db.sql(
		f"""
		SELECT COUNT(*) AS total
		FROM `tabShift Request`
		WHERE {where_clause}
		""",
		tuple(params),
	)
	total = total_row[0][0] if total_row else 0

	# Fetch the page (LIMIT/OFFSET)
	records = frappe.db.sql(
		f"""
		SELECT
			name, employee, shift_type, from_date, to_date, status, approver, docstatus, creation
		FROM `tabShift Request`
		WHERE {where_clause}
		ORDER BY creation DESC
		LIMIT %s OFFSET %s
		""",
		tuple(params + [page_size, (page - 1) * page_size]),
		as_dict=True,
	)

	roles = frappe.get_roles(frappe.session.user)
	is_hr_or_sys_manager = "HR Manager" in roles or "System Manager" in roles

	# can_approve is computed only for the page's rows (avoids the N+1 the
	# full-list endpoint did for every visible request).
	for r in records:
		if r.employee:
			r["employee_name"] = frappe.db.get_value("Employee", r.employee, "employee_name")

		can_approve = False
		if is_hr_or_sys_manager:
			can_approve = True
		elif r.approver == frappe.session.user:
			can_approve = True
		else:
			dept = frappe.db.get_value("Employee", r.employee, "department")
			shift_approver = frappe.db.get_value("Employee", r.employee, "shift_request_approver")

			approvers = []
			if dept:
				approvers_res = frappe.db.sql(
					"""select approver from `tabDepartment Approver` where parent = %s and parentfield = 'shift_request_approver'""",
					(dept),
				)
				approvers = [row[0] for row in approvers_res]
			if shift_approver:
				approvers.append(shift_approver)

			if frappe.session.user in approvers:
				can_approve = True

		r["can_approve"] = can_approve

	return {"data": records, "total": total, "page": page, "page_size": page_size}


def validate_shift_request(employee=None, shift_type=None, from_date=None, to_date=None, edit_name=None, is_approving=False):
	"""
	Check for active employee, default shift, overlapping shift requests, leave applications,
	and overlapping active shift assignments.
	"""
	from_date = getdate(from_date)
	to_date = getdate(to_date)

	# 1. Validate active employee
	employee_status, employee_name = frappe.db.get_value("Employee", employee, ["status", "employee_name"])
	if employee_status != "Active":
		return False, _("Employee {0} is not Active.").format(frappe.bold(employee_name or employee))

	# 2. Check that employee has a shift request approver configured
	if not frappe.db.get_value("Employee", employee, "shift_request_approver"):
		return False, _("No shift request approver configured for this employee. Please contact HR.")

	# 3. Validate default shift
	default_shift = frappe.db.get_value("Employee", employee, "default_shift")
	if shift_type == default_shift:
		return False, _("You can not request for your Default Shift: {0}").format(frappe.bold(shift_type))

	# 4. Check for overlapping shift requests
	shift = frappe.qb.DocType("Shift Request")
	overlapping = (
		frappe.qb.from_(shift)
		.select("name", "shift_type", "from_date", "to_date")
		.where(
			(shift.employee == employee)
			& (shift.docstatus < 2)
			& (shift.name != edit_name)
			& ((shift.to_date >= from_date) | (shift.to_date.isnull()))
			& (shift.from_date <= to_date)
		)
		.run(as_dict=True)
	)
	if overlapping:
		overlap = overlapping[0]
		return False, _(
			"A shift request for <strong>{shift_type}</strong> already exists from {from_date} to {to_date} (Request: {name})"
		).format(
			shift_type=overlap.shift_type,
			from_date=str(overlap.from_date),
			to_date=str(overlap.to_date) if overlap.to_date else str(overlap.from_date),
			name=overlap.name,
		)

	# 5. Check for active overlapping shift assignments (only when approving)
	if not is_approving:
		return True, ""

	shift_assign = frappe.qb.DocType("Shift Assignment")
	query = (
		frappe.qb.from_(shift_assign)
		.select(shift_assign.name, shift_assign.shift_type)
		.where(
			(shift_assign.employee == employee)
			& (shift_assign.docstatus == 1)
			& (shift_assign.status == "Active")
			& ((shift_assign.end_date >= from_date) | (shift_assign.end_date.isnull()))
		)
	)
	if to_date:
		query = query.where(shift_assign.start_date <= to_date)

	overlapping_assignments = query.run(as_dict=True)

	if overlapping_assignments:
		from frappe.utils import cint, get_link_to_form
		from hrms.hr.doctype.shift_assignment.shift_assignment import has_overlapping_timings

		allow_multiple = cint(frappe.db.get_single_value("HR Settings", "allow_multiple_shift_assignments"))
		if not allow_multiple:
			msg = _("There is already a shift assigned on the specific dates. Please delete or edit that manually before approving.")
			return False, msg
		else:
			for d in overlapping_assignments:
				if has_overlapping_timings(shift_type, d.shift_type):
					msg = _(
						"Employee {0} already has an active Shift {1}: {2} that overlaps within this period."
					).format(
						frappe.bold(employee_name or employee),
						frappe.bold(d.shift_type),
						get_link_to_form("Shift Assignment", d.name),
					)
					return False, msg

	return True, None


@frappe.whitelist()
def get_shift_request_approvers():
	user = frappe.session.user
	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")

	default_approver = frappe.db.get_value("Employee", employee, "shift_request_approver") if employee else None

	roles_with_submit = frappe.get_all("Custom DocPerm", filters={"parent": "Shift Request", "submit": 1}, pluck="role")
	roles_with_submit += frappe.get_all("DocPerm", filters={"parent": "Shift Request", "submit": 1}, pluck="role")
	valid_roles = set(roles_with_submit + ["HR Manager", "System Manager"])

	approver_users = frappe.db.sql("""
		SELECT DISTINCT parent 
		FROM `tabHas Role` 
		WHERE role IN %s
	""", (tuple(valid_roles),), pluck=True)

	approver_users = list(approver_users) if approver_users else []
	if default_approver and default_approver not in approver_users:
		approver_users.append(default_approver)

	approvers = []
	if approver_users:
		approvers = frappe.db.sql("""
			SELECT user_id as user, employee_name 
			FROM `tabEmployee`
			WHERE status = 'Active' AND user_id IN %s
		""", (tuple(approver_users),), as_dict=True)

	return {
		"approvers": approvers,
		"default_approver": default_approver
	}


@frappe.whitelist()
def create_shift_request(employee=None, shift_type=None, from_date=None, to_date=None, approver=None):
	"""Create a new Shift Request (Draft) and return its name."""
	if not to_date:
		to_date = from_date

	if not all([employee, shift_type, from_date]):
		frappe.throw(_("Employee, Shift Type, and From Date are required"))

	from_date = getdate(from_date)
	to_date = getdate(to_date)
	if to_date < from_date:
		frappe.throw(_("To Date cannot be before From Date"))

	valid, error_msg = validate_shift_request(
		employee=employee,
		shift_type=shift_type,
		from_date=from_date,
		to_date=to_date,
	)
	if not valid:
		frappe.throw(error_msg, title=_("Error"))

	doc_fields = {
		"doctype": "Shift Request",
		"employee": employee,
		"shift_type": shift_type,
		"from_date": from_date,
		"to_date": to_date,
		"status": "Draft",
	}
	if approver:
		doc_fields["approver"] = approver

	doc = frappe.get_doc(doc_fields)
	doc.insert()
	frappe.db.commit()

	try:
		from arijentek_core.api.notifications import notify_approvers
		emp_name = frappe.db.get_value("Employee", doc.employee, "employee_name") or doc.employee
		title = "New Shift Request"
		body = f"{emp_name} has requested a shift change to {doc.shift_type} (ID: {doc.name})."
		notify_approvers(doc, title, body, module="hrm", route="/roster?tab=requests")
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Shift Request Creation Notification Error")
	return doc.name


@frappe.whitelist()
def update_shift_request(name, shift_type=None, from_date=None, to_date=None, approver=None):
	"""Update an existing Shift Request. Only Draft documents can be edited."""
	doc = frappe.get_doc("Shift Request", name)
	if doc.docstatus != 0:
		frappe.throw(_("Only Draft requests can be edited"))

	old_from = doc.from_date
	old_to = doc.to_date

	if shift_type:
		doc.shift_type = shift_type
	if from_date:
		doc.from_date = getdate(from_date)
	if to_date:
		doc.to_date = getdate(to_date)
	if approver:
		doc.approver = approver

	if doc.to_date < doc.from_date:
		frappe.throw(_("To Date cannot be before From Date"))

	# Validate overlaps only if dates actually changed
	if from_date or to_date:
		valid, error_msg = validate_shift_request(
			employee=doc.employee,
			shift_type=doc.shift_type,
			from_date=doc.from_date,
			to_date=doc.to_date,
			edit_name=name,  # skip self
		)
		if not valid:
			frappe.throw(error_msg, title=_("Error"))

	doc.save()
	frappe.db.commit()
	return doc.name


@frappe.whitelist()
def cancel_shift_request(name):
	"""Delete a Shift Request. Approvers can delete any request, creators can only delete Drafts."""
	doc = frappe.get_doc("Shift Request", name)

	# Check permissions
	my_employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user})
	is_creator = doc.employee == my_employee

	roles = frappe.get_roles(frappe.session.user)
	is_hr_or_sys_manager = "HR Manager" in roles or "System Manager" in roles
	department = frappe.db.get_value("Employee", doc.employee, "department")
	shift_approver = frappe.db.get_value("Employee", doc.employee, "shift_request_approver")

	approvers = []
	if department:
		approvers_res = frappe.db.sql(
			"""select approver from `tabDepartment Approver` where parent = %s and parentfield = 'shift_request_approver'""",
			(department),
		)
		approvers = [r[0] for r in approvers_res]
	if shift_approver:
		approvers.append(shift_approver)
	if doc.approver:
		approvers.append(doc.approver)

	is_approver = frappe.session.user in approvers or is_hr_or_sys_manager

	if not is_approver and not (is_creator and doc.docstatus == 0):
		return {"success": False, "message": _("You don't have permission to delete this request")}

	# Check if linked to any Shift Assignment
	linked_assignments = frappe.get_all("Shift Assignment", filters={"shift_request": name}, pluck="name")
	if linked_assignments:
		assignments_str = ", ".join(linked_assignments)
		return {"success": False, "message": _("Cannot delete or cancel Shift Request {0} because it is linked to Shift Assignment(s): {1}").format(name, assignments_str)}

	if is_approver and doc.docstatus == 1:
		# If it's already approved (submitted), they need explicit delete permission
		if not frappe.has_permission("Shift Request", "delete"):
			return {"success": False, "message": _("You need explicit Delete permission to delete an approved Shift Request")}

	if doc.docstatus == 1:
		# Cancel it first if submitted
		doc.flags.ignore_permissions = True
		doc.cancel()

	doc.delete(ignore_permissions=True)
	return {"success": True, "message": "Deleted"}


@frappe.whitelist()
def update_shift_request_status(name, status):
	"""Update status of a Shift Request (Approved or Rejected) and submit it."""
	if status not in ["Approved", "Rejected"]:
		frappe.throw(_("Invalid status. Only 'Approved' and 'Rejected' are allowed."))

	doc = frappe.get_doc("Shift Request", name)
	if doc.docstatus != 0:
		frappe.throw(_("Only Draft requests can be approved or rejected"))

	# Verify permission
	employee = doc.employee
	department = frappe.db.get_value("Employee", employee, "department")
	shift_approver = frappe.db.get_value("Employee", employee, "shift_request_approver")

	approvers = []
	if department:
		approvers_res = frappe.db.sql(
			"""select approver from `tabDepartment Approver` where parent = %s and parentfield = 'shift_request_approver'""",
			(department),
		)
		approvers = [r[0] for r in approvers_res]

	if shift_approver:
		approvers.append(shift_approver)
	if doc.approver:
		approvers.append(doc.approver)

	is_approver = frappe.session.user in approvers
	roles = frappe.get_roles(frappe.session.user)
	is_hr_or_sys_manager = "HR Manager" in roles or "System Manager" in roles

	if not (is_approver or is_hr_or_sys_manager):
		frappe.throw(_("You do not have permission to approve/reject this Shift Request"))

	# Update the status and approver
	doc.status = status
	if not doc.approver:
		doc.approver = frappe.session.user
	doc.flags.ignore_permissions = True

	if doc.status == "Approved":
		valid, error_msg = validate_shift_request(
			employee=doc.employee,
			shift_type=doc.shift_type,
			from_date=doc.from_date,
			to_date=doc.to_date,
			is_approving=True
		)
		if not valid:
			frappe.throw(error_msg, title=_("Multiple Shift Assignments"))

	doc.save()
	doc.submit()

	frappe.db.commit()

	try:
		from arijentek_core.api.notifications import notify_owner
		title = f"Shift Request {status}"
		body = f"Your shift request for {doc.shift_type} (ID: {doc.name}) has been {status.lower()}."
		notify_owner(doc, title, body, module="hrm", route="/roster?tab=requests")
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Shift Request Status Notification Error")

	return doc.name


@frappe.whitelist()
def is_shift_approver():
	"""Check if the current user is a shift request approver or HR/System Manager."""
	roles = frappe.get_roles(frappe.session.user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	approver_exists = frappe.db.exists("Employee", {"shift_request_approver": frappe.session.user})
	if approver_exists:
		return True

	dept_approver_exists = frappe.db.exists(
		"Department Approver",
		{"approver": frappe.session.user, "parentfield": "shift_request_approver"}
	)
	if dept_approver_exists:
		return True

	return False


# ---------------------------------------------------------------------------
# Weekly / Monthly Roster APIs
# ---------------------------------------------------------------------------

def get_approved_leaves_for_dates(employee_id: str, start_date, end_date):
	"""
	Get approved leave applications for a date range.

	Returns a dict mapping date string -> leave_type.
	Only includes approved, submitted leave applications.
	"""
	leaves = frappe.get_all(
		"Leave Application",
		filters={
			"employee": employee_id,
			"docstatus": 1,
			"status": "Approved",
			"from_date": ["<=", str(end_date)],
			"to_date": [">=", str(start_date)],
		},
		fields=["leave_type", "from_date", "to_date"],
	)

	leave_map = {}
	for leave in leaves:
		from_date = getdate(leave.from_date)
		to_date = getdate(leave.to_date)
		current = from_date
		while current <= to_date:
			leave_map[str(current)] = leave.leave_type
			current = add_days(current, 1)

	return leave_map


def get_holidays_for_dates(employee_id: str, start_date, end_date):
	"""
	Get company holidays for a date range using the employee's holiday list.

	Returns a dict mapping date string -> holiday description/name.
	Uses ERPNext's get_holiday_list_for_employee to resolve the correct list.
	"""
	from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee

	start_date = getdate(start_date)
	end_date = getdate(end_date)

	# Get employee's holiday list
	holiday_list = get_holiday_list_for_employee(employee_id, raise_exception=False)
	if not holiday_list:
		return {}

	# Query Holiday child table for dates in range
	holidays = frappe.get_all(
		"Holiday",
		filters={
			"parent": holiday_list,
			"holiday_date": ["between", [str(start_date), str(end_date)]],
		},
		fields=["holiday_date", "description"],
	)

	return {str(h.holiday_date): h.description for h in holidays}


def _get_weekly_notes(employee_id, week_start, week_end):
	"""Swap requests pending or decided this week, for the roster 'Requests & notes' panel."""
	from frappe.utils import formatdate

	records = frappe.get_all(
		"Shift Request",
		filters=[
			["employee", "=", employee_id],
			["docstatus", "<", 2],
			["status", "!=", "Rejected"],
			["from_date", "<=", week_end],
			["to_date", ">=", week_start],
		],
		fields=["shift_type", "from_date", "to_date", "status"],
		order_by="creation desc",
		limit_page_length=10,
	)

	return [
		{
			"kind": "swap",
			"title": _("Shift swap request · {0}").format(r.shift_type),
			"detail": _("Requested {0} → {1}").format(formatdate(r.from_date), formatdate(r.to_date)),
			"status": r.status,
		}
		for r in records
	]


def _ensure_roster_visibility(employee_id):
	"""Reject employee_ids the current user cannot see (self, unless roster admin)."""
	if employee_id and employee_id not in {e["name"] for e in get_employee_list()}:
		frappe.throw(
			_("You are not authorized to view this employee's roster"), frappe.PermissionError
		)


@frappe.whitelist()
def get_weekly_roster(employee_id: str | None = None, start_date: str | None = None):
	"""
	Get weekly roster/schedule for an employee.

	Args:
	    employee_id: Employee ID (optional, defaults to current user)
	    start_date: Start date for the week (optional, defaults to current week start)

	Returns:
	    Dict with weekly schedule including shifts for each day
	"""
	from frappe.utils import add_days, getdate

	if not employee_id:
		employee_id = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")

	if not employee_id:
		frappe.throw(_("No employee record found for current user"))

	_ensure_roster_visibility(employee_id)

	today = getdate()

	# Get start of current week (Monday)
	if start_date:
		week_start = getdate(start_date)
	else:
		week_start = today - timedelta(days=today.weekday())

	week_end = add_days(week_start, 6)

	# Get all shift assignments for the employee in this date range
	shift_assignments = frappe.get_all(
		"Shift Assignment",
		filters={
			"employee": employee_id,
			"docstatus": 1,
			"start_date": ["<=", week_end],
		},
		fields=["name", "shift_type", "start_date", "end_date"],
		order_by="start_date asc",
	)

	# Batch fetch checkins for the whole week to prevent N+1 queries
	week_end_plus1 = add_days(week_end, 1)
	week_checkins = frappe.get_all(
		"Employee Checkin",
		filters=[
			["Employee Checkin", "employee", "=", employee_id],
			["Employee Checkin", "time", ">=", week_start],
			["Employee Checkin", "time", "<", week_end_plus1],
		],
		fields=["name", "log_type", "time"],
		order_by="time asc",
	)

	# Group checkins by date string (YYYY-MM-DD)
	checkins_by_date = {}
	for c in week_checkins:
		date_str = str(c.time.date() if hasattr(c.time, "date") else getdate(c.time))
		checkins_by_date.setdefault(date_str, []).append(c)

	# Batch fetch shift types
	shift_type_names = list({a.shift_type for a in shift_assignments if a.shift_type})
	shift_types_map = {}
	if shift_type_names:
		shifts_data = frappe.get_all(
			"Shift Type",
			filters={"name": ("in", shift_type_names)},
			fields=["name", "start_time", "end_time"],
		)
		shift_types_map = {}
		for s in shifts_data:
			working = calculate_hours(s.start_time, s.end_time) or 8
			shift_types_map[s.name] = dict(s, working_hours=working)

	# Get approved leave types for the week
	leave_map = get_approved_leaves_for_dates(employee_id, week_start, week_end)

	# Get company holidays for the week
	holiday_set = get_holidays_for_dates(employee_id, week_start, week_end)

	# Build daily schedule
	schedule = []
	current_date = week_start
	# Track date index for overnight shift resolution
	date_index = 0

	while current_date <= week_end:
		day_schedule = {
			"date": str(current_date),
			"day_name": current_date.strftime("%A"),
			"day_short": current_date.strftime("%a"),
			"day_num": current_date.day,
			"is_today": current_date == today,
			"is_past": current_date < today,
			"shift": None,
			"checkins": [],
			"total_hours": 0,
			"status": "pending",
		}

		# Check if the employee is on approved leave for this date
		leave_type = leave_map.get(str(current_date))

		# Find if there is an assigned shift for this day
		assigned_shifts = []
		assigned_shift_names = set()
		for assignment in shift_assignments:
			assign_start = getdate(assignment.start_date)
			assign_end = getdate(assignment.end_date) if assignment.end_date else None

			if assign_start <= current_date and (not assign_end or assign_end >= current_date):
				if assignment.shift_type:
					st = shift_types_map.get(assignment.shift_type)
					if st and st.get("name") not in assigned_shift_names:
						assigned_shifts.append({
							"name": st.get("name"),
							"shift_name": st.get("name"),
							"start_time": str(st.get("start_time")) if st.get("start_time") else None,
							"end_time": str(st.get("end_time")) if st.get("end_time") else None,
							"working_hours": calculate_hours(st.get("start_time"), st.get("end_time")) or 8,
							"shift_assignment": assignment.name,
						})
						assigned_shift_names.add(st.get("name"))

		if str(current_date) in holiday_set:
			# Company holiday — show actual holiday name/description
			day_schedule["status"] = "holiday"
			holiday_name = holiday_set.get(str(current_date), "Holiday")
			day_schedule["shift"] = {
				"name": "Holiday",
				"shift_name": holiday_name,
				"start_time": None,
				"end_time": None,
				"working_hours": 0,
			}
			day_schedule["shifts"] = [day_schedule["shift"]]
			# Keep checkins if any
			checkins = checkins_by_date.get(str(current_date), [])
			day_schedule["checkins"] = [{"log_type": c.log_type, "time": str(c.time)} for c in checkins]
		elif leave_type:
			# Employee is on approved leave — show leave type instead of shift
			day_schedule["status"] = "on_leave"
			day_schedule["shift"] = {
				"name": leave_type,
				"shift_name": leave_type,
				"start_time": None,
				"end_time": None,
				"working_hours": 0,
			}
			day_schedule["shifts"] = [day_schedule["shift"]]
			# Keep checkins if any
			checkins = checkins_by_date.get(str(current_date), [])
			day_schedule["checkins"] = [{"log_type": c.log_type, "time": str(c.time)} for c in checkins]
		elif assigned_shifts:
			# Employee has assigned shifts — show them
			day_schedule["shifts"] = assigned_shifts
			day_schedule["shift"] = assigned_shifts[0]
			day_schedule["status"] = "working"

		# Get check-in logs for this day from batched data
		checkins = checkins_by_date.get(str(current_date), [])

		# No shift assignment found — mark pending
		if not day_schedule.get("shifts"):
			day_schedule["status"] = "pending"
			day_schedule["shift"] = {
				"name": "Pending",
				"shift_name": "Yet to assign",
				"start_time": None,
				"end_time": None,
				"working_hours": 0,
			}
			day_schedule["shifts"] = [day_schedule["shift"]]

		if checkins:
			day_schedule["checkins"] = [{"log_type": c.log_type, "time": str(c.time)} for c in checkins]
			# Calculate shift hours for this day
			shift_hours, total_secs = calculate_completed_shift_hours(checkins)
			day_schedule["total_hours"] = shift_hours

		schedule.append(day_schedule)
		date_index += 1
		current_date = add_days(current_date, 1)

	# Get roster summary
	roster = get_employee_roster(employee_id)

	return {
		"employee_id": employee_id,
		"week_start": str(week_start),
		"week_end": str(week_end),
		"schedule": schedule,
		"roster": roster,
		"notes": _get_weekly_notes(employee_id, week_start, week_end),
		"summary": {
			"total_working_days": len([d for d in schedule if d["status"] not in ("holiday", "on_leave")]),
			"total_hours": sum(d["total_hours"] for d in schedule),
			"target_hours": sum(sum(s["working_hours"] for s in d["shifts"]) for d in schedule if d.get("shifts")),
		},
	}




@frappe.whitelist()
def get_monthly_roster(employee_id: str | None = None, year: int | str | None = None, month: int | str | None = None):
	"""
	Get monthly roster/schedule for an employee.

	Args:
	    employee_id: Employee ID (optional, defaults to current user)
	    year: Year (optional, defaults to current year)
	    month: Month 1-12 (optional, defaults to current month)

	Returns:
	    Dict with calendar array of 35-42 day cells (prev month fillers + current month + next month fillers)
	"""
	from frappe.utils import add_days, getdate
	from frappe.utils import today as get_today

	if not employee_id:
		employee_id = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")

	if not employee_id:
		frappe.throw(_("No employee record found for current user"))

	_ensure_roster_visibility(employee_id)

	today = date.today()

	if not year:
		year = today.year
	if not month:
		month = today.month

	year = int(year)
	month = int(month)

	# Compute month range — use date constructor directly to guarantee date objects
	_, days_in_month = monthrange(year, month)
	first_day = date(year, month, 1)
	last_day = date(year, month, days_in_month)

	# We need cells covering the full grid: from Monday before 1st to Sunday after last_day
	# weekday(): 0=Mon ... 6=Sun
	weekday_of_first = first_day.weekday()
	start_offset = weekday_of_first  # days before first day that need filler cells
	grid_start = first_day - timedelta(days=start_offset)
	grid_end = last_day + timedelta(days=(6 - last_day.weekday()))

	# Get shift assignments for the entire grid range
	shift_assignments = frappe.get_all(
		"Shift Assignment",
		filters={
			"employee": employee_id,
			"docstatus": 1,
			"start_date": ["<=", grid_end],
		},
		fields=["name", "shift_type", "start_date", "end_date"],
		order_by="start_date asc",
	)

	# Batch fetch checkins for the entire grid
	week_checkins = frappe.get_all(
		"Employee Checkin",
		filters=[
			["Employee Checkin", "employee", "=", employee_id],
			["Employee Checkin", "time", ">=", grid_start],
			["Employee Checkin", "time", "<=", add_days(grid_end, 1)],
		],
		fields=["name", "log_type", "time"],
		order_by="time asc",
	)

	checkins_by_date = {}
	for c in week_checkins:
		date_str = str(c.time.date() if hasattr(c.time, "date") else getdate(c.time))
		checkins_by_date.setdefault(date_str, []).append(c)

	# Batch fetch shift types
	shift_type_names = list({a.shift_type for a in shift_assignments if a.shift_type})
	shift_types_map = {}
	if shift_type_names:
		shifts_data = frappe.get_all(
			"Shift Type",
			filters={"name": ("in", shift_type_names)},
			fields=["name", "start_time", "end_time"],
		)
		for s in shifts_data:
			working = calculate_hours(s.start_time, s.end_time) or 8
			shift_types_map[s.name] = dict(s, working_hours=working)

	# Approved leaves for the month
	leave_map = get_approved_leaves_for_dates(employee_id, first_day, last_day)

	# Company holidays for the entire grid range (including fillers)
	holiday_set = get_holidays_for_dates(employee_id, grid_start, grid_end)

	# Build calendar array
	calendar = []
	current = grid_start
	date_index = 0
	while current <= grid_end:
		date_str = str(current)
		is_current_month = current.month == month

		day_schedule = {
			"date": date_str,
			"day_name": current.strftime("%A"),
			"day_short": current.strftime("%a"),
			"day_num": current.day,
			"is_today": current == today,
			"is_current_month": is_current_month,
			"shift": None,
			"checkins": [],
			"total_hours": 0,
			"status": "pending",
		}

		# Leave check (only for current month days)
		leave_type = None
		if is_current_month:
			leave_type = leave_map.get(date_str)

		assigned_shifts = []
		assigned_shift_names = set()
		for assignment in shift_assignments:
			assign_start = getdate(assignment.start_date)
			assign_end = getdate(assignment.end_date) if assignment.end_date else None
			if assign_start <= current and (not assign_end or assign_end >= current):
				if assignment.shift_type:
					st = shift_types_map.get(assignment.shift_type)
					if st and st.get("name") not in assigned_shift_names:
						assigned_shifts.append({
							"name": st.get("name"),
							"shift_name": st.get("name"),
							"start_time": str(st.get("start_time")) if st.get("start_time") else None,
							"end_time": str(st.get("end_time")) if st.get("end_time") else None,
							"working_hours": calculate_hours(st.get("start_time"), st.get("end_time")) or 8,
							"shift_assignment": assignment.name,
						})
						assigned_shift_names.add(st.get("name"))

		if is_current_month and date_str in holiday_set:
			day_schedule["status"] = "holiday"
			holiday_name = holiday_set.get(date_str, "Holiday")
			day_schedule["shift"] = {
				"name": "Holiday",
				"shift_name": holiday_name,
				"start_time": None,
				"end_time": None,
				"working_hours": 0,
			}
			day_schedule["shifts"] = [day_schedule["shift"]]
			checkins = checkins_by_date.get(date_str, [])
			day_schedule["checkins"] = [{"log_type": c.log_type, "time": str(c.time)} for c in checkins]
		elif leave_type:
			day_schedule["status"] = "on_leave"
			day_schedule["shift"] = {
				"name": leave_type,
				"shift_name": leave_type,
				"start_time": None,
				"end_time": None,
				"working_hours": 0,
			}
			day_schedule["shifts"] = [day_schedule["shift"]]
			checkins = checkins_by_date.get(date_str, [])
			day_schedule["checkins"] = [{"log_type": c.log_type, "time": str(c.time)} for c in checkins]
		elif assigned_shifts:
			day_schedule["shifts"] = assigned_shifts
			day_schedule["shift"] = assigned_shifts[0]
			day_schedule["status"] = "working"

		# Checkins
		checkins = checkins_by_date.get(date_str, [])

		# No shift assigned — mark pending
		if not day_schedule.get("shifts"):
			day_schedule["status"] = "pending"
			day_schedule["shift"] = {
				"name": "Pending",
				"shift_name": "Yet to assign",
				"start_time": None,
				"end_time": None,
				"working_hours": 0,
			}
			day_schedule["shifts"] = [day_schedule["shift"]]

		if checkins:
			day_schedule["checkins"] = [{"log_type": c.log_type, "time": str(c.time)} for c in checkins]
			# Calculate shift hours for this day
			shift_hours, _ = calculate_completed_shift_hours(checkins)
			day_schedule["total_hours"] = shift_hours

		calendar.append(day_schedule)
		date_index += 1
		current = add_days(current, 1)

	return {
		"employee_id": employee_id,
		"year": year,
		"month": month,
		"calendar": calendar,
		"summary": {
			"total_working_days": len([d for d in calendar if d.get("is_current_month") and d.get("status") not in ("holiday", "on_leave")]),
			"total_hours": sum(d.get("total_hours", 0) for d in calendar if d.get("is_current_month")),
			"target_hours": sum(sum(s.get("working_hours", 0) for s in d.get("shifts", [])) for d in calendar if d.get("is_current_month") and d.get("shifts")),
		},
	}


# ---------------------------------------------------------------------------
# Employee list (for admin filter dropdown)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_employee_list():
	"""
	Return a list of employees for the matrix.
	If the user has 'submit' permission on Shift Assignment, or is System Manager / HR Manager,
	they see all active employees.
	Otherwise, they only see their own employee record.
	"""
	user = frappe.session.user

	if has_roster_admin_permission():
		# Admin / HR / Submitter sees everyone — except platform staff
		# (raw SQL never sees employee_query_conditions).
		from arijentek_core.services.internal_access import internal_employee_sql

		exclude_internal = internal_employee_sql()
		employees = frappe.db.sql(
			"""
			SELECT name, employee_name, department, designation
			FROM `tabEmployee`
			WHERE status IN ('Active', 'Suspended') AND docstatus < 2
			{exclude}
			ORDER BY employee_name ASC
		""".format(exclude=f"AND {exclude_internal}" if exclude_internal else ""),
			as_dict=True,
		)
		return employees
	else:
		# Regular user sees only themselves
		my_employee = frappe.db.get_value(
			"Employee",
			{"user_id": user},
			["name", "employee_name", "department", "designation"],
			as_dict=True
		)
		if my_employee:
			return [my_employee]
		return []


@frappe.whitelist()
def get_shift_locations(page=0, page_size=0):
	"""
	Return a list of Shift Locations.

	Parameters:
	    page: 1-based page number (default 0 = legacy, return all)
	    page_size: rows per page (default 0 = legacy, return all)

	Returns:
	    list[dict] when page_size is 0 (legacy, for dropdowns)
	    dict when page_size > 0: {'data': [...], 'total': int, 'page': int, 'page_size': int}
	"""
	kwargs = {
		"fields": ["name", "location_name"],
		"order_by": "name asc",
	}
	if page_size and page > 0:
		kwargs["limit_start"] = (page - 1) * page_size
		kwargs["limit_page_length"] = page_size
	locations = frappe.get_all("Shift Location", **kwargs)
	if page_size and page > 0:
		total = frappe.db.count("Shift Location")
		return {"data": locations, "total": total, "page": page, "page_size": page_size}
	return locations


# ---------------------------------------------------------------------------
# Add Roster (manual shift assignment via employee portal)
# ---------------------------------------------------------------------------

def has_roster_admin_permission():
	if frappe.session.user == "Administrator":
		return True
	roles = frappe.get_roles(frappe.session.user)
	if "System Manager" in roles or "HR Manager" in roles:
		return True
	if frappe.has_permission("Shift Assignment", "submit"):
		return True
	return False

@frappe.whitelist()
def can_add_roster():
	"""
	Check if the current user has admin/submit permission for Rosters.
	"""
	return has_roster_admin_permission()


@frappe.whitelist()
def get_frequency_options():
	"""Return the list of frequency options from the Shift Schedule doctype."""
	meta = frappe.get_meta("Shift Schedule")
	freq_field = meta.get_field("frequency")
	if freq_field and freq_field.options:
		return [opt.strip() for opt in freq_field.options.split("\n") if opt.strip()]
	return ["Every Week", "Every 2 Weeks", "Every 3 Weeks", "Every 4 Weeks"]


@frappe.whitelist()
def add_roster(
	employee: str,
	shift_type: str,
	start_date: str,
	end_date: str | None = None,
	shift_location: str | None = None,
	assignment_name: str | None = None,
	schedule_enabled: bool = False,
	repeat_on_days: str | None = None,
	frequency: str | None = None,
):
	"""
	Create or Update a Shift Assignment (roster entry) for an employee.

	Only users with 'create' permission on Shift Assignment can call this.

	Args:
	    employee: Employee ID
	    shift_type: Shift Type name
	    start_date: Start date (YYYY-MM-DD)
	    end_date: End date (YYYY-MM-DD), optional (defaults to start_date if omitted)
	    shift_location: Shift Location name, optional
	    assignment_name: Name of existing assignment to edit, optional
	    schedule_enabled: If True, create a scheduled (recurring) shift assignment
	    repeat_on_days: JSON list of day names, e.g. '["Monday","Wednesday"]'
	    frequency: Frequency string, e.g. 'Every Week'

	Returns:
	    dict: {"name": "<assignment_name>", "message": "Success message"}
	"""
	from frappe.utils import cint

	if not frappe.has_permission("Shift Assignment", "create"):
		frappe.throw(_("You do not have permission to create shift assignments"), frappe.PermissionError)

	if not end_date:
		end_date = start_date

	if assignment_name:
		if not can_edit_roster():
			frappe.throw(_("You do not have permission to edit shift assignments"), frappe.PermissionError)
		doc = frappe.get_doc("Shift Assignment", assignment_name)
		if doc.docstatus == 1:
			doc.cancel()
		frappe.delete_doc("Shift Assignment", assignment_name, ignore_permissions=True)

	company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.get_value("Employee", employee, "company")

	# --- Scheduled (recurring) shift assignment ---
	if cint(schedule_enabled) and repeat_on_days and frequency:
		import json as _json
		if isinstance(repeat_on_days, str):
			repeat_on_days = _json.loads(repeat_on_days)
		if not repeat_on_days:
			frappe.throw(_("Please select at least one day for the schedule"))

		try:
			from hrms.hr.doctype.shift_schedule.shift_schedule import get_or_insert_shift_schedule

			shift_schedule_name = get_or_insert_shift_schedule(shift_type, frequency, repeat_on_days)

			ssa = frappe.new_doc("Shift Schedule Assignment")
			ssa.employee = employee
			ssa.company = company
			ssa.shift_schedule = shift_schedule_name
			ssa.shift_status = "Active"
			ssa.enabled = 1
			ssa.create_shifts_after = start_date
			if shift_location:
				ssa.shift_location = shift_location
			ssa.insert(ignore_permissions=True)

			ssa.create_shifts(start_date, end_date)
			frappe.db.commit()

			return {"name": ssa.name, "message": _("Shift schedule assignment created: {0}").format(ssa.name)}
		except Exception as e:
			frappe.db.rollback()
			frappe.log_error("Shift Schedule Assignment Create Failed", frappe.get_traceback())
			return {"success": False, "message": frappe._("Failed to create shift schedule assignment: {0}").format(str(e))}

	# --- Single (non-recurring) shift assignment ---
	assignment = frappe.new_doc("Shift Assignment")
	assignment.employee = employee
	assignment.company = company
	assignment.shift_type = shift_type
	assignment.start_date = start_date
	assignment.end_date = end_date
	assignment.status = "Active"
	if shift_location:
		assignment.shift_location = shift_location

	try:
		assignment.insert(ignore_permissions=True)
		assignment.submit()
		frappe.db.commit()
		return {"name": assignment.name, "message": _("Shift assignment created: {0}").format(assignment.name)}
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error("Shift Assignment Create Failed", frappe.get_traceback())
		return {"success": False, "message": frappe._("Failed to create shift assignment: {0}").format(str(e))}


@frappe.whitelist()
def allow_multiple_shifts():
	"""
	Check if 'Allow Multiple Shift Assignments for Same Date' is enabled in HR Settings.
	"""
	from frappe.utils import cint
	return cint(frappe.db.get_single_value("HR Settings", "allow_multiple_shift_assignments"))


@frappe.whitelist()
def can_delete_roster():
	"""
	Check if the current user has permission to delete Rosters.
	Requires System Manager, HR Manager, or Shift Assignment delete permission.
	"""
	if frappe.session.user == "Administrator":
		return True
	roles = frappe.get_roles(frappe.session.user)
	if "System Manager" in roles or "HR Manager" in roles:
		return True
	if frappe.has_permission("Shift Assignment", "delete"):
		return True
	return False


@frappe.whitelist()
def can_edit_roster():
	"""
	Check if the current user has permission to edit Rosters.
	Requires System Manager, HR Manager, or Shift Assignment amend permission.
	"""
	if frappe.session.user == "Administrator":
		return True
	roles = frappe.get_roles(frappe.session.user)
	if "System Manager" in roles or "HR Manager" in roles:
		return True
	if frappe.has_permission("Shift Assignment", "amend"):
		return True
	return False


def validate_shift_assignment_delete(doc, delete_date=None):
	"""
	Check if the Shift Assignment is linked to any Employee Checkins or Attendances.
	If so, throw a friendly error message instead of the core validation error.
	"""
	start_date = delete_date or doc.start_date
	end_date = delete_date or doc.end_date or doc.start_date

	checkins = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": doc.employee,
			"shift": doc.shift_type,
			"time": ["between", [start_date, end_date]],
		},
		limit=1
	)
	if checkins:
		frappe.throw(_("Cannot delete shift assignment because the employee has already checked in for this shift between {0} and {1}.").format(start_date, end_date))

	attendances = frappe.get_all(
		"Attendance",
		filters={
			"employee": doc.employee,
			"shift": doc.shift_type,
			"attendance_date": ["between", [start_date, end_date]],
			"docstatus": 1,
		},
		limit=1
	)
	if attendances:
		frappe.throw(_("Cannot delete shift assignment because the employee already has marked attendance for this shift between {0} and {1}.").format(start_date, end_date))


@frappe.whitelist()
def delete_roster(assignment_name: str, delete_date: str = None):
	"""
	Cancel and delete a Shift Assignment.
	If delete_date is provided and the assignment spans multiple dates, it will split/truncate
	the assignment to remove just that specific date.
	Only users with 'delete' permission on Shift Assignment can call this.
	"""
	if not can_delete_roster():
		frappe.throw(_("You do not have permission to delete shift assignments"), frappe.PermissionError)

	try:
		doc = frappe.get_doc("Shift Assignment", assignment_name)

		# Custom friendly validation before standard cancellation/deletion
		validate_shift_assignment_delete(doc, delete_date)

		# Check if we need to split (partial delete)
		if delete_date and str(doc.start_date) != str(doc.end_date):
			from frappe.utils import add_days, getdate

			d_start = getdate(doc.start_date)
			d_end = getdate(doc.end_date)
			d_target = getdate(delete_date)

			if d_target >= d_start and d_target <= d_end:
				# We will cancel and delete the original, then recreate the pieces
				emp = doc.employee
				stype = doc.shift_type
				sloc = doc.shift_location
				company = doc.company

				if doc.docstatus == 1:
					# Bypass core validation since we already did our custom date-specific validation
					doc.validate_employee_checkin = lambda: None
					doc.validate_attendance = lambda: None
					doc.cancel()
				frappe.delete_doc("Shift Assignment", assignment_name, ignore_permissions=True)

				# Recreate piece before delete_date
				if d_target > d_start:
					new_end = add_days(d_target, -1)
					new_doc1 = frappe.new_doc("Shift Assignment")
					new_doc1.employee = emp
					new_doc1.shift_type = stype
					new_doc1.start_date = d_start
					new_doc1.end_date = new_end
					if sloc:
						new_doc1.shift_location = sloc
					new_doc1.company = company
					new_doc1.status = "Active"
					new_doc1.insert(ignore_permissions=True)
					new_doc1.submit()

				# Recreate piece after delete_date
				if d_target < d_end:
					new_start = add_days(d_target, 1)
					new_doc2 = frappe.new_doc("Shift Assignment")
					new_doc2.employee = emp
					new_doc2.shift_type = stype
					new_doc2.start_date = new_start
					new_doc2.end_date = d_end
					if sloc:
						new_doc2.shift_location = sloc
					new_doc2.company = company
					new_doc2.status = "Active"
					new_doc2.insert(ignore_permissions=True)
					new_doc2.submit()

				frappe.db.commit()
				return {"success": True, "message": _("Specific date removed successfully")}

		# Full delete (or fallback if start == end)
		if doc.docstatus == 1:
			# Bypass core validation since we already did our custom validation
			doc.validate_employee_checkin = lambda: None
			doc.validate_attendance = lambda: None
			doc.cancel()
		frappe.delete_doc("Shift Assignment", assignment_name, ignore_permissions=True)
		frappe.db.commit()
		return {"success": True, "message": _("Shift assignment deleted successfully")}
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(f"Shift Assignment Delete Failed for {assignment_name}", frappe.get_traceback())
		return {"success": False, "message": _("Failed to delete shift assignment: {0}").format(str(e))}


@frappe.whitelist()
def get_shift_assignments(employee_id=None, month=None, year=None):
	"""
	Return all Shift Assignments for an employee or all visible employees,
	optionally filtered by month and year.
	"""
	user = frappe.session.user
	visible_employees = get_employee_list()
	if not visible_employees:
		return []

	employee_names = [e["name"] for e in visible_employees]

	# Validate/restrict target employee
	if employee_id:
		if employee_id not in employee_names:
			frappe.throw(_("You do not have permission to view roster for this employee"))
		target_employees = [employee_id]
	else:
		target_employees = employee_names

	# Base query
	query = """
		SELECT
			sa.name, sa.employee, sa.shift_type, sa.start_date, sa.end_date, sa.status, sa.docstatus, sa.shift_location
		FROM `tabShift Assignment` sa
		WHERE sa.docstatus < 2
		AND sa.employee IN ({})
	""".format(", ".join(["%s"] * len(target_employees)))

	params = list(target_employees)

	if year and month:
		from calendar import monthrange
		from datetime import date
		year = int(year)
		month = int(month)
		_, days_in_month = monthrange(year, month)
		start_date = date(year, month, 1)
		end_date = date(year, month, days_in_month)

		query += " AND sa.start_date <= %s AND (sa.end_date IS NULL OR sa.end_date >= %s)"
		params.extend([str(end_date), str(start_date)])

	query += " ORDER BY sa.start_date DESC"

	assignments = frappe.db.sql(query, tuple(params), as_dict=True)

	# Batch fetch all employee names in one query (avoids N+1)
	if assignments:
		employee_ids = tuple(set(a["employee"] for a in assignments))
		emp_map = frappe.db.get_values(
			"Employee",
			filters={"name": ["in", employee_ids]},
			fieldname=["name", "employee_name"],
			as_dict=True,
		)
		emp_name_map = {e["name"]: e["employee_name"] for e in emp_map}

		# Batch fetch shift locations in one query (avoids N+1)
		loc_ids = tuple(set(
			a["shift_location"] for a in assignments
			if a.get("shift_location")
		))
		loc_map = {}
		if loc_ids:
			loc_map = frappe.db.get_values(
				"Shift Location",
				filters={"name": ["in", loc_ids]},
				fieldname=["name", "location_name"],
				as_dict=True,
			)
			loc_map = {l["name"]: l["location_name"] for l in loc_map}

		for a in assignments:
			a["employee_name"] = emp_name_map.get(a["employee"], "")
			if a.get("shift_location"):
				a["location_name"] = loc_map.get(a["shift_location"], "")
			else:
				a["location_name"] = ""

	return assignments


@frappe.whitelist()
def get_shift_assignment_list(month=None, year=None, department=None, designation=None, employee=None, page=1, page_size=10):
	"""
	Return shift assignments as a flat list for the list view.
	Fetches actual Shift Assignment Doctype records.
	"""
	import math
	from calendar import monthrange
	from datetime import date

	user = frappe.session.user
	visible_employees = get_employee_list()
	if not visible_employees:
		return {"assignments": [], "total": 0, "page": int(page), "page_size": int(page_size)}

	employee_names = [e["name"] for e in visible_employees]

	# Validate/restrict target employee
	if employee:
		if employee not in employee_names:
			frappe.throw(_("You do not have permission to view roster for this employee"))
		target_employees = [employee]
	else:
		target_employees = employee_names

	base_conditions = "sa.docstatus < 2 AND sa.employee IN %(employee_names)s"

	# Base query - fetch actual Shift Assignment Doctype records
	query = f"""
		SELECT
			sa.name, sa.employee, sa.shift_type, sa.start_date, sa.end_date, sa.status, sa.shift_location
		FROM `tabShift Assignment` sa
		WHERE {base_conditions}
	"""
	params = {"employee_names": tuple(target_employees)}

	if year and month:
		year = int(year)
		month = int(month)
		_, days_in_month = monthrange(year, month)
		start_date = date(year, month, 1)
		end_date = date(year, month, days_in_month)

		condition = " AND sa.start_date <= %(end_date)s AND (sa.end_date IS NULL OR sa.end_date >= %(start_date)s)"
		query += condition
		base_conditions += condition
		params["end_date"] = str(end_date)
		params["start_date"] = str(start_date)

	# Add department filter
	if department:
		employees_in_dept = frappe.get_all("Employee", filters={"department": department, "name": ["in", target_employees]}, pluck="name")
		if employees_in_dept:
			condition = " AND sa.employee IN %(dept_employees)s"
			query += condition
			base_conditions += condition
			params["dept_employees"] = tuple(employees_in_dept)
		else:
			return {"assignments": [], "total": 0, "page": int(page), "page_size": int(page_size)}

	# Add designation filter
	if designation:
		employees_in_desig = frappe.get_all("Employee", filters={"designation": designation, "name": ["in", target_employees]}, pluck="name")
		if employees_in_desig:
			condition = " AND sa.employee IN %(desig_employees)s"
			query += condition
			base_conditions += condition
			params["desig_employees"] = tuple(employees_in_desig)
		else:
			return {"assignments": [], "total": 0, "page": int(page), "page_size": int(page_size)}

	# Get total count
	total = frappe.db.sql(f"""
		SELECT COUNT(*) as count FROM `tabShift Assignment` sa
		WHERE {base_conditions}
	""", params, as_dict=True)[0].count

	# Add pagination
	offset = (int(page) - 1) * int(page_size)
	query += " ORDER BY sa.start_date DESC LIMIT %(page_size)s OFFSET %(offset)s"
	params["page_size"] = int(page_size)
	params["offset"] = offset

	assignments = frappe.db.sql(query, params, as_dict=True)

	# Batch fetch all employee names and departments in one query (avoids N+1)
	if assignments:
		employee_ids = tuple(set(a["employee"] for a in assignments))
		emp_map = frappe.db.get_values(
			"Employee",
			filters={"name": ["in", employee_ids]},
			fieldname=["name", "employee_name", "department"],
			as_dict=True,
		)
		emp_name_map = {e["name"]: e["employee_name"] for e in emp_map}
		emp_dept_map = {e["name"]: e.get("department") or "" for e in emp_map}

		# Batch fetch shift locations in one query (avoids N+1)
		loc_ids = tuple(set(
			a["shift_location"] for a in assignments
			if a.get("shift_location")
		))
		loc_map = {}
		if loc_ids:
			loc_map = frappe.db.get_values(
				"Shift Location",
				filters={"name": ["in", loc_ids]},
				fieldname=["name", "location_name"],
				as_dict=True,
			)
			loc_map = {l["name"]: l["location_name"] for l in loc_map}

		for a in assignments:
			a["employee_name"] = emp_name_map.get(a["employee"], "")
			a["department"] = emp_dept_map.get(a["employee"], "")
			if a.get("shift_location"):
				a["location_name"] = loc_map.get(a["shift_location"], "")
			else:
				a["location_name"] = ""

	return {
		"assignments": assignments,
		"total": total,
		"page": int(page),
		"page_size": int(page_size),
		"total_pages": math.ceil(total / int(page_size)) if int(page_size) > 0 else 0
	}



@frappe.whitelist()
def get_shift_matrix(month, year, department=None, designation=None, employee=None):
	"""
	Returns matrix data for shift assignments:
	{
		"employees": [
			{
				"name": "EMP-001",
				"employee_name": "John",
				"department": "...",
				"designation": "...",
				"shifts": {
					"2023-10-01": [{"name": "assign_id", "shift_type": "Morning"}],
					...
				}
			}
		],
		"days": [
			{"date": "2023-10-01", "day_num": 1, "day_short": "Mon"},
			...
		]
	}
	"""
	from calendar import monthrange
	from datetime import date

	month = int(month)
	year = int(year)
	_, days_in_month = monthrange(year, month)
	start_date = date(year, month, 1)
	end_date = date(year, month, days_in_month)

	# Get visible employees
	visible_employees = get_employee_list()
	if not visible_employees:
		# Fallback: get current user's employee directly
		my_employee = frappe.db.get_value(
			"Employee",
			{"user_id": frappe.session.user},
			["name", "employee_name", "department", "designation"],
			as_dict=True
		)
		if my_employee:
			visible_employees = [my_employee]
		else:
			return {"employees": [], "days": []}

	employee_names = [e["name"] for e in visible_employees]

	# Fetch full details for filtering
	filters = {"name": ["in", employee_names]}
	if department:
		filters["department"] = department
	if designation:
		filters["designation"] = designation
	if employee:
		filters["name"] = employee

	employees = frappe.get_all(
		"Employee",
		filters=filters,
		fields=["name", "employee_name", "department", "designation"],
		order_by="employee_name asc"
	)

	if not employees:
		return {"employees": [], "days": []}

	filtered_emp_names = [e.name for e in employees]

	# Get assignments for these employees in the given month
	query = """
		SELECT
			sa.name, sa.employee, sa.shift_type, sa.start_date, sa.end_date, sa.status, sa.shift_location,
			st.start_time, st.end_time
		FROM `tabShift Assignment` sa
		LEFT JOIN `tabShift Type` st ON st.name = sa.shift_type
		WHERE sa.docstatus < 2
		AND sa.employee IN ({})
		AND sa.start_date <= %s 
		AND (sa.end_date IS NULL OR sa.end_date >= %s)
	""".format(", ".join(["%s"] * len(filtered_emp_names)))

	params = list(filtered_emp_names)
	params.extend([str(end_date), str(start_date)])

	assignments = frappe.db.sql(query, tuple(params), as_dict=True)

	# Fetch Attendance records for the month
	attendances = frappe.get_all(
		"Attendance",
		filters={
			"employee": ["in", filtered_emp_names],
			"attendance_date": ["between", [start_date, end_date]],
			"docstatus": 1
		},
		fields=["name", "employee", "attendance_date", "status"]
	)

	attendance_map = {}
	for att in attendances:
		if att.employee not in attendance_map:
			attendance_map[att.employee] = {}
		attendance_map[att.employee][str(att.attendance_date)] = {
			"status": att.status,
			"name": att.name
		}

	# Structure shift assignments by employee and date
	from frappe.utils import add_days, getdate

	emp_dict = {e.name: {"name": e.name, "employee_name": e.employee_name, "department": e.department, "designation": e.designation, "shifts": {}} for e in employees}

	for sa in assignments:
		if sa.employee not in emp_dict:
			continue

		# sa.start_date to sa.end_date or month end
		a_start = getdate(sa.start_date)
		a_end = getdate(sa.end_date) if sa.end_date else end_date

		# Format times
		start_time_str = str(sa.start_time) if sa.start_time else ""
		end_time_str = str(sa.end_time) if sa.end_time else ""

		# Limit to current month window
		loop_start = max(a_start, start_date)
		loop_end = min(a_end, end_date)

		current = loop_start
		while current <= loop_end:
			d_str = str(current)
			att_data = attendance_map.get(sa.employee, {}).get(d_str)
			att_status = att_data.get("status") if att_data else None
			att_name = att_data.get("name") if att_data else None

			if d_str not in emp_dict[sa.employee]["shifts"]:
				emp_dict[sa.employee]["shifts"][d_str] = []

			emp_dict[sa.employee]["shifts"][d_str].append({
				"name": sa.name,
				"shift_assignment": sa.name,
				"shift_type": sa.shift_type,
				"shift_location": sa.shift_location,
				"status": sa.status,
				"start_time": start_time_str,
				"end_time": end_time_str,
				"start_date": str(sa.start_date),
				"end_date": str(sa.end_date) if sa.end_date else str(sa.start_date),
				"attendance": att_status,
				"attendance_id": att_name
			})
			current = add_days(current, 1)

	# Generate days array
	days_arr = []
	curr = start_date
	while curr <= end_date:
		days_arr.append({
			"date": str(curr),
			"day_num": curr.day,
			"day_short": curr.strftime("%a")
		})
		curr = add_days(curr, 1)

	return {
		"employees": list(emp_dict.values()),
		"days": days_arr
	}


@frappe.whitelist()
def bulk_add_roster(employee_ids, shift_type, start_date, end_date=None, shift_location=None, schedule_enabled=False, repeat_on_days=None, frequency=None):
	"""
	Bulk assign shifts. employee_ids is a JSON list.
	"""
	import json
	if isinstance(employee_ids, str):
		employee_ids = json.loads(employee_ids)

	if not frappe.has_permission("Shift Assignment", "create"):
		frappe.throw(_("You do not have permission to create shift assignments"), frappe.PermissionError)

	success_count = 0
	failed = []

	for emp in employee_ids:
		try:
			# Direct call to existing add_roster logic
			res = add_roster(
				employee=emp,
				shift_type=shift_type,
				start_date=start_date,
				end_date=end_date,
				shift_location=shift_location,
				schedule_enabled=schedule_enabled,
				repeat_on_days=repeat_on_days,
				frequency=frequency
			)
			if res.get("success") is False:
				failed.append({"employee": emp, "message": res.get("message")})
			else:
				success_count += 1
		except Exception as e:
			failed.append({"employee": emp, "message": str(e)})

	return {
		"success_count": success_count,
		"failed": failed,
		"total": len(employee_ids)
	}


@frappe.whitelist()
def get_departments_and_designations():
	departments = frappe.get_all("Department", fields=["name"], filters={"disabled": 0}, order_by="name asc")
	designations = frappe.get_all("Designation", fields=["name"], order_by="name asc")
	return {
		"departments": [d.name for d in departments if d.name != "All Departments"],
		"designations": [d.name for d in designations]
	}

@frappe.whitelist()
def check_shift_conflict(employees, start_date, end_date, exclude_assignment=None, schedule_enabled=False, repeat_on_days=None):
	import json
	if isinstance(employees, str):
		employees = json.loads(employees)

	if schedule_enabled and isinstance(repeat_on_days, str):
		repeat_on_days = json.loads(repeat_on_days)

	from frappe.utils import add_days, cint, get_weekday, getdate
	allow_multiple = cint(frappe.db.get_single_value("HR Settings", "allow_multiple_shift_assignments"))
	if allow_multiple:
		return {"has_conflict": False, "message": ""}

	filters={
		"employee": ["in", employees],
		"status": "Active",
		"docstatus": ["<", 2],
		"start_date": ["<=", end_date],
		"end_date": [">=", start_date]
	}

	if exclude_assignment:
		filters["name"] = ["!=", exclude_assignment]

	conflicts = frappe.get_all(
		"Shift Assignment",
		filters=filters,
		fields=["name", "employee", "employee_name", "start_date", "end_date"]
	)

	if conflicts and cint(schedule_enabled) and repeat_on_days:
		actual_conflicts = []
		for c in conflicts:
			c_start = getdate(c.start_date)
			c_end = getdate(c.end_date) if c.end_date else c_start

			curr = c_start
			has_overlap = False
			while curr <= c_end:
				if get_weekday(curr) in repeat_on_days:
					has_overlap = True
					break
				curr = add_days(curr, 1)

			if has_overlap:
				actual_conflicts.append(c)
		conflicts = actual_conflicts

	if conflicts:
		emp_names = list(set([c.employee_name or c.employee for c in conflicts]))
		names_str = ", ".join(emp_names)
		if len(emp_names) == 1:
			msg = f"Employee {names_str} already has a shift assigned on these dates."
		else:
			msg = f"Employees {names_str} already have shifts assigned on these dates."
		return {"has_conflict": True, "message": msg}

	return {"has_conflict": False, "message": ""}

@frappe.whitelist()
def get_shift_assignment_details(assignment_id, date=None):
	"""
	Fetch details for a single Shift Assignment, including linked attendance.
	"""
	if not assignment_id:
		return {"error": True, "message": "Shift Assignment ID is required"}

	try:
		assignment = frappe.get_doc("Shift Assignment", assignment_id)
	except frappe.DoesNotExistError:
		return {"error": True, "message": "Entry is not available or has been deleted."}

	target_date = date if date else assignment.start_date

	# Fetch related Attendance if any
	attendance = frappe.db.get_value(
		"Attendance",
		{
			"employee": assignment.employee,
			"attendance_date": target_date,
			"docstatus": ("!=", 2)
		},
		["name", "status"],
		as_dict=True
	)

	shift_type_info = frappe.db.get_value(
		"Shift Type",
		assignment.shift_type,
		["start_time", "end_time"],
		as_dict=True
	) if assignment.shift_type else None

	can_delete = can_delete_roster()
	can_edit = can_edit_roster()

	return {
		"assignment_id": assignment.name,
		"employee": assignment.employee,
		"employee_name": assignment.employee_name,
		"department": assignment.get("department") or frappe.db.get_value("Employee", assignment.employee, "department"),
		"shift_type": assignment.shift_type,
		"shift_location": assignment.get("shift_location"),
		"start_time": str(shift_type_info.start_time) if shift_type_info and shift_type_info.start_time else "",
		"end_time": str(shift_type_info.end_time) if shift_type_info and shift_type_info.end_time else "",
		"date": target_date,
		"start_date": assignment.start_date,
		"end_date": assignment.end_date,
		"attendance_id": attendance.name if attendance else None,
		"attendance_status": attendance.status if attendance else "Not Marked",
		"docstatus": assignment.docstatus,
		"status": assignment.status,
		"can_edit": bool(can_edit),
		"can_delete": bool(can_delete),
	}


# ---------------------------------------------------------------------------
# Permission helpers — Shift Request
# ---------------------------------------------------------------------------

@frappe.whitelist()
def can_read_shift_request():
	"""
	Returns True if the current user can read a Shift Request.
	True for HR Manager, System Manager, or users with explicit read permission.
	"""
	if frappe.session.user == "Administrator":
		return True
	roles = frappe.get_roles(frappe.session.user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Shift Request", "read"):
		return True
	return False


@frappe.whitelist()
def can_create_shift_request():
	"""
	Returns True if the current user can create a Shift Request.
	True for HR Manager, System Manager, or users with explicit create permission.
	"""
	if frappe.session.user == "Administrator":
		return True
	roles = frappe.get_roles(frappe.session.user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Shift Request", "create"):
		return True
	return False


@frappe.whitelist()
def can_edit_shift_request():
	"""
	Returns True if the current user can edit (write) a Shift Request.
	True for HR Manager, System Manager, or users with explicit write permission.
	"""
	if frappe.session.user == "Administrator":
		return True
	roles = frappe.get_roles(frappe.session.user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Shift Request", "write"):
		return True
	return False


@frappe.whitelist()
def can_delete_shift_request():
	"""
	Returns True if the current user can delete a Shift Request.
	True for HR Manager, System Manager, or users with explicit delete permission.
	"""
	if frappe.session.user == "Administrator":
		return True
	roles = frappe.get_roles(frappe.session.user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Shift Request", "delete"):
		return True
	return False


@frappe.whitelist()
def can_submit_shift_request():
	"""
	Returns True if the current user can submit (approve) a Shift Request.
	True for HR Manager, System Manager, or users with explicit submit permission.
	"""
	if frappe.session.user == "Administrator":
		return True
	roles = frappe.get_roles(frappe.session.user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Shift Request", "submit"):
		return True
	return False


# ---------------------------------------------------------------------------
# Permission helpers — Shift Assignment
# ---------------------------------------------------------------------------

@frappe.whitelist()
def can_read_shift_assignment():
	"""
	Returns True if the current user can read a Shift Assignment.
	True for HR Manager, System Manager, or users with explicit read permission.
	"""
	if frappe.session.user == "Administrator":
		return True
	roles = frappe.get_roles(frappe.session.user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Shift Assignment", "read"):
		return True
	return False


@frappe.whitelist()
def can_create_shift_assignment():
	"""
	Returns True if the current user can create a Shift Assignment.
	True for HR Manager, System Manager, or users with explicit create permission.
	"""
	if frappe.session.user == "Administrator":
		return True
	roles = frappe.get_roles(frappe.session.user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Shift Assignment", "create"):
		return True
	return False


@frappe.whitelist()
def can_edit_shift_assignment():
	"""
	Returns True if the current user can edit (write) a Shift Assignment.
	True for HR Manager, System Manager, or users with explicit write permission.
	"""
	if frappe.session.user == "Administrator":
		return True
	roles = frappe.get_roles(frappe.session.user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Shift Assignment", "write"):
		return True
	return False


@frappe.whitelist()
def can_delete_shift_assignment():
	"""
	Returns True if the current user can delete a Shift Assignment.
	True for HR Manager, System Manager, or users with explicit delete permission.
	"""
	if frappe.session.user == "Administrator":
		return True
	roles = frappe.get_roles(frappe.session.user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Shift Assignment", "delete"):
		return True
	return False


@frappe.whitelist()
def can_submit_shift_assignment():
	"""
	Returns True if the current user can submit a Shift Assignment.
	True for HR Manager, System Manager, or users with explicit submit permission.
	"""
	if frappe.session.user == "Administrator":
		return True
	roles = frappe.get_roles(frappe.session.user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Shift Assignment", "submit"):
		return True
	return False


# ---------------------------------------------------------------------------
# Permission helpers — Shift Location
# ---------------------------------------------------------------------------

@frappe.whitelist()
def can_read_shift_location():
	"""
	Returns True if the current user can read a Shift Location.
	True for HR Manager, System Manager, or users with explicit read permission.
	"""
	if frappe.session.user == "Administrator":
		return True
	roles = frappe.get_roles(frappe.session.user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Shift Location", "read"):
		return True
	return False


@frappe.whitelist()
def can_create_shift_location():
	"""
	Returns True if the current user can create a Shift Location.
	True for HR Manager, System Manager, or users with explicit create permission.
	"""
	if frappe.session.user == "Administrator":
		return True
	roles = frappe.get_roles(frappe.session.user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Shift Location", "create"):
		return True
	return False


@frappe.whitelist()
def can_edit_shift_location():
	"""
	Returns True if the current user can edit (write) a Shift Location.
	True for HR Manager, System Manager, or users with explicit write permission.
	"""
	if frappe.session.user == "Administrator":
		return True
	roles = frappe.get_roles(frappe.session.user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Shift Location", "write"):
		return True
	return False


@frappe.whitelist()
def can_delete_shift_location():
	"""
	Returns True if the current user can delete a Shift Location.
	True for HR Manager, System Manager, or users with explicit delete permission.
	"""
	if frappe.session.user == "Administrator":
		return True
	roles = frappe.get_roles(frappe.session.user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Shift Location", "delete"):
		return True
	return False


@frappe.whitelist()
def can_submit_shift_location():
	"""
	Returns True if the current user can submit a Shift Location.
	True for HR Manager, System Manager, or users with explicit submit permission.
	"""
	if frappe.session.user == "Administrator":
		return True
	roles = frappe.get_roles(frappe.session.user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Shift Location", "submit"):
		return True
	return False


# ---------------------------------------------------------------------------
# Permission helpers — Shift Type
# ---------------------------------------------------------------------------

@frappe.whitelist()
def can_read_shift_type():
	"""
	Returns True if the current user can read a Shift Type.
	True for HR Manager, System Manager, or users with explicit read permission.
	"""
	if frappe.session.user == "Administrator":
		return True
	roles = frappe.get_roles(frappe.session.user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Shift Type", "read"):
		return True
	return False


@frappe.whitelist()
def can_create_shift_type():
	"""
	Returns True if the current user can create a Shift Type.
	True for HR Manager, System Manager, or users with explicit create permission.
	"""
	if frappe.session.user == "Administrator":
		return True
	roles = frappe.get_roles(frappe.session.user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Shift Type", "create"):
		return True
	return False


@frappe.whitelist()
def can_edit_shift_type():
	"""
	Returns True if the current user can edit (write) a Shift Type.
	True for HR Manager, System Manager, or users with explicit write permission.
	"""
	if frappe.session.user == "Administrator":
		return True
	roles = frappe.get_roles(frappe.session.user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Shift Type", "write"):
		return True
	return False


@frappe.whitelist()
def can_delete_shift_type():
	"""
	Returns True if the current user can delete a Shift Type.
	True for HR Manager, System Manager, or users with explicit delete permission.
	"""
	if frappe.session.user == "Administrator":
		return True
	roles = frappe.get_roles(frappe.session.user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Shift Type", "delete"):
		return True
	return False


@frappe.whitelist()
def can_submit_shift_type():
	"""
	Returns True if the current user can submit a Shift Type.
	True for HR Manager, System Manager, or users with explicit submit permission.
	"""
	if frappe.session.user == "Administrator":
		return True
	roles = frappe.get_roles(frappe.session.user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Shift Type", "submit"):
		return True
	return False


# ---------------------------------------------------------------------------
# Shift Location & Shift Type Management CRUD & Permission APIs
# ---------------------------------------------------------------------------

@frappe.whitelist()
def can_manage_shift_location():
	"""Check if current user has permission to create/edit/delete shift locations."""
	return can_create_shift_location() or can_edit_shift_location() or can_delete_shift_location()


@frappe.whitelist()
def save_shift_location(location_name=None, name=None):
	"""Create a new Shift Location."""
	if not can_create_shift_location():
		frappe.throw(_("Not permitted to create Shift Location"), frappe.PermissionError)
	target_name = location_name or name
	if not target_name:
		frappe.throw(_("Location Name is required"))

	doc = frappe.get_doc({
		"doctype": "Shift Location",
		"location_name": target_name
	})
	doc.insert()
	return doc.name


@frappe.whitelist()
def edit_shift_location(original_name=None, location_name=None, name=None):
	"""Edit an existing Shift Location."""
	if not can_edit_shift_location():
		frappe.throw(_("Not permitted to edit Shift Location"), frappe.PermissionError)
	target = original_name or name
	if not target:
		frappe.throw(_("Location identifier is required"))

	if frappe.db.exists("Shift Location", target):
		doc = frappe.get_doc("Shift Location", target)
		if location_name:
			doc.location_name = location_name
		doc.save()
		return doc.name
	else:
		frappe.throw(_("Shift Location {0} not found").format(target))


@frappe.whitelist()
def delete_shift_location(location_name=None, name=None):
	"""Delete a Shift Location."""
	if not can_delete_shift_location():
		frappe.throw(_("Not permitted to delete Shift Location"), frappe.PermissionError)
	target = location_name or name
	if not target:
		frappe.throw(_("Location identifier is required"))

	frappe.delete_doc("Shift Location", target)
	return True


@frappe.whitelist()
def can_view_shift_type():
	"""Alias for can_read_shift_type."""
	return can_read_shift_type()


@frappe.whitelist()
def can_user_create_shift_types():
	"""Alias for can_create_shift_type."""
	return can_create_shift_type()


@frappe.whitelist()
def can_edit_shift_types():
	"""Alias for can_edit_shift_type."""
	return can_edit_shift_type()


@frappe.whitelist()
def can_delete_shift_types():
	"""Alias for can_delete_shift_type."""
	return can_delete_shift_type()


@frappe.whitelist()
def save_shift_type(shift_name=None, name=None, start_time=None, end_time=None):
	"""Create a new Shift Type."""
	if not can_create_shift_type():
		frappe.throw(_("Not permitted to create Shift Type"), frappe.PermissionError)
	target_name = shift_name or name
	if not target_name:
		frappe.throw(_("Shift Name is required"))

	doc = frappe.get_doc({
		"doctype": "Shift Type",
		"name": target_name,
		"start_time": start_time,
		"end_time": end_time
	})
	doc.insert()
	return doc.name


@frappe.whitelist()
def edit_shift_type(original_name=None, shift_name=None, name=None, start_time=None, end_time=None):
	"""Edit an existing Shift Type."""
	if not can_edit_shift_type():
		frappe.throw(_("Not permitted to edit Shift Type"), frappe.PermissionError)
	target = original_name or shift_name or name
	if not target:
		frappe.throw(_("Shift Type identifier is required"))

	doc = frappe.get_doc("Shift Type", target)
	if start_time is not None:
		doc.start_time = start_time
	if end_time is not None:
		doc.end_time = end_time
	doc.save()
	return doc.name


@frappe.whitelist()
def delete_shift_type(shift_name=None, name=None):
	"""Delete a Shift Type."""
	if not can_delete_shift_type():
		frappe.throw(_("Not permitted to delete Shift Type"), frappe.PermissionError)
	target = shift_name or name
	if not target:
		frappe.throw(_("Shift Type identifier is required"))

	frappe.delete_doc("Shift Type", target)
	return True



# ---------------------------------------------------------------------------
# Shift Assignment Report API
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_shift_assignment_report_filter_options():
	"""
	Returns filter options for the Shift Assignment report.
	"""
	departments = frappe.get_all("Department", fields=["name as id", "name as name"], order_by="name asc")
	designations = frappe.get_all("Designation", fields=["name as id", "name as name"], order_by="name asc")
	shift_types = frappe.get_all("Shift Type", fields=["name as id", "name as name"], order_by="name asc")

	# For employees, we should ideally filter by allowed employees
	visible_employees = get_employee_list()
	employees = []
	if visible_employees:
		employees = [
			{"id": e["name"], "name": f"{e['name']} - {e.get('employee_name', '')}"}
			for e in visible_employees
		]

	return {
		"departments": departments,
		"designations": designations,
		"employees": employees,
		"shift_types": shift_types
	}


@frappe.whitelist()
def report_shift_assignment_list(from_date=None, to_date=None, department=None, designation=None, employee=None, shift_type=None, export=False, pdf=False):
	"""
	Returns shift assignments for the report.
	"""
	import frappe
	from frappe import _
	from frappe.utils import cint, getdate, now_datetime
	from frappe.utils.pdf import get_pdf
	from frappe.utils.xlsxutils import build_xlsx_response

	# Base query
	visible_employees = get_employee_list()
	if not visible_employees:
		return {"columns": [], "data": []}

	employee_names = [e["name"] for e in visible_employees]

	if employee:
		if employee not in employee_names:
			frappe.throw(_("You do not have permission to view roster for this employee"))
		target_employees = [employee]
	else:
		target_employees = employee_names

	base_conditions = ["sa.docstatus < 2", "sa.employee IN %(employee_names)s"]
	params = {"employee_names": tuple(target_employees)}

	if from_date and to_date:
		base_conditions.append("sa.start_date <= %(to_date)s AND (sa.end_date IS NULL OR sa.end_date >= %(from_date)s)")
		params["from_date"] = from_date
		params["to_date"] = to_date

	if shift_type:
		base_conditions.append("sa.shift_type = %(shift_type)s")
		params["shift_type"] = shift_type

	query = f"""
		SELECT
			sa.name, sa.employee, e.employee_name, e.department, e.designation, sa.shift_type, sa.start_date, sa.end_date, sa.status
		FROM `tabShift Assignment` sa
		LEFT JOIN `tabEmployee` e ON sa.employee = e.name
		WHERE {" AND ".join(base_conditions)}
	"""

	if department:
		query += " AND e.department = %(department)s"
		params["department"] = department

	if designation:
		query += " AND e.designation = %(designation)s"
		params["designation"] = designation

	query += " ORDER BY sa.start_date DESC"

	data = frappe.db.sql(query, params, as_dict=True)

	columns = [
		{"label": "Employee ID", "fieldname": "employee"},
		{"label": "Employee Name", "fieldname": "employee_name"},
		{"label": "Department", "fieldname": "department"},
		{"label": "Designation", "fieldname": "designation"},
		{"label": "Shift Type", "fieldname": "shift_type"},
		{"label": "Start Date", "fieldname": "start_date"},
		{"label": "End Date", "fieldname": "end_date"},
		{"label": "Status", "fieldname": "status"},
	]

	# Format dates
	for row in data:
		if row.get("start_date"):
			row["start_date"] = str(row["start_date"])
		if row.get("end_date"):
			row["end_date"] = str(row["end_date"])

	is_export = cint(export) if isinstance(export, (int, str)) and str(export).isdigit() else frappe.parse_json(export)
	is_pdf = cint(pdf) if isinstance(pdf, (int, str)) and str(pdf).isdigit() else frappe.parse_json(pdf)

	if is_export:
		xlsx_data = [[c["label"] for c in columns]]
		for row in data:
			xlsx_data.append([row.get(c["fieldname"], "") for c in columns])
		return build_xlsx_response(xlsx_data, "Shift_Assignment_Report")

	if is_pdf:
		company_name = frappe.db.get_single_value("Global Defaults", "default_company") or "Company"

		date_range = "All Dates"
		if from_date and to_date:
			date_range = f"{from_date} to {to_date}"

		context = {
			"report_title": _("Shift Assignment Report"),
			"company_name": company_name,
			"date_range": date_range,
			"selected_department": department,
			"selected_designation": designation,
			"selected_employee": employee,
			"selected_shift": shift_type,
			"generated_on": now_datetime().strftime("%Y-%m-%d %H:%M"),
			"columns": columns,
			"data": data
		}

		html_content = frappe.render_template("arijentek_core/templates/reports/shift_assignment_report.html", context)

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
		frappe.local.response.filename = f"Shift_Assignment_Report_{safe_date_range}.pdf"
		frappe.local.response.filecontent = pdf_binary
		frappe.local.response.type = "pdf"
		return

	return {
		"columns": columns,
		"data": data
	}

# ---------------------------------------------------------------------------
# Shift Location Report API
# ---------------------------------------------------------------------------

@frappe.whitelist()
def report_shift_location_list(export=False, pdf=False):
	"""
	Returns shift locations for the report.
	"""
	import frappe
	from frappe import _
	from frappe.utils import cint, now_datetime
	from frappe.utils.pdf import get_pdf
	from frappe.utils.xlsxutils import build_xlsx_response

	# Verify permissions
	if not can_read_shift_location():
		frappe.throw(_("You do not have permission to view Shift Locations"))

	query = """
		SELECT
			name, location_name, latitude, longitude, checkin_radius
		FROM `tabShift Location`
		ORDER BY name ASC
	"""
	data = frappe.db.sql(query, as_dict=True)

	columns = [
		{"label": "ID", "fieldname": "name"},
		{"label": "Location Name", "fieldname": "location_name"},
		{"label": "Latitude", "fieldname": "latitude"},
		{"label": "Longitude", "fieldname": "longitude"},
		{"label": "Check-in Radius (m)", "fieldname": "checkin_radius"},
	]

	is_export = cint(export) if isinstance(export, (int, str)) and str(export).isdigit() else frappe.parse_json(export)
	is_pdf = cint(pdf) if isinstance(pdf, (int, str)) and str(pdf).isdigit() else frappe.parse_json(pdf)

	if is_export:
		xlsx_data = [[c["label"] for c in columns]]
		for row in data:
			xlsx_data.append([row.get(c["fieldname"], "") for c in columns])
		return build_xlsx_response(xlsx_data, "Shift_Location_Report")

	if is_pdf:
		company_name = frappe.db.get_single_value("Global Defaults", "default_company") or "Company"

		context = {
			"report_title": _("Shift Location Report"),
			"company_name": company_name,
			"generated_on": now_datetime().strftime("%Y-%m-%d %H:%M"),
			"columns": columns,
			"data": data
		}

		html_content = frappe.render_template("arijentek_core/templates/reports/shift_location_report.html", context)

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
		frappe.local.response.filename = "Shift_Location_Report.pdf"
		frappe.local.response.filecontent = pdf_binary
		frappe.local.response.type = "pdf"
		return

	return {
		"columns": columns,
		"data": data
	}

# ---------------------------------------------------------------------------
# Shift Types Report API
# ---------------------------------------------------------------------------

@frappe.whitelist()
def report_shift_types_list(export=False, pdf=False):
	"""
	Returns shift types for the report.
	"""
	import frappe
	from frappe import _
	from frappe.utils import cint, now_datetime
	from frappe.utils.pdf import get_pdf
	from frappe.utils.xlsxutils import build_xlsx_response

	# Verify permissions
	if not can_read_shift_type():
		frappe.throw(_("You do not have permission to view Shift Types"))

	query = """
		SELECT
			name, start_time, end_time
		FROM `tabShift Type`
		ORDER BY name ASC
	"""
	data = frappe.db.sql(query, as_dict=True)

	columns = [
		{"label": "Shift ID", "fieldname": "name"},
		{"label": "Start Time", "fieldname": "start_time"},
		{"label": "End Time", "fieldname": "end_time"},
	]

	# Format data
	for row in data:
		if row.get("start_time"):
			row["start_time"] = str(row["start_time"])
		if row.get("end_time"):
			row["end_time"] = str(row["end_time"])

	is_export = cint(export) if isinstance(export, (int, str)) and str(export).isdigit() else frappe.parse_json(export)
	is_pdf = cint(pdf) if isinstance(pdf, (int, str)) and str(pdf).isdigit() else frappe.parse_json(pdf)

	if is_export:
		xlsx_data = [[c["label"] for c in columns]]
		for row in data:
			xlsx_data.append([row.get(c["fieldname"], "") for c in columns])
		return build_xlsx_response(xlsx_data, "Shift_Types_Report")

	if is_pdf:
		company_name = frappe.db.get_single_value("Global Defaults", "default_company") or "Company"

		context = {
			"report_title": _("Shift Types Report"),
			"company_name": company_name,
			"generated_on": now_datetime().strftime("%Y-%m-%d %H:%M"),
			"columns": columns,
			"data": data
		}

		html_content = frappe.render_template("arijentek_core/templates/reports/shift_type_report.html", context)

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
		frappe.local.response.filename = "Shift_Types_Report.pdf"
		frappe.local.response.filecontent = pdf_binary
		frappe.local.response.type = "pdf"
		return

	return {
		"columns": columns,
		"data": data
	}


