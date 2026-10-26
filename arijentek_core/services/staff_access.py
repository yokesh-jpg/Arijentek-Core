"""Team Hub business logic — one page, one call, stacked personas.

``api/staff_access.py`` is the thin whitelisted layer; everything real
lives here. The hub collapses what Frappe spreads across User / Employee /
Role / Role Profile into a single persona-driven flow:

- ``create_staff_member`` — User + Employee (+ optional store allocation)
  in ONE transaction; one or more personas (Role Profiles) as the single
  source of the user's roles (Frappe re-materializes ``doc.roles`` as the
  union of all profiles on every User save).
- ``get_staff_overview`` — the whole page's data in one batched payload.
- ``update_staff_member`` — re-persona / enable / disable / password reset
  with tier protections (managers may never mutate admin/desk accounts).

Personas come from the curated catalog (role_profile_catalog) plus custom
personas built in-app (custom_personas). Access model (locked with the
client): ``staff.manage`` (admins + Store Managers). Standard personas are
assignable by any of them; admin-tier personas (bundle contains System
Manager) need the admin tier; desk-tier personas additionally need
``can_grant_desk_roles``. A persona STACK is gated by its most privileged
member.
"""

from __future__ import annotations

import secrets
import string

import frappe
from frappe import _
from frappe.utils import getdate, today, validate_email_address

from arijentek_core.services.custom_personas import get_custom_persona_map, get_custom_personas
from arijentek_core.services.permissions import (
	DESK_ROLES,
	can_grant_desk_roles,
	get_permissions_for_user,
	require_permission,
)
from arijentek_core.services.role_profile_catalog import (
	TIER_ADMIN,
	TIER_DESK,
	TIER_STANDARD,
	_is_admin_tier,
	get_catalog_profile,
	get_label,
	get_visible_personas,
)
from arijentek_core.utils.session_elevation import session_as as _session_as

_PROTECTED_USERS = ("Administrator", "Guest")
_EMPLOYEE_MODES = ("create", "link", "none")

GENDER_OPTIONS = None  # lazily read from the Employee doctype


# ── catalog ──────────────────────────────────────────────────────────────────


def get_catalog_for_user(user: str | None = None) -> list[dict]:
	"""Personas the caller may assign, with role pills and landing hint.

	Curated catalog personas + in-app custom personas, both tier-filtered.
	"""
	personas = []
	for persona in get_visible_personas(user):
		personas.append(
			{
				"name": persona["name"],
				"label": persona.get("label", persona["name"]),
				"roles": list(persona["roles"]),
				"tier": persona["tier"],
				"description": persona["description"],
				"landing": persona["landing"],
				"sort": persona["sort"],
				"custom": False,
			}
		)
	personas.extend(get_custom_personas(user))
	return personas


def _persona_spec(profile_name: str) -> dict | None:
	"""Catalog spec or custom-persona spec for ``profile_name`` (unfiltered)."""
	return get_catalog_profile(profile_name) or get_custom_persona_map().get(profile_name)


def _assert_persona_assignable(profile_name: str, user: str | None = None) -> dict:
	"""Throw unless ``user`` may assign ``profile_name``; return the spec."""
	spec = _persona_spec(profile_name)
	if not spec:
		frappe.throw(
			_("{0} is not an available persona.").format(_(profile_name)),
			frappe.PermissionError,
		)
	require_permission("staff.manage", user)
	if spec["tier"] == TIER_DESK:
		from arijentek_core.services.permissions import require_desk_grant_right

		require_desk_grant_right(user)
	elif spec["tier"] == TIER_ADMIN and not _is_admin_tier(user):
		frappe.throw(
			_("Admin-tier personas may only be assigned by an administrator."),
			frappe.PermissionError,
		)
	return spec


def _normalize_persona_list(value) -> list[str]:
	"""str|list → ordered, de-duplicated persona names (legacy str still works)."""
	if isinstance(value, str):
		value = [value]
	seen, out = set(), []
	for name in value or []:
		name = (name or "").strip()
		if name and name not in seen:
			seen.add(name)
			out.append(name)
	return out


# ── create ───────────────────────────────────────────────────────────────────


def create_staff_member(payload: dict) -> dict:
	"""Create User + Employee + persona stack + store allocation in one call."""
	require_permission("staff.manage")

	# One persona or a stack — Frappe unions all profiles into doc.roles.
	role_profiles = _normalize_persona_list(payload.get("role_profiles") or payload.get("role_profile"))
	if not role_profiles:
		frappe.throw(_("Pick at least one persona."))
	first_name = (payload.get("first_name") or "").strip()
	last_name = (payload.get("last_name") or "").strip()
	email = (payload.get("email") or "").strip().lower()
	password = payload.get("password") or ""
	gender = (payload.get("gender") or "").strip()
	date_of_birth = (payload.get("date_of_birth") or "").strip()
	employee_mode = payload.get("employee_mode") or "create"
	# Optional profile extras carried over from the legacy Settings form (all
	# validated by the User doc itself; absent keys keep today's behavior).
	username = (payload.get("username") or "").strip()
	middle_name = (payload.get("middle_name") or "").strip()
	time_zone = (payload.get("time_zone") or "").strip()
	user_image = (payload.get("user_image") or "").strip()

	for profile in role_profiles:
		_assert_persona_assignable(profile)

	if not first_name:
		frappe.throw(_("First name is required."))
	if not email:
		frappe.throw(_("Email is required."))
	validate_email_address(email, throw=True)
	if frappe.db.exists("User", email):
		frappe.throw(_("A user with email {0} already exists.").format(email))
	if employee_mode not in _EMPLOYEE_MODES:
		frappe.throw(_("Invalid employee mode."))
	if password and len(password) < 6:
		frappe.throw(_("Password must be at least 6 characters."))

	employee_id = None
	if employee_mode == "link":
		employee_id = (payload.get("employee_id") or "").strip()
		if not employee_id or not frappe.db.exists("Employee", employee_id):
			frappe.throw(_("Pick the employee record to link."))
		existing_user = frappe.db.get_value("Employee", employee_id, "user_id")
		if existing_user and existing_user != email:
			frappe.throw(
				_("Employee {0} is already linked to user {1}.").format(employee_id, existing_user)
			)
	elif employee_mode == "create":
		# "none" skips employee validation entirely — there is no employee
		# record to validate (the old else-branch wrongly demanded gender/DOB
		# for none-mode users too).
		_validate_employee_fields(gender, date_of_birth)

	frappe.db.savepoint("staff_create")
	try:
		generated_password = None
		if not password:
			generated_password = _generate_password()
			password = generated_password

		user = frappe.new_doc("User")
		user.email = email
		user.first_name = first_name
		user.middle_name = middle_name or None
		user.last_name = last_name or None
		user.username = username or None
		user.gender = gender or None
		user.birth_date = date_of_birth or None
		user.time_zone = time_zone or None
		user.user_image = user_image or None
		user.new_password = password
		user.send_welcome_email = 0
		# Personas only — never set doc.roles; profiles are the single
		# source of truth and repopulate roles (as a union) on validate.
		for profile in role_profiles:
			user.append("role_profiles", {"role_profile": profile})
		user.insert(ignore_permissions=True)

		if employee_mode == "create":
			employee_id = _insert_employee(payload, email, first_name, last_name, gender, date_of_birth)
		elif employee_mode == "link":
			_link_employee(employee_id, email)

		pos_profiles = payload.get("pos_profiles") or []
		if pos_profiles:
			from arijentek_core.api.store_allocation import _apply_store_allocations

			_apply_store_allocations([{"user_id": email, "pos_profiles": pos_profiles}])
	except Exception:
		# save_point is keyword-only in this Frappe (there is no
		# rollback_to_savepoint method); partial rollback keeps earlier
		# work in the caller's transaction intact.
		frappe.db.rollback(save_point="staff_create")
		raise

	frappe.clear_cache(user=email)

	from arijentek_core.api.auth import get_user_landing_route

	result = {
		"user": email,
		"employee": employee_id,
		"role_profile": role_profiles[0],
		"role_profiles": role_profiles,
		"roles": sorted({r.role for r in frappe.get_doc("User", email).roles}),
		"landing_route": get_user_landing_route(email),
	}
	if generated_password:
		result["generated_password"] = generated_password
	return result


def _validate_employee_fields(gender: str, date_of_birth: str) -> None:
	if not gender:
		frappe.throw(_("Gender is required for the employee record."))
	if gender not in _gender_options():
		frappe.throw(_("Invalid gender option."))
	if not date_of_birth:
		frappe.throw(_("Date of birth is required for the employee record."))
	try:
		dob = getdate(date_of_birth)
	except Exception:
		frappe.throw(_("Date of birth is not a valid date."))
		return
	if dob >= getdate(today()):
		frappe.throw(_("Date of birth must be in the past."))


def _gender_options() -> set[str]:
	"""Valid gender values — Employee.gender is a Link on stock ERPNext but a
	Select on some sites, so read the meta and cache whichever shape applies."""
	global GENDER_OPTIONS
	if GENDER_OPTIONS is None:
		field = frappe.get_meta("Employee").get_field("gender")
		if field.fieldtype == "Link":
			GENDER_OPTIONS = set(frappe.get_all(field.options, pluck="name"))
		else:
			GENDER_OPTIONS = {o.strip() for o in (field.options or "").split("\n") if o.strip()}
	return GENDER_OPTIONS


def _insert_employee(
	payload: dict, email: str, first_name: str, last_name: str, gender: str, date_of_birth: str
) -> str:
	company = _resolve_default_company()
	doc = frappe.new_doc("Employee")
	doc.company = company
	doc.first_name = first_name
	doc.last_name = last_name or None
	doc.user_id = email
	doc.gender = gender
	doc.date_of_birth = date_of_birth
	doc.date_of_joining = payload.get("date_of_joining") or today()
	doc.designation = payload.get("designation") or None
	doc.department = payload.get("department") or None
	doc.default_shift = payload.get("shift_type") or None
	doc.holiday_list = payload.get("holiday_list") or None
	# Optional workflow approvers (payload keys match the legacy Settings form;
	# the Employee fields themselves are shift_request_approver etc.).
	doc.expense_approver = payload.get("expense_approver") or None
	doc.leave_approver = payload.get("leave_approver") or None
	doc.shift_request_approver = payload.get("shift_approver") or None
	if payload.get("mobile"):
		doc.cell_number = payload.get("mobile")
	doc.status = "Active"
	return _elevated_insert(doc)


def _link_employee(employee_id: str, email: str) -> None:
	"""Attach the existing Employee to the new user (elevated: writes user_id)."""
	with _session_as("Administrator"):
		emp = frappe.get_doc("Employee", employee_id)
		emp.user_id = email
		emp.save(ignore_permissions=True)


def _elevated_insert(doc) -> str:
	"""Insert ``doc`` as Administrator, then hand ownership back.

	ERPNext's Employee.on_update writes a User Permission row and checks
	doctype perms as the session user — Store Manager lacks create on User
	Permission, so the insert would die after the Employee itself is valid.
	"""
	acting_user = frappe.session.user
	with _session_as("Administrator"):
		doc.insert(ignore_permissions=True)
	frappe.db.set_value(doc.doctype, doc.name, "owner", acting_user)
	return doc.name


def _resolve_default_company() -> str:
	"""payload company → session-user default → Global Defaults."""
	# Read BEFORE any elevation block — user defaults track the acting user.
	company = (
		frappe.defaults.get_user_default("Company")
		or frappe.db.get_single_value("Global Defaults", "default_company")
	)
	if not company:
		frappe.throw(_("No default company found — set one in Global Defaults first."))
	return company


def _generate_password() -> str:
	"""Readable-but-strong starter password (returned once, never logged)."""
	alphabet = string.ascii_letters + string.digits
	password = "".join(secrets.choice(alphabet) for _ in range(12))
	password += secrets.choice(string.ascii_uppercase)
	password += secrets.choice(string.ascii_lowercase)
	password += secrets.choice(string.digits)
	password += secrets.choice("!@#$%&*")
	chars = list(password)
	secrets.SystemRandom().shuffle(chars)
	return "".join(chars)


# ── overview ─────────────────────────────────────────────────────────────────


def get_staff_overview() -> dict:
	"""The whole Team page in one batched payload (no per-row get_doc)."""
	require_permission("staff.manage")

	# Platform accounts (Administrator, Guest, internal-flagged staff) are
	# never tenant-visible — get_all bypasses permission_query_conditions,
	# so the exclusion is explicit.
	from arijentek_core.services.internal_access import get_internal_user_names

	users = frappe.get_all(
		"User",
		filters={
			"name": ("not in", sorted(set(_PROTECTED_USERS) | set(get_internal_user_names()))),
			"user_type": ("!=", "Website User"),
		},
		fields=["name", "email", "full_name", "enabled", "last_active", "user_image", "role_profile_name"],
		order_by="enabled desc, name asc",
	)
	names = [u.name for u in users]

	roles_by_user: dict[str, list[str]] = {}
	for row in frappe.get_all(
		"Has Role", filters={"parenttype": "User", "parent": ("in", names)}, fields=["parent", "role"]
	):
		roles_by_user.setdefault(row.parent, []).append(row.role)

	profiles_by_user: dict[str, list[str]] = {}
	for row in frappe.get_all(
		"User Role Profile",
		filters={"parenttype": "User", "parent": ("in", names)},
		fields=["parent", "role_profile"],
	):
		profiles_by_user.setdefault(row.parent, []).append(row.role_profile)

	employee_by_user = {}
	for row in frappe.get_all(
		"Employee",
		fields=["name", "employee_name", "user_id", "designation", "department", "status"],
	):
		if row.user_id:
			employee_by_user[row.user_id] = row

	pos_profiles_by_user: dict[str, list[str]] = {}
	for row in frappe.get_all("POS Profile User", fields=["user", "parent"]):
		if row.user:
			pos_profiles_by_user.setdefault(row.user, []).append(row.parent)

	staff = []
	custom_map = get_custom_persona_map()
	tier_rank = {TIER_STANDARD: 0, TIER_ADMIN: 1, TIER_DESK: 2}
	for u in users:
		profiles = set(profiles_by_user.get(u.name, []))
		if u.role_profile_name:
			profiles.add(u.role_profile_name)
		# Known-ness lookups are unfiltered (like get_catalog_profile): a
		# manager still SEES that a row holds an admin persona they can't grant.
		known_tiers = [
			tier
			for tier in (
				(get_catalog_profile(p) or custom_map.get(p) or {}).get("tier") for p in profiles
			)
			if tier
		]
		persona = next((p for p in sorted(profiles) if get_catalog_profile(p) or custom_map.get(p)), None)
		employee = employee_by_user.get(u.name)
		staff.append(
			{
				"user": u.name,
				"email": u.email or u.name,
				"full_name": u.full_name or u.name,
				"user_image": u.user_image,
				"enabled": bool(u.enabled),
				"last_active": u.last_active,
				"roles": sorted(set(roles_by_user.get(u.name, []))),
				"role_profiles": sorted(profiles),
				"role_profile_labels": [get_label(p) for p in sorted(profiles)],
				"persona": persona,
				"persona_label": get_label(persona) if persona else None,
				"persona_tier": max(known_tiers, key=lambda t: tier_rank[t]) if known_tiers else None,
				"employee": employee["name"] if employee else None,
				"employee_name": employee["employee_name"] if employee else None,
				"designation": employee["designation"] if employee else None,
				"department": employee["department"] if employee else None,
				"employee_status": employee["status"] if employee else None,
				"pos_profiles": sorted(set(pos_profiles_by_user.get(u.name, []))),
			}
		)

	return {
		"staff": staff,
		"counts": {
			"total": len(staff),
			"active": sum(1 for s in staff if s["enabled"]),
			"disabled": sum(1 for s in staff if not s["enabled"]),
			"unlinked": sum(1 for s in staff if not s["employee"]),
		},
		# Caller capabilities the UI gates on (server-authoritative).
		"caller": {
			"is_admin_tier": _is_admin_tier(),
			"can_manage_personas": _is_admin_tier(),
			# set_manager_pin needs the RAW System Manager role for other
			# users — the Gemora Admin alias does not count there.
			"can_set_pins": frappe.session.user == "Administrator"
			or "System Manager" in set(frappe.get_roles(frappe.session.user)),
		},
		"options": _overview_options(),
	}


def _overview_options() -> dict:
	"""Dropdown sources for the create form (kept small on purpose)."""
	return {
		"genders": sorted(_gender_options()),
		"departments": frappe.get_all(
			"Department", filters={"is_group": 0}, pluck="name", order_by="name asc"
		),
		"designations": frappe.get_all("Designation", pluck="name", order_by="name asc"),
		"pos_profiles": frappe.get_all("POS Profile", fields=["name", "company"], order_by="name asc"),
		"shift_types": frappe.get_all("Shift Type", pluck="name", order_by="name asc"),
		"holiday_lists": frappe.get_all("Holiday List", pluck="name", order_by="name asc"),
		"unlinked_employees": frappe.get_all(
			"Employee",
			filters={"user_id": ("in", ["", None]), "status": "Active"},
			fields=["name", "employee_name"],
			order_by="creation desc",
			limit=50,
		),
	}


# ── update ───────────────────────────────────────────────────────────────────


def update_staff_member(payload: dict) -> dict:
	"""Re-persona / enable / disable / password reset, with tier protections."""
	require_permission("staff.manage")

	user = (payload.get("user") or "").strip()
	if not user or user in _PROTECTED_USERS:
		frappe.throw(_("Invalid user."))

	_assert_may_mutate(user)

	updates = {}
	requested_profiles = _normalize_persona_list(
		payload.get("role_profiles") or payload.get("role_profile")
	)
	if requested_profiles:
		updates.update(_reassign_persona(user, requested_profiles))
	if payload.get("password") is not None or payload.get("generate_password"):
		updates.update(_reset_password(user, payload.get("password")))
	if payload.get("enabled") is not None:
		updates.update(_set_enabled(user, bool(payload.get("enabled"))))
	if payload.get("department") or payload.get("designation"):
		updates.update(_update_employee_fields(user, payload))

	if not updates:
		frappe.throw(_("Nothing to update."))

	frappe.clear_cache(user=user)
	return {"user": user, **updates}


def _assert_may_mutate(user: str) -> None:
	"""Managers may never mutate admin/desk-tier accounts (or themselves out).

	Platform accounts (Administrator + internal-flagged staff) are
	platform-only — no tenant session may touch them through the hub
	(the User.validate firewall covers desk/REST writes).
	Self-mutation stays allowed (persona change among assignable tiers,
	password reset, no self-disable) — the persona check carries that gating.
	"""
	from arijentek_core.services.internal_access import _is_platform_actor

	if not _is_platform_actor(frappe.session.user):
		from arijentek_core.services.internal_access import is_internal_user

		if user == "Administrator" or is_internal_user(user):
			frappe.throw(
				_("Platform accounts may only be managed by Gemora."),
				frappe.PermissionError,
			)

	roles = set(frappe.get_roles(user))
	if roles & DESK_ROLES:
		from arijentek_core.services.permissions import require_desk_grant_right

		require_desk_grant_right()
	elif _normalize_role_set(roles) & {"System Manager", "Administrator"} and not _is_admin_tier():
		frappe.throw(
			_("Admin-tier accounts may only be managed by an administrator."),
			frappe.PermissionError,
		)


def _reassign_persona(user: str, role_profiles: list[str]) -> dict:
	"""Set the user's persona stack; profile sync replaces the whole role bundle."""
	for profile in role_profiles:
		_assert_persona_assignable(profile)
	if not frappe.db.exists("User", user):
		frappe.throw(_("User {0} not found.").format(user), frappe.DoesNotExistError)

	doc = frappe.get_doc("User", user)
	doc.set("role_profiles", [])
	for profile in role_profiles:
		doc.append("role_profiles", {"role_profile": profile})
	doc.role_profile_name = None
	doc.save(ignore_permissions=True)
	return {
		"role_profile": role_profiles[0],
		"role_profiles": role_profiles,
		"roles": sorted({r.role for r in frappe.get_doc("User", user).roles}),
	}


def _reset_password(user: str, password: str | None) -> dict:
	from frappe.utils.password import update_password

	generated = None
	if not password:
		generated = _generate_password()
		password = generated
	elif len(password) < 6:
		frappe.throw(_("Password must be at least 6 characters."))
	update_password(user, password)
	return {"generated_password": generated} if generated else {"password_reset": True}


def _set_enabled(user: str, enabled: bool) -> dict:
	if user == frappe.session.user and not enabled:
		frappe.throw(_("You cannot disable your own account."))
	frappe.db.set_value("User", user, "enabled", 1 if enabled else 0)
	return {"enabled": enabled}


def _update_employee_fields(user: str, payload: dict) -> dict:
	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee:
		frappe.throw(_("This user has no linked employee record to update."))
	updates = {k: payload.get(k) for k in ("department", "designation") if payload.get(k)}
	if updates:
		frappe.db.set_value("Employee", employee, updates)
	return {"employee": employee, **updates}


def _normalize_role_set(roles: set[str]) -> set[str]:
	from arijentek_core.services.permissions import _normalize_roles

	return _normalize_roles(roles)


def get_staff_permissions(user: str) -> dict[str, bool]:
	"""Effective permission-key map for the hub's permissions drawer."""
	require_permission("staff.manage")
	if not user or not frappe.db.exists("User", user):
		frappe.throw(_("User not found."), frappe.DoesNotExistError)
	return get_permissions_for_user(user)
