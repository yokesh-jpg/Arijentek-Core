import frappe
from frappe import _


@frappe.whitelist()
def can_read_hr_settings():
	"""
	Returns True if the current user has permission to read HR Settings.
	This is true for 'HR Manager', 'System Manager', 'Administrator', 'HR User',
	or users with explicit read permissions on the 'HR Settings' Doctype.
	"""
	user = frappe.session.user
	if user == "Administrator":
		return True

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles or "HR User" in roles:
		return True

	if frappe.has_permission("HR Settings", "read"):
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
	timesheet_with_clockin = frappe.db.get_default("ep_timesheet_with_clockin")
	if timesheet_with_clockin is None:
		try:
			timesheet_with_clockin = frappe.db.get_single_value("HR Settings", "timesheet_with_clockin")
		except Exception:
			timesheet_with_clockin = 0

	mark_present_on_clock_out = frappe.db.get_default("ep_mark_present_on_clock_out")
	if mark_present_on_clock_out is None:
		try:
			mark_present_on_clock_out = frappe.db.get_single_value("HR Settings", "mark_present_on_clock_out")
		except Exception:
			mark_present_on_clock_out = 0

	disable_auto_attendance = frappe.db.get_default("ep_disable_auto_attendance")
	if disable_auto_attendance is None:
		try:
			disable_auto_attendance = frappe.db.get_single_value("HR Settings", "disable_auto_attendance")
		except Exception:
			disable_auto_attendance = 0

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
	frappe.db.set_default("ep_timesheet_with_clockin", str(val))
	try:
		frappe.db.set_single_value("HR Settings", "timesheet_with_clockin", val)
	except Exception:
		pass
	frappe.db.commit()
	return {"status": "success", "timesheet_with_clockin": val}


@frappe.whitelist()
def update_mark_present_on_clock_out(mark_present_on_clock_out=0):
	"""
	Update Make Present while Clock Out setting in HR Settings (requires HR Manager or System Manager role).
	"""
	_check_hr_settings_permission()
	val = frappe.utils.cint(mark_present_on_clock_out)
	frappe.db.set_default("ep_mark_present_on_clock_out", str(val))
	try:
		frappe.db.set_single_value("HR Settings", "mark_present_on_clock_out", val)
	except Exception:
		pass
	frappe.db.commit()
	return {"status": "success", "mark_present_on_clock_out": val}


@frappe.whitelist()
def update_disable_auto_attendance(disable_auto_attendance=0):
	"""
	Update Disable Auto Attendance setting in HR Settings (requires HR Manager or System Manager role).
	"""
	_check_hr_settings_permission()
	val = frappe.utils.cint(disable_auto_attendance)
	frappe.db.set_default("ep_disable_auto_attendance", str(val))
	try:
		frappe.db.set_single_value("HR Settings", "disable_auto_attendance", val)
	except Exception:
		pass
	frappe.db.commit()
	return {"status": "success", "disable_auto_attendance": val}
