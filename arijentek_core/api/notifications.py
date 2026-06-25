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



