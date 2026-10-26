"""Single source of truth for the Gemora 360 staff persona catalog.

A persona is a Role Profile with a curated role bundle. Assigning the profile
to a User is how the Team Hub grants access (Frappe re-materializes the user's
whole role table from the profile on every User save — the profile IS the
source of truth for a persona's permissions).

This module owns:

- ``ROLE_PROFILE_CATALOG`` — every persona the platform ships: its role
  bundle, assignment tier, UI label, client-facing description and
  landing-route hint.
- ``sync_catalog_profiles`` — the idempotent exact-set upsert used by BOTH
  ``install.create_core_role_profiles`` (fresh sites) and the migration
  patch (existing sites). Catalog-owned profiles are kept exactly as defined
  here; profiles outside the catalog are never touched.

Tiers (who may assign the persona):

- ``desk``   — platform-only personas (Gemora-branded); requires
  ``services.permissions.can_grant_desk_roles`` (desk tier / Administrator).
- ``admin``  — the customer owner persona ("Admin User" role); requires
  the admin tier (Admin User, System Manager, Administrator — Gemora
  aliases included). No customer persona bundles a desk or platform role.
- ``standard`` — everything else; any ``staff.manage`` holder (Store
  Managers included) may assign. Every store persona bundles Employee +
  Employee Self Service so the whole staff reaches the employee portal.

Note: a standalone Role named "Bench Jeweler" also exists (v1_2 patch) —
it is distinct from the Role Profile that was formerly in this catalog.

Labels vs names:
  ``name`` = the DB key (Role Profile name), never renamed.
  ``label`` = human-friendly UI display name.
  The frontend renders ``label`` everywhere; API calls use ``name``.
"""

from __future__ import annotations

import frappe

TIER_DESK = "desk"
TIER_ADMIN = "admin"
TIER_STANDARD = "standard"

# name -> {"label", "roles", "tier", "description", "landing", "sort"}
# Standard (store) personas first, then admin, then desk.
# Every standard-tier persona bundles Employee + Employee Self Service
# so the employee portal is always reachable.
ROLE_PROFILE_CATALOG: dict[str, dict] = {
	"Store Manager": {
		"label": "Store Manager",
		"roles": (
			"Store Manager", "Sales Manager", "POS Manager", "Stock Manager",
			"Leave Approver", "Expense Approver", "Employee", "Employee Self Service",
		),
		"tier": TIER_STANDARD,
		"description": "Runs the store, approves leave & expenses",
		"landing": "/",
		"sort": 1,
	},
	"Sales": {
		"label": "POS Cashier",
		"roles": ("Sales User", "Employee", "Employee Self Service"),
		"tier": TIER_STANDARD,
		"description": "Rings sales and processes payments at the register",
		"landing": "/terminal",
		"sort": 2,
	},
	"Inventory": {
		"label": "Inventory & Stock",
		"roles": (
			"Stock User", "Stock Manager", "Item Manager",
			"Employee", "Employee Self Service",
		),
		"tier": TIER_STANDARD,
		"description": "Manages stock, vault, counts & transfers",
		"landing": "/inventory",
		"sort": 3,
	},
	"HR": {
		"label": "HR & People Ops",
		"roles": (
			"HR Manager", "HR User", "Leave Approver", "Expense Approver",
			"Employee", "Employee Self Service",
		),
		"tier": TIER_STANDARD,
		"description": "Attendance, leave approvals & employee onboarding",
		"landing": "/",
		"sort": 4,
	},
	# The customer's owner-admin: every SPA business module + Team
	# management, but NO desk and NO System Manager — the platform
	# equivalent lives in the desk-tier Gemora personas below. The bundle
	# carries the "Admin User" ROLE itself: assigning this persona IS the
	# admin grant (holder becomes admin-tier, builder included).
	"Admin User": {
		"label": "Owner / Admin",
		"roles": (
			"Admin User", "Sales Manager", "POS Manager", "Stock Manager",
			"Item Manager", "Accounts Manager", "Purchase Manager", "HR Manager",
			"Employee", "Employee Self Service",
		),
		"tier": TIER_ADMIN,
		"description": "Full access — store owner level",
		"landing": "/",
		"sort": 5,
	},
	# Desk tier from here down: platform (Gemora team) personas. Bundled
	# System Manager is what makes /app usable — a bare desk role has
	# entry but no DocPerms.
	"Gemora Super Admin": {
		"label": "Gemora Super Admin",
		"roles": ("Gemora Super Admin", "Gemora Admin", "System Manager"),
		"tier": TIER_DESK,
		"description": "Platform owner (Desk tier)",
		"landing": "/app",
		"sort": 6,
	},
	"Gemora Developer": {
		"label": "Gemora Developer",
		"roles": ("Gemora Developer", "System Manager"),
		"tier": TIER_DESK,
		"description": "Platform developer (Desk tier)",
		"landing": "/app",
		"sort": 7,
	},
}

# Profiles removed in v1_6 simplification. The migration patch reassigns
# users from these to the target profile, then deletes the Role Profile doc.
# Kept here so the patch and any diagnostic tooling can reference the map.
DEPRECATED_PROFILE_MAP: dict[str, str | None] = {
	"Jewelry Sales Consultant": "Sales",
	"Bench Jeweler": "Sales",
	"Bookkeeper & Accounts": "Admin User",
	"Accounts": "Admin User",
	"Purchase": "Admin User",
	"Manufacturing": None,
	"Inventory & Vault Custodian": "Inventory",
	"Gemora Executive Admin": "Gemora Super Admin",
	# Pre-catalog leftover flagged as a custom persona (Script Manager +
	# legacy Super Admin role inside) — tenant-visible junk, removed v1_6.
	"Super User": "Store Manager",
}


def get_catalog() -> dict[str, dict]:
	"""The full catalog, keyed by Role Profile name (copy-safe view)."""
	return {name: dict(spec) for name, spec in ROLE_PROFILE_CATALOG.items()}


def get_catalog_profile(name: str) -> dict | None:
	"""Catalog spec for ``name``, or None when the profile is not ours."""
	spec = ROLE_PROFILE_CATALOG.get(name)
	return dict(spec) if spec else None


def get_label(name: str) -> str:
	"""UI-friendly label for a catalog profile, falling back to ``name``."""
	spec = ROLE_PROFILE_CATALOG.get(name)
	return spec["label"] if spec else name


def persona_requires_desk_grant(name: str) -> bool:
	"""True when assigning ``name`` needs the desk-grant right."""
	spec = ROLE_PROFILE_CATALOG.get(name)
	return bool(spec and spec["tier"] == TIER_DESK)


def persona_requires_admin(name: str) -> bool:
	"""True when assigning ``name`` needs the admin tier."""
	spec = ROLE_PROFILE_CATALOG.get(name)
	return bool(spec and spec["tier"] == TIER_ADMIN)


def _is_admin_tier(user: str | None = None) -> bool:
	"""Admin tier via raw roles expanded by ROLE_ALIASES (Gemora passes).

	"Admin User" is the customer owner role — the SPA-admin counterpart of
	the platform's System Manager. ``user=None`` means the session user (the
	hub's create/update paths rely on that — never a "not logged in" answer).
	"""
	from arijentek_core.services.permissions import _user_roles

	user = user or frappe.session.user
	if not user or user == "Guest":
		return False
	if user == "Administrator":
		return True
	return bool(_user_roles(user) & {"System Manager", "Administrator", "Admin User"})


def get_visible_personas(user: str | None = None) -> list[dict]:
	"""Catalog personas ``user`` may assign, catalog sort order.

	Desk personas need the desk-grant right; admin personas need the admin
	tier; everything else is visible to any ``staff.manage`` holder.
	"""
	from arijentek_core.services.permissions import can_grant_desk_roles

	user = user or frappe.session.user
	show_desk = can_grant_desk_roles(user)
	show_admin = _is_admin_tier(user)

	personas = []
	for name, spec in ROLE_PROFILE_CATALOG.items():
		if spec["tier"] == TIER_DESK and not show_desk:
			continue
		if spec["tier"] == TIER_ADMIN and not show_admin:
			continue
		personas.append({"name": name, **spec})
	return sorted(personas, key=lambda p: p["sort"])


def sync_catalog_profiles() -> list[str]:
	"""Exact-set upsert of catalog-owned Role Profiles. Idempotent.

	Creates profiles that are missing, fixes role bundles that drifted, and
	re-saves users assigned to changed profiles so Frappe's
	``populate_role_profile_roles`` re-materializes their roles (a profile
	edit alone does not propagate until the User doc is saved). Returns the
	names of the profiles that changed (empty on a second run). Profiles
	outside the catalog are never touched; existing Role records are never
	modified.
	"""
	if not frappe.db.exists("DocType", "Role Profile"):
		return []

	_ensure_catalog_roles()

	changed: list[str] = []
	for name, spec in ROLE_PROFILE_CATALOG.items():
		desired = set(spec["roles"])
		is_new = not frappe.db.exists("Role Profile", name)
		if is_new:
			doc = frappe.new_doc("Role Profile")
			doc.role_profile = name
		else:
			current = set(
				frappe.get_all(
					"Has Role",
					filters={"parent": name, "parenttype": "Role Profile"},
					pluck="role",
				)
			)
			if current == desired:
				continue
			doc = frappe.get_doc("Role Profile", name)
			doc.set("roles", [])

		for role in spec["roles"]:
			if frappe.db.exists("Role", role):
				doc.append("roles", {"role": role})

		if is_new:
			doc.insert(ignore_permissions=True)
		else:
			doc.save(ignore_permissions=True)
		# RoleProfile.on_update queue_action()s (update_all_users) and defers
		# the doc unlock to the enqueued job — a rolled-back test transaction
		# never enqueues it, and the orphaned lock file would fail every later
		# save of this name (including other processes). Unlock it ourselves
		# in test context; real runs keep the deferred-unlock semantics.
		if frappe.flags.in_test or getattr(doc, "is_locked", False):
			doc.unlock()
		changed.append(name)

	if changed:
		frappe.logger().info("role_profile_catalog: synced %s", ", ".join(changed))
		_resave_users_of_profiles(changed)

	return changed


def _ensure_catalog_roles() -> None:
	"""Create Role records the catalog references but the site lacks.

	Bootstrap only — existing Role records are never modified (desk_access
	and friends belong to fixtures/patches, not this catalog).
	"""
	referenced = {r for spec in ROLE_PROFILE_CATALOG.values() for r in spec["roles"]}
	for role in sorted(referenced):
		if frappe.db.exists("Role", role):
			continue
		doc = frappe.new_doc("Role")
		doc.role_name = role
		doc.desk_access = 0
		doc.insert(ignore_permissions=True)
		frappe.logger().info("role_profile_catalog: created missing Role %s", role)


def _resave_users_of_profiles(profile_names: list[str]) -> None:
	"""Re-save users assigned to ``profile_names`` so roles re-materialize.

	Runs elevated (Administrator): the desk-role guard and plan limits must
	not block a catalog sync, and re-saving adds no users.
	"""
	users = set(
		frappe.get_all(
			"User Role Profile",
			filters={"parenttype": "User", "role_profile": ("in", profile_names)},
			pluck="parent",
		)
	)
	users |= set(
		frappe.get_all(
			"User",
			filters={"role_profile_name": ("in", profile_names)},
			pluck="name",
		)
	)
	users.discard("Guest")
	users.discard("Administrator")

	acting_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		for user in sorted(users):
			try:
				frappe.get_doc("User", user).save(ignore_permissions=True)
				frappe.clear_cache(user=user)
			except Exception:
				frappe.log_error(f"role_profile_catalog: failed to re-save user {user}")
	finally:
		frappe.set_user(acting_user)
