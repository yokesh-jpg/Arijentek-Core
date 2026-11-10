"""Tasks module for Arijentek Core"""

import frappe


@frappe.whitelist()
def can_assign_tasks():
	"""
	Returns True if the current user has permission to assign tasks.
	Checks for 'HR Manager', 'HR User', or 'System Manager' roles.
	"""
	user = frappe.session.user
	if user == "Administrator":
		return True

	roles = set(frappe.get_roles(user))
	allowed_roles = {"HR Manager", "HR User", "System Manager"}
	return bool(roles & allowed_roles)


@frappe.whitelist()
def can_assign_task():
	return can_assign_tasks()

