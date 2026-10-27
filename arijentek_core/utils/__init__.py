import frappe
from werkzeug.exceptions import HTTPException
from werkzeug.utils import redirect

PORTAL_PATH = "/employee-portal"


class DeskRedirect(HTTPException):
	code = 302

	def __init__(self, location="/"):
		super().__init__()
		self.location = location

	def get_response(self, environ=None):
		return redirect(self.location, code=302)


def block_desk_access():
	"""
	Enforce complete separation of non-admin users from Frappe Desk (/app, /desk).
	Also redirect root (/) visits to /employee-portal.
	Only Administrator may access /app or /desk.
	All other users are redirected to /employee-portal.
	"""
	request = getattr(frappe.local, "request", None)
	if request is None:
		return

	path = getattr(request, "path", "") or ""

	# Redirect root / directly to /employee-portal
	if path == "/" or path == "":
		raise DeskRedirect(PORTAL_PATH)

	if path == "/app" or path.startswith("/app/") or path == "/desk" or path.startswith("/desk/"):
		user = getattr(frappe.session, "user", None) or "Guest"

		# Only Administrator is allowed to access Desk
		if user == "Administrator":
			return

		raise DeskRedirect(PORTAL_PATH)


# ---------- Hook: get_website_user_home_page ----------


def get_employee_home_page(user: str):
	"""Frappe hook - returns home page URL. Non-admin users land on Employee Portal."""
	if user == "Guest":
		return None
	if user == "Administrator":
		return "app"
	return PORTAL_PATH.lstrip("/")


# ---------- Hook: on_session_creation & on_login ----------


def redirect_employee_after_login(login_manager=None, *args, **kwargs):
	"""Set redirect so non-admin users land on Employee Portal after login, Administrator lands on /app."""
	user = getattr(frappe.session, "user", None)
	if login_manager and getattr(login_manager, "user", None):
		user = login_manager.user

	if user == "Administrator":
		frappe.local.response["home_page"] = "/app"
		frappe.local.response["redirect_to"] = "/app"
	else:
		frappe.local.flags.home_page = PORTAL_PATH.lstrip("/")
		frappe.local.response["home_page"] = PORTAL_PATH
		frappe.local.response["redirect_to"] = PORTAL_PATH


# ---------- Hook: boot_session ----------


def redirect_employee_on_boot(bootinfo):
	"""Do NOT set home_page here. It would make the desk try to load
	'employee-portal' as a desk workspace, causing 'Page employee-portal not found'.
	Login redirect (custom_login + redirect_employee_after_login) already sends
	everyone to the portal first. When System Users click 'Open Desk', the desk
	should use its normal default (apps grid), not try to load the portal.
	"""
	pass


# ---------- Permission check for add_to_apps_screen ----------


def has_portal_permission():
	"""Return True for any logged-in System User (for apps screen tile)."""
	user = frappe.session.user
	if user == "Guest":
		return False
	user_type = frappe.db.get_value("User", user, "user_type")
	return user_type == "System User"
