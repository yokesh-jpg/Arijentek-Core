"""Internal-user isolation & privilege-escalation defense (v2_0).

One module for everything that separates Gemora platform staff from
tenant users:

- the internal marker (``custom_is_gemora_internal`` on User / Employee /
  Role Profile) and who carries it (``is_internal_user``,
  ``get_internal_user_names``)
- ``guard_user_roles`` — the ``User.validate`` firewall: platform roles,
  the owner grant ("Admin User"), the marker itself and protected
  targets are platform-controlled on every write surface (SPA endpoints,
  desk, ``/api/resource`` — ``ignore_permissions`` does not skip
  doc_events)
- ``*_query_conditions`` — REST/desk list scoping for User / Role /
  Role Profile / Employee. ``frappe.get_all`` bypasses these; pickers
  filter explicitly via ``get_internal_user_names``
- ``sanitize_audit_user`` — tenant-facing audit streams show platform
  actors as "Gemora Support", never their identities
- ``enforce_support_expiry`` / ``disable_expired_support_accounts`` — the
  kill switch for ephemeral support accounts
  (``saas_settings.prepare_support_token`` mints them,
  ``api.auth.support_token_login`` redeems the one-time token)

Marker fields are created by patches/v2_0/seed_gemora_internal_marker.
Every marker read is guarded with ``has_field`` so pre-migrate sites
(and the control plane, which does not run zevar patches) keep working.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, now_datetime

from arijentek_core.services.permissions import PLATFORM_ROLES

INTERNAL_MARKER = "custom_is_gemora_internal"
SUPPORT_EXPIRY_FIELD = "custom_support_expires_at"

# Tenant-facing display name for every masked platform identity.
SUPPORT_DISPLAY_NAME = "Gemora Support"

# Frappe sets these during migrations/installs/imports — platform tooling
# writes then, not user sessions, so the guard must not fire.
_SYSTEM_FLAGS = ("in_migrate", "in_install", "in_patch", "in_setup_wizard", "in_import")


def _has_marker_field(doctype: str) -> bool:
	"""True when the v2_0 marker column exists on ``doctype`` (pre-migrate guard)."""
	try:
		return frappe.get_meta(doctype).has_field(INTERNAL_MARKER)
	except Exception:
		return False


def _has_expiry_field() -> bool:
	try:
		return frappe.get_meta("User").has_field(SUPPORT_EXPIRY_FIELD)
	except Exception:
		return False


def is_internal_user(user: str | None) -> bool:
	"""True for platform staff accounts (Administrator + flagged users)."""
	if not user or user == "Guest":
		return False
	if user == "Administrator":
		return True
	if not _has_marker_field("User"):
		return False
	return bool(frappe.db.get_value("User", user, INTERNAL_MARKER))


def get_internal_user_names() -> list[str]:
	"""Every internal User name (Administrator + flagged).

	For explicit ``not in`` filters in ``frappe.get_all`` pickers, which
	bypass ``permission_query_conditions``.
	"""
	names = {"Administrator"}
	if _has_marker_field("User"):
		names.update(frappe.get_all("User", filters={INTERNAL_MARKER: 1}, pluck="name"))
	return sorted(names)


def get_internal_employee_names() -> list[str]:
	"""Employee names carrying the internal marker.

	Same purpose as ``get_internal_user_names`` for staff counts and
	employee pickers built on ``frappe.get_all`` (which bypasses
	``employee_query_conditions``).
	"""
	if not _has_marker_field("Employee"):
		return []
	return frappe.get_all("Employee", filters={INTERNAL_MARKER: 1}, pluck="name")


def internal_employee_sql(table: str = "`tabEmployee`") -> str:
	"""SQL fragment excluding internal employees ("" pre-migrate).

	For the raw-SQL staff surfaces (roster matrix, commission summary)
	which never see ``permission_query_conditions``.
	"""
	if not _has_marker_field("Employee"):
		return ""
	return f"({table}.{INTERNAL_MARKER} IS NULL OR {table}.{INTERNAL_MARKER} = 0)"


def _is_platform_actor(user: str | None) -> bool:
	"""True when ``user`` writes with platform authority.

	Administrator, internal-flagged accounts (support logins), and — on
	platform sites — desk-grant holders (the pre-v2_0 desk population
	created before the marker existed).
	"""
	if not user or user == "Guest":
		return False
	if user == "Administrator" or is_internal_user(user):
		return True
	from arijentek_core.services.permissions import can_grant_desk_roles

	return can_grant_desk_roles(user)


def _in_system_context() -> bool:
	return any(getattr(frappe.flags, flag, False) for flag in _SYSTEM_FLAGS)


# ── User.validate firewall ───────────────────────────────────────────────────


def guard_user_roles(doc, method: str | None = None) -> None:
	"""doc_events: User.validate — platform-controlled writes only.

	Rules, enforced for every actor EXCEPT platform staff
	(``_is_platform_actor``) and system contexts (migrate/patch/install):

	1. ``PLATFORM_ROLES`` may never be added or removed — granting AND
	   stripping a platform role both change who can reach the platform.
	2. the owner grant ("Admin User") may only be changed by the admin
	   tier (Admin User / System Manager / Administrator).
	3. the internal marker is read-only platform state.
	4. protected targets (Administrator + internal users) may not be
	   edited at all from a tenant session.

	Complements ``permissions.guard_user_desk_roles`` (desk tier); both
	run on the same User.validate event. Role Profile materialization
	happens earlier in the same validate pass, so the role diff covers
	direct edits, profile assignment and profile re-syncs alike.
	"""
	if _in_system_context():
		return
	actor = frappe.session.user
	if _is_platform_actor(actor):
		return

	# 4. Protected targets: nothing about platform accounts is editable
	#    from a tenant session (role-preserving saves included).
	if doc.name and (doc.name == "Administrator" or is_internal_user(doc.name)):
		frappe.throw(
			_("Platform accounts may only be managed by Gemora."),
			frappe.PermissionError,
		)

	before = doc.get_doc_before_save()
	existing = {r.role for r in (before.get("roles") or [])} if before else set()
	current = {r.role for r in (doc.get("roles") or [])}
	changed = existing ^ current

	# 1. Platform roles — never grantable (or strippable) by tenants.
	if changed & PLATFORM_ROLES:
		frappe.throw(
			_("Platform roles are assigned by Gemora only."),
			frappe.PermissionError,
		)

	# 2. The owner grant needs the admin tier.
	if "Admin User" in changed:
		from arijentek_core.services.role_profile_catalog import _is_admin_tier

		if not _is_admin_tier(actor):
			frappe.throw(
				_("The owner persona may only be assigned by an administrator."),
				frappe.PermissionError,
			)

	# 3. The marker itself is platform-only state.
	if _has_marker_field("User"):
		old = cint(before.get(INTERNAL_MARKER)) if before else 0
		if cint(doc.get(INTERNAL_MARKER)) != old:
			frappe.throw(
				_("Internal platform flags may only be set by Gemora."),
				frappe.PermissionError,
			)


# ── permission_query_conditions (desk + REST lists; get_all bypasses) ────────


def _sees_internal(user: str | None) -> bool:
	"""Internal/platform staff see everything; tenant users never do."""
	return _is_platform_actor(user or frappe.session.user)


def user_query_conditions(user: str | None = None) -> str:
	"""Hide platform accounts (Administrator, Guest, internal) from tenant lists."""
	if _sees_internal(user):
		return ""
	if not _has_marker_field("User"):
		return "`tabUser`.name NOT IN ('Administrator', 'Guest')"
	return (
		"`tabUser`.name NOT IN ('Administrator', 'Guest') "
		f"AND (`tabUser`.{INTERNAL_MARKER} IS NULL OR `tabUser`.{INTERNAL_MARKER} = 0)"
	)


def role_query_conditions(user: str | None = None) -> str:
	"""Hide the platform roles from tenant role lists (the four grants)."""
	if _sees_internal(user):
		return ""
	hidden = sorted(PLATFORM_ROLES - {"Administrator"})
	names = ", ".join(f"'{role}'" for role in hidden)
	return f"`tabRole`.name NOT IN ({names})"


def role_profile_query_conditions(user: str | None = None) -> str:
	"""Hide internal-flagged Role Profiles (desk personas) from tenants."""
	if _sees_internal(user):
		return ""
	if not _has_marker_field("Role Profile"):
		return ""
	return f"(`tabRole Profile`.{INTERNAL_MARKER} IS NULL OR `tabRole Profile`.{INTERNAL_MARKER} = 0)"


def employee_query_conditions(user: str | None = None) -> str:
	"""Hide internal-flagged Employees from tenant lists."""
	if _sees_internal(user):
		return ""
	if not _has_marker_field("Employee"):
		return ""
	return f"(`tabEmployee`.{INTERNAL_MARKER} IS NULL OR `tabEmployee`.{INTERNAL_MARKER} = 0)"


def user_has_permission(doc, ptype: str = "read", user: str | None = None) -> bool | None:
	"""has_permission: User — platform accounts are unreachable tenant-side.

	Closes the single-doc gap ``user_query_conditions`` cannot: it scopes
	lists, while ``/api/resource/User/<name>`` and ``frappe.client.get``
	go through ``frappe.has_permission``. Platform actors fall through to
	default permissions; everything else is denied on Administrator,
	Guest and internal-flagged accounts.
	"""
	if _is_platform_actor(user or frappe.session.user):
		return None
	if doc.name in ("Administrator", "Guest") or is_internal_user(doc.name):
		return False
	return None


# ── audit identity masking ───────────────────────────────────────────────────


def sanitize_audit_user(user: str | None) -> str:
	"""Mask one platform identity in a tenant-facing activity stream."""
	if not user:
		return ""
	if user == "Administrator" or is_internal_user(user):
		return SUPPORT_DISPLAY_NAME
	return user


def sanitize_audit_users(users) -> dict[str, str]:
	"""Bulk raw → display-name map (only internal entries change)."""
	internal = set(get_internal_user_names())
	return {u: (SUPPORT_DISPLAY_NAME if u in internal else u) for u in users}


# ── ephemeral support sessions ───────────────────────────────────────────────


def enforce_support_expiry() -> None:
	"""before_request: an expired support session dies on its next request.

	The hourly sweep (``disable_expired_support_accounts``) is the
	backstop; this closes the window between expiry and sweep. Regular
	users (no expiry lease) pay one indexed read.
	"""
	user = getattr(frappe.session, "user", None)
	if not user or user in ("Guest", "Administrator"):
		return
	if not _has_expiry_field():
		return
	expires = frappe.db.get_value("User", user, SUPPORT_EXPIRY_FIELD)
	if not expires:
		return  # regular user: no support lease on the account
	if now_datetime() <= get_datetime(expires):
		return
	disable_expired_support_user(user)
	frappe.throw(
		_("This support session has expired. Please start a new one from the console."),
		frappe.AuthenticationError,
	)


def disable_expired_support_accounts() -> None:
	"""Hourly scheduler: disable expired support users + purge their sessions."""
	if not _has_expiry_field():
		return
	# List-form filters: the same field appears twice ("is set" + "<"), which a
	# dict cannot express. The explicit notnull() matters — on this Frappe/
	# MariaDB pair a bare ``<`` comparison on the Datetime column ALSO matches
	# NULL rows, so without it the sweep disables every enabled user site-wide
	# (that is exactly how zevar.localhost lost all 30 accounts on 2026-10-12).
	expired = frappe.get_all(
		"User",
		filters=[
			["enabled", "=", 1],
			["name", "not in", frappe.STANDARD_USERS],
			[SUPPORT_EXPIRY_FIELD, "is", "set"],
			[SUPPORT_EXPIRY_FIELD, "<", now_datetime()],
		],
		pluck="name",
	)
	for user in expired:
		disable_expired_support_user(user)
	# Test transactions roll back with the class; never commit inside them.
	if expired and not frappe.flags.in_test:
		frappe.db.commit()


def disable_expired_support_user(user: str) -> None:
	"""Kill one support account: disable + delete every session row."""
	if not frappe.db.exists("User", user):
		return
	frappe.db.set_value("User", user, "enabled", 0, update_modified=False)
	# tabSessions is a bare table (no DocType meta) — frappe.qb, not get_all.
	sessions = frappe.qb.DocType("Sessions")
	for sid in (
		frappe.qb.from_(sessions).where(sessions.user == user).select(sessions.sid).run(pluck=True)
	):
		frappe.db.delete("Sessions", {"sid": sid})
		frappe.cache.hdel("session", sid)
