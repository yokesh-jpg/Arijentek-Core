__version__ = "1.0.0"


def _patch_hrms_app_permission():
	"""
	Monkey-patch HRMS's check_app_permission to return False for Website Users.

	This fixes a design issue where Website Users with Employee role get redirected
	to /desk/people after login, but can't access it (403 Forbidden).

	The patch makes HRMS invisible in the apps screen for Website Users,
	so get_default_path() won't return /desk/people for them.
	"""
	try:
		import frappe
		from hrms.hr import utils as hrms_utils

		# Store original function for reference
		_original_check_app_permission = hrms_utils.check_app_permission

		def patched_check_app_permission():
			"""
			Override: Return False for Website Users to prevent desk redirect.
			Website Users should use the employee-portal, not /desk/people.
			"""
			# Early return for guest
			if frappe.session.user == "Guest":
				return False

			# Check if user is a Website User
			user_type = frappe.get_cached_value("User", frappe.session.user, "user_type")
			if user_type == "Website User":
				# Website Users cannot access desk, so don't show HRMS app
				return False

			# For System Users, use original logic
			return _original_check_app_permission()

		# Apply the patch
		hrms_utils.check_app_permission = patched_check_app_permission

	except ImportError:
		# HRMS not installed, no need to patch
		pass
	except Exception:
		# Silently fail - don't break app loading
		pass


# Apply patch when module loads
_patch_hrms_app_permission()


import frappe


@frappe.whitelist()
def can_mark_attendance():
	user = frappe.session.user
	if "System Manager" in frappe.get_roles():
		return True
	count = frappe.db.count(
		"Employee",
		filters={"status": "Active", "shift_request_approver": user}
	)
	return bool(count)


@frappe.whitelist()
def get_leave_approver_employees():
	"""Get list of active employees where current user is the leave_approver"""
	user = frappe.session.user
	if "System Manager" in frappe.get_roles():
		return frappe.get_all(
			"Employee",
			filters={"status": "Active"},
			fields=["name", "employee_name"],
			order_by="employee_name asc",
		)
	reports = frappe.get_all(
		"Employee",
		filters={"status": "Active", "leave_approver": user},
		fields=["name", "employee_name"],
		order_by="employee_name asc",
	)
	return reports


@frappe.whitelist()
def get_shift_approver_employees():
	"""Get list of active employees where current user is the shift_request_approver"""
	user = frappe.session.user
	if "System Manager" in frappe.get_roles():
		return frappe.get_all(
			"Employee",
			filters={"status": "Active"},
			fields=["name", "employee_name"],
			order_by="employee_name asc",
		)

	reports = frappe.get_all(
		"Employee",
		filters={"status": "Active", "shift_request_approver": user},
		fields=["name", "employee_name"],
		order_by="employee_name asc",
	)
	if reports:
		current_employee = frappe.db.get_value(
			"Employee",
			{"user_id": user, "status": "Active"},
			["name", "employee_name"],
			as_dict=True
		)

		if current_employee:
			if not any(emp["name"] == current_employee["name"] for emp in reports):
				reports.append(current_employee)
				reports.sort(key=lambda x: x.get("employee_name") or "")

	return reports


@frappe.whitelist()
def get_expense_approver_employees():
	"""Get list of active employees where current user is the expense_approver"""
	user = frappe.session.user
	if "System Manager" in frappe.get_roles():
		return frappe.get_all(
			"Employee",
			filters={"status": "Active"},
			fields=["name", "employee_name"],
			order_by="employee_name asc",
		)
	reports = frappe.get_all(
		"Employee",
		filters={"status": "Active", "expense_approver": user},
		fields=["name", "employee_name"],
		order_by="employee_name asc",
	)
	return reports



