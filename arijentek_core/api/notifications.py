import frappe
from frappe import _


def notify_leave_application(doc):
	"""Notify leave approver about new leave application"""
	recipient = doc.leave_approver

	if not recipient and doc.employee:
		recipient = frappe.db.get_value("Employee", doc.employee, "leave_approver")

	if not recipient:
		return

	employee_name = getattr(doc, "employee_name", None)
	if not employee_name and doc.employee:
		employee_name = frappe.db.get_value("Employee", doc.employee, "employee_name")

	subject = _("New Leave Application: {0}").format(employee_name or doc.employee)
	message = _("{0} has applied for {1} from {2} to {3}.").format(
		employee_name or doc.employee, doc.leave_type, doc.from_date, doc.to_date
	)

	# System Notification
	create_system_notification(recipient, subject, message, "Leave Application", doc.name)

	# Email (if configured)
	# frappe.sendmail(recipients=[manager_user], subject=subject, message=message)


def notify_leave_status(doc):
	"""Notify employee about leave status change"""
	employee = frappe.get_doc("Employee", doc.employee)
	if not employee.user_id:
		return

	status = doc.status
	subject = _("Leave Application {0}").format(status)
	message = _("Your leave application for {0} to {1} has been {2}.").format(
		doc.from_date, doc.to_date, status
	)

	create_system_notification(employee.user_id, subject, message, "Leave Application", doc.name)


def create_system_notification(user, subject, message, ref_doctype, ref_docname):
	"""Create a standard Frappe Notification Log"""
	notification = frappe.get_doc(
		{
			"doctype": "Notification Log",
			"subject": subject,
			"email_content": message,
			"for_user": user,
			"document_type": ref_doctype,
			"document_name": ref_docname,
			"type": "Alert",
		}
	)
	notification.insert(ignore_permissions=True)


@frappe.whitelist()
def get_pending_leave_count():
	user = frappe.session.user

	# Identify active employees where this user is the Leave Approver
	team_employees = frappe.get_all(
		"Employee",
		filters={"status": "Active", "leave_approver": user},
		pluck="name"
	)

	if not team_employees:
		return {"count": 0}

	# Count pending open applications
	count = frappe.db.count(
		"Leave Application",
		filters={
			"employee": ["in", team_employees],
			"status": "Open",
			"docstatus": 0
		}
	)
	return {"count": count}


@frappe.whitelist()
def get_team_pending_counts():
	user = frappe.session.user
	user_roles = frappe.get_roles(user)
	is_system_or_hr_manager = "System Manager" in user_roles or "HR Manager" in user_roles

	# 1. Leave Applications
	if is_system_or_hr_manager:
		leave_employees = frappe.get_all(
			"Employee",
			filters={"status": "Active"},
			pluck="name",
		)
	else:
		leave_employees = frappe.get_all(
			"Employee",
			filters={"status": "Active", "leave_approver": user},
			pluck="name",
		)

	leave_count = 0
	if leave_employees:
		leave_count = frappe.db.count(
			"Leave Application",
			filters={
				"employee": ["in", leave_employees],
				"status": "Open",
				"docstatus": 0
			}
		)

	# 2. Expense Claims
	if is_system_or_hr_manager:
		expense_employees = frappe.get_all(
			"Employee",
			filters={"status": "Active"},
			pluck="name",
		)
	else:
		current_employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
		if current_employee:
			expense_employees = frappe.get_all(
				"Employee",
				filters={"status": "Active"},
				or_filters={
					"reports_to": current_employee,
					"leave_approver": user,
					"shift_request_approver": user,
				},
				pluck="name",
			)
		else:
			expense_employees = []

	expense_count = 0
	if expense_employees:
		expense_count = frappe.db.count(
			"Expense Claim",
			filters={
				"employee": ["in", expense_employees],
				"approval_status": "Draft",
				"docstatus": ["<", 2]
			}
		)

	# 3. Attendance Requests
	if is_system_or_hr_manager:
		attendance_employees = frappe.get_all(
			"Employee",
			filters={"status": "Active"},
			pluck="name"
		)
	else:
		try:
			from arijentek_core import get_shift_approver_employees
			attendance_employees = [e["name"] for e in get_shift_approver_employees()]
		except Exception:
			attendance_employees = []

	attendance_count = 0
	if attendance_employees:
		attendance_count = frappe.db.count(
			"Attendance Request",
			filters={
				"employee": ["in", attendance_employees],
				"docstatus": 0
			}
		)

	total = leave_count + expense_count + attendance_count

	return {
		"leaves": leave_count,
		"expenses": expense_count,
		"attendance": attendance_count,
		"total": total
	}




