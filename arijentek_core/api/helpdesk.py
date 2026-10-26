"""
Helpdesk API - Issue reporting and ticket management
"""

import frappe
from frappe import _
from frappe.utils import now_datetime


def _ensure_mapping(doctype, value, extra_fields=None):
	if not value or not frappe.db.exists("DocType", doctype):
		return False
	if frappe.db.exists(doctype, value):
		return True
	try:
		doc_fields = {"doctype": doctype, "__newname": value}
		if extra_fields:
			doc_fields.update(extra_fields)
		frappe.get_doc(doc_fields).insert(
			ignore_permissions=True,
			ignore_mandatory=True,
		)
		return True
	except Exception:
		frappe.log_error(
			f"Helpdesk Mapping Create: {doctype}={value}",
			frappe.get_traceback(),
		)
		return False


def _field_exists(doctype, fieldname):
	return frappe.db.exists("DocField", {"parent": doctype, "fieldname": fieldname})


def _link_target_exists(doctype, fieldname, value):
	if not _field_exists(doctype, fieldname):
		return False
	field_meta = frappe.get_meta(doctype).get_field(fieldname)
	if not field_meta or field_meta.fieldtype != "Link":
		return True
	return bool(frappe.db.exists(field_meta.options, value))


def _set_if_link_valid(doc_dict, doctype, fieldname, value):
	if not value:
		return
	if _link_target_exists(doctype, fieldname, value):
		doc_dict[fieldname] = value


def _try_create_hd_ticket(subject, description, raised_by, priority, category, extra_fields=None):
	if not frappe.db.exists("DocType", "HD Ticket"):
		return None

	_ensure_mapping(
		"HD Ticket Status",
		"Open",
		{"label_agent": "Open", "label_customer": "Open", "category": "Open"},
	)
	_ensure_mapping("HD Ticket Priority", priority, {"integer_value": 1})
	_ensure_mapping("HD Ticket Type", category)

	ticket_doc = {
		"doctype": "HD Ticket",
		"subject": subject,
		"description": description,
		"raised_by": raised_by,
	}

	_set_if_link_valid(ticket_doc, "HD Ticket", "status", "Open")
	_set_if_link_valid(ticket_doc, "HD Ticket", "priority", priority)
	_set_if_link_valid(ticket_doc, "HD Ticket", "ticket_type", category)

	if extra_fields:
		for field, val in extra_fields.items():
			if _field_exists("HD Ticket", field):
				ticket_doc[field] = val

	ticket = frappe.get_doc(ticket_doc)
	ticket.flags.ignore_permissions = True
	ticket.insert()
	return ticket


def _try_create_issue(subject, description, raised_by, priority, category):
	if not frappe.db.exists("DocType", "Issue"):
		return None

	_ensure_mapping("Issue Priority", priority)
	_ensure_mapping("Issue Type", category)

	issue_doc = {
		"doctype": "Issue",
		"subject": subject,
		"description": description,
		"raised_by": raised_by,
		"status": "Open",
	}

	_set_if_link_valid(issue_doc, "Issue", "priority", priority)
	_set_if_link_valid(issue_doc, "Issue", "issue_type", category)

	issue = frappe.get_doc(issue_doc)
	issue.flags.ignore_permissions = True
	issue.insert()
	return issue


def _create_todo_fallback(subject, full_description, category, assigned_to):
	allocated_to = assigned_to or "Administrator"
	try:
		hr_user = frappe.db.get_value("Has Role", {"role": "HR Manager", "parenttype": "User"}, "parent")
		if hr_user:
			allocated_to = hr_user
	except Exception:
		pass

	todo = frappe.get_doc(
		{
			"doctype": "ToDo",
			"description": f"[{category}] {subject}\n\n{full_description}",
			"allocated_to": allocated_to,
			"status": "Open",
			"date": frappe.utils.today(),
		}
	)
	todo.flags.ignore_permissions = True
	todo.insert()
	return todo


@frappe.whitelist()
def create_support_ticket(
	subject: str,
	description: str,
	category: str = "Other",
	sub_category: str | None = None,
	priority: str = "Medium",
	department: str | None = None,
	reference_type: str | None = None,
	reference_name: str | None = None,
):
	if not subject:
		frappe.throw(_("Subject is required"))
	if not description:
		frappe.throw(_("Description is required"))

	employee = frappe.db.get_value(
		"Employee",
		{"user_id": frappe.session.user},
		["name", "employee_name", "department", "designation", "reports_to"],
		as_dict=True,
	)

	manager_user_id = None
	if employee and employee.get("reports_to"):
		manager_user_id = frappe.db.get_value("Employee", {"name": employee.reports_to}, "user_id")

	assigned_to = manager_user_id
	if department:
		dept_user = frappe.db.get_value(
			"Employee",
			{"department": department, "status": "Active"},
			"user_id",
			order_by="creation desc",
		)
		if dept_user:
			assigned_to = dept_user

	reporter = employee.employee_name if employee else frappe.session.user
	emp_id = employee.name if employee else "N/A"
	emp_dept = employee.department if employee else "N/A"
	dt_str = now_datetime().strftime("%Y-%m-%d %H:%M:%S")

	context_info = (
		"**Reported by:** {}\n"
		"**Employee ID:** {}\n"
		"**Employee Department:** {}\n"
		"**Category:** {}\n"
		"**Sub-Category:** {}\n"
		"**Priority:** {}\n"
		"**Responsible Department:** {}\n"
		"**Date/Time:** {}"
	).format(
		reporter,
		emp_id,
		emp_dept,
		category,
		sub_category or "N/A",
		priority,
		department or "N/A",
		dt_str,
	)

	if reference_type and reference_name:
		context_info += f"\n**Related {reference_type}:** {reference_name}"

	full_description = f"{context_info}\n\n---\n\n**Issue Description:**\n\n{description}"

	ticket = None
	try:
		ticket = _try_create_hd_ticket(
			subject,
			full_description,
			frappe.session.user,
			priority,
			category,
			{
				"custom_category": category,
				"custom_sub_category": sub_category or "",
				"custom_department": department or "",
			},
		)
	except Exception:
		frappe.log_error("HD Ticket Create Failed", frappe.get_traceback())

	if ticket:
		return {
			"success": True,
			"ticket_id": ticket.name,
			"message": _("Ticket {0} created successfully").format(ticket.name),
			"helpdesk_installed": True,
		}

	issue = None
	try:
		issue = _try_create_issue(
			subject,
			full_description,
			frappe.session.user,
			priority,
			category,
		)
	except Exception:
		frappe.log_error("Issue Create Failed", frappe.get_traceback())

	if issue:
		if assigned_to:
			try:
				todo = frappe.get_doc(
					{
						"doctype": "ToDo",
						"reference_type": "Issue",
						"reference_name": issue.name,
						"description": f"[{category}] {subject}",
						"allocated_to": assigned_to,
						"status": "Open",
					}
				)
				todo.flags.ignore_permissions = True
				todo.insert()
			except Exception:
				pass
		return {
			"success": True,
			"ticket_id": issue.name,
			"message": _("Issue {0} created successfully").format(issue.name),
			"helpdesk_installed": False,
		}

	todo = _create_todo_fallback(subject, full_description, category, assigned_to)
	return {
		"success": True,
		"ticket_id": todo.name,
		"message": _("Your issue has been reported. A ToDo has been created."),
		"helpdesk_installed": False,
	}


@frappe.whitelist()
def get_support_categories():
	return [
		{
			"value": "Customer Issue",
			"label": "Customer Issue",
			"department": "Customer Service",
			"sub_categories": [
				{"value": "Return Request", "label": "Return Request"},
				{"value": "Exchange Request", "label": "Exchange Request"},
				{"value": "Complaint", "label": "Complaint"},
				{"value": "Billing Dispute", "label": "Billing Dispute"},
				{"value": "Layaway Issue", "label": "Layaway Issue"},
				{"value": "Gift Card Issue", "label": "Gift Card Issue"},
			],
		},
		{
			"value": "Jewelry Issue",
			"label": "Jewelry Issue",
			"department": "Quality Control",
			"sub_categories": [
				{"value": "Quality Defect", "label": "Quality Defect"},
				{"value": "Sizing Issue", "label": "Sizing Issue"},
				{"value": "Damage", "label": "Damage"},
				{"value": "Missing Stones", "label": "Missing Stones"},
				{"value": "Hallmark Issue", "label": "Hallmark Issue"},
			],
		},
		{
			"value": "Vendor Issue",
			"label": "Vendor Issue",
			"department": "Procurement",
			"sub_categories": [
				{"value": "Late Delivery", "label": "Late Delivery"},
				{"value": "Quality Problem", "label": "Quality Problem"},
				{"value": "Wrong Item", "label": "Wrong Item"},
				{"value": "Pricing Dispute", "label": "Pricing Dispute"},
			],
		},
		{
			"value": "Employee Issue",
			"label": "Employee Issue",
			"department": "Human Resources",
			"sub_categories": [
				{"value": "Attendance", "label": "Attendance"},
				{"value": "Payroll", "label": "Payroll"},
				{"value": "Leave", "label": "Leave"},
				{"value": "Manager", "label": "Manager"},
			],
		},
		{
			"value": "Store Issue",
			"label": "Store Issue",
			"department": "Operations",
			"sub_categories": [
				{"value": "Equipment", "label": "Equipment"},
				{"value": "Security", "label": "Security"},
				{"value": "Inventory", "label": "Inventory"},
				{"value": "POS System", "label": "POS System"},
			],
		},
		{
			"value": "Technical",
			"label": "Technical / IT",
			"department": "IT Support",
			"sub_categories": [],
		},
		{
			"value": "Other",
			"label": "Other",
			"department": "General",
			"sub_categories": [],
		},
	]


@frappe.whitelist()
def get_responsible_departments():
	departments = frappe.get_all(
		"Department",
		filters={"is_group": 0},
		fields=["name", "department_name"],
		order_by="name",
	)

	result = []
	for dept in departments:
		manager = frappe.db.get_value(
			"Employee",
			{"department": dept.name, "designation": "Manager"},
			["user_id", "employee_name"],
			as_dict=True,
		)
		result.append(
			{
				"value": dept.name,
				"label": dept.department_name or dept.name,
				"manager": manager.employee_name if manager else None,
				"manager_email": manager.user_id if manager else None,
			}
		)

	return result


@frappe.whitelist()
def create_attendance_issue(
	subject: str,
	description: str,
	issue_type: str = "Attendance",
	priority: str = "Medium",
):
	if not subject:
		frappe.throw(_("Subject is required"))
	if not description:
		frappe.throw(_("Description is required"))

	employee = frappe.db.get_value(
		"Employee",
		{"user_id": frappe.session.user},
		["name", "employee_name", "department", "designation", "reports_to"],
		as_dict=True,
	)

	manager_user_id = None
	if employee and employee.get("reports_to"):
		manager_user_id = frappe.db.get_value("Employee", {"name": employee.reports_to}, "user_id")

	reporter = employee.employee_name if employee else frappe.session.user
	emp_id = employee.name if employee else "N/A"
	emp_dept = employee.department if employee else "N/A"
	emp_desig = employee.designation if employee else "N/A"
	dt_str = now_datetime().strftime("%Y-%m-%d %H:%M:%S")

	full_description = (
		f"**Reported by Employee:** {reporter}\n"
		f"**Employee ID:** {emp_id}\n"
		f"**Department:** {emp_dept}\n"
		f"**Designation:** {emp_desig}\n"
		f"**Date/Time:** {dt_str}\n\n---\n\n"
		f"**Issue Description:**\n\n{description}"
	)

	ticket = None
	try:
		ticket = _try_create_hd_ticket(
			subject,
			full_description,
			frappe.session.user,
			priority,
			issue_type,
		)
	except Exception:
		frappe.log_error("HD Ticket Create Failed (attendance)", frappe.get_traceback())

	if ticket:
		return {
			"success": True,
			"ticket_id": ticket.name,
			"message": _("Ticket {0} created successfully").format(ticket.name),
			"helpdesk_installed": True,
		}

	issue = None
	try:
		issue = _try_create_issue(
			subject,
			full_description,
			frappe.session.user,
			priority,
			issue_type,
		)
	except Exception:
		frappe.log_error("Issue Create Failed (attendance)", frappe.get_traceback())

	if issue:
		if manager_user_id:
			try:
				todo = frappe.get_doc(
					{
						"doctype": "ToDo",
						"reference_type": "Issue",
						"reference_name": issue.name,
						"description": f"New issue assigned: {subject}",
						"allocated_to": manager_user_id,
						"status": "Open",
					}
				)
				todo.flags.ignore_permissions = True
				todo.insert()
			except Exception:
				pass
		return {
			"success": True,
			"ticket_id": issue.name,
			"message": _("Issue {0} created successfully").format(issue.name),
			"helpdesk_installed": False,
		}

	todo = _create_todo_fallback(subject, full_description, issue_type, manager_user_id)
	return {
		"success": True,
		"ticket_id": todo.name,
		"message": _("Your issue has been reported. A ToDo has been created for HR."),
		"helpdesk_installed": False,
	}


@frappe.whitelist()
def get_employee_tickets(
	status: str | None = None,
	start_date: str | None = None,
	end_date: str | None = None,
	employee_filter: str | None = None,
	limit: int = 50,
):
	tickets = []
	user = frappe.session.user
	is_hr_manager = "HR Manager" in frappe.get_roles(user) or "System Manager" in frappe.get_roles(user)

	if is_hr_manager:
		if employee_filter:
			employees = [employee_filter]
		else:
			employees = None
	else:
		allowed_employees = [emp.name for emp in get_grievance_employees()]
		if employee_filter:
			if employee_filter in allowed_employees:
				employees = [employee_filter]
			else:
				employees = []
		else:
			employees = allowed_employees

	if frappe.db.exists("DocType", "Employee Grievance"):
		filters = {}
		if employees is not None:
			if not employees:
				return []
			filters["raised_by"] = ["in", employees]

		if status:
			filters["status"] = status
		if start_date and end_date:
			filters["date"] = ["between", [start_date, end_date]]
		elif start_date:
			filters["date"] = [">=", start_date]
		elif end_date:
			filters["date"] = ["<=", end_date]

		grievances = frappe.get_all(
			"Employee Grievance",
			filters=filters,
			fields=[
				"name",
				"subject",
				"status",
				"date",
				"grievance_type",
				"creation",
				"modified",
				"description",
				"employee_name",
				"grievance_against_party",
				"grievance_against",
				"raised_by",
				"cause_of_grievance",
				"resolved_by",
				"resolution_date",
				"resolution_detail",
				"designation",
				"reports_to",
				"associated_document_type",
				"associated_document",
				"employee_responsible",
			],
			order_by="creation desc",
			limit=limit,
		)

		for g in grievances:
			tickets.append(
				{
					"name": g.name,
					"subject": g.subject,
					"status": g.status,
					"priority": "Medium",
					"issue_type": g.grievance_type,
					"category": g.grievance_type,
					"creation": str(g.creation),
					"modified": str(g.modified),
					"resolution": "",
					"source": "grievance",
					"employee_name": g.employee_name,
					"date": str(g.date) if g.date else "",
					"description": g.description,
					"grievance_against_party": g.grievance_against_party,
					"grievance_against": g.grievance_against,
					"raised_by": g.raised_by,
					"cause_of_grievance": g.cause_of_grievance or "",
					"resolved_by": g.resolved_by or "",
					"resolution_date": str(g.resolution_date) if g.resolution_date else "",
					"resolution_detail": g.resolution_detail or "",
					"designation": g.designation or "",
					"reports_to": g.reports_to or "",
					"associated_document_type": g.associated_document_type or "",
					"associated_document": g.associated_document or "",
					"employee_responsible": g.employee_responsible or "",
				}
			)

	return tickets


@frappe.whitelist()
def get_ticket_details(ticket_id: str):
	if frappe.db.exists("DocType", "Employee Grievance") and frappe.db.exists("Employee Grievance", ticket_id):
		grievance = frappe.get_doc("Employee Grievance", ticket_id)
		employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
		if grievance.raised_by != employee:
			frappe.throw(_("You can only view your own grievances"))
		return {
			"name": grievance.name,
			"subject": grievance.subject,
			"description": grievance.description,
			"status": grievance.status,
			"priority": "Medium",
			"issue_type": grievance.grievance_type,
			"creation": str(grievance.creation),
			"modified": str(grievance.modified),
			"resolution": grievance.resolution_detail or "",
			"source": "grievance",
		}

	frappe.throw(_("Ticket not found"))


@frappe.whitelist()
def add_ticket_reply(ticket_id: str, message: str):
	if not message:
		frappe.throw(_("Message is required"))

	if frappe.db.exists("DocType", "HD Ticket") and frappe.db.exists("HD Ticket", ticket_id):
		ticket = frappe.get_doc("HD Ticket", ticket_id)
		if ticket.raised_by != frappe.session.user:
			frappe.throw(_("You can only reply to your own tickets"))
		frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": "Comment",
				"reference_doctype": "HD Ticket",
				"reference_name": ticket_id,
				"content": message,
				"comment_email": frappe.session.user,
			}
		).insert(ignore_permissions=True)
		return {"success": True, "message": _("Reply added successfully")}

	if frappe.db.exists("Issue", ticket_id):
		issue = frappe.get_doc("Issue", ticket_id)
		if issue.raised_by != frappe.session.user:
			frappe.throw(_("You can only reply to your own tickets"))
		frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": "Comment",
				"reference_doctype": "Issue",
				"reference_name": ticket_id,
				"content": message,
				"comment_email": frappe.session.user,
			}
		).insert(ignore_permissions=True)
		return {"success": True, "message": _("Reply added successfully")}

	frappe.throw(_("Ticket not found"))


@frappe.whitelist()
def get_issue_types():
	return [
		{"value": "Attendance", "label": "Attendance Issue"},
		{"value": "Manager", "label": "Manager/Escalation"},
		{"value": "Payroll", "label": "Payroll/Salary"},
		{"value": "Leave", "label": "Leave Request Issue"},
		{"value": "Other", "label": "Other"},
	]


@frappe.whitelist()
def get_ticket_stats():
	stats = {"total": 0, "open": 0, "closed": 0, "pending": 0}
	user = frappe.session.user

	if frappe.db.exists("DocType", "HD Ticket"):
		hd_stats = frappe.db.sql(  # nosemgrep
			"""
			SELECT status, COUNT(*) as count
			FROM `tabHD Ticket`
			WHERE raised_by = %s
			GROUP BY status
		""",
			(user,),
			as_dict=True,
		)
		for s in hd_stats:
			stats["total"] += s.count
			if s.status in ["Open", "Replied"]:
				stats["open"] += s.count
			elif s.status in ["Resolved", "Closed"]:
				stats["closed"] += s.count
			else:
				stats["pending"] += s.count

	if frappe.db.exists("DocType", "Issue"):
		issue_stats = frappe.db.sql(  # nosemgrep
			"""
			SELECT status, COUNT(*) as count
			FROM `tabIssue`
			WHERE raised_by = %s
			GROUP BY status
		""",
			(user,),
			as_dict=True,
		)
		for s in issue_stats:
			stats["total"] += s.count
			if s.status in ["Open"]:
				stats["open"] += s.count
			elif s.status in ["Closed", "Resolved"]:
				stats["closed"] += s.count
			else:
				stats["pending"] += s.count

	return stats


@frappe.whitelist()
def get_employee_rievance():
	stats = {
		"added_this_month": 0,
		"resolved_this_month": 0,
		"investigated": 0,
		"investigated_this_month": 0,
		"open": 0,
		"total": 0
	}
	if not frappe.db.exists("DocType", "Employee Grievance"):
		return stats

	user = frappe.session.user
	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee:
		return stats

	from frappe.utils import get_first_day, get_last_day, getdate
	today = getdate()
	start_date = get_first_day(today)
	end_date = get_last_day(today)

	stats["added_this_month"] = frappe.db.count(
		"Employee Grievance",
		filters={
			"raised_by": employee,
			"date": ["between", [start_date, end_date]]
		}
	)

	stats["resolved_this_month"] = frappe.db.count(
		"Employee Grievance",
		filters={
			"raised_by": employee,
			"status": "Resolved",
			"resolution_date": ["between", [start_date, end_date]]
		}
	)

	stats["investigated"] = frappe.db.count(
		"Employee Grievance",
		filters={
			"raised_by": employee,
			"status": "Investigated"
		}
	)

	stats["investigated_this_month"] = frappe.db.count(
		"Employee Grievance",
		filters={
			"raised_by": employee,
			"status": "Investigated",
			"date": ["between", [start_date, end_date]]
		}
	)

	stats["open"] = frappe.db.count(
		"Employee Grievance",
		filters={
			"raised_by": employee,
			"status": "Open"
		}
	)

	stats["total"] = frappe.db.count(
		"Employee Grievance",
		filters={
			"raised_by": employee
		}
	)

	return stats


@frappe.whitelist()
def get_grievance_statuses():
	if not frappe.db.exists("DocType", "Employee Grievance"):
		return []
	meta = frappe.get_meta("Employee Grievance")
	status_options = meta.get_field("status").options.split('\n')
	return [{"value": s, "label": s} for s in status_options if s]


@frappe.whitelist()
def get_grievance_types():
	if not frappe.db.exists("DocType", "Grievance Type"):
		return []
	types = frappe.get_all("Grievance Type", fields=["name"])
	return [{"value": t.name, "label": t.name} for t in types]


@frappe.whitelist()
def search_link_options(doctype: str, query: str = None, raised_by: str = None):
	if doctype not in ["Company", "Department", "Employee Group", "Employee Grade", "Employee"]:
		frappe.throw(_("Invalid Link Type"))

	filters = {}
	if doctype == "Employee" and raised_by:
		filters["name"] = ["!=", raised_by]

	if query:
		meta = frappe.get_meta(doctype)
		search_field = meta.title_field or "name"
		filters[search_field] = ["like", f"%{query}%"]

	records = frappe.get_all(doctype, filters=filters, fields=["name"], limit=50)
	return [{"value": r.name, "label": r.name} for r in records]


@frappe.whitelist()
def create_employee_grievance(
	subject: str,
	description: str,
	date: str,
	status: str,
	grievance_against_party: str,
	grievance_against: str,
	grievance_type: str,
	name: str | None = None,
):
	if not subject:
		frappe.throw(_("Subject is required"))
	if not description:
		frappe.throw(_("Description is required"))
	if not grievance_against_party:
		frappe.throw(_("Grievance Against Party is required"))
	if not grievance_against:
		frappe.throw(_("Grievance Against is required"))
	if not grievance_type:
		frappe.throw(_("Grievance Type is required"))

	user = frappe.session.user
	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee:
		frappe.throw(_("Employee record not found for the current user"))

	if name and frappe.db.exists("Employee Grievance", name):
		doc = frappe.get_doc("Employee Grievance", name)
		# Ensure security: non-managers can only edit their own
		is_hr_manager = "HR Manager" in frappe.get_roles(user) or "System Manager" in frappe.get_roles(user)
		if not is_hr_manager and doc.raised_by != employee:
			frappe.throw(_("You are not authorized to edit this grievance."))
		doc.subject = subject
		doc.description = description
		doc.date = date or frappe.utils.today()
		doc.grievance_against_party = grievance_against_party
		doc.grievance_against = grievance_against
		doc.grievance_type = grievance_type
		doc.save(ignore_permissions=True)
	else:
		doc = frappe.get_doc({
			"doctype": "Employee Grievance",
			"subject": subject,
			"description": description,
			"raised_by": employee,
			"date": date or frappe.utils.today(),
			"status": status or "Open",
			"grievance_against_party": grievance_against_party,
			"grievance_against": grievance_against,
			"grievance_type": grievance_type,
		})
		doc.insert(ignore_permissions=True)

	try:
		doc.submit()
	except Exception:
		pass

	return {
		"success": True,
		"name": doc.name,
		"message": _("Grievance {0} saved successfully").format(doc.name)
	}


@frappe.whitelist()
def delete_employee_grievance(name: str):
	try:
		user = frappe.session.user
		is_hr_manager = "HR Manager" in frappe.get_roles(user) or "System Manager" in frappe.get_roles(user)

		doc = frappe.get_doc("Employee Grievance", name)
		if not is_hr_manager:
			employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
			if doc.raised_by != employee:
				frappe.throw(_("You are not authorized to delete this grievance."))

		frappe.delete_doc("Employee Grievance", name)
		return {"success": True}
	except Exception as e:
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_grievance_employees():
	user = frappe.session.user
	roles = frappe.get_roles(user)

	if "System Manager" in roles or "HR Manager" in roles:
		return frappe.get_all(
			"Employee",
			filters={"status": ["in", ["Active", "Suspended"]]},
			fields=["name", "employee_name"],
			order_by="employee_name ASC",
		)

	# Otherwise, only return their own employee details
	employee = frappe.db.get_value("Employee", {"user_id": user}, ["name", "employee_name"], as_dict=True)
	if employee:
		status = frappe.db.get_value("Employee", employee.name, "status")
		if status in ["Active", "Suspended"]:
			return [employee]
	return []


@frappe.whitelist()
def investigate_employee_grievance(name: str, cause_of_grievance: str):
	if not name:
		frappe.throw(_("Grievance ID is required"))
	if not cause_of_grievance:
		frappe.throw(_("Cause of Issue is required"))

	user = frappe.session.user
	doc = frappe.get_doc("Employee Grievance", name)

	# Security check: Ensure they are not investigating their own grievance
	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if doc.raised_by == employee:
		frappe.throw(_("You cannot investigate your own grievance."))

	# Security check: Ensure they are allowed to edit/investigate this grievance
	is_hr_manager = "HR Manager" in frappe.get_roles(user) or "System Manager" in frappe.get_roles(user)
	allowed_employees = [emp.name for emp in get_grievance_employees()]
	if not is_hr_manager and doc.raised_by not in allowed_employees:
		frappe.throw(_("You are not authorized to investigate this grievance."))

	if doc.docstatus == 1:
		doc.db_set("status", "Investigated")
		doc.db_set("cause_of_grievance", cause_of_grievance)
	else:
		doc.status = "Investigated"
		doc.cause_of_grievance = cause_of_grievance
		doc.save(ignore_permissions=True)

	return {
		"success": True,
		"message": _("Grievance {0} updated to Investigated status.").format(name)
	}


@frappe.whitelist()
def get_users_list():
	return frappe.get_list(
		"User",
		filters={"enabled": 1, "user_type": "System User"},
		fields=["name", "full_name"],
		order_by="full_name ASC",
	)


@frappe.whitelist()
def resolve_employee_grievance(
	name: str,
	resolved_by: str,
	resolution_date: str,
	resolution_detail: str,
):
	frappe.only_for(["HR Manager", "System Manager"])
	if not name:
		frappe.throw(_("Grievance ID is required"))
	if not resolved_by:
		frappe.throw(_("Resolved By user is required"))
	if not resolution_date:
		frappe.throw(_("Resolution Date is required"))
	if not resolution_detail:
		frappe.throw(_("Resolution Detail is required"))

	user = frappe.session.user
	doc = frappe.get_doc("Employee Grievance", name)

	# Security check: Ensure they are not resolving their own grievance
	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if doc.raised_by == employee:
		frappe.throw(_("You cannot resolve your own grievance."))

	if doc.docstatus == 1:
		doc.db_set("status", "Resolved")
		doc.db_set("resolved_by", resolved_by)
		doc.db_set("resolution_date", resolution_date)
		doc.db_set("resolution_detail", resolution_detail)
	else:
		doc.status = "Resolved"
		doc.resolved_by = resolved_by
		doc.resolution_date = resolution_date
		doc.resolution_detail = resolution_detail
		doc.save(ignore_permissions=True)
		try:
			doc.submit()
		except Exception:
			frappe.log_error("Grievance Submit Failed on Resolve", frappe.get_traceback())

	return {
		"success": True,
		"name": doc.name,
		"message": _("Grievance {0} has been resolved and submitted successfully.").format(name)
	}
