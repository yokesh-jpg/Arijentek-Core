"""WS-9 RBAC single source — permission matrix, tiers and role aliases.

The frontend ``utils/permissions.js`` and this module must agree on the
role list for each permission key (ROADMAP WS-9 exit c). This is the
backend half:

- ``PERMISSIONS`` — action-key → roles matrix (``inventory.*`` plus the
  general keys). Gate endpoints with ``require_permission(key)``.
- ``TIER_ROLES`` — employee/manager/admin tier mirror used for parity
  documentation and future API-side tier checks.
- ``ROLE_ALIASES`` — Zevar custom roles expanded to their canonical
  equivalents (mirror of ``normalizeRoles`` in the frontend).

Admins (``System Manager`` / ``Administrator``) always pass. Unknown keys
deny by default (fail-closed). New endpoints should gate with
``require_permission("<key>")`` instead of hand-rolling
``frappe.only_for([...])``.
"""

from __future__ import annotations

import frappe
from frappe import _

# <key> -> roles allowed. Mirrors frontend utils/permissions.js
# PERMISSIONS. Keep the two in lockstep (ROADMAP WS-9 exit c).
PERMISSIONS: dict[str, tuple[str, ...]] = {
	"inventory.view": (
		"System Manager", "Administrator", "Store Manager",
		"Stock Manager", "Inventory Manager", "Sales Manager",
	),
	"inventory.adjust": (
		"System Manager", "Administrator", "Store Manager",
		"Stock Manager", "Inventory Manager",
	),
	"inventory.transfer": (
		"System Manager", "Administrator", "Store Manager",
		"Stock Manager", "Inventory Manager",
	),
	"inventory.receive": (
		"System Manager", "Administrator", "Store Manager",
		"Stock Manager", "Inventory Manager",
	),
	"inventory.ownership": (
		"System Manager", "Administrator", "Store Manager",
	),
	"inventory.cycle_count": (
		"System Manager", "Administrator", "Store Manager",
		"Stock Manager", "Inventory Manager",
	),
	"inventory.count_signoff": (
		"System Manager", "Administrator", "Store Manager",
	),
	"inventory.variance_approve": (
		"System Manager", "Administrator", "Store Manager", "Sales Manager",
	),
	"inventory.tag_print": (
		"System Manager", "Administrator", "Store Manager",
		"Stock Manager", "Inventory Manager", "Sales User",
	),
	"inventory.tag_assign": (
		"System Manager", "Administrator", "Store Manager",
		"Stock Manager", "Inventory Manager",
	),
	"inventory.search.all_stores": (
		"System Manager", "Administrator",
	),
	"inventory.audit_log": (
		"System Manager", "Administrator", "Store Manager",
	),
	"finance.view": (
		"System Manager", "Administrator", "Accounts Manager", "Store Manager",
	),
	"vendors.view": (
		"System Manager", "Administrator", "Store Manager", "Stock Manager",
		"Inventory Manager", "Purchase Manager",
	),
	"reports.view": (
		"System Manager", "Administrator", "Store Manager",
		"Sales Manager", "Accounts Manager",
	),
	"sales.void": (
		"System Manager", "Administrator", "Store Manager", "Sales Manager",
	),
	"discount.override": (
		"System Manager", "Administrator", "Store Manager", "Sales Manager",
	),
	"employee.manage": (
		"System Manager", "Administrator", "Store Manager", "HR Manager",
	),
	"pricing.approve": (
		"System Manager", "Administrator", "Store Manager", "Sales Manager",
	),
	"settings.manage": (
		"System Manager", "Administrator", "Store Manager",
	),
	"settings.read": (
		"System Manager", "Administrator", "Store Manager",
		"Sales Manager", "Accounts Manager", "POS Manager",
	),
	"settings.stores": (
		"System Manager", "Administrator", "Store Manager",
	),
	"settings.finance": (
		"System Manager", "Administrator", "Accounts Manager", "Store Manager",
	),
	"settings.users": (
		"System Manager", "Administrator",
	),
	"settings.hardware": (
		"System Manager", "Administrator", "Store Manager",
	),
	"settings.system": (
		"System Manager", "Administrator",
	),
	# Team hub: create/edit staff (User + Employee + persona). Admins and
	# Store Managers only — HR Manager deliberately absent (the hub is a
	# system-access surface, not an HR records surface). "Admin User" is
	# the customer owner tier (patches v1_5).
	"staff.manage": (
		"System Manager", "Administrator", "Admin User", "Store Manager",
	),
}

# Legacy alias: the matrix was inventory-only before the general keys
# were merged in. Kept so existing importers keep working.
INVENTORY_PERMISSIONS = PERMISSIONS

# employee/manager/admin tiers. Mirrors frontend REPORT_TIER_ROLES.
# "Admin User" is the customer owner role — the SPA-admin counterpart of
# the platform's Gemora Admin (patches v1_5/restructure_personas).
TIER_ROLES: dict[str, tuple[str, ...]] = {
	"admin": ("Administrator", "System Manager", "Accounts Manager", "Admin User", "Gemora Admin", "Gemora Super Admin", "Gemora Developer"),
	"manager": (
		"Store Manager", "Sales Manager", "Stock Manager", "Inventory Manager",
		"HR Manager", "HR User", "POS Manager",
	),
	"employee": (
		"Sales User", "Employee", "Employee Self Service", "Sales Associate",
		"Technician", "Cashier", "POS User",
	),
}

# Zevar custom roles → canonical equivalents. Mirrors frontend
# ROLE_ALIASES / normalizeRoles. An alias grants the canonical role's
# full capability set.
ROLE_ALIASES: dict[str, str] = {
	"Gemora Cashier": "Sales User",
	"Gemora Inventory": "Inventory Manager",
	"Gemora Manager": "Store Manager",
	# Shared-terminal accounts: alias grants cashier-class capabilities while
	# the SPA confines the session to /terminal (most restrictive wins).
	"POS Terminal": "Sales User",
	# UI admin + desk tiers expand to System Manager: full capability inside
	# the SPA (and the desk, for the two desk roles, via their role profiles).
	# The alias reaches only this module's helpers — raw ``frappe.only_for``
	# / ``frappe.get_roles`` gates do NOT expand it (see api/pos.py).
	# Customer owners use the real "Admin User" role instead (v1_5) — it is
	# listed explicitly in _ADMIN_ROLES / TIER_ROLES / PERMISSIONS and in the
	# raw only_for gates, never aliased.
	"Gemora Admin": "System Manager",
	"Gemora Super Admin": "System Manager",
	"Gemora Developer": "System Manager",
}

_ADMIN_ROLES = frozenset(("System Manager", "Administrator", "Admin User"))

# Roles that unlock the Frappe Desk (/app). Everyone else — including plain
# System Manager holders such as tenant owners — stays in the SPA
# (api/auth.block_desk_access). Kept here so auth, user_info and the
# assignment guard share one definition.
DESK_ROLES = frozenset(("Gemora Super Admin", "Gemora Developer"))

# Platform super-grants: assignable only by Gemora itself, never from a
# tenant session (User.validate firewall — services/internal_access.py).
# "Admin User" is deliberately NOT here — it is the customer owner grant,
# which the tenant's own admin tier may hand over. The persona-bundle
# firewall in custom_personas uses a broader set (bundles vs user
# assignment are different surfaces).
PLATFORM_ROLES = frozenset({
	"System Manager",
	"Administrator",
	"Gemora Super Admin",
	"Gemora Developer",
	"Gemora Admin",
})


def _normalize_roles(roles: set[str] | tuple | list | None) -> set[str]:
	"""Expand Zevar aliases; originals are preserved."""
	roles = set(roles or ())
	for role in list(roles):
		canonical = ROLE_ALIASES.get(role)
		if canonical:
			roles.add(canonical)
	return roles


def _user_roles(user: str | None) -> set[str]:
	if not user or user == "Guest":
		return set()
	return _normalize_roles(frappe.get_roles(user))


def has_permission(key: str, user: str | None = None) -> bool:
	"""True if ``user`` may perform the ``<key>`` action.

	Admins always pass. Unknown keys deny by default (fail-closed).
	"""
	user = user or frappe.session.user
	roles = _user_roles(user)
	if roles & _ADMIN_ROLES:
		return True
	allowed = PERMISSIONS.get(key)
	if not allowed:
		return False
	return bool(roles & set(allowed))


def require_permission(key: str, user: str | None = None) -> None:
	"""Throw ``PermissionError`` if the user lacks ``<key>``."""
	if not has_permission(key, user):
		frappe.throw(
			_("You do not have permission to perform this action ({0}).").format(key),
			frappe.PermissionError,
		)


def has_any_permission(keys, user: str | None = None) -> bool:
	"""True if ``user`` may perform ANY of ``keys`` (admins always pass)."""
	return any(has_permission(key, user) for key in keys)


def get_permissions_for_user(user: str | None = None) -> dict[str, bool]:
	"""Every key -> bool, for client bootstrapping / debugging."""
	user = user or frappe.session.user
	return {key: has_permission(key, user) for key in PERMISSIONS}


def is_platform_site() -> bool:
	"""True when this site is a Gemora platform (internal) site.

	Desk-tier personas exist on every site but are only assignable and
	visible in the Team UI on platform sites — customer sites never show
	them, site Administrator included. Assigning desk access is a platform
	operation, never a tenant one.
	"""
	if getattr(frappe.flags, "is_platform_site", None) is not None:
		return bool(frappe.flags.is_platform_site)
	if not frappe.db.exists("DocType", "Zevar Business Settings"):
		return False
	if not frappe.get_meta("Zevar Business Settings").has_field("is_platform_site"):
		return False
	return bool(frappe.db.get_single_value("Zevar Business Settings", "is_platform_site"))


def can_grant_desk_roles(user: str | None = None) -> bool:
	"""True if ``user`` may assign DESK_ROLES to other users.

	Desk access is platform-controlled: the desk tier is grantable only on
	Gemora platform sites (Business Settings → Gemora Platform Site), and
	there only by current desk-role holders or the site Administrator. A
	tenant Administrator on a customer site never sees the desk tier — a
	Gemora Admin must never be able to self-promote to it.
	"""
	if not is_platform_site():
		return False
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	if not user or user == "Guest":
		return False
	return bool(set(frappe.get_roles(user)) & DESK_ROLES)


def require_desk_grant_right(user: str | None = None) -> None:
	"""Throw ``PermissionError`` unless ``user`` may assign DESK_ROLES."""
	if not can_grant_desk_roles(user):
		frappe.throw(
			_("Desk personas may only be assigned on Gemora platform sites by a desk-role holder."),
			frappe.PermissionError,
		)


def guard_user_desk_roles(doc, method: str | None = None) -> None:
	"""doc_events: User.validate — enforce the desk-grant right on every write surface.

	The whitelisted SPA endpoints guard their own payloads, but a System
	Manager (e.g. a tenant owner) can also reach the User doctype through
	the Frappe desk or ``/api/resource/User`` — including via Role Profiles
	(``role_profiles`` / legacy ``role_profile_name``), which Frappe
	materializes into ``doc.roles`` earlier in the same validate pass. One
	diff against the pre-save roles therefore covers direct role edits,
	profile assignment, and re-syncs after a profile is edited to include
	a desk role.
	"""
	if frappe.session.user == "Administrator":
		return

	before = doc.get_doc_before_save()
	existing = {r.role for r in (before.get("roles") or [])} if before else set()
	current = {r.role for r in (doc.get("roles") or [])}
	if (existing ^ current) & DESK_ROLES:
		require_desk_grant_right()


# ── Legacy inventory names (pre-merge API) ──────────────────────────────────


def has_inventory_permission(key: str, user: str | None = None) -> bool:
	"""Legacy alias of :func:`has_permission` (inventory.* keys)."""
	return has_permission(key, user)


def require_inventory_permission(key: str, user: str | None = None) -> None:
	"""Legacy alias of :func:`require_permission` (inventory.* keys)."""
	require_permission(key, user)


def get_inventory_permissions_for_user(user: str | None = None) -> dict[str, bool]:
	"""Legacy alias of :func:`get_permissions_for_user` (inventory.* keys)."""
	user = user or frappe.session.user
	return {key: has_permission(key, user) for key in PERMISSIONS if key.startswith("inventory.")}
