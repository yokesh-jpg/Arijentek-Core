import frappe

# Issues API

@frappe.whitelist()
def can_create_employee_grievance():
	"""
	Returns True if the current user has permission to create an Employee Grievance.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Employee Grievance", "create"):
		return True
	return False

@frappe.whitelist()
def can_read_employee_grievance():
	"""
	Returns True if the current user has permission to read an Employee Grievance.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Employee Grievance", "read"):
		return True
	return False

@frappe.whitelist()
def can_edit_employee_grievance():
	"""
	Returns True if the current user has permission to edit an Employee Grievance.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Employee Grievance", "write"):
		return True
	return False

@frappe.whitelist()
def can_delete_employee_grievance():
	"""
	Returns True if the current user has permission to delete an Employee Grievance.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Employee Grievance", "delete"):
		return True
	return False

@frappe.whitelist()
def can_submit_employee_grievance():
	"""
	Returns True if the current user has permission to submit an Employee Grievance.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Employee Grievance", "submit"):
		return True
	return False

@frappe.whitelist()
def can_create_grievance_type():
	"""
	Returns True if the current user has permission to create a Grievance Type.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Grievance Type", "create"):
		return True
	return False

@frappe.whitelist()
def can_read_grievance_type():
	"""
	Returns True if the current user has permission to read a Grievance Type.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Grievance Type", "read"):
		return True
	return False

@frappe.whitelist()
def can_edit_grievance_type():
	"""
	Returns True if the current user has permission to edit a Grievance Type.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Grievance Type", "write"):
		return True
	return False

@frappe.whitelist()
def can_delete_grievance_type():
	"""
	Returns True if the current user has permission to delete a Grievance Type.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if frappe.has_permission("Grievance Type", "delete"):
		return True
	return False

@frappe.whitelist()
def get_issues_types(id=None):
	"""
	Fetch Grievance Types. If id is provided, fetch specific record.
	Returns all fields.
	"""
	if not can_read_grievance_type():
		frappe.throw(frappe._("Not permitted to read Grievance Type"), frappe.PermissionError)

	filters = {}
	if id:
		filters["name"] = id

	return frappe.get_all("Grievance Type", filters=filters, fields=["*"])

@frappe.whitelist()
def save_issue_type(doc):
	import json
	if isinstance(doc, str):
		doc = json.loads(doc)

	original_name = doc.get("original_name")
	new_name = doc.get("name")
	description = doc.get("description")

	if original_name and original_name != new_name:
		if not can_edit_grievance_type():
			frappe.throw(frappe._("Not permitted to edit Grievance Type"), frappe.PermissionError)
		frappe.rename_doc("Grievance Type", original_name, new_name)
		frappe.db.set_value("Grievance Type", new_name, "description", description)
		return new_name

	if original_name:
		if not can_edit_grievance_type():
			frappe.throw(frappe._("Not permitted to edit Grievance Type"), frappe.PermissionError)
		frappe.db.set_value("Grievance Type", original_name, "description", description)
		return original_name
	else:
		if not can_create_grievance_type():
			frappe.throw(frappe._("Not permitted to create Grievance Type"), frappe.PermissionError)
		new_doc = frappe.new_doc("Grievance Type")
		new_doc.name = new_name
		new_doc.description = description
		new_doc.insert()
		return new_doc.name

@frappe.whitelist()
def delete_issue_type(name):
	if not can_delete_grievance_type():
		frappe.throw(frappe._("Not permitted to delete Grievance Type"), frappe.PermissionError)
	frappe.delete_doc("Grievance Type", name)
	return True

@frappe.whitelist()
def get_issues(
	id=None,
	search_term=None,
	status=None,
	employee=None,
	grievance_type=None,
	from_date=None,
	to_date=None,
	page: int = 1,
	page_size: int = 0
):
	"""
	Fetch Employee Grievances with optional filters and server-side pagination.
	When page_size > 0: returns dict with 'data', 'total', 'page', 'page_size', and 'stats'.
	When page_size == 0: returns list of issues (legacy format).
	"""
	from frappe.utils import cint

	if not can_read_employee_grievance():
		frappe.throw(frappe._("Not permitted to read Employee Grievance"), frappe.PermissionError)

	if id:
		return frappe.get_all("Employee Grievance", filters={"name": id}, fields=["*"])

	page = max(1, cint(page) or 1)
	page_size = cint(page_size) or 0

	can_submit = can_submit_employee_grievance()

	conditions = ["eg.docstatus < 2"]
	params = {}

	if not can_submit:
		user_emp = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
		if user_emp:
			conditions.append("eg.raised_by = %(user_emp)s")
			params["user_emp"] = user_emp
		else:
			conditions.append("eg.owner = %(owner)s")
			params["owner"] = frappe.session.user
	elif employee and employee not in ["All", ""]:
		conditions.append("eg.raised_by = %(employee)s")
		params["employee"] = employee

	if grievance_type and grievance_type not in ["All", ""]:
		conditions.append("eg.grievance_type = %(grievance_type)s")
		params["grievance_type"] = grievance_type

	if from_date and to_date:
		conditions.append("eg.date BETWEEN %(from_date)s AND %(to_date)s")
		params["from_date"] = from_date
		params["to_date"] = to_date
	elif from_date:
		conditions.append("eg.date >= %(from_date)s")
		params["from_date"] = from_date
	elif to_date:
		conditions.append("eg.date <= %(to_date)s")
		params["to_date"] = to_date

	if search_term:
		conditions.append("(eg.name LIKE %(search)s OR eg.subject LIKE %(search)s)")
		params["search"] = f"%{search_term}%"

	base_where = " AND ".join(conditions)

	table_conditions = list(conditions)
	if status and status not in ["All", ""]:
		table_conditions.append("eg.status = %(status)s")
		params["status"] = status
	table_where = " AND ".join(table_conditions)

	# Stats aggregation over base_where (across all statuses for active filters)
	stats = {"total": 0, "Open": 0, "Investigated": 0, "Resolved": 0, "Invalid": 0}
	stats_rows = frappe.db.sql(
		f"""
		SELECT eg.status, COUNT(*) AS count
		FROM `tabEmployee Grievance` eg
		WHERE {base_where}
		GROUP BY eg.status
		""",
		params,
		as_dict=True,
	)
	for r in stats_rows:
		st = r.get("status")
		cnt = r.get("count", 0)
		if st in stats:
			stats[st] = cnt
		stats["total"] += cnt

	# Paginated response (page_size > 0)
	if page_size > 0:
		total_row = frappe.db.sql(
			f"""
			SELECT COUNT(*) AS count
			FROM `tabEmployee Grievance` eg
			WHERE {table_where}
			""",
			params,
			as_dict=True,
		)
		total = total_row[0].count if total_row else 0

		offset = (page - 1) * page_size
		params["limit"] = page_size
		params["offset"] = offset

		issues = frappe.db.sql(
			f"""
			SELECT
				eg.*,
				COALESCE(NULLIF(eg.employee_name, ''), e.employee_name, '') AS employee_name
			FROM `tabEmployee Grievance` eg
			LEFT JOIN `tabEmployee` e ON eg.raised_by = e.name
			WHERE {table_where}
			ORDER BY eg.creation DESC
			LIMIT %(limit)s OFFSET %(offset)s
			""",
			params,
			as_dict=True,
		)

		return {
			"data": issues,
			"total": total,
			"page": page,
			"page_size": page_size,
			"stats": stats,
		}

	# Legacy response (page_size == 0)
	issues = frappe.db.sql(
		f"""
		SELECT
			eg.*,
			COALESCE(NULLIF(eg.employee_name, ''), e.employee_name, '') AS employee_name
		FROM `tabEmployee Grievance` eg
		LEFT JOIN `tabEmployee` e ON eg.raised_by = e.name
		WHERE {table_where}
		ORDER BY eg.creation DESC
		""",
		params,
		as_dict=True,
	)
	return issues

@frappe.whitelist()
def delete_issues(name):
	if not can_delete_employee_grievance():
		frappe.throw(frappe._("Not permitted to delete Employee Grievance"), frappe.PermissionError)

	issue_doc = frappe.get_doc("Employee Grievance", name)
	if issue_doc.status != "Open" and not can_submit_employee_grievance():
		frappe.throw(frappe._("Only authorized managers can delete grievances that are no longer Open."), frappe.PermissionError)

	frappe.delete_doc("Employee Grievance", name)
	return True

@frappe.whitelist()
def get_employees():
	if not can_read_employee_grievance():
		frappe.throw(frappe._("Not permitted"), frappe.PermissionError)
	if not can_submit_employee_grievance():
		user_emp = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, ["name", "employee_name"], as_dict=True)
		if user_emp:
			return [user_emp]
	return frappe.get_all("Employee", filters={"status": "Active"}, fields=["name", "employee_name"])

@frappe.whitelist()
def get_statuses():
	if can_submit_employee_grievance():
		return ["Open", "Investigated", "Resolved", "Invalid"]
	return ["Open"]

@frappe.whitelist()
def get_grievance_against_party_options():
	return ["Company/Others", "Department", "Employee"]

@frappe.whitelist()
def get_grievance_against_list(party):
	if not can_read_employee_grievance():
		frappe.throw(frappe._("Not permitted"), frappe.PermissionError)
	if party == "Company/Others" or party == "Company":
		return frappe.get_all("Company", fields=["name", "company_name as label"])
	elif party == "Department":
		return frappe.get_all("Department", fields=["name", "department_name as label"])
	elif party == "Employee":
		return frappe.get_all("Employee", filters={"status": "Active"}, fields=["name", "employee_name as label"])
	return []

@frappe.whitelist()
def get_users():
	if not can_read_employee_grievance():
		frappe.throw(frappe._("Not permitted"), frappe.PermissionError)
	return frappe.get_all("User", filters={"enabled": 1, "user_type": "System User"}, fields=["name", "full_name"])

@frappe.whitelist()
def save_issue(doc):
	import json
	if isinstance(doc, str):
		doc = json.loads(doc)

	is_new = not doc.get("name")
	if is_new:
		if not can_create_employee_grievance():
			frappe.throw(frappe._("Not permitted to create Employee Grievance"), frappe.PermissionError)
		issue_doc = frappe.new_doc("Employee Grievance")
	else:
		if not can_edit_employee_grievance():
			frappe.throw(frappe._("Not permitted to edit Employee Grievance"), frappe.PermissionError)
		issue_doc = frappe.get_doc("Employee Grievance", doc.get("name"))
		if issue_doc.status != "Open" and not can_submit_employee_grievance():
			frappe.throw(frappe._("Only authorized managers can edit grievances that are no longer Open."), frappe.PermissionError)

	fields = [
		"subject", "date", "raised_by", "status", "grievance_against_party",
		"grievance_against", "grievance_type", "description", "cause_of_grievance",
		"resolved_by", "resolution_date", "resolution_detail"
	]

	for field in fields:
		if field in doc:
			issue_doc.set(field, doc.get(field))

	# Map Company/Others back to Company for the database
	if issue_doc.grievance_against_party == "Company/Others":
		issue_doc.grievance_against_party = "Company"

	issue_doc.save()

	try:
		from arijentek_core.api.notifications import notify_approvers, notify_owner
		if is_new:
			emp_name = frappe.db.get_value("Employee", issue_doc.raised_by, "employee_name") or issue_doc.raised_by or issue_doc.owner
			title = "New Employee Grievance"
			body = f"{emp_name} has raised a new grievance: {issue_doc.subject or issue_doc.name}."
			notify_approvers(issue_doc, title, body, module="hrm", route="/issues?tab=issues")
		else:
			new_status = issue_doc.status
			if new_status and new_status != "Open":
				title = f"Grievance {new_status}"
				body = f"Your grievance '{issue_doc.subject or issue_doc.name}' has been marked as {new_status}."
				notify_owner(issue_doc, title, body, module="hrm", route="/issues?tab=issues")
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Grievance Notification Error")

	return issue_doc.name


@frappe.whitelist()
def get_issue_report_filter_options():
	"""
	Returns dropdown options for Employee, Status (Open, Investigated, Resolved, Invalid), and Issue Type.
	"""
	employees = frappe.get_all("Employee", fields=["name as id", "employee_name as name"], order_by="name asc")
	statuses = [
		{"id": "Open", "name": "Open"},
		{"id": "Investigated", "name": "Investigated"},
		{"id": "Resolved", "name": "Resolved"},
		{"id": "Invalid", "name": "Invalid"}
	]
	issue_types = frappe.get_all("Grievance Type", fields=["name as id", "name as name"], order_by="name asc")

	return {
		"employees": [{"id": e.id, "name": f"{e.name} ({e.id})"} for e in employees],
		"statuses": statuses,
		"issue_types": issue_types
	}


@frappe.whitelist()
def report_issue_list(from_date=None, to_date=None, employee=None, status=None, issue_type=None, export=0, pdf=0):
	"""
	Returns Issues / Employee Grievance list for report based on filters.
	Ignores Cancelled status.
	"""
	import frappe
	from frappe.utils import getdate, now_datetime
	from frappe.utils.pdf import get_pdf
	from frappe.utils.xlsxutils import build_xlsx_response

	conditions = ["eg.docstatus < 2", "COALESCE(eg.status, '') != 'Cancelled'"]
	params = {}

	if employee:
		conditions.append("eg.raised_by = %(employee)s")
		params["employee"] = employee

	if status and status.lower() != "all":
		conditions.append("eg.status = %(status)s")
		params["status"] = status

	if issue_type and issue_type.lower() != "all":
		conditions.append("eg.grievance_type = %(issue_type)s")
		params["issue_type"] = issue_type

	if from_date and to_date:
		conditions.append("eg.date BETWEEN %(from_date)s AND %(to_date)s")
		params["from_date"] = getdate(from_date)
		params["to_date"] = getdate(to_date)
	elif from_date:
		conditions.append("eg.date >= %(from_date)s")
		params["from_date"] = getdate(from_date)
	elif to_date:
		conditions.append("eg.date <= %(to_date)s")
		params["to_date"] = getdate(to_date)

	where_clause = " AND ".join(conditions)

	query = f"""
		SELECT
			eg.name,
			eg.subject,
			DATE_FORMAT(eg.date, '%%Y-%%m-%%d') as date,
			eg.raised_by,
			COALESCE(eg.employee_name, e.employee_name, '') AS employee_name,
			COALESCE(eg.grievance_type, '') AS issue_type,
			COALESCE(eg.status, 'Open') AS status
		FROM `tabEmployee Grievance` eg
		LEFT JOIN `tabEmployee` e ON eg.raised_by = e.name
		WHERE {where_clause}
		ORDER BY eg.date DESC, eg.name DESC
	"""

	data = frappe.db.sql(query, params, as_dict=True)

	result = []
	for r in data:
		emp_id = r.get("raised_by") or ""
		emp_name = r.get("employee_name") or ""
		emp_display = f"{emp_id} - {emp_name}" if (emp_id and emp_name) else (emp_id or emp_name or "-")

		result.append({
			"name": r.name,
			"subject": r.subject or "-",
			"date": r.date or "",
			"raised_by": emp_id,
			"employee_name": emp_name,
			"raised_by_str": emp_display,
			"issue_type": r.issue_type or "-",
			"status": r.status or "Open"
		})

	if int(export):
		xlsx_data = [["Issue ID", "Subject", "Date", "Raised By", "Type", "Status"]]
		for r in result:
			xlsx_data.append([
				r["name"],
				r["subject"],
				r["date"],
				r["raised_by_str"],
				r["issue_type"],
				r["status"]
			])

		build_xlsx_response(xlsx_data, "Issues_Report")
		return

	if int(pdf):
		context = {
			"data": result,
			"filters": {
				"from_date": from_date,
				"to_date": to_date,
				"employee": employee,
				"status": status,
				"issue_type": issue_type
			}
		}

		html = frappe.render_template("arijentek_core/templates/reports/issue_report.html", context)
		pdf_binary = get_pdf(html, {
			"page-size": "A4",
			"orientation": "Landscape",
			"margin-top": "10mm",
			"margin-bottom": "10mm",
			"margin-left": "8mm",
			"margin-right": "8mm"
		})

		frappe.local.response.filename = f"Issues_Report_{now_datetime().strftime('%Y%m%d')}.pdf"
		frappe.local.response.filecontent = pdf_binary
		frappe.local.response.type = "pdf"
		return

	return result


