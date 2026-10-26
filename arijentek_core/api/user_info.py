"""
User Info API for POS Dashboard.

Provides current user information including roles for role-based
dashboard tile rendering.
"""

import frappe

from arijentek_core.services.permissions import DESK_ROLES


@frappe.whitelist(allow_guest=True)
def get_user_info():
	"""Return current user info with roles for the POS dashboard.

	Returns:
		dict: Contains user email, full_name, and list of role names.
	"""
	user = frappe.session.user
	if user == "Guest":
		return "Guest"

	try:
		from arijentek_core.api.auth import get_user_landing_route, get_user_role_profiles

		roles = frappe.get_roles(user)
		role_profiles = get_user_role_profiles(user)
		landing_route = get_user_landing_route(user)
		user_details = frappe.db.get_value("User", user, ["full_name", "user_image"], as_dict=True) or {}
		full_name = user_details.get("full_name") or user
		user_image = user_details.get("user_image")
		# Desk access = the desk tier only (api/auth.block_desk_access is the
		# gate). System Manager holders — e.g. tenant owners — stay in the SPA.
		has_desk_access = user == "Administrator" or bool(set(roles) & DESK_ROLES)

		return {
			"user": user,
			"full_name": full_name,
			"user_image": user_image,
			"roles": roles,
			"role_profiles": role_profiles,
			"landing_route": landing_route,
			"has_desk_access": has_desk_access,
		}
	except Exception as e:
		frappe.logger("arijentek_core").error(f"Error in get_user_info for {user}: {e}")
		session_roles = getattr(getattr(frappe.local, "session", None), "roles", []) or []
		return {
			"user": user,
			"full_name": user,
			"user_image": None,
			"roles": list(session_roles),
			"role_profiles": [],
			"landing_route": "/",
			"has_desk_access": False,
		}


@frappe.whitelist()
def user_has_desk_access():
	"""Return True if the current user may load the Frappe Desk (/app).

	True for the desk tier (Gemora Super Admin / Gemora Developer — see
	services.permissions.DESK_ROLES) and the site Administrator. System
	Manager alone does NOT grant desk access; those users live in the SPA.
	"""
	user = frappe.session.user
	if user == "Administrator":
		return True
	roles = frappe.get_roles(user)
	return bool(set(roles) & DESK_ROLES)
