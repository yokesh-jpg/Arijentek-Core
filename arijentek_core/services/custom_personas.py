"""Custom personas — Role Profiles built in the Team Hub.

Curated personas live in ``role_profile_catalog.ROLE_PROFILE_CATALOG``; custom
personas are Role Profile docs flagged ``custom_is_custom_persona`` (custom
fields synced by ``custom_fields.py``), with description + landing route
stored alongside. Tier is NEVER stored: ``compute_persona_tier`` derives it
from the role bundle at read time, so editing a bundle can never leave a
stale tier behind.

Save/delete are admin-tier gated (the builder is admin-only); a bundle
containing desk roles additionally requires the desk-grant right. When a
bundle changes, assigned users are re-saved — elevated via ``session_as``
because this runs in HTTP request context, never a bare ``frappe.set_user``
(that clobbers the caller's session; see utils/session_elevation.py).

Platform-role firewall (v1_5): a customer admin (Admin User tier) must
never assemble a platform-granting bundle. Roles in ``_PLATFORM_ROLES`` —
and any role prefixed ``"Gemora "`` — are hidden from the builder options
and rejected server-side on save, unless the caller holds the desk-grant
right (platform staff).
"""

from __future__ import annotations

import frappe
from frappe import _

from arijentek_core.services.permissions import (
	DESK_ROLES,
	_normalize_roles,
	can_grant_desk_roles,
	require_permission,
)
from arijentek_core.services.role_profile_catalog import (
	ROLE_PROFILE_CATALOG,
	TIER_ADMIN,
	TIER_DESK,
	TIER_STANDARD,
	_is_admin_tier,
)
from arijentek_core.utils.session_elevation import session_as

# Landing routes a custom persona may declare (mirrors the catalog's set).
PERSONA_LANDING_ROUTES = ("/", "/terminal", "/inventory", "/repairs", "/reports", "/app")

_EXCLUDED_BUILDER_ROLES = ("Guest", "All")

# Platform-only grants, never bundleable by a customer admin: System Manager
# and Administrator are platform super-grants, Admin User IS the admin grant
# itself (assigned via the Admin User persona / provisioning, not bundles),
# Gemora Admin is the platform write tier, and DESK_ROLES are desk-only.
# The "Gemora " prefix guard below also catches Gemora Cashier / Inventory /
# Manager — the whole prefix is platform territory.
_PLATFORM_ROLES = frozenset(DESK_ROLES | {"System Manager", "Administrator", "Gemora Admin", "Admin User"})


def _is_platform_role(role: str) -> bool:
    return role in _PLATFORM_ROLES or (role or "").startswith("Gemora ")


# ── tier + specs ─────────────────────────────────────────────────────────────


def compute_persona_tier(role_names) -> str:
	"""desk > admin > standard, derived from the raw role bundle.

	Admin set mirrors role_profile_catalog._is_admin_tier — "Admin User" is
	the customer owner grant and makes a bundle admin-tier.
	"""
	roles = set(role_names or [])
	if roles & DESK_ROLES:
		return TIER_DESK
	if _normalize_roles(roles) & {"System Manager", "Administrator", "Admin User"}:
		return TIER_ADMIN
	return TIER_STANDARD


def _custom_fields_ready() -> bool:
	return bool(frappe.get_meta("Role Profile").has_field("custom_is_custom_persona"))


def get_custom_persona(name: str) -> dict | None:
	"""Unfiltered spec for one custom persona (assignability checks tier itself)."""
	return get_custom_persona_map().get(name)


def get_custom_persona_map() -> dict[str, dict]:
	"""All custom personas unfiltered (name → spec), for lookups.

	Mirrors get_catalog_profile: known-ness checks must not depend on the
	viewer's tier — only visibility (get_custom_personas) does.
	"""
	if not _custom_fields_ready():
		return {}
	docs = frappe.get_all(
		"Role Profile",
		filters={"custom_is_custom_persona": 1},
		fields=["name", "custom_persona_description", "custom_landing_route"],
		order_by="name asc",
	)
	roles_by_profile = _roles_of_profiles([d.name for d in docs])
	return {
		d.name: {
			"name": d.name,
			"label": d.name,
			"roles": sorted(set(roles_by_profile.get(d.name, []))),
			"tier": compute_persona_tier(roles_by_profile.get(d.name, [])),
			"description": d.custom_persona_description or "",
			"landing": d.custom_landing_route or "/",
			"sort": 100 + i,
			"custom": True,
		}
		for i, d in enumerate(docs)
	}


def _roles_of_profiles(names: list[str]) -> dict[str, list[str]]:
	out: dict[str, list[str]] = {}
	if not names:
		return out
	for row in frappe.get_all(
		"Has Role",
		filters={"parenttype": "Role Profile", "parent": ("in", names)},
		fields=["parent", "role"],
	):
		out.setdefault(row.parent, []).append(row.role)
	return out


def get_custom_personas(user: str | None = None) -> list[dict]:
	"""Custom personas ``user`` may see/assign, tier-filtered like the catalog."""
	custom_map = get_custom_persona_map()
	out = []
	for persona in custom_map.values():
		tier = persona["tier"]
		if tier == TIER_DESK and not can_grant_desk_roles(user):
			continue
		if tier == TIER_ADMIN and not _is_admin_tier(user):
			continue
		out.append(persona)
	return out


# ── builder ──────────────────────────────────────────────────────────────────


def _require_builder_right() -> None:
	require_permission("staff.manage")
	if not _is_admin_tier():
		frappe.throw(
			_("Custom personas may only be managed by an administrator."),
			frappe.PermissionError,
		)


def get_persona_builder_options() -> dict:
	"""Role picker + landing routes for the persona builder (admin tier).

	Platform roles (super-grants, the admin grant itself, Gemora-prefixed
	roles) appear only for desk-grant holders — hiding is UX; ``save_custom_persona``
	enforces the same rule server-side.
	"""
	_require_builder_right()
	show_platform = can_grant_desk_roles()
	roles = [
		r
		for r in frappe.get_all(
			"Role",
			filters={"name": ("not in", list(_EXCLUDED_BUILDER_ROLES))},
			fields=["name", "desk_access", "disabled"],
			order_by="name asc",
		)
		if show_platform or not _is_platform_role(r.name)
	]
	return {
		"roles": [
			{
				"name": r.name,
				"desk_access": bool(r.desk_access) or r.name in DESK_ROLES,
				"disabled": bool(r.disabled),
			}
			for r in roles
		],
		"landings": list(PERSONA_LANDING_ROUTES),
	}


def save_custom_persona(payload: dict) -> dict:
	"""Create or update a custom persona (exact-set bundle, admin tier only)."""
	_require_builder_right()
	if not _custom_fields_ready():
		frappe.throw(_("Run bench migrate first — persona fields are missing."))

	name = (payload.get("name") or "").strip()
	description = (payload.get("description") or "").strip()
	landing = (payload.get("landing") or "/").strip() or "/"
	roles = _clean_role_list(payload.get("roles"))

	if not name:
		frappe.throw(_("Persona name is required."))
	if len(name) > 140:
		frappe.throw(_("Persona name must be 140 characters or fewer."))
	if landing not in PERSONA_LANDING_ROUTES:
		frappe.throw(_("Invalid landing route."))
	if not roles:
		frappe.throw(_("Pick at least one role for the persona."))
	unknown = [r for r in roles if not frappe.db.exists("Role", r)]
	if unknown:
		frappe.throw(_("Unknown roles: {0}").format(", ".join(unknown)))
	if set(roles) & DESK_ROLES:
		from arijentek_core.services.permissions import require_desk_grant_right

		require_desk_grant_right()
	# Platform-role firewall (v1_5): without the desk-grant right a caller
	# cannot bundle super-grants (System Manager / Administrator), the admin
	# grant itself (Admin User), or any Gemora-prefixed platform role.
	platform_hits = sorted(r for r in roles if _is_platform_role(r))
	if platform_hits and not can_grant_desk_roles():
		frappe.throw(
			_("Platform roles cannot be bundled in a custom persona: {0}").format(
				", ".join(platform_hits)
			),
			frappe.PermissionError,
		)
	if name in ROLE_PROFILE_CATALOG:
		frappe.throw(
			_("{0} is a curated persona — its bundle is managed by the Team catalog.").format(name)
		)

	existed = bool(frappe.db.exists("Role Profile", name))
	if existed and not frappe.db.get_value("Role Profile", name, "custom_is_custom_persona"):
		frappe.throw(
			_("{0} already exists as a non-custom Role Profile.").format(name), frappe.DuplicateEntryError
		)

	_doc, old_roles = _upsert_profile(name, roles, description, landing)

	if existed and old_roles != set(roles):
		_resave_assigned_users(name)

	return {
		"name": name,
		"roles": sorted(set(roles)),
		"tier": compute_persona_tier(roles),
		"created": not existed,
	}


def _clean_role_list(value) -> list[str]:
	"""str|list → ordered, de-duplicated, stripped list."""
	if isinstance(value, str):
		value = value.split(",")
	seen, out = set(), []
	for role in value or []:
		role = (role or "").strip()
		if role and role not in seen:
			seen.add(role)
			out.append(role)
	return out


def _upsert_profile(name: str, roles: list[str], description: str, landing: str):
	"""Exact-set save with one retry on stale timestamps (RoleProfile locks)."""
	last_error = None
	for _attempt in range(2):
		try:
			if frappe.db.exists("Role Profile", name):
				doc = frappe.get_doc("Role Profile", name)
				old_roles = {r.role for r in doc.roles}
			else:
				doc = frappe.new_doc("Role Profile")
				doc.role_profile = name
				old_roles = set()
			doc.set("roles", [])
			for role in roles:
				doc.append("roles", {"role": role})
			doc.custom_is_custom_persona = 1
			doc.custom_persona_description = description
			doc.custom_landing_route = landing
			doc.save(ignore_permissions=True)
			# Same deferred-unlock hazard as sync_catalog_profiles: test
			# transactions never reach the queued unlock job, and the
			# orphaned lock would fail every later save of this name.
			if frappe.flags.in_test:
				doc.unlock()
			return doc, old_roles
		except frappe.TimestampMismatchError as e:
			# Stale in-memory doc (RoleProfile locks aggressively) — the next
			# iteration re-fetches fresh; never roll back the caller's work.
			last_error = e
	raise last_error


def _resave_assigned_users(profile_name: str) -> None:
	"""Re-save users holding the persona so Frappe re-materializes roles.

	Runs in request context → elevation MUST go through ``session_as``.
	Administrator session is also what the desk-role guard skips.
	"""
	users = set(
		frappe.get_all(
			"User Role Profile",
			filters={"role_profile": profile_name, "parenttype": "User"},
			pluck="parent",
		)
	)
	legacy = frappe.get_all(
		"User", filters={"role_profile_name": profile_name}, pluck="name"
	)
	users.update(legacy)
	for user in users:
		if user in ("Guest", "Administrator"):
			continue
		with session_as("Administrator"):
			frappe.get_doc("User", user).save(ignore_permissions=True)
		frappe.clear_cache(user=user)


def delete_custom_persona(name: str) -> dict:
	"""Delete a custom persona; blocked while any user still holds it."""
	_require_builder_right()
	if name in ROLE_PROFILE_CATALOG:
		frappe.throw(
			_("{0} is a curated persona and cannot be deleted here.").format(name)
		)
	if not frappe.db.exists("Role Profile", name):
		frappe.throw(_("Persona {0} not found.").format(name), frappe.DoesNotExistError)
	if not frappe.db.get_value("Role Profile", name, "custom_is_custom_persona"):
		frappe.throw(_("{0} is not a custom persona.").format(name))

	assigned = set(
		frappe.get_all(
			"User Role Profile",
			filters={"role_profile": name, "parenttype": "User"},
			pluck="parent",
		)
	)
	legacy = frappe.get_all("User", filters={"role_profile_name": name}, pluck="name")
	assigned.update(legacy)
	if assigned:
		frappe.throw(
			_("Cannot delete {0} — assigned to user(s): {1}. Change their persona first.").format(
				name, ", ".join(sorted(assigned))
			)
		)

	frappe.delete_doc("Role Profile", name, force=True, ignore_permissions=True)
	return {"deleted": name}
