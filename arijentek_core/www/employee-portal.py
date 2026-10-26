"""Context for the Employee Portal www page."""

import frappe
from frappe import _

# Roles that may open the employee portal. Floor staff typically hold "Employee"; HR and
# store management hold the rest. The page-level gate complements (does not replace) the
# per-endpoint only_for / ownership checks in the api layer.
_PORTAL_ROLES = {
	"Employee",
	"Employee Self Service",
	"HR Manager",
	"HR User",
	"Store Manager",
	"Sales Manager",
	"Sales User",
	"System Manager",
}


def get_context(context):
	"""Set no_cache, enforce a page-level role gate, and expose a dev-mode flag."""
	context.no_cache = 1

	user = frappe.session.user

	# Gate 1: guests must log in.
	if user == "Guest":
		frappe.redirect_to_message(
			_("Login required"),
			_("Please sign in to access the Employee Portal."),
			indicator="info",
		)
		raise frappe.Redirect

	# Gate 2: authenticated users must have an Employee record OR a portal/HR/manager role.
	roles = set(frappe.get_roles(user))
	has_employee = bool(
		frappe.db.exists("Employee", {"user_id": user, "status": "Active"})
	) if user != "Administrator" else True
	if user != "Administrator" and not has_employee and not (roles & _PORTAL_ROLES):
		frappe.redirect_to_message(
			_("Not authorized"),
			_("Your account is not linked to an employee record and lacks portal roles."),
			indicator="red",
		)
		raise frappe.Redirect

	# Only render the on-page error/debug overlay when Developer Mode is on (site_config.json).
	context.is_developer = bool(frappe.conf.get("developer_mode"))
