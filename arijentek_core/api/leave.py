import frappe
from frappe import _


def get_department_approvers(department: str, parentfield: str) -> list:
	"""Fetch all approvers for the given department and its sub-departments.

	Uses the nested set model (lft/rgt) on Department to find the full subtree,
	then joins Department Approver child table with User to return names.
	"""
	if not department:
		return []

	department_details = frappe.db.get_value("Department", department, ["lft", "rgt"], as_dict=True)
	if not department_details:
		return []

	departments = frappe.get_all(
		"Department",
		filters={
			"lft": ("<=", department_details.lft),
			"rgt": (">=", department_details.rgt),
			"disabled": 0,
		},
		pluck="name",
	)

	Approver = frappe.qb.DocType("Department Approver")
	User = frappe.qb.DocType("User")
	department_approvers = (
		frappe.qb.from_(User)
		.join(Approver)
		.on(Approver.approver == User.name)
		.select(User.name.as_("name"), User.full_name.as_("full_name"))
		.where((Approver.parent.isin(departments)) & (Approver.parentfield == parentfield))
	).run(as_dict=True)

	return department_approvers


@frappe.whitelist()
def get_leave_approval_details(employee: str) -> dict:
	"""Return leave approval details for a given employee.

	Follows the same logic as hrms.api.get_leave_approval_details:
	1. Reads the employee's direct leave_approver field
	2. Falls back to the first approver in the department's leave_approvers table
	3. Fetches all department (sub-department) approvers via get_department_approvers
	4. If the direct approver is not in the department list, appends them
	"""
	leave_approver, department = frappe.get_cached_value(
		"Employee",
		employee,
		["leave_approver", "department"],
	)

	if not leave_approver and department:
		leave_approver = frappe.db.get_value(
			"Department Approver",
			{"parent": department, "parentfield": "leave_approvers", "idx": 1},
			"approver",
		)

	leave_approver_name = (
		frappe.db.get_value("User", leave_approver, "full_name", cache=True) if leave_approver else None
	)
	department_approvers = get_department_approvers(department, "leave_approvers")

	if leave_approver and leave_approver not in [approver.name for approver in department_approvers]:
		department_approvers.append({"name": leave_approver, "full_name": leave_approver_name})

	return dict(
		leave_approver=leave_approver,
		leave_approver_name=leave_approver_name,
		department_approvers=department_approvers,
		is_mandatory=frappe.db.get_single_value(
			"HR Settings", "leave_approver_mandatory_in_leave_application"
		),
	)


@frappe.whitelist()
def is_user_leave_approver(employee_id: str | None = None) -> dict:
	"""Check if current user is a leave approver and return accessible employees.

	- frappe.get_all respects Employee doctype read permissions automatically
	- Explicitly assigned approvers (special_employees) are always included
	"""
	user = frappe.session.user
	has_approver_role = frappe.has_permission("Leave Application", "submit")
	has_global_approver = has_approver_role and not frappe.permissions.get_user_permissions(user).get(
		"Employee"
	)

	# Employees this user is explicitly assigned as approver for
	special_employees = frappe.db.get_all(
		"Employee",
		filters={"leave_approver": user, "status": ["in", ["Active", "Suspended"]]},
		fields=["name", "employee_name"],
		order_by="employee_name ASC",
	)

	# Also add themselves to the list if they are an employee
	my_employee = frappe.db.get_value("Employee", {"user_id": user}, ["name", "employee_name"], as_dict=True)

	is_approver = has_approver_role or bool(special_employees)

	if not is_approver:
		prevent_self = frappe.db.get_single_value("HR Settings", "prevent_self_leave_approval")
		return {
			"is_approver": False,
			"type": "none",
			"employees": [],
			"is_global_approver": False,
			"prevent_self_leave_approval": prevent_self,
		}

	if has_global_approver:
		employees = frappe.get_list(
			"Employee",
			filters={"status": ["in", ["Active", "Suspended"]]},
			fields=["name", "employee_name"],
			order_by="employee_name ASC",
		)
		existing = {e["name"] for e in employees}
		for emp in special_employees:
			if emp["name"] not in existing:
				employees.append(emp)
				existing.add(emp["name"])
	else:
		employees = list(special_employees)

	# Ensure self is at the front if not already present (only for users with global Leave Approver role)
	if has_global_approver and my_employee and not any(e["name"] == my_employee.name for e in employees):
		employees.insert(0, my_employee)

	prevent_self = frappe.db.get_single_value("HR Settings", "prevent_self_leave_approval")

	approver_type = "global" if has_global_approver else "special"
	return {
		"is_approver": True,
		"type": approver_type,
		"employees": employees,
		"is_global_approver": has_global_approver,
		"prevent_self_leave_approval": prevent_self,
	}


@frappe.whitelist()
def get_leave_status_options() -> list:
	"""Return allowed status options for Leave Application from the DocType."""
	options = frappe.get_meta("Leave Application").get_field("status").options or ""
	if isinstance(options, str):
		return [opt for opt in options.split("\n") if opt.strip() and opt.strip() != "Cancelled"]

	if isinstance(options, list):
		return [opt for opt in options if opt != "Cancelled"]

	return options or []


@frappe.whitelist()
def validate_leave_application(
	leave_type: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	employee: str | None = None,
) -> dict:
	"""Validate leave application data before creation.

	Returns {"success": True} if valid, or {"success": False, "error": str} with error message.
	"""
	if not all([leave_type, from_date, to_date]):
		return {"success": False, "error": "All fields are required: leave_type, from_date, to_date"}

	if not employee:
		employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
		if not employee:
			return {"success": False, "error": "No Employee found for current user. Please contact HR."}

	from_date = frappe.utils.getdate(from_date)
	to_date = frappe.utils.getdate(to_date)
	if to_date < from_date:
		return {"success": False, "error": "To Date must be after From Date"}

	employee_doc = frappe.get_doc("Employee", employee)
	if employee_doc.status not in ("Active", "Suspended"):
		return {"success": False, "error": f"Employee {employee_doc.employee_name} is not active"}

	leave_approver = frappe.db.get_value("Employee", employee, "leave_approver")
	if not leave_approver:
		return {
			"success": False,
			"error": f"Employee {employee_doc.employee_name} ({employee}) has no leave approver assigned. Please contact HR.",
		}

	return {"success": True}


@frappe.whitelist()
def create_leave_application(
	employee: str,
	leave_type: str,
	from_date: str,
	to_date: str,
	half_day: bool = False,
	leave_approver: str | None = None,
	leave_approver_name: str | None = None,
	status: str = "Open",
	description: str | None = None,
	name: str | None = None,
) -> dict:
	"""Create a new Leave Application document.

	- Checks can_create_leave_application permission
	- Validates all fields before creation
	- Uses ignore_permissions since this is an API endpoint for employees
	- Validates date range and leave type eligibility
	"""
	if not can_create_leave_application():
		return {"success": False, "error": "You do not have permission to create a Leave Application"}

	# Validate all inputs first
	validation = validate_leave_application(leave_type, from_date, to_date, employee)
	if not validation.get("success"):
		return validation

	from_date = frappe.utils.getdate(from_date)
	to_date = frappe.utils.getdate(to_date)
	employee_doc = frappe.get_doc("Employee", employee)

	# Check for holiday list
	holiday_list = employee_doc.holiday_list
	if not holiday_list:
		holiday_list = frappe.db.get_value(
			"Holiday List Assignment",
			{"applicable_for": "Employee", "assigned_to": employee},
			"holiday_list"
		)
	if not holiday_list:
		holiday_list = frappe.db.get_value("Company", employee_doc.company, "default_holiday_list")
	if not holiday_list:
		holiday_list = frappe.db.get_value(
			"Holiday List Assignment",
			{"applicable_for": "Company", "assigned_to": employee_doc.company},
			"holiday_list"
		)

	if not holiday_list:
		return {"success": False, "error": "Holiday list isn't assigned contact hr and continue."}

	# Resolve leave_approver if not provided
	if not leave_approver:
		leave_approver, dept = frappe.db.get_value("Employee", employee, ["leave_approver", "department"])

	# Explicitly set leave_approver_name (fetch_from is not configured on DocType)
	if not leave_approver_name:
		leave_approver_name = frappe.db.get_value("User", leave_approver, "full_name")

	if name:
		doc = frappe.get_doc("Leave Application", name)
		doc.leave_type = leave_type
		doc.from_date = from_date
		doc.to_date = to_date
		doc.half_day = half_day
		doc.description = description
		doc.leave_approver = leave_approver
		doc.leave_approver_name = leave_approver_name
		doc.status = status
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": employee,
				"employee_name": employee_doc.employee_name,
				"leave_type": leave_type,
				"from_date": from_date,
				"to_date": to_date,
				"half_day": half_day,
				"description": description,
				"leave_approver": leave_approver,
				"leave_approver_name": leave_approver_name,
				"status": status,
			}
		)
	try:
		if name:
			doc.save()
		else:
			doc.insert(ignore_permissions=True)

		if status in ("Approved", "Rejected") and doc.docstatus == 0:
			doc.submit()

		try:
			if not name:
				from arijentek_core.api.notifications import notify_approvers
				title = "New Leave Application"
				body = f"{doc.employee_name} has applied for {doc.leave_type} leave."
				notify_approvers(doc, title, body, module="hrm", route="/leave?tab=approvals")
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Leave Application Creation Notification Error")
	except Exception as e:
		frappe.db.rollback()
		msg = str(e)
		if frappe.message_log:
			import json

			try:
				msg = json.loads(frappe.message_log[-1]).get("message", msg)
			except Exception:
				pass
		msg = frappe.utils.strip_html_tags(msg)
		return {"success": False, "error": msg}

	return {"success": True, "name": doc.name, "message": _("Leave application saved")}


@frappe.whitelist()
def delete_leave_application(name: str):
	try:
		if frappe.db.exists("Leave Application", name):
			doc = frappe.get_doc("Leave Application", name)
			if doc.docstatus == 1:
				doc.cancel()
		frappe.delete_doc("Leave Application", name)
		# Ensure associated ledger entries are purged so no ghost records remain
		if frappe.db.table_exists("Leave Ledger Entry"):
			frappe.db.delete("Leave Ledger Entry", {"transaction_name": name})
		return {"success": True}
	except Exception as e:
		return {"success": False, "error": str(e)}


def on_leave_application_trash(doc, method=None):
	"""
	Safety-net hook executed whenever a Leave Application is deleted (via Portal, Desk, or API).
	Purges associated Leave Ledger Entries so no ghost records remain.
	"""
	if frappe.db.table_exists("Leave Ledger Entry"):
		frappe.db.delete("Leave Ledger Entry", {"transaction_name": doc.name})



@frappe.whitelist()
def get_leave_applications_for_all(
	employee: str | None = None,
	status: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	search_text: str | None = None,
	page: int = 1,
	page_size: int = 0,
) -> dict | list[dict]:
	"""Return all leave applications for employees the current user can access.

	Uses the same employee visibility logic as is_user_leave_approver so that
	approvers see applications for everyone they can approve, not just their own.
	"""
	user = frappe.session.user

	special_employees = frappe.db.get_all(
		"Employee",
		filters={"leave_approver": user, "status": ["in", ["Active", "Suspended"]]},
		fields=["name", "employee_name"],
		order_by="employee_name ASC",
	)

	my_employee = frappe.db.get_value("Employee", {"user_id": user}, ["name", "employee_name"], as_dict=True)

	permission_employees = frappe.get_list(
		"Employee",
		filters={"status": ["in", ["Active", "Suspended"]]},
		fields=["name", "employee_name"],
		order_by="employee_name ASC",
	)

	existing = {e["name"] for e in permission_employees}
	for emp in special_employees:
		if emp["name"] not in existing:
			permission_employees.append(emp)
			existing.add(emp["name"])

	if my_employee and not any(e["name"] == my_employee.name for e in permission_employees):
		permission_employees.insert(0, my_employee)

	if not permission_employees:
		return {"rows": [], "total": 0, "page": page, "page_size": page_size} if page_size > 0 else []

	employee_names = [e["name"] for e in permission_employees]

	where_conditions = ["la.docstatus < 2"]
	params = []

	if employee:
		if employee in employee_names:
			where_conditions.append("la.employee = %s")
			params.append(employee)
		else:
			return {"rows": [], "total": 0, "page": page, "page_size": page_size} if page_size > 0 else []
	else:
		where_conditions.append(f"la.employee IN ({', '.join(['%s'] * len(employee_names))})")
		params.extend(employee_names)

	if status:
		where_conditions.append("la.status = %s")
		params.append(status)

	if from_date and to_date:
		where_conditions.append("la.from_date <= %s AND la.to_date >= %s")
		params.extend([to_date, from_date])
	elif from_date:
		where_conditions.append("la.to_date >= %s")
		params.append(from_date)
	elif to_date:
		where_conditions.append("la.from_date <= %s")
		params.append(to_date)

	if search_text:
		where_conditions.append("(la.name LIKE %s OR la.employee_name LIKE %s OR la.leave_type LIKE %s)")
		like_param = f"%{search_text}%"
		params.extend([like_param, like_param, like_param])

	where_clause = " AND ".join(where_conditions)

	total = 0
	if page_size > 0:
		count_query = f"SELECT COUNT(*) FROM `tabLeave Application` la WHERE {where_clause}"
		total = frappe.db.sql(count_query, tuple(params))[0][0]

	limit_clause = ""
	query_params = list(params)
	if page_size > 0:
		limit_clause = "LIMIT %s OFFSET %s"
		query_params.extend([page_size, (max(1, page) - 1) * page_size])

	applications = frappe.db.sql(
		f"""
		SELECT
			la.name, la.posting_date, la.employee, la.employee_name, la.leave_type,
			la.status, la.from_date, la.to_date, la.half_day, la.description,
			la.total_leave_days, la.leave_balance, la.leave_approver, la.creation
		FROM `tabLeave Application` la
		WHERE {where_clause}
		ORDER BY la.from_date DESC, la.creation DESC
		{limit_clause}
		""",
		tuple(query_params),
		as_dict=True,
	)

	if page_size > 0:
		return {"rows": applications, "total": total, "page": page, "page_size": page_size}

	return applications


@frappe.whitelist()
def update_leave_status(name: str, status: str):
	try:
		doc = frappe.get_doc("Leave Application", name)

		if status == "Approved" and doc.docstatus == 0:
			holiday_list = frappe.db.get_value("Employee", doc.employee, "holiday_list")
			if not holiday_list:
				holiday_list = frappe.db.get_value(
					"Holiday List Assignment",
					{"applicable_for": "Employee", "assigned_to": doc.employee},
					"holiday_list"
				)
			if not holiday_list:
				holiday_list = frappe.db.get_value("Company", doc.company, "default_holiday_list")
			if not holiday_list:
				holiday_list = frappe.db.get_value(
					"Holiday List Assignment",
					{"applicable_for": "Company", "assigned_to": doc.company},
					"holiday_list"
				)

			if not holiday_list:
				frappe.throw("Employee doesn't have a holiday list assigned. Please assign a holiday list and continue.")

		doc.status = status
		if status in ("Approved", "Rejected") and doc.docstatus == 0:
			doc.submit()
		else:
			doc.save()

		try:
			from arijentek_core.api.notifications import notify_owner
			title = f"Leave Application {status}"
			body = f"Your {doc.leave_type} leave application has been {status}."
			notify_owner(doc, title, body, module="hrm", route="/leave?tab=applications")
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Leave Application Status Notification Error")

		return {"success": True}
	except Exception as e:
		frappe.db.rollback()
		msg = str(e)
		if frappe.message_log:
			import json

			try:
				msg = json.loads(frappe.message_log[-1]).get("message", msg)
			except Exception:
				pass
		msg = frappe.utils.strip_html_tags(msg)
		return {"success": False, "error": msg}


@frappe.whitelist()
def delete_approved_rejected_leave(leave_application):
	"""Delete approved/rejected leave application and its related attendance entries."""
	user = frappe.session.user
	leave = frappe.get_doc("Leave Application", leave_application)

	is_system_manager = "System Manager" in frappe.get_roles(user)
	is_approver = frappe.db.exists(
		"Employee", {"name": leave.employee, "status": "Active", "leave_approver": user}
	)

	if not (is_system_manager or is_approver):
		return {"success": False, "error": "Not authorized to delete this leave application"}

	try:
		# 1. Get and delete related attendance records
		attendances = frappe.get_all(
			"Attendance",
			filters={
				"employee": leave.employee,
				"attendance_date": ["between", [leave.from_date, leave.to_date]],
			},
			fields=["name", "docstatus"],
		)
		for att in attendances:
			if att.docstatus == 1:
				att_doc = frappe.get_doc("Attendance", att.name)
				att_doc.cancel()
			frappe.delete_doc("Attendance", att.name, ignore_permissions=True)

		# 2. Cancel Leave Application if submitted
		if leave.docstatus == 1:
			leave.cancel()

		# 3. Delete the Leave Application
		frappe.delete_doc("Leave Application", leave.name, ignore_permissions=True)
		# Ensure associated ledger entries are purged
		if frappe.db.table_exists("Leave Ledger Entry"):
			frappe.db.delete("Leave Ledger Entry", {"transaction_name": leave.name})
		frappe.db.commit()
		return {"success": True}
	except Exception as e:
		frappe.db.rollback()
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_leave_application(name: str) -> dict:
	try:
		doc = frappe.get_doc("Leave Application", name)
		doc.check_permission("read")
		return doc.as_dict()
	except frappe.PermissionError:
		frappe.throw(_("Not permitted to view this Leave Application"), frappe.PermissionError)


def _handle_exception(e):
	frappe.db.rollback()
	msg = str(e)
	if frappe.message_log:
		import json

		try:
			msg = json.loads(frappe.message_log[-1]).get("message", msg)
		except Exception:
			pass
	msg = frappe.utils.strip_html_tags(msg)
	return {"success": False, "error": msg}


@frappe.whitelist()
def get_compensatory_leave_requests(
	name=None, employee=None, month_year=None, start_date=None, end_date=None, search_text: str | None = None, page: int = 1, page_size: int = 0
):
	"""Return compensatory leave requests.

	If ``name`` is provided, return the full document as a dict (single record detail view).
	Otherwise return a list of records matching the filter criteria.
	"""
	# --- Single record mode ---
	if name:
		try:
			doc = frappe.get_doc("Zevar Compensatory Leave Request", name)
			doc.check_permission("read")
			return doc.as_dict()
		except frappe.PermissionError:
			frappe.throw(_("Not permitted to view this Compensatory Leave Request"), frappe.PermissionError)

	# --- List mode ---
	user = frappe.session.user
	has_submit_perm = frappe.has_permission("Zevar Compensatory Leave Request", "submit")

	filters = {}
	if not has_submit_perm:
		emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
		if not emp:
			return {"rows": [], "total": 0, "page": page, "page_size": page_size} if page_size > 0 else []
		filters["employee"] = emp
	elif employee:
		filters["employee"] = employee

	if start_date and end_date:
		filters["work_from_date"] = ["between", [start_date, end_date]]
	elif month_year:
		filters["work_from_date"] = ["like", f"{month_year}%"]

	if search_text:
		filters["name"] = ["like", f"%{search_text}%"]

	limit_start = (max(1, page) - 1) * page_size if page_size > 0 else 0
	limit_page_length = page_size if page_size > 0 else 0

	requests = frappe.get_all(
		"Zevar Compensatory Leave Request",
		filters=filters,
		fields=[
			"name",
			"employee",
			"employee_name",
			"department",
			"leave_type",
			"leave_allocation",
			"work_from_date",
			"work_end_date",
			"half_day",
			"half_day_date",
			"reason",
			"docstatus",
			"status",
			"creation",
		],
		order_by="creation desc",
		limit_start=limit_start,
		limit_page_length=limit_page_length,
	)

	if page_size > 0:
		total = frappe.db.count("Zevar Compensatory Leave Request", filters=filters)
		return {"rows": requests, "total": total, "page": page, "page_size": page_size}

	return requests


@frappe.whitelist()
def create_compensatory_leave_request(**kwargs) -> dict:
	try:
		validation = validate_compensatory_leave_request(kwargs)
		if not validation.get("success"):
			return validation

		user = frappe.session.user
		has_submit_perm = frappe.has_permission("Zevar Compensatory Leave Request", "submit")

		employee = kwargs.get("employee")
		if not has_submit_perm or not employee:
			employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
			if not employee:
				frappe.throw(_("No Employee record found for current user"))

		doc = frappe.get_doc(
			{
				"doctype": "Zevar Compensatory Leave Request",
				"employee": employee,
				"leave_type": kwargs.get("leave_type") or "Compensatory Off",
				"work_from_date": kwargs.get("work_from_date"),
				"work_end_date": kwargs.get("work_end_date"),
				"half_day": frappe.utils.cint(kwargs.get("half_day", 0)),
				"half_day_date": kwargs.get("half_day_date")
				if frappe.utils.cint(kwargs.get("half_day", 0))
				else None,
				"reason": kwargs.get("reason"),
			}
		)

		doc.insert()

		try:
			from arijentek_core.api.notifications import notify_approvers
			title = "New Compensatory Leave Request"
			body = f"{doc.employee_name} has requested compensatory leave."
			notify_approvers(doc, title, body, module="hrm", route="/leave?tab=compensatory_leave")
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Compensatory Leave Creation Notification Error")

		return {"success": True, "name": doc.name}
	except Exception as e:
		return _handle_exception(e)


@frappe.whitelist()
def update_compensatory_leave_request(**kwargs) -> dict:
	try:
		name = kwargs.get("name")
		if not name:
			frappe.throw(_("Document name is required"))

		doc = frappe.get_doc("Zevar Compensatory Leave Request", name)
		if doc.docstatus != 0:
			frappe.throw(_("Only Draft compensatory leave requests can be updated"))

		doc.check_permission("write")

		if kwargs.get("leave_type"):
			doc.leave_type = kwargs.get("leave_type")
		if kwargs.get("work_from_date"):
			doc.work_from_date = kwargs.get("work_from_date")
		if kwargs.get("work_end_date"):
			doc.work_end_date = kwargs.get("work_end_date")
		doc.half_day = frappe.utils.cint(kwargs.get("half_day", 0))
		doc.half_day_date = kwargs.get("half_day_date") if doc.half_day else None
		if kwargs.get("reason"):
			doc.reason = kwargs.get("reason")

		# Reset status to Open when an employee updates a Rejected draft
		doc.status = "Open"
		doc.save()
		return {"success": True, "name": doc.name}
	except Exception as e:
		return _handle_exception(e)


@frappe.whitelist()
def delete_compensatory_leave_request(name: str) -> dict:
	try:
		if not name:
			frappe.throw(_("Document name is required"))

		doc = frappe.get_doc("Zevar Compensatory Leave Request", name)
		if doc.docstatus != 0:
			if not can_submit_compensatory_leave_request():
				frappe.throw(_("Only Draft compensatory leave requests can be deleted"))
			if doc.docstatus == 1:
				doc.cancel()
			frappe.delete_doc("Zevar Compensatory Leave Request", name, ignore_permissions=True)
			return {"success": True}

		doc.check_permission("delete")
		frappe.delete_doc("Zevar Compensatory Leave Request", name)
		return {"success": True}
	except Exception as e:
		return _handle_exception(e)


@frappe.whitelist()
def approve_compensatory_leave_request(name: str) -> dict:
	try:
		if not name:
			frappe.throw(_("Document name is required"))

		doc = frappe.get_doc("Zevar Compensatory Leave Request", name)
		if doc.docstatus == 1:
			return {"success": True, "message": _("Already approved")}

		doc.check_permission("submit")
		doc.status = "Approved"
		doc.submit()

		try:
			from arijentek_core.api.notifications import notify_owner
			title = "Compensatory Leave Approved"
			body = "Your compensatory leave request has been Approved."
			notify_owner(doc, title, body, module="hrm", route="/leave?tab=compensatory_leave")
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Compensatory Leave Status Notification Error")

		return {"success": True, "name": doc.name}
	except Exception as e:
		return _handle_exception(e)


@frappe.whitelist()
def reject_compensatory_leave_request(name: str) -> dict:
	try:
		if not name:
			frappe.throw(_("Document name is required"))

		doc = frappe.get_doc("Zevar Compensatory Leave Request", name)

		# Flag it as explicitly rejected so the UI knows it wasn't just cancelled by the user
		doc.db_set("status", "Rejected")

		# User requested to not change anything in the 'desk column' (docstatus) when rejecting
		# It just stays as it is with status updated.

		try:
			from arijentek_core.api.notifications import notify_owner
			title = "Compensatory Leave Rejected"
			body = "Your compensatory leave request has been Rejected."
			notify_owner(doc, title, body, module="hrm", route="/leave?tab=compensatory_leave")
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Compensatory Leave Status Notification Error")

		return {"success": True, "name": doc.name}
	except Exception as e:
		return _handle_exception(e)


@frappe.whitelist()
def can_approve_compensatory_leaves() -> bool:
	return bool(frappe.has_permission("Zevar Compensatory Leave Request", "submit"))


@frappe.whitelist()
def get_compensatory_leave_types() -> list[str]:
	return frappe.get_all("Leave Type", filters={"is_compensatory": 1}, pluck="name")


@frappe.whitelist()
def get_holidays_for_employee(employee: str) -> list[dict]:
	from hrms.utils.holiday_list import get_holiday_list_for_employee

	holiday_list = get_holiday_list_for_employee(employee, raise_exception=False)
	if not holiday_list:
		return []

	Holiday = frappe.qb.DocType("Holiday")
	holidays = (
		frappe.qb.from_(Holiday)
		.select(Holiday.name, Holiday.holiday_date, Holiday.description, Holiday.weekly_off)
		.where(Holiday.parent == holiday_list)
		.orderby(Holiday.holiday_date, order=frappe.qb.asc)
	).run(as_dict=True)

	for holiday in holidays:
		holiday["description"] = frappe.utils.strip_html_tags(holiday["description"] or "").strip()

	return holidays


def validate_compensatory_leave_request(kwargs) -> dict:
	"""Validate compensatory leave request dates against active leave periods.
	Returns {'success': True} if a leave period covering the dates exists,
	otherwise returns {'success': False, 'error': <friendly message>}.
	"""
	work_from = kwargs.get("work_from_date")
	work_to = kwargs.get("work_end_date")
	if not work_from:
		return {"success": False, "error": "Work From Date is required."}
	# Convert to date objects
	try:
		work_from_date = frappe.utils.getdate(work_from)
	except Exception:
		return {"success": False, "error": "Invalid Work From Date format."}
	if work_to:
		try:
			work_to_date = frappe.utils.getdate(work_to)
		except Exception:
			return {"success": False, "error": "Invalid Work End Date format."}
	else:
		work_to_date = work_from_date
	# Find active Leave Period covering the range
	filters = {"is_active": 1, "from_date": ("<=", work_from_date), "to_date": (">=", work_to_date)}
	leave_period = frappe.get_all("Leave Period", filters=filters, limit=1)
	if not leave_period:
		return {
			"success": False,
			"error": "No active Leave Period covers the selected dates. Please ask HR to create an appropriate Leave Period.",
		}
	return {"success": True}


@frappe.whitelist()
def can_read_leave_application():
	"""
	Returns True if the current user has permission to read Leave Application.
	This is true for 'HR Manager', 'System Manager', or users with explicit read permissions on the 'Leave Application' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Leave Application", "read"):
		return True

	return False


@frappe.whitelist()
def can_create_leave_application():
	"""
	Returns True if the current user has permission to create a Leave Application.
	This is true for 'HR Manager', 'System Manager', or users with explicit create permissions on the 'Leave Application' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Leave Application", "create"):
		return True

	return False


@frappe.whitelist()
def get_employee_list_for_leave(department="", designation="", branch="", employment_type="", leave_period="", exclude_has_leave_policy_for_period=False):
	"""
	Return a list of employees for the leave page.
	Accessible if the user is an 'HR Manager' or 'System Manager' or has 'submit' permission on 'Leave Application' doctype.
	Otherwise, returns an empty list.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)

	if (
		"HR Manager" in roles
		or "System Manager" in roles
		or frappe.has_permission("Leave Application", "submit")
	):
		filters = {"status": ["in", ["Active", "Suspended"]]}
		if department:
			filters["department"] = department
		if designation:
			filters["designation"] = designation
		if branch:
			filters["branch"] = branch
		if employment_type:
			filters["employment_type"] = employment_type

		if str(exclude_has_leave_policy_for_period).lower() in ["true", "1"] and leave_period:
			assigned_employees = frappe.get_all(
				"Leave Policy Assignment",
				filters={"leave_period": leave_period, "docstatus": ("<", 2)},
				pluck="employee"
			)
			if assigned_employees:
				filters["name"] = ["not in", assigned_employees]

		return frappe.get_all(
			"Employee",
			filters=filters,
			fields=["name", "employee_name", "department", "designation", "branch"],
			order_by="employee_name asc",
		)
	return []


@frappe.whitelist()
def get_supported_countries():
	try:
		from erpnext.setup.doctype.holiday_list.holiday_list import local_country_name
		from holidays.utils import list_supported_countries
	except ImportError:
		return {"countries": [], "subdivisions_by_country": {}}

	subdivisions_by_country = list_supported_countries()
	countries = [
		{"value": country, "label": local_country_name(country)}
		for country in subdivisions_by_country.keys()
	]
	return {
		"countries": countries,
		"subdivisions_by_country": subdivisions_by_country,
	}

@frappe.whitelist()
def get_local_holidays(country, from_date, to_date, subdivision=None):
	try:
		from holidays import country_holidays
	except ImportError:
		return []

	from frappe.utils import getdate

	from_date = getdate(from_date)
	to_date = getdate(to_date)

	holidays = []

	for holiday_date, holiday_name in country_holidays(
		country,
		subdiv=subdivision,
		years=list(range(from_date.year, to_date.year + 1)),
		language=frappe.local.lang,
	).items():
		if holiday_date < from_date or holiday_date > to_date:
			continue

		holidays.append({
			"date": holiday_date.strftime("%Y-%m-%d"),
			"description": holiday_name,
			"is_half_day": False
		})

	return holidays


@frappe.whitelist()
def can_submit_leave_application():
	"""
	Returns True if the current user has permission to submit a Leave Application.
	This is true for 'HR Manager', 'System Manager', or users with explicit submit permissions on the 'Leave Application' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Leave Application", "submit"):
		return True

	return False


@frappe.whitelist()
def can_edit_leave_application():
	"""
	Returns True if the current user has permission to edit (write) a Leave Application.
	This is true for 'HR Manager', 'System Manager', or users with explicit write permissions on the 'Leave Application' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Leave Application", "write"):
		return True

	return False


@frappe.whitelist()
def can_delete_leave_application():
	"""
	Returns True if the current user has permission to delete a Leave Application.
	This is true for 'HR Manager', 'System Manager', or users with explicit delete permissions on the 'Leave Application' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Leave Application", "delete"):
		return True

	return False


@frappe.whitelist()
def can_read_compensatory_leave_request():
	"""
	Returns True if the current user has permission to read Compensatory Leave Request.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Zevar Compensatory Leave Request", "read"):
		return True

	return False


@frappe.whitelist()
def can_create_compensatory_leave_request():
	"""
	Returns True if the current user has permission to create a Compensatory Leave Request.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Zevar Compensatory Leave Request", "create"):
		return True

	return False


@frappe.whitelist()
def can_submit_compensatory_leave_request():
	"""
	Returns True if the current user has permission to submit a Compensatory Leave Request.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Zevar Compensatory Leave Request", "submit"):
		return True

	return False


@frappe.whitelist()
def can_edit_compensatory_leave_request():
	"""
	Returns True if the current user has permission to edit (write) a Compensatory Leave Request.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Zevar Compensatory Leave Request", "write"):
		return True

	return False


@frappe.whitelist()
def can_delete_compensatory_leave_request():
	"""
	Returns True if the current user has permission to delete a Compensatory Leave Request.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Zevar Compensatory Leave Request", "delete"):
		return True

	return False


@frappe.whitelist()
def can_read_leave_types():
	"""
	Returns True if the current user has permission to read Leave Type.
	This is true for 'HR Manager', 'System Manager', or users with explicit read permissions on the 'Leave Type' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Leave Type", "read"):
		return True

	return False


@frappe.whitelist()
def can_create_leave_types():
	"""
	Returns True if the current user has permission to create a Leave Type.
	This is true for 'HR Manager', 'System Manager', or users with explicit create permissions on the 'Leave Type' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Leave Type", "create"):
		return True

	return False


@frappe.whitelist()
def can_edit_leave_types():
	"""
	Returns True if the current user has permission to edit (write) a Leave Type.
	This is true for 'HR Manager', 'System Manager', or users with explicit write permissions on the 'Leave Type' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Leave Type", "write"):
		return True

	return False


@frappe.whitelist()
def can_delete_leave_types():
	"""
	Returns True if the current user has permission to delete a Leave Type.
	This is true for 'HR Manager', 'System Manager', or users with explicit delete permissions on the 'Leave Type' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Leave Type", "delete"):
		return True

	return False


@frappe.whitelist()
def get_employee_leave_balance_map(employee: str | None = None) -> dict[str, dict[str, float]]:
	from frappe.utils import getdate
	from hrms.hr.doctype.leave_application.leave_application import get_leave_details

	if not employee:
		employee = frappe.db.get_value(
			"Employee", {"user_id": frappe.session.user, "status": "Active"}, "name"
		)

	if not employee:
		return {}

	date = getdate()
	leave_map = {}

	leave_details = get_leave_details(employee, date)
	allocation = leave_details.get("leave_allocation", {})

	for leave_type, details in allocation.items():
		leave_map[leave_type] = {
			"allocated_leaves": details.get("total_leaves", 0),
			"balance_leaves": details.get("remaining_leaves", 0),
			"used_leaves": details.get("leaves_taken", 0),
			"pending_leaves": details.get("leaves_pending_approval", 0) or details.get("pending_leaves", 0),
		}

	return leave_map


@frappe.whitelist()
def get_leave_types(search_text: str | None = None, page: int = 1, page_size: int = 0) -> dict | list[dict]:
	"""Return all Leave Type records with key fields for listing."""
	filters = {}
	if search_text:
		filters["leave_type_name"] = ["like", f"%{search_text}%"]

	limit_start = (max(1, page) - 1) * page_size if page_size > 0 else 0
	limit_page_length = page_size if page_size > 0 else 0

	leave_types = frappe.get_all(
		"Leave Type",
		filters=filters,
		fields=[
			"name",
			"leave_type_name",
			"max_leaves_allowed",
			"applicable_after",
			"max_continuous_days_allowed",
			"is_carry_forward",
			"is_lwp",
			"is_optional_leave",
			"allow_negative",
			"include_holiday",
			"is_compensatory",
			"is_earned_leave",
			"is_ppl",
			"allow_encashment",
			"allow_over_allocation",
		],
		order_by="leave_type_name asc",
		limit_start=limit_start,
		limit_page_length=limit_page_length,
	)

	if page_size > 0:
		total = frappe.db.count("Leave Type", filters=filters)
		return {"rows": leave_types, "total": total, "page": page, "page_size": page_size}

	return leave_types


@frappe.whitelist()
def get_leave_type(name: str) -> dict:
	"""Fetch a single Leave Type document by name."""
	try:
		doc = frappe.get_doc("Leave Type", name)
		return doc.as_dict()
	except frappe.DoesNotExistError:
		frappe.throw(_("Leave Type {0} does not exist").format(name))


@frappe.whitelist()
def save_leave_type(leave_type_data: dict) -> dict:
	"""Create or update a Leave Type document.

	- If leave_type_data contains 'name', updates the existing document
	- Otherwise creates a new Leave Type
	"""
	frappe.only_for(["HR Manager", "System Manager"])
	try:
		name = leave_type_data.get("name")
		leave_type_name = leave_type_data.get("leave_type_name")

		if not leave_type_name:
			return {"success": False, "error": "Leave Type name is required"}

		if name:
			if name != leave_type_name:
				frappe.rename_doc("Leave Type", name, leave_type_name)
				name = leave_type_name

			doc = frappe.get_doc("Leave Type", name)
			doc.is_lwp = leave_type_data.get("is_lwp", 0)
			doc.is_compensatory = leave_type_data.get("is_compensatory", 0)
			doc.save()
		else:
			doc = frappe.get_doc(
				{
					"doctype": "Leave Type",
					"leave_type_name": leave_type_name,
					"is_lwp": leave_type_data.get("is_lwp", 0),
					"is_compensatory": leave_type_data.get("is_compensatory", 0),
				}
			)
			doc.insert(ignore_permissions=True)

		return {"success": True, "name": doc.name, "message": _("Leave Type saved")}
	except frappe.DuplicateEntryError:
		frappe.db.rollback()
		return {"success": False, "error": _("Leave Type '{0}' already exists").format(leave_type_name)}
	except Exception as e:
		frappe.db.rollback()
		msg = str(e)
		if frappe.message_log:
			import json

			try:
				msg = json.loads(frappe.message_log[-1]).get("message", msg)
			except Exception:
				pass
		msg = frappe.utils.strip_html_tags(msg)
		return {"success": False, "error": msg}


@frappe.whitelist()
def delete_leave_type(name: str) -> dict:
	"""Delete a Leave Type."""
	try:
		if not can_delete_leave_types():
			return {"success": False, "error": _("Not permitted to delete Leave Types")}

		doc = frappe.get_doc("Leave Type", name)
		doc.delete()
		return {"success": True}
	except Exception as e:
		frappe.db.rollback()
		msg = str(e)
		if frappe.message_log:
			import json

			try:
				msg = json.loads(frappe.message_log[-1]).get("message", msg)
			except Exception:
				pass
		msg = frappe.utils.strip_html_tags(msg)
		return {"success": False, "error": msg}


@frappe.whitelist()
def validate_delete_approved_entry(name: str) -> dict:
	try:
		if not name:
			return {"success": False, "error": _("Document name is required")}

		doc = frappe.get_doc("Zevar Compensatory Leave Request", name)

		if doc.docstatus != 0:
			if not can_submit_compensatory_leave_request():
				return {
					"success": False,
					"error": _("Not authorized to delete submitted compensatory leave requests"),
				}

		if doc.docstatus == 1:
			# Proactive balance check based on Leave Allocation and Leave Application
			date_difference = frappe.utils.date_diff(doc.work_end_date, doc.work_from_date) + 1
			if doc.half_day:
				date_difference -= 0.5

			allocated = (
				frappe.db.sql(
					"""
				SELECT SUM(total_leaves_allocated) FROM `tabLeave Allocation`
				WHERE employee = %s AND leave_type = %s AND docstatus = 1
			""",
					(doc.employee, doc.leave_type),
				)[0][0]
				or 0
			)

			used = (
				frappe.db.sql(
					"""
				SELECT SUM(total_leave_days) FROM `tabLeave Application`
				WHERE employee = %s AND leave_type = %s AND docstatus = 1
			""",
					(doc.employee, doc.leave_type),
				)[0][0]
				or 0
			)

			if (allocated - date_difference) < used:
				return {
					"success": False,
					"error": _(
						"Cannot delete: This compensatory leave has already been used in a Leave Application."
					),
				}

			doc.cancel()

		frappe.delete_doc("Zevar Compensatory Leave Request", name, ignore_permissions=True)
		return {"success": True}

	except Exception as e:
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def can_read_leave_policy():
	"""
	Returns True if the current user has permission to read Leave Policy.
	This is true for 'HR Manager', 'System Manager', or users with explicit read permissions on the 'Leave Policy' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Leave Policy", "read"):
		return True

	return False


@frappe.whitelist()
def can_create_leave_policy():
	"""
	Returns True if the current user has permission to create a Leave Policy.
	This is true for 'HR Manager', 'System Manager', or users with explicit create permissions on the 'Leave Policy' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Leave Policy", "create"):
		return True

	return False


@frappe.whitelist()
def can_edit_leave_policy():
	"""
	Returns True if the current user has permission to edit (write) a Leave Policy.
	This is true for 'HR Manager', 'System Manager', or users with explicit write permissions on the 'Leave Policy' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Leave Policy", "write"):
		return True

	return False


@frappe.whitelist()
def can_delete_leave_policy():
	"""
	Returns True if the current user has permission to delete a Leave Policy.
	This is true for 'HR Manager', 'System Manager', or users with explicit delete permissions on the 'Leave Policy' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Leave Policy", "delete"):
		return True

	return False


@frappe.whitelist()
def can_read_leave_period():
	"""
	Returns True if the current user has permission to read Leave Period.
	This is true for 'HR Manager', 'System Manager', or users with explicit read permissions on the 'Leave Period' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Leave Period", "read"):
		return True

	return False


@frappe.whitelist()
def can_create_leave_period():
	"""
	Returns True if the current user has permission to create a Leave Period.
	This is true for 'HR Manager', 'System Manager', or users with explicit create permissions on the 'Leave Period' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Leave Period", "create"):
		return True

	return False


@frappe.whitelist()
def can_edit_leave_period():
	"""
	Returns True if the current user has permission to edit (write) a Leave Period.
	This is true for 'HR Manager', 'System Manager', or users with explicit write permissions on the 'Leave Period' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Leave Period", "write"):
		return True

	return False


@frappe.whitelist()
def can_delete_leave_period():
	"""
	Returns True if the current user has permission to delete a Leave Period.
	This is true for 'HR Manager', 'System Manager', or users with explicit delete permissions on the 'Leave Period' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Leave Period", "delete"):
		return True

	return False


@frappe.whitelist()
def get_leave_period(name: str | None = None):
	"""
	If 'name' is provided, fetch a single Leave Period document as a dict.
	Otherwise, return a list of Leave Period records.
	"""
	if name:
		try:
			doc = frappe.get_doc("Leave Period", name)
			return doc.as_dict()
		except frappe.DoesNotExistError:
			frappe.throw(_("Leave Period {0} does not exist").format(name))

	return frappe.get_all(
		"Leave Period",
		fields=["name", "from_date", "to_date", "is_active", "company"],
		order_by="creation desc",
	)


@frappe.whitelist()
def save_leave_period(leave_period_data: dict) -> dict:
	"""Create or update a Leave Period document.

	- If leave_period_data contains 'name', updates the existing document
	- Otherwise creates a new Leave Period
	"""
	frappe.only_for(["HR Manager", "System Manager"])
	try:
		from frappe.utils import getdate

		name = leave_period_data.get("name")
		from_date = leave_period_data.get("from_date")
		to_date = leave_period_data.get("to_date")

		if not from_date:
			return {"success": False, "error": "From Date is required"}
		if not to_date:
			return {"success": False, "error": "To Date is required"}

		if getdate(from_date) >= getdate(to_date):
			return {"success": False, "error": "To Date must be greater than From Date"}

		company = leave_period_data.get("company") or frappe.defaults.get_defaults().company
		if not company:
			return {"success": False, "error": "Company is required"}

		if name:
			doc = frappe.get_doc("Leave Period", name)
			doc.from_date = from_date
			doc.to_date = to_date
			doc.is_active = leave_period_data.get("is_active", 0)
			doc.company = company
			doc.save()
		else:
			doc = frappe.get_doc(
				{
					"doctype": "Leave Period",
					"from_date": from_date,
					"to_date": to_date,
					"is_active": leave_period_data.get("is_active", 0),
					"company": company,
				}
			)
			doc.insert(ignore_permissions=True)

		return {"success": True, "name": doc.name, "message": _("Leave Period saved")}
	except Exception as e:
		frappe.db.rollback()
		msg = str(e)
		if frappe.message_log:
			import json

			try:
				msg = json.loads(frappe.message_log[-1]).get("message", msg)
			except Exception:
				pass
		msg = frappe.utils.strip_html_tags(msg)
		return {"success": False, "error": msg}


@frappe.whitelist()
def can_read_leave_allocation():
	"""
	Returns True if the current user has permission to read Leave Allocation.
	This is true for 'HR Manager', 'System Manager', or users with explicit read permissions on the 'Leave Allocation' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Leave Allocation", "read"):
		return True

	return False


@frappe.whitelist()
def can_create_leave_allocation():
	"""
	Returns True if the current user has permission to create a Leave Allocation.
	This is true for 'HR Manager', 'System Manager', or users with explicit create permissions on the 'Leave Allocation' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Leave Allocation", "create"):
		return True

	return False


@frappe.whitelist()
def can_edit_leave_allocation():
	"""
	Returns True if the current user has permission to edit (write) a Leave Allocation.
	This is true for 'HR Manager', 'System Manager', or users with explicit write permissions on the 'Leave Allocation' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Leave Allocation", "write"):
		return True

	return False


@frappe.whitelist()
def can_delete_leave_allocation():
	"""
	Returns True if the current user has permission to delete a Leave Allocation.
	This is true for 'HR Manager', 'System Manager', or users with explicit delete permissions on the 'Leave Allocation' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Leave Allocation", "delete"):
		return True

	return False


@frappe.whitelist()
def get_leave_policy(name: str | None = None, search_text: str | None = None, page: int = 1, page_size: int = 0):
	"""
	If 'name' is provided, fetch a single Leave Policy document as a dict.
	Otherwise, return a list of Leave Policy records, optionally filtered by 'search_text'.
	"""
	if name:
		try:
			doc = frappe.get_doc("Leave Policy", name)
			doc_dict = doc.as_dict()
			doc_dict["is_used"] = bool(frappe.db.exists("Leave Policy Assignment", {"leave_policy": name}))
			return doc_dict
		except frappe.DoesNotExistError:
			frappe.throw(_("Leave Policy {0} does not exist").format(name))

	filters = {}
	if search_text:
		filters["title"] = ["like", f"%{search_text}%"]

	limit_start = (max(1, page) - 1) * page_size if page_size > 0 else 0
	limit_page_length = page_size if page_size > 0 else 0

	policies = frappe.get_all(
		"Leave Policy",
		filters=filters,
		fields=["name", "title"],
		order_by="name asc",
		limit_start=limit_start,
		limit_page_length=limit_page_length,
	)

	if policies:
		policy_names = [p.name for p in policies]
		details = frappe.get_all(
			"Leave Policy Detail",
			filters={"parent": ["in", policy_names]},
			fields=["parent", "leave_type", "annual_allocation"],
			order_by="idx asc",
		)
		details_by_parent = {}
		for d in details:
			details_by_parent.setdefault(d.parent, []).append(d)
		for p in policies:
			p["leave_policy_details"] = details_by_parent.get(p.name, [])

	if page_size > 0:
		total = frappe.db.count("Leave Policy", filters=filters)
		return {"rows": policies, "total": total, "page": page, "page_size": page_size}

	return policies


@frappe.whitelist()
def get_leave_periods(name: str | None = None, search_text: str | None = None, page: int = 1, page_size: int = 0):
	"""
	If 'name' is provided, fetch a single Leave Period document as a dict.
	Otherwise, return a list of Leave Period records, optionally filtered by 'search_text'.
	"""
	if name:
		try:
			doc = frappe.get_doc("Leave Period", name)
			return doc.as_dict()
		except frappe.DoesNotExistError:
			frappe.throw(_("Leave Period {0} does not exist").format(name))

	filters = {}
	if search_text:
		filters["name"] = ["like", f"%{search_text}%"]

	limit_start = (max(1, page) - 1) * page_size if page_size > 0 else 0
	limit_page_length = page_size if page_size > 0 else 0

	periods = frappe.get_all(
		"Leave Period",
		filters=filters,
		fields=["*"],
		order_by="from_date desc",
		limit_start=limit_start,
		limit_page_length=limit_page_length,
	)

	if page_size > 0:
		total = frappe.db.count("Leave Period", filters=filters)
		return {"rows": periods, "total": total, "page": page, "page_size": page_size}

	return periods


@frappe.whitelist()
def get_leave_allocations(name: str | None = None, search_text: str | None = None, employee: str | None = None, page: int = 1, page_size: int = 0):
	"""
	If 'name' is provided, fetch a single Leave Allocation document as a dict.
	Otherwise, return a list of Leave Allocation records, optionally filtered by 'search_text' and 'employee'.
	"""
	if name:
		try:
			doc = frappe.get_doc("Leave Allocation", name)
			return doc.as_dict()
		except frappe.DoesNotExistError:
			frappe.throw(_("Leave Allocation {0} does not exist").format(name))

	filters = {}
	if employee:
		filters["employee"] = employee
	if search_text:
		filters["name"] = ["like", f"%{search_text}%"]

	limit_start = (max(1, page) - 1) * page_size if page_size > 0 else 0
	limit_page_length = page_size if page_size > 0 else 0

	allocations = frappe.get_all(
		"Leave Allocation",
		filters=filters,
		fields=["*"],
		order_by="creation desc",
		limit_start=limit_start,
		limit_page_length=limit_page_length,
	)

	if page_size > 0:
		total = frappe.db.count("Leave Allocation", filters=filters)
		return {"rows": allocations, "total": total, "page": page, "page_size": page_size}

	return allocations


@frappe.whitelist()
def delete_leave_policy(name: str) -> dict:
	"""Cancel (if submitted) and Delete a Leave Policy."""
	try:
		if not can_delete_leave_policy():
			return {"success": False, "error": _("Not permitted to delete Leave Policies")}

		doc = frappe.get_doc("Leave Policy", name)

		# If the document is submitted, cancel it first
		if doc.docstatus == 1:
			# Ensure the user has permission to cancel
			if not frappe.has_permission("Leave Policy", "cancel"):
				return {"success": False, "error": _("Not permitted to cancel Leave Policies")}
			doc.cancel()

		# Delete the document
		doc.delete()
		return {"success": True}
	except Exception as e:
		frappe.db.rollback()
		msg = str(e)
		if frappe.message_log:
			import json

			try:
				msg = json.loads(frappe.message_log[-1]).get("message", msg)
			except Exception:
				pass
		msg = frappe.utils.strip_html_tags(msg)
		return {"success": False, "error": msg}


@frappe.whitelist()
def save_leave_policy(leave_policy_data: str | dict) -> dict:
	import json

	try:
		if isinstance(leave_policy_data, str):
			leave_policy_data = json.loads(leave_policy_data)

		name = leave_policy_data.get("name")

		if name:
			if not frappe.has_permission("Leave Policy", "write"):
				return {"success": False, "error": _("Not permitted to update Leave Policy")}
			doc = frappe.get_doc("Leave Policy", name)
		else:
			if not frappe.has_permission("Leave Policy", "create"):
				return {"success": False, "error": _("Not permitted to create Leave Policy")}
			doc = frappe.new_doc("Leave Policy")

		doc.title = leave_policy_data.get("title")

		# Set details
		valid_details = []
		for detail in leave_policy_data.get("leave_policy_details", []):
			if not detail.get("leave_type"):
				continue
			row = {
				"leave_type": detail.get("leave_type"),
				"annual_allocation": float(detail.get("annual_allocation") or 0.0),
			}
			if detail.get("name"):
				row["name"] = detail.get("name")
			valid_details.append(row)

		# This is safer than clearing the array manually and appending,
		# and avoids the "child row not found" frappe errors.
		doc.set("leave_policy_details", valid_details)

		doc.save()
		if getattr(doc, "docstatus", 0) == 0:
			doc.submit()

		return {"success": True, "name": doc.name}
	except Exception as e:
		frappe.db.rollback()
		msg = str(e)
		if frappe.message_log:
			try:
				msg = json.loads(frappe.message_log[-1]).get("message", msg)
			except Exception:
				pass
		msg = frappe.utils.strip_html_tags(msg)
		return {"success": False, "error": msg}


@frappe.whitelist()
def save_leave_allocation(leave_allocation_data: dict) -> dict:
	import json

	try:
		if isinstance(leave_allocation_data, str):
			leave_allocation_data = json.loads(leave_allocation_data)

		name = leave_allocation_data.get("name")

		if name:
			if not frappe.has_permission("Leave Allocation", "write"):
				return {"success": False, "error": frappe._("Not permitted to update Leave Allocation")}
			doc = frappe.get_doc("Leave Allocation", name)
		else:
			if not frappe.has_permission("Leave Allocation", "create"):
				return {"success": False, "error": frappe._("Not permitted to create Leave Allocation")}
			doc = frappe.new_doc("Leave Allocation")

		doc.employee = leave_allocation_data.get("employee")
		doc.leave_type = leave_allocation_data.get("leave_type")
		doc.from_date = leave_allocation_data.get("from_date")
		doc.to_date = leave_allocation_data.get("to_date")
		doc.new_leaves_allocated = leave_allocation_data.get("new_leaves_allocated")
		if leave_allocation_data.get("leave_period"):
			doc.leave_period = leave_allocation_data.get("leave_period")
		if leave_allocation_data.get("description"):
			doc.description = leave_allocation_data.get("description")

		doc.save()
		return {"success": True, "name": doc.name}
	except Exception as e:
		frappe.db.rollback()
		msg = str(e)
		if hasattr(frappe, "message_log") and frappe.message_log:
			try:
				msg = json.loads(frappe.message_log[-1]).get("message", msg)
			except Exception:
				pass
		msg = frappe.utils.strip_html_tags(msg)
		return {"success": False, "error": msg}


@frappe.whitelist()
def delete_leave_allocation(name: str) -> dict:
	import json

	try:
		if not frappe.has_permission("Leave Allocation", "delete"):
			return {"success": False, "error": frappe._("Not permitted to delete Leave Allocation")}
		doc = frappe.get_doc("Leave Allocation", name)
		if doc.docstatus == 1:
			doc.cancel()
		doc.delete()
		return {"success": True}
	except Exception as e:
		frappe.db.rollback()
		msg = str(e)
		if hasattr(frappe, "message_log") and frappe.message_log:
			try:
				msg = json.loads(frappe.message_log[-1]).get("message", msg)
			except Exception:
				pass
		msg = frappe.utils.strip_html_tags(msg)
		return {"success": False, "error": msg}


@frappe.whitelist()
def delete_leave_period(name: str) -> dict:
	import json

	try:
		if not frappe.has_permission("Leave Period", "delete"):
			return {"success": False, "error": frappe._("Not permitted to delete Leave Period")}
		doc = frappe.get_doc("Leave Period", name)
		doc.delete()
		return {"success": True}
	except Exception as e:
		frappe.db.rollback()
		msg = str(e)
		if hasattr(frappe, "message_log") and frappe.message_log:
			try:
				msg = json.loads(frappe.message_log[-1]).get("message", msg)
			except Exception:
				pass
		msg = frappe.utils.strip_html_tags(msg)
		return {"success": False, "error": msg}


@frappe.whitelist()
def can_read_leave_policy_assignment():
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Leave Policy Assignment", "read"):
		return True
	return False


@frappe.whitelist()
def can_create_leave_policy_assignment():
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Leave Policy Assignment", "create"):
		return True
	return False


@frappe.whitelist()
def can_edit_leave_policy_assignment():
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Leave Policy Assignment", "write"):
		return True
	return False


@frappe.whitelist()
def can_delete_leave_policy_assignment():
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Leave Policy Assignment", "delete"):
		return True
	return False


@frappe.whitelist()
def get_leave_policy_assignments(
	name: str | None = None,
	search_text: str | None = None,
	employee: str | None = None,
	leave_policy: str | None = None,
	page: int = 1,
	page_size: int = 0,
):
	"""
	If 'name' is provided, fetch a single Leave Policy Assignment document as a dict.
	Otherwise, return a list of Leave Policy Assignment records, optionally filtered.
	"""
	if name:
		try:
			doc = frappe.get_doc("Leave Policy Assignment", name)
			doc_dict = doc.as_dict()
			if doc_dict.get("leave_policy"):
				doc_dict["leave_policy_title"] = frappe.db.get_value(
					"Leave Policy", doc_dict["leave_policy"], "title"
				)
			return doc_dict
		except frappe.DoesNotExistError:
			frappe.throw(frappe._("Leave Policy Assignment {0} does not exist").format(name))

	filters = {"docstatus": ["<", 2]}
	if employee:
		filters["employee"] = employee
	if leave_policy:
		filters["leave_policy"] = leave_policy
	if search_text:
		filters["employee"] = ["like", f"%{search_text}%"]

	limit_start = (max(1, page) - 1) * page_size if page_size > 0 else 0
	limit_page_length = page_size if page_size > 0 else 0

	assignments = frappe.get_all(
		"Leave Policy Assignment",
		filters=filters,
		fields=["*"],
		order_by="creation desc",
		limit_start=limit_start,
		limit_page_length=limit_page_length,
	)

	# Fetch all Leave Policies to map titles
	policies = {p.name: p.title for p in frappe.get_all("Leave Policy", fields=["name", "title"])}
	for a in assignments:
		a["leave_policy_title"] = policies.get(a.get("leave_policy"), a.get("leave_policy") or "")

	if page_size > 0:
		total = frappe.db.count("Leave Policy Assignment", filters=filters)
		return {"rows": assignments, "total": total, "page": page, "page_size": page_size}

	return assignments


@frappe.whitelist()
def delete_holiday_list(name: str) -> dict:
	try:
		if not frappe.has_permission("Holiday List", "delete"):
			return {"success": False, "error": frappe._("Not permitted to delete Holiday List")}
		doc = frappe.get_doc("Holiday List", name)
		if getattr(doc, "docstatus", 0) == 1:
			doc.cancel()
		doc.delete()
		return {"success": True}
	except Exception as e:
		return _handle_exception(e)


@frappe.whitelist()
def delete_holiday_list_assignment(name: str) -> dict:
	try:
		if not can_delete_holiday_list_assignment():
			return {"success": False, "error": frappe._("Not permitted to delete Holiday List Assignment")}
		doc = frappe.get_doc("Holiday List Assignment", name)
		if getattr(doc, "docstatus", 0) == 1:
			doc.cancel()
		doc.delete()

		# Clear the holiday_list directly on the Employee profile if applicable
		if getattr(doc, "applicable_for", None) == "Employee" and getattr(doc, "assigned_to", None):
			frappe.db.set_value("Employee", doc.assigned_to, "holiday_list", None)

		return {"success": True}
	except Exception as e:
		return _handle_exception(e)

@frappe.whitelist()
def delete_leave_policy_assignment(name: str) -> dict:
	import json

	try:
		if not can_delete_leave_policy_assignment():
			return {"success": False, "error": frappe._("Not permitted to delete Leave Policy Assignment")}
		doc = frappe.get_doc("Leave Policy Assignment", name)

		# Check if any leave type is used in a Leave Application
		allocations = frappe.get_all(
			"Leave Allocation",
			filters={"leave_policy_assignment": name},
			fields=["name", "leave_type", "from_date", "to_date"]
		)

		for alloc in allocations:
			used = frappe.get_all(
				"Leave Application",
				filters={
					"employee": doc.employee,
					"leave_type": alloc.leave_type,
					"docstatus": 1,
					"from_date": ("<=", alloc.to_date),
					"to_date": (">=", alloc.from_date)
				},
				limit=1
			)
			if used:
				return {"success": False, "error": frappe._("cannot delete because this is used in the leave application")}

		# Not used, so delete the allocations
		for alloc in allocations:
			delete_leave_allocation(alloc.name)

		# Reload the document because deleting child allocations modifies the parent's timestamp
		doc.reload()

		if doc.docstatus == 1:
			doc.cancel()
		doc.delete()
		return {"success": True}
	except Exception as e:
		frappe.db.rollback()
		msg = str(e)
		if hasattr(frappe, "message_log") and frappe.message_log:
			try:
				msg = json.loads(frappe.message_log[-1]).get("message", msg)
			except Exception:
				pass
		msg = frappe.utils.strip_html_tags(msg)
		return {"success": False, "error": msg}


@frappe.whitelist()
def save_leave_policy_assignment(assignment_data: str | dict) -> dict:
	import datetime
	import json

	from frappe.utils import add_days, add_years, getdate, today

	try:
		if isinstance(assignment_data, str):
			assignment_data = json.loads(assignment_data)

		name = assignment_data.get("name")
		employee = assignment_data.get("employee")
		leave_policy = assignment_data.get("leave_policy")
		assignment_based_on = assignment_data.get("assignment_based_on")

		if not employee or not leave_policy or not assignment_based_on:
			return {
				"success": False,
				"error": frappe._("Employee, Leave Policy, and Assignment Basis are mandatory"),
			}

		if name:
			if not can_edit_leave_policy_assignment():
				return {
					"success": False,
					"error": frappe._("Not permitted to update Leave Policy Assignment"),
				}
			doc = frappe.get_doc("Leave Policy Assignment", name)

			if doc.docstatus == 1:
				# Cancel and delete linked Leave Allocations first
				linked_allocs = frappe.get_all(
					"Leave Allocation", filters={"leave_policy_assignment": name, "docstatus": ["<", 2]}
				)
				for alloc in linked_allocs:
					alloc_doc = frappe.get_doc("Leave Allocation", alloc.name)
					if alloc_doc.docstatus == 1:
						alloc_doc.cancel()
					alloc_doc.delete()

				frappe.db.set_value("Leave Policy Assignment", name, "docstatus", 2)
				frappe.clear_document_cache("Leave Policy Assignment", name)
				frappe.db.commit()
				new_doc = frappe.new_doc("Leave Policy Assignment")
				new_doc.amended_from = name
				doc = new_doc
		else:
			if not can_create_leave_policy_assignment():
				return {
					"success": False,
					"error": frappe._("Not permitted to create Leave Policy Assignment"),
				}
			doc = frappe.new_doc("Leave Policy Assignment")

		doc.employee = employee
		doc.leave_policy = leave_policy
		doc.assignment_based_on = assignment_based_on

		if assignment_based_on == "Joining Date":
			joining_date_str = frappe.db.get_value("Employee", employee, "date_of_joining")
			if not joining_date_str:
				return {
					"success": False,
					"error": frappe._("Employee {0} does not have a Date of Joining defined").format(
						employee
					),
				}

			joining_date = getdate(joining_date_str)
			current_year = getdate(today()).year

			try:
				effective_from = datetime.date(current_year, joining_date.month, joining_date.day)
			except ValueError:
				effective_from = datetime.date(current_year, 2, 28)

			effective_to = add_days(add_years(effective_from, 1), -1)

			doc.effective_from = effective_from
			doc.effective_to = effective_to
			doc.leave_period = None

		elif assignment_based_on == "Leave Period":
			leave_period = assignment_data.get("leave_period")
			active_period = None

			if leave_period:
				active_period = frappe.db.get_value(
					"Leave Period",
					{"name": leave_period},
					["name", "from_date", "to_date"],
					as_dict=True,
				)

			if not active_period:
				current_today = today()
				active_period = frappe.db.get_value(
					"Leave Period",
					{"from_date": ("<=", current_today), "to_date": (">=", current_today), "is_active": 1},
					["name", "from_date", "to_date"],
					as_dict=True,
				)
			if not active_period:
				active_period = frappe.db.get_value(
					"Leave Period", {"is_active": 1}, ["name", "from_date", "to_date"], as_dict=True
				)

			if not active_period:
				return {"success": False, "error": frappe._("No active Leave Period found")}

			doc.leave_period = active_period["name"]
			doc.effective_from = active_period["from_date"]
			doc.effective_to = active_period["to_date"]

		if not doc.company:
			doc.company = frappe.db.get_value("Employee", employee, "company")

		doc.save()

		if doc.docstatus == 0:
			doc.submit()

		return {"success": True, "name": doc.name}
	except Exception as e:
		frappe.db.rollback()
		msg = str(e)
		if hasattr(frappe, "message_log") and frappe.message_log:
			try:
				msg = json.loads(frappe.message_log[-1]).get("message", msg)
			except Exception:
				pass
		msg = frappe.utils.strip_html_tags(msg)
		return {"success": False, "error": msg}

@frappe.whitelist()
def bulk_save_leave_policy_assignment(employees: str | list, leave_policy: str, assignment_based_on: str, leave_period: str = None) -> dict:
	import json

	if isinstance(employees, str):
		try:
			employees = json.loads(employees)
		except Exception:
			return {"success": False, "error": "Invalid employees list"}

	if not employees or not isinstance(employees, list):
		return {"success": False, "error": "No employees selected"}

	if not leave_policy or not assignment_based_on:
		return {"success": False, "error": frappe._("Leave Policy and Assignment Basis are mandatory")}

	if not can_create_leave_policy_assignment():
		return {"success": False, "error": frappe._("Not permitted to create Leave Policy Assignment")}

	results = []
	errors = []

	for employee in employees:
		assignment_data = {
			"employee": employee,
			"leave_policy": leave_policy,
			"assignment_based_on": assignment_based_on,
			"leave_period": leave_period
		}

		res = save_leave_policy_assignment(assignment_data)
		if not res.get("success"):
			errors.append(f"Failed for {employee}: {res.get('error')}")
		else:
			results.append(employee)

	if errors:
		return {
			"success": False,
			"error": "<br>".join(errors),
			"assigned": len(results)
		}

	return {"success": True, "assigned": len(results)}


@frappe.whitelist()
def can_read_holiday_list():
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Holiday List", "read"):
		return True
	return False


@frappe.whitelist()
def can_create_holiday_list():
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Holiday List", "create"):
		return True
	return False


@frappe.whitelist()
def can_edit_holiday_list():
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Holiday List", "write"):
		return True
	return False


@frappe.whitelist()
def can_delete_holiday_list():
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Holiday List", "delete"):
		return True
	return False


@frappe.whitelist()
def can_read_holiday_list_assignment():
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Holiday List Assignment", "read"):
		return True
	return False


@frappe.whitelist()
def can_create_holiday_list_assignment():
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Holiday List Assignment", "create"):
		return True
	return False


@frappe.whitelist()
def can_edit_holiday_list_assignment():
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Holiday List Assignment", "write"):
		return True
	return False


@frappe.whitelist()
def can_delete_holiday_list_assignment():
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Holiday List Assignment", "delete"):
		return True
	return False


@frappe.whitelist()
def get_holiday_list(name: str | None = None, search_text: str | None = None, page: int = 0, page_size: int = 0):
	"""
	If 'name' is provided, fetch a single Holiday List document as a dict.
	Otherwise, return a list of Holiday List records, optionally filtered by 'search_text'.

	When `page_size > 0`, server-side pagination is applied: a single page
	(LIMIT/OFFSET) is returned along with the total count, as a dict
	{data, total, page, page_size}. `page_size = 0` returns the full list
	(legacy behaviour, backward compatible).
	"""
	if name:
		try:
			doc = frappe.get_doc("Holiday List", name)
			return doc.as_dict()
		except frappe.DoesNotExistError:
			frappe.throw(frappe._("Holiday List {0} does not exist").format(name))

	filters = {}
	if search_text:
		filters["holiday_list_name"] = ["like", f"%{search_text}%"]

	holiday_lists = frappe.get_all(
		"Holiday List",
		filters=filters,
		fields=["*"],
		order_by="creation desc",
		limit_page_length=page_size if page_size > 0 else 0,
		limit_start=(max(1, page) - 1) * page_size if page_size > 0 else 0,
	)

	if page_size > 0:
		# Total comes from the full filtered set (same filters), so it is
		# not affected by which page is being returned.
		total = frappe.db.count("Holiday List", filters=filters)
		return {
			"data": holiday_lists,
			"total": total,
			"page": page,
			"page_size": page_size,
		}

	return holiday_lists


@frappe.whitelist()
def get_holiday_list_assignment(name: str | None = None, search_text: str | None = None, page: int = 0, page_size: int = 0, assigned_to: str | None = None, holiday_list: str | None = None):
	"""
	If 'name' is provided, fetch a single Holiday List Assignment document as a dict.
	Otherwise, return a list of Holiday List Assignment records, optionally filtered by 'search_text'.

	When `page_size > 0`, server-side pagination is applied: a single page
	(LIMIT/OFFSET) is returned along with the total count, as a dict
	{data, total, page, page_size}. `page_size = 0` returns the full list
	(legacy behaviour, backward compatible).
	"""
	if name:
		try:
			doc = frappe.get_doc("Holiday List Assignment", name)
			return doc.as_dict()
		except frappe.DoesNotExistError:
			frappe.throw(frappe._("Holiday List Assignment {0} does not exist").format(name))

	filters = []
	if search_text:
		filters.append(["assigned_to", "like", f"%{search_text}%"])
	if assigned_to:
		filters.append(["assigned_to", "=", assigned_to])
	if holiday_list:
		filters.append(["holiday_list", "=", holiday_list])

	assignments = frappe.get_all(
		"Holiday List Assignment",
		filters=filters,
		fields=["*"],
		order_by="creation desc",
		ignore_permissions=True,
		limit_page_length=page_size if page_size > 0 else 0,
		limit_start=(max(1, page) - 1) * page_size if page_size > 0 else 0,
	)

	if page_size > 0:
		# Total comes from the full filtered set (same filters), so it is
		# not affected by which page is being returned.
		total = frappe.db.count("Holiday List Assignment", filters=filters)
		return {
			"data": assignments,
			"total": total,
			"page": page,
			"page_size": page_size,
		}

	return assignments


@frappe.whitelist()
def save_holiday_list(holiday_list_data):
	if isinstance(holiday_list_data, str):
		holiday_list_data = frappe.parse_json(holiday_list_data)

	is_new = not holiday_list_data.get("name")

	if is_new:
		doc = frappe.new_doc("Holiday List")
	else:
		old_name = holiday_list_data.get("name")
		new_name = holiday_list_data.get("holiday_list_name")
		if old_name and new_name and old_name != new_name:
			frappe.flags.ignore_permissions = True
			try:
				frappe.rename_doc("Holiday List", old_name, new_name)
			finally:
				frappe.flags.ignore_permissions = False
			old_name = new_name

		doc = frappe.get_doc("Holiday List", old_name)

	doc.holiday_list_name = holiday_list_data.get("holiday_list_name")
	doc.from_date = holiday_list_data.get("from_date")
	doc.to_date = holiday_list_data.get("to_date")

	doc.set("holidays", [])

	for h in holiday_list_data.get("holidays", []):
		doc.append("holidays", {
			"holiday_date": h.get("date"),
			"description": h.get("description"),
			"is_half_day": h.get("is_half_day")
		})

	if is_new:
		doc.insert()
	else:
		doc.save()

	return doc.name


@frappe.whitelist()
def save_holiday_list_assignment(**kwargs) -> dict:
	try:
		name = kwargs.get("name")
		if name:
			doc = frappe.get_doc("Holiday List Assignment", name)
			doc.holiday_list = kwargs.get("holiday_list")
			doc.applicable_for = kwargs.get("applicable_for")
			doc.assigned_to = kwargs.get("assigned_to")
			doc.from_date = kwargs.get("from_date")
			doc.save(ignore_permissions=True)
		else:
			doc = frappe.get_doc({
				"doctype": "Holiday List Assignment",
				"holiday_list": kwargs.get("holiday_list"),
				"applicable_for": kwargs.get("applicable_for"),
				"assigned_to": kwargs.get("assigned_to"),
				"from_date": kwargs.get("from_date")
			})
			doc.insert(ignore_permissions=True)
			doc.submit()

		return {"success": True, "name": doc.name}
	except Exception as e:
		return _handle_exception(e)


@frappe.whitelist()
def get_leave_application_report_filter_options():
	"""
	Returns dropdown options for Employee, Leave Type, and Status for the Leave Application report.
	"""
	employees = get_employee_list_for_leave()

	leave_types = get_leave_types()

	statuses = get_leave_status_options()

	return {
		"employees": [{"id": e.name, "name": f"{e.employee_name} ({e.name})"} for e in employees],
		"leave_types": [lt.name for lt in leave_types],
		"statuses": statuses
	}


@frappe.whitelist()
def report_leave_application_list(from_date=None, to_date=None, employee=None, leave_type=None, status=None, export=0, pdf=0):
	"""
	Returns Leave Application data based on filters.
	Handles standard JSON return, Excel export, and PDF generation.
	"""
	import frappe
	from frappe.utils import getdate

	filters = {}

	if from_date and to_date:
		filters["from_date"] = [">=", getdate(from_date)]
		filters["to_date"] = ["<=", getdate(to_date)]
	elif from_date:
		filters["from_date"] = [">=", getdate(from_date)]
	elif to_date:
		filters["to_date"] = ["<=", getdate(to_date)]

	if employee:
		filters["employee"] = employee

	if leave_type:
		filters["leave_type"] = leave_type

	if status:
		filters["status"] = status
	else:
		filters["status"] = ["!=", "Cancelled"]

	data = frappe.get_all(
		"Leave Application",
		filters=filters,
		fields=["name", "employee", "employee_name", "from_date", "to_date", "leave_type", "status", "total_leave_days"],
		order_by="from_date desc"
	)

	if int(export):
		from frappe.utils.xlsxutils import build_xlsx_response

		xlsx_data = [["Reference", "Employee", "From Date", "To Date", "Total Leave Days", "Leave Type", "Status"]]
		for d in data:
			from_date_str = str(d.from_date).split(' ')[0] if d.from_date else ""
			to_date_str = str(d.to_date).split(' ')[0] if d.to_date else ""

			xlsx_data.append([
				d.name,
				f"{d.employee} - {d.employee_name}",
				from_date_str,
				to_date_str,
				d.total_leave_days,
				d.leave_type,
				d.status
			])

		build_xlsx_response(xlsx_data, "Leave_Application_Report")
		return

	if int(pdf):
		from frappe.utils.pdf import get_pdf

		context = {
			"data": data,
			"filters": {
				"from_date": from_date,
				"to_date": to_date,
				"employee": employee,
				"leave_type": leave_type,
				"status": status,
			}
		}

		html = frappe.render_template("arijentek_core/templates/reports/leave_application_report.html", context)
		pdf_binary = get_pdf(html, {"page-size": "A4", "orientation": "Portrait", "margin-top": "10mm", "margin-bottom": "10mm", "margin-left": "8mm", "margin-right": "8mm"})

		frappe.local.response.filename = f"Leave_Application_Report_{frappe.utils.nowdate()}.pdf"
		frappe.local.response.filecontent = pdf_binary
		frappe.local.response.type = "pdf"
		return

	return data


@frappe.whitelist()
def get_compensatory_leave_status_options() -> list:
	"""Return allowed status options for Compensatory Leave Application."""
	options = frappe.get_meta("Zevar Compensatory Leave Request").get_field("status").options or ""
	if isinstance(options, str):
		return [opt for opt in options.split("\n") if opt.strip() and opt.strip() != "Cancelled"]

	if isinstance(options, list):
		return [opt for opt in options if opt != "Cancelled"]

	return options or []


@frappe.whitelist()
def get_compensatory_leave_report_filter_options():
	"""
	Returns dropdown options for Employee and Status for the Compensatory Leave report.
	"""
	employees = get_employee_list_for_leave()

	statuses = get_compensatory_leave_status_options()

	return {
		"employees": [{"id": e.name, "name": f"{e.employee_name} ({e.name})"} for e in employees],
		"statuses": statuses
	}


@frappe.whitelist()
def report_compensatory_leave_list(from_date=None, to_date=None, employee=None, status=None, export=0, pdf=0):
	"""
	Returns Compensatory Leave data based on filters.
	Handles standard JSON return, Excel export, and PDF generation.
	"""
	import frappe
	from frappe.utils import getdate

	filters = {}

	if from_date and to_date:
		filters["work_from_date"] = [">=", getdate(from_date)]
		filters["work_end_date"] = ["<=", getdate(to_date)]
	elif from_date:
		filters["work_from_date"] = [">=", getdate(from_date)]
	elif to_date:
		filters["work_end_date"] = ["<=", getdate(to_date)]

	if employee:
		filters["employee"] = employee

	if status:
		filters["status"] = status
	else:
		filters["status"] = ["!=", "Cancelled"]

	data = frappe.get_all(
		"Zevar Compensatory Leave Request",
		filters=filters,
		fields=["name", "employee", "employee_name", "work_from_date", "work_end_date", "status", "reason", "half_day"],
		order_by="work_from_date desc"
	)

	if int(export):
		from frappe.utils.xlsxutils import build_xlsx_response

		xlsx_data = [["Reference", "Employee", "Work From Date", "Work End Date", "Half Day", "Status", "Reason"]]
		for d in data:
			from_date_str = str(d.work_from_date).split(' ')[0] if d.work_from_date else ""
			to_date_str = str(d.work_end_date).split(' ')[0] if d.work_end_date else ""

			xlsx_data.append([
				d.name,
				f"{d.employee} - {d.employee_name}",
				from_date_str,
				to_date_str,
				"Yes" if d.half_day else "No",
				d.status,
				d.reason
			])

		build_xlsx_response(xlsx_data, "Compensatory_Leave_Report")
		return

	if int(pdf):
		from frappe.utils.pdf import get_pdf

		context = {
			"data": data,
			"filters": {
				"from_date": from_date,
				"to_date": to_date,
				"employee": employee,
				"status": status,
			}
		}

		html = frappe.render_template("arijentek_core/templates/reports/compensatory_leave_report.html", context)
		pdf_binary = get_pdf(html, {"page-size": "A4", "orientation": "Portrait", "margin-top": "10mm", "margin-bottom": "10mm", "margin-left": "8mm", "margin-right": "8mm"})

		frappe.local.response.filename = f"Compensatory_Leave_Report_{frappe.utils.nowdate()}.pdf"
		frappe.local.response.filecontent = pdf_binary
		frappe.local.response.type = "pdf"
		return

	return data

@frappe.whitelist()
def get_leave_policy_assignment_report_filter_options():
	"""
	Returns dropdown options for Employee and Leave Policy for the Leave Policy Assignment report.
	"""
	employees = get_employee_list_for_leave()
	leave_policies = frappe.get_all("Leave Policy", fields=["name as id", "title as name"], order_by="name asc")

	return {
		"employees": [{"id": e.name, "name": f"{e.employee_name} ({e.name})"} for e in employees],
		"leave_policies": leave_policies
	}

@frappe.whitelist()
def report_leave_policy_assignment_list(employee=None, leave_policy=None, export=0, pdf=0):
	"""
	Returns Leave Policy Assignment data based on filters.
	"""
	import frappe

	filters = {"docstatus": ["<", 2]}

	if employee:
		filters["employee"] = employee

	if leave_policy:
		filters["leave_policy"] = leave_policy

	# Check permissions via get_employee_list_for_leave
	allowed_employees = [e.name for e in get_employee_list_for_leave()]
	if employee and employee not in allowed_employees:
		return []
	elif not employee:
		if not allowed_employees:
			return []
		filters["employee"] = ["in", allowed_employees]

	data = frappe.get_all(
		"Leave Policy Assignment",
		filters=filters,
		fields=["name", "employee", "employee_name", "leave_policy", "effective_from", "effective_to"],
		order_by="creation desc"
	)

	if int(export):
		from frappe.utils.xlsxutils import build_xlsx_response

		xlsx_data = [["Assignment ID", "Employee ID", "Employee Name", "Leave Policy", "Effective From", "Effective To"]]
		for d in data:
			xlsx_data.append([
				d.name,
				d.employee,
				d.employee_name,
				d.leave_policy,
				str(d.effective_from) if d.effective_from else "",
				str(d.effective_to) if d.effective_to else ""
			])

		build_xlsx_response(xlsx_data, "Leave_Policy_Assignment_Report")
		return

	if int(pdf):
		from frappe.utils.pdf import get_pdf

		context = {
			"data": data,
			"filters": {
				"employee": employee,
				"leave_policy": leave_policy
			}
		}

		html = frappe.render_template("arijentek_core/templates/reports/leave_policy_assignment_report.html", context)
		pdf_binary = get_pdf(html, {"page-size": "A4", "orientation": "Portrait", "margin-top": "10mm", "margin-bottom": "10mm", "margin-left": "8mm", "margin-right": "8mm"})

		frappe.local.response.filename = f"Leave_Policy_Assignment_Report_{frappe.utils.nowdate()}.pdf"
		frappe.local.response.filecontent = pdf_binary
		frappe.local.response.type = "pdf"
		return

	return data


@frappe.whitelist()
def get_leave_allocation_report_filter_options():
	"""
	Returns dropdown options for Employee and Leave Type for the Leave Allocation & Balance report.
	"""
	employees = get_employee_list_for_leave()
	leave_types = frappe.get_all("Leave Type", fields=["name as id", "name as name"], order_by="name asc")

	return {
		"employees": [{"id": e.name, "name": f"{e.employee_name} ({e.name})"} for e in employees],
		"leave_types": leave_types
	}


@frappe.whitelist()
def report_leave_allocation_balance_list(from_date=None, to_date=None, employee=None, leave_type=None, export=0, pdf=0):
	"""
	Returns Leave Allocation & Balance data based on filters.
	Calculates leaves_taken from approved Leave Applications and remaining leave_balance.
	"""
	import frappe
	from frappe.utils import getdate

	allowed_employees = [e.name for e in get_employee_list_for_leave()]
	if employee and employee not in allowed_employees:
		return []
	elif not employee:
		if not allowed_employees:
			return []

	target_employees = [employee] if employee else allowed_employees

	conditions = ["la.docstatus < 2", "la.employee IN %(employees)s"]
	params = {"employees": tuple(target_employees)}

	if from_date and to_date:
		conditions.append("la.from_date <= %(to_date)s AND la.to_date >= %(from_date)s")
		params["from_date"] = getdate(from_date)
		params["to_date"] = getdate(to_date)
	elif from_date:
		conditions.append("la.to_date >= %(from_date)s")
		params["from_date"] = getdate(from_date)
	elif to_date:
		conditions.append("la.from_date <= %(to_date)s")
		params["to_date"] = getdate(to_date)

	if leave_type:
		conditions.append("la.leave_type = %(leave_type)s")
		params["leave_type"] = leave_type

	where_clause = " AND ".join(conditions)

	query = f"""
		SELECT
			la.name,
			la.employee,
			la.employee_name,
			la.leave_type,
			la.from_date,
			la.to_date,
			la.total_leaves_allocated,
			la.new_leaves_allocated,
			la.unused_leaves
		FROM `tabLeave Allocation` la
		WHERE {where_clause}
		ORDER BY la.from_date DESC, la.employee ASC
	"""

	allocations = frappe.db.sql(query, params, as_dict=True)

	# Fetch approved leaves taken per employee, leave_type, and allocation period
	result_data = []
	for alloc in allocations:
		app_query = """
			SELECT SUM(total_leave_days)
			FROM `tabLeave Application`
			WHERE employee = %s
			  AND leave_type = %s
			  AND docstatus = 1
			  AND status = 'Approved'
			  AND from_date >= %s
			  AND to_date <= %s
		"""
		leaves_taken = frappe.db.sql(
			app_query,
			(alloc.employee, alloc.leave_type, alloc.from_date, alloc.to_date)
		)[0][0] or 0.0

		allocated = float(alloc.total_leaves_allocated or 0.0)
		taken = float(leaves_taken)
		balance = allocated - taken

		result_data.append({
			"name": alloc.name,
			"employee": alloc.employee,
			"employee_name": alloc.employee_name,
			"leave_type": alloc.leave_type,
			"from_date": str(alloc.from_date) if alloc.from_date else "",
			"to_date": str(alloc.to_date) if alloc.to_date else "",
			"total_leaves_allocated": allocated,
			"leaves_taken": taken,
			"leave_balance": balance
		})

	if int(export):
		from frappe.utils.xlsxutils import build_xlsx_response

		xlsx_data = [[
			"Allocation ID", "Employee ID", "Employee Name", "Leave Type",
			"From Date", "To Date", "Total Allocated", "Leaves Taken", "Remaining Balance"
		]]
		for d in result_data:
			xlsx_data.append([
				d["name"],
				d["employee"],
				d["employee_name"],
				d["leave_type"],
				d["from_date"],
				d["to_date"],
				d["total_leaves_allocated"],
				d["leaves_taken"],
				d["leave_balance"]
			])

		build_xlsx_response(xlsx_data, "Leave_Allocations_and_Balances_Report")
		return

	if int(pdf):
		from frappe.utils.pdf import get_pdf

		context = {
			"data": result_data,
			"filters": {
				"from_date": from_date,
				"to_date": to_date,
				"employee": employee,
				"leave_type": leave_type
			}
		}

		html = frappe.render_template("arijentek_core/templates/reports/leave_allocation_balance_report.html", context)
		pdf_binary = get_pdf(html, {
			"page-size": "A4",
			"orientation": "Landscape",
			"margin-top": "10mm",
			"margin-bottom": "10mm",
			"margin-left": "8mm",
			"margin-right": "8mm"
		})

		frappe.local.response.filename = f"Leave_Allocations_and_Balances_Report_{frappe.utils.nowdate()}.pdf"
		frappe.local.response.filecontent = pdf_binary
		frappe.local.response.type = "pdf"
		return

	return result_data


@frappe.whitelist()
def get_holiday_list_assignment_report_filter_options():
	"""
	Returns dropdown options for Employee, Holiday List, and Applicable For for the Holiday List Assignment report.
	"""
	employees = get_employee_list_for_leave()
	holiday_lists = frappe.get_all("Holiday List", fields=["name as id", "holiday_list_name as name"], order_by="name asc")
	applicable_fors = [
		{"id": "Company", "name": "Company"},
		{"id": "Employee", "name": "Employee"}
	]

	return {
		"employees": [{"id": e.name, "name": f"{e.employee_name} ({e.name})"} for e in employees],
		"holiday_lists": holiday_lists,
		"applicable_fors": applicable_fors
	}


@frappe.whitelist()
def report_holiday_list_assignment_list(from_date=None, to_date=None, employee=None, holiday_list=None, applicable_for=None, export=0, pdf=0):
	"""
	Returns Holiday List Assignment data based on filters.
	"""
	import frappe
	from frappe.utils import getdate

	conditions = ["hla.docstatus < 2"]
	params = {}

	if applicable_for:
		conditions.append("hla.applicable_for = %(applicable_for)s")
		params["applicable_for"] = applicable_for

	if holiday_list:
		conditions.append("hla.holiday_list = %(holiday_list)s")
		params["holiday_list"] = holiday_list

	if from_date and to_date:
		conditions.append("hla.from_date BETWEEN %(from_date)s AND %(to_date)s")
		params["from_date"] = getdate(from_date)
		params["to_date"] = getdate(to_date)
	elif from_date:
		conditions.append("hla.from_date >= %(from_date)s")
		params["from_date"] = getdate(from_date)
	elif to_date:
		conditions.append("hla.from_date <= %(to_date)s")
		params["to_date"] = getdate(to_date)

	allowed_employees = [e.name for e in get_employee_list_for_leave()]
	if employee:
		if employee not in allowed_employees:
			return []
		conditions.append("hla.assigned_to = %(employee)s")
		params["employee"] = employee
	else:
		if allowed_employees:
			conditions.append("(hla.applicable_for != 'Employee' OR hla.assigned_to IN %(allowed_employees)s)")
			params["allowed_employees"] = tuple(allowed_employees)
		else:
			conditions.append("hla.applicable_for != 'Employee'")

	where_clause = " AND ".join(conditions)

	query = f"""
		SELECT
			hla.name,
			hla.applicable_for,
			hla.assigned_to,
			COALESCE(e.employee_name, hla.employee_name, '') AS employee_name,
			hla.holiday_list,
			hla.from_date
		FROM `tabHoliday List Assignment` hla
		LEFT JOIN `tabEmployee` e ON (hla.applicable_for = 'Employee' AND hla.assigned_to = e.name)
		WHERE {where_clause}
		ORDER BY hla.from_date DESC
	"""

	data = frappe.db.sql(query, params, as_dict=True)


	if int(export):
		from frappe.utils.xlsxutils import build_xlsx_response

		xlsx_data = [["Assignment ID", "Applicable For", "Employee ID", "Employee Name", "Holiday List", "Effective From"]]
		for d in data:
			xlsx_data.append([
				d.name,
				d.applicable_for or "Employee",
				d.assigned_to or "",
				d.employee_name or "",
				d.holiday_list or "",
				str(d.from_date) if d.from_date else ""
			])

		build_xlsx_response(xlsx_data, "Holiday_List_Assignment_Report")
		return

	if int(pdf):
		from frappe.utils.pdf import get_pdf

		context = {
			"data": data,
			"filters": {
				"from_date": from_date,
				"to_date": to_date,
				"employee": employee,
				"holiday_list": holiday_list,
				"applicable_for": applicable_for
			}
		}

		html = frappe.render_template("arijentek_core/templates/reports/holiday_list_assignment_report.html", context)
		pdf_binary = get_pdf(html, {
			"page-size": "A4",
			"orientation": "Portrait",
			"margin-top": "10mm",
			"margin-bottom": "10mm",
			"margin-left": "8mm",
			"margin-right": "8mm"
		})

		frappe.local.response.filename = f"Holiday_List_Assignment_Report_{frappe.utils.nowdate()}.pdf"
		frappe.local.response.filecontent = pdf_binary
		frappe.local.response.type = "pdf"
		return

	return data



