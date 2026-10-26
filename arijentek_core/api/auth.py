import secrets

import frappe
from frappe.auth import LoginManager
from frappe.utils import get_datetime, get_url, now_datetime
from werkzeug.exceptions import HTTPException
from werkzeug.utils import redirect

from arijentek_core.services.permissions import DESK_ROLES
from arijentek_core.services.role_profile_catalog import ROLE_PROFILE_CATALOG

# One-time cross-domain login handoff. The central portal verifies the
# user's password via get_login_link and redirects their browser to the
# redeem URL; the token is single-use and expires in minutes.
ONE_TIME_LOGIN_KEY = "one_time_login:{}"


class DeskRedirect(HTTPException):
	code = 302

	def __init__(self, location="/"):
		super().__init__()
		self.location = location

	def get_response(self, environ=None):
		return redirect(self.location, code=302)


def get_user_role_profiles(user: str) -> list[str]:
	"""Return list of Role Profile names assigned to the user."""
	if not user or user == "Guest":
		return []

	try:
		profiles = frappe.get_all(
			"User Role Profile",
			filters={"parent": user, "parenttype": "User"},
			pluck="role_profile",
		)
		legacy_profile = frappe.db.get_value("User", user, "role_profile_name")
		if legacy_profile and legacy_profile not in profiles:
			profiles.append(legacy_profile)
		return profiles
	except Exception:
		return []


@frappe.whitelist()
def get_user_landing_route(user: str | None = None) -> str:
	"""
	Determine the default landing route based on the user's Role Profile and Roles.

	Role Profile Routing (v1_6 simplified catalog):
	- 'Sales' (POS Cashier) -> '/terminal' (POS Register)
	- 'Inventory' (Inventory & Stock) -> '/inventory'
	- 'Store Manager' -> '/' (Dashboard)
	- 'HR' (HR & People Ops) -> '/' (via catalog fallback)
	- 'Admin User' (Owner / Admin) -> '/' (via catalog fallback)

	Role Fallback Routing:
	- Desk roles (Gemora Super Admin / Gemora Developer) -> '/app'
	- Inventory / Stock roles -> '/inventory'
	- Cashier / Sales User roles -> '/terminal'
	- Accounts / Finance roles -> '/reports'
	- Manager / Admin roles (incl. 'Admin User', the customer owner tier) -> '/'
	- Employee Self Service only -> '/employee-portal'
	"""
	if not user:
		user = getattr(frappe.session, "user", None)

	if not user or user == "Guest":
		return "/login"

	profiles = set(get_user_role_profiles(user))
	roles = set(frappe.get_roles(user))

	# 0. Desk tier wins over every persona route — the SPA login sends these
	# users to the Frappe Desk (raw role check: aliases do not apply here).
	if user == "Administrator" or roles & DESK_ROLES:
		return "/app"

	# 1. Match by Role Profile (catalog personas kept in v1_6)
	if "Sales" in profiles:
		return "/terminal"
	if "Inventory" in profiles:
		return "/inventory"
	if "Store Manager" in profiles:
		return "/"

	# 1b. Persona catalog + Team-Hub custom personas: per-profile landing in
	# assignment order — first profile with a declared route wins. Covers
	# stacked personas and custom personas.
	for profile in get_user_role_profiles(user):
		spec = ROLE_PROFILE_CATALOG.get(profile)
		if spec and spec.get("landing"):
			return spec["landing"]
		custom_landing = frappe.db.get_value("Role Profile", profile, "custom_landing_route")
		if custom_landing:
			return custom_landing

	# 2. Match by Roles
	if (
		"System Manager" in roles
		or "Administrator" in roles
		or "Gemora Admin" in roles
		or "Admin User" in roles  # customer owner tier (v1_5)
	):
		return "/"
	if "Store Manager" in roles or "POS Manager" in roles or "Gemora Manager" in roles:
		return "/"
	if "Gemora Inventory" in roles or "Stock Manager" in roles:
		return "/inventory"
	if "Accounts Manager" in roles or "Accounts User" in roles:
		return "/reports"
	# Dedicated kiosk terminal accounts land directly on the sell screen.
	if "POS Terminal" in roles:
		return "/terminal"
	if "Gemora Cashier" in roles or "Sales User" in roles:
		return "/terminal"

	# 3. Employee Self Service portal
	if "Employee Self Service" in roles and not roles.intersection(
		{"Sales User", "Gemora Cashier", "Gemora Manager", "Stock User", "Accounts User"}
	):
		return "/employee-portal"

	return "/"


@frappe.whitelist()
def get_landing_route(user: str | None = None) -> str:
	"""Public whitelisted method to fetch landing route for current or specified user."""
	return get_user_landing_route(user)


def block_desk_access():
	"""
	Enforce complete separation of POS & Retail users from Frappe Desk (/app).
	All managers, admins, and retail staff operate 100% inside Zevar UI —
	only the desk tier (services.permissions.DESK_ROLES) and Administrator
	(in developer_mode) may load /app or /desk.
	Any other request targeting /app or /desk is dynamically redirected
	based on the user's role profile.
	"""
	request = getattr(frappe.local, "request", None)
	if request is None:
		return

	path = getattr(request, "path", "") or ""

	# Check if user is attempting to access Frappe Desk
	if path == "/app" or path.startswith("/app/") or path == "/desk" or path.startswith("/desk/"):
		user = getattr(frappe.session, "user", None) or "Guest"

		# Desk tier: Gemora Super Admin / Gemora Developer pass (raw role check).
		if user != "Guest" and set(frappe.get_roles(user)) & DESK_ROLES:
			return

		# Allow only Administrator when explicitly in developer_mode (for bench/CLI migrations)
		if user == "Administrator" and frappe.conf.get("developer_mode"):
			return

		# Route to their role-specific landing page. A computed "/app" here
		# means the user failed the desk checks above (e.g. Administrator on a
		# production site without developer_mode) — redirecting there again
		# would loop, so drop them on the SPA root instead.
		landing_route = get_user_landing_route(user)
		if landing_route == "/app":
			landing_route = "/"
		raise DeskRedirect(landing_route)


def _generate_temporary_login_link(user: str, expiry_minutes: int = 2) -> str:
	"""Mint a single-use, short-lived login token and return its redeem URL."""
	token = secrets.token_urlsafe(32)
	frappe.cache().set_value(
		ONE_TIME_LOGIN_KEY.format(token), user, expires_in_sec=expiry_minutes * 60
	)
	return get_url(f"/api/method/arijentek_core.api.auth.redeem_login_link?token={token}")


@frappe.whitelist(allow_guest=True)
def get_login_link(email, password):
	"""
	Validates password and returns a one-time login link.
	Used by the central Gemora 360 Portal for seamless cross-domain login.
	"""
	email = (email or "").strip()
	password = password or ""
	try:
		# LoginManager.authenticate rather than a raw password check: it is
		# lettercase agnostic, rejects disabled users, and feeds the IP and
		# per-user failed-login throttles — this is a guest endpoint, so
		# credential guessing must be rate limited exactly like the login
		# form. authenticate alone creates no session; only the redeem
		# endpoint below does, inside the user's browser.
		manager = LoginManager()
		manager.authenticate(user=email, pwd=password)

		from frappe.twofactor import should_run_2fa

		if should_run_2fa(manager.user):
			return {
				"status": "error",
				"message": "This account uses two-factor authentication and cannot sign in via a login link.",
			}

		login_url = _generate_temporary_login_link(manager.user, expiry_minutes=2)
		return {"status": "success", "login_url": login_url}

	except frappe.AuthenticationError:
		return {"status": "error", "message": "Incorrect email or password."}
	except Exception as e:
		frappe.log_error(title="Failed to generate login link", message=str(e))
		return {"status": "error", "message": "Internal server error."}


@frappe.whitelist(allow_guest=True)
def redeem_login_link(token: str):
	"""Exchange a one-time login token for a session, then redirect home."""
	token = (token or "").strip()
	if not token or len(token) > 128:
		frappe.throw("Invalid or expired login link.", frappe.AuthenticationError)

	key = ONE_TIME_LOGIN_KEY.format(token)
	user = frappe.cache().get_value(key)
	# Burn the token on the first redemption attempt — one-time means one-time.
	frappe.cache().delete_value(key)
	if not user or user == "Guest":
		frappe.throw("Invalid or expired login link.", frappe.AuthenticationError)
	if user != "Administrator" and not frappe.db.get_value("User", user, "enabled"):
		frappe.throw("User disabled or missing.", frappe.AuthenticationError)

	frappe.local.login_manager = LoginManager()
	frappe.local.login_manager.login_as(user)

	# Full-page redirect into the SPA (or the Desk for the desk tier).
	landing_route = get_user_landing_route(user)
	target = "/app" if landing_route == "/app" else f"/pos{landing_route}"
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = target


@frappe.whitelist(allow_guest=True)
def support_token_login(token: str):
	"""Exchange a single-use support token (60s TTL) for a desk session.

	The console's ``support_login`` mints the token hash on the tenant via
	bench execute (``saas_settings.prepare_support_token``). Guest endpoint
	by necessity — the operator's browser arrives with no session. The
	raw token is never stored anywhere; only its SHA-256 hash matches.
	"""
	from hashlib import sha256

	SUPPORT_TOKEN_KEY = "saas:support_token:{}"
	from arijentek_core.services.internal_access import (
		SUPPORT_EXPIRY_FIELD,
		disable_expired_support_user,
	)

	token = (token or "").strip()
	if not token or len(token) > 128:
		frappe.throw("Invalid or expired support token.", frappe.AuthenticationError)

	key = SUPPORT_TOKEN_KEY.format(sha256(token.encode("utf-8")).hexdigest())
	user = frappe.cache().get_value(key)
	# Single use regardless of outcome — burn on the first attempt.
	frappe.cache().delete_value(key)
	if not user or user in ("Guest", "Administrator"):
		frappe.throw("Invalid or expired support token.", frappe.AuthenticationError)
	if not frappe.db.get_value("User", user, "enabled"):
		frappe.throw("This support session is no longer active.", frappe.AuthenticationError)

	expires = (
		frappe.db.get_value("User", user, SUPPORT_EXPIRY_FIELD)
		if frappe.get_meta("User").has_field(SUPPORT_EXPIRY_FIELD)
		else None
	)
	if not expires or now_datetime() > get_datetime(expires):
		disable_expired_support_user(user)
		frappe.throw("This support session has expired.", frappe.AuthenticationError)

	frappe.local.login_manager = LoginManager()
	frappe.local.login_manager.login_as(user)

	# Support accounts hold desk roles — this lands on /app.
	landing_route = get_user_landing_route(user)
	target = "/app" if landing_route == "/app" else f"/pos{landing_route}"
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = target


@frappe.whitelist(allow_guest=True)
def login(usr, pwd, remember_me=False):
	# If usr matches an Employee ID, resolve it to their user_id
	if frappe.db.exists("Employee", {"name": usr}):
		user_id = frappe.db.get_value("Employee", {"name": usr}, "user_id")
		if not user_id:
			frappe.throw("No user account is linked to this Employee ID.", frappe.AuthenticationError)
		usr = user_id
		frappe.form_dict["usr"] = usr

	frappe.local.login_manager = LoginManager()
	frappe.local.login_manager.login()

	# ponytail: extend session expiry when "Remember Me" is checked.
	if remember_me and frappe.session.user != "Guest":
		sid = frappe.session.sid
		session_data = frappe.cache.hget("session", sid)
		if session_data:
			session_data["data"]["session_expiry"] = "720:00:00"  # 30 days
			frappe.cache.hset("session", sid, session_data)

	# Shared-terminal kiosk sign-in: record it on the attribution trail
	# (which machine account opened the register session).
	if frappe.session.user != "Guest" and "POS Terminal" in frappe.get_roles(frappe.session.user):
		user_roles = set(frappe.get_roles(frappe.session.user))
		privileged_roles = {"System Manager", "Administrator", "Store Manager", "Sales Manager", "POS Manager"}
		if not (user_roles & privileged_roles):
			try:
				from arijentek_core.api.audit_log import log_event_safely

				log_event_safely(
					event_type="terminal_login",
					details={"remember_me": bool(remember_me)},
				)
			except Exception:
				frappe.log_error("terminal_login audit failed")

	landing_route = get_user_landing_route(usr)
	return {
		"success": True,
		"user": usr,
		"landing_route": landing_route,
	}

