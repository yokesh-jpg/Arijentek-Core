import frappe
from frappe import _


@frappe.whitelist()
def can_read_hr_settings():
	"""
	Returns True if the current user has permission to read HR Settings.
	This is true for 'HR Manager', 'System Manager', or users with explicit read permissions on the 'HR Settings' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	return False


@frappe.whitelist()
def can_access_hr_settings():
	return can_read_hr_settings()


@frappe.whitelist()
def has_hr_settings_permission():
	return can_read_hr_settings()


def _check_hr_settings_permission():
	if not can_read_hr_settings():
		frappe.throw(_("Not authorized to access or update HR Settings"), frappe.PermissionError)



@frappe.whitelist()
def get_hr_settings():
	"""
	Fetch HR Settings for employee portal customization.
	"""
	_check_hr_settings_permission()
	timesheet_with_clockin = frappe.db.get_single_value("HR Settings", "timesheet_with_clockin")
	mark_present_on_clock_out = frappe.db.get_single_value("HR Settings", "mark_present_on_clock_out")
	disable_auto_attendance = frappe.db.get_single_value("HR Settings", "disable_auto_attendance")
	return {
		"timesheet_with_clockin": frappe.utils.cint(timesheet_with_clockin),
		"mark_present_on_clock_out": frappe.utils.cint(mark_present_on_clock_out),
		"disable_auto_attendance": frappe.utils.cint(disable_auto_attendance),
	}


@frappe.whitelist()
def update_timesheet_automation(timesheet_with_clockin=0):
	"""
	Update Timesheet Automation setting in HR Settings (requires HR Manager or System Manager role).
	"""
	_check_hr_settings_permission()
	val = frappe.utils.cint(timesheet_with_clockin)
	frappe.db.set_single_value("HR Settings", "timesheet_with_clockin", val)
	frappe.db.commit()
	return {"status": "success", "timesheet_with_clockin": val}


@frappe.whitelist()
def update_mark_present_on_clock_out(mark_present_on_clock_out=0):
	"""
	Update Make Present while Clock Out setting in HR Settings (requires HR Manager or System Manager role).
	"""
	_check_hr_settings_permission()
	val = frappe.utils.cint(mark_present_on_clock_out)
	frappe.db.set_single_value("HR Settings", "mark_present_on_clock_out", val)
	frappe.db.commit()
	return {"status": "success", "mark_present_on_clock_out": val}


@frappe.whitelist()
def update_disable_auto_attendance(disable_auto_attendance=0):
	"""
	Update Disable Auto Attendance setting in HR Settings (requires HR Manager or System Manager role).
	"""
	_check_hr_settings_permission()
	val = frappe.utils.cint(disable_auto_attendance)
	frappe.db.set_single_value("HR Settings", "disable_auto_attendance", val)
	frappe.db.commit()
	return {"status": "success", "disable_auto_attendance": val}
