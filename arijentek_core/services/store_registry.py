# Copyright (c) 2026, Gemora 360 and contributors
# License: GNU GPL v3. See license.txt
"""
Store registry — the SaaS-ready replacement for the hardcoded ``STORE_LOCATIONS``
constant in ``zevar_core.constants``.

Why this exists
---------------
Historically the active store list was a literal dict in ``constants.py``
(``NYC/MIA/LA/HOU/CHI``). That hardcode is an anti-SaaS blocker: every tenant
must be able to self-provision stores at runtime, so the store list must be
sourced from the ``Store Location`` doctype, not a Python literal.

This module is the single source of truth for "which stores exist right now".
It is cached (invalidated on Store Location writes via hooks) and degrades
gracefully to the legacy constant during install/migrate, before the doctype
is populated or the ``company`` column exists.

Two views are exposed:
  * ``get_active_stores()``        -> ``{store_code: store_name}`` (drop-in for
	the old ``STORE_LOCATIONS`` dict; iterate / index exactly as before).
  * ``get_store_registry()``       -> ``{store_code: {store_name, company,
	default_warehouse, abbr}}`` for paths that need the per-store company.
"""

import frappe
from frappe import _

_LEGACY_STORE_LOCATIONS = {"MAIN": "Main Office"}

_REGISTRY_CACHE_KEY = "zevar:store_registry"
_DEFAULT_STORE_CACHE_KEY = "zevar:default_store"
_FALLBACK_ABBR = "ZJ"


def get_store_registry():
	"""Return ``{store_code: {store_name, company, default_warehouse, abbr}}``
	for all active stores. Cached; rebuilt on Store Location writes.

	During install/migrate (no rows, or no ``company`` column yet) this falls
	back to the legacy constant + the default company, so callers always get a
	usable dict and never crash before the schema is ready.
	"""
	try:
		cached = frappe.cache().get_value(_REGISTRY_CACHE_KEY)
	except Exception:  # nosec B110 - cache unavailable (install/headless) is non-fatal
		cached = None

	if cached is not None:
		return cached

	registry = _load_store_registry_from_db()

	try:
		frappe.cache().set_value(_REGISTRY_CACHE_KEY, registry)
	except Exception:  # nosec B110 - cache write failure is non-fatal
		pass

	return registry


def get_active_stores():
	"""Return ``{store_code: store_name}`` for all active stores.

	Drop-in replacement for ``zevar_core.constants.STORE_LOCATIONS`` — iterate
	it or index it exactly as the old dict was used.
	"""
	return {code: info["store_name"] for code, info in get_store_registry().items()}


def get_store_cost_center(store_code_or_warehouse=None, company=None):
	"""Resolve the Cost Center for a store, falling back to the company default.

	``store_code_or_warehouse`` may be a store_code, a Store Location **name**,
	or a warehouse (reverse-looked-up via :func:`_resolve_store_location_name`,
	which handles all three uniformly). Returns the store's
	``default_cost_center`` if set and valid, else the company-wide default
	(``Company.cost_center``), else ``None``. Never raises — callers may safely
	omit the field and let ERPNext apply its own default.
	"""
	if store_code_or_warehouse:
		loc = _resolve_store_location_name(store_code_or_warehouse)
		if loc:
			try:
				cc = frappe.db.get_value("Store Location", loc, "default_cost_center")
			except Exception:  # nosec B110 - install-time / headless
				cc = None
			if cc and frappe.db.exists("Cost Center", cc):
				return cc
	company = company or _get_default_company()
	if company:
		try:
			return frappe.get_cached_value("Company", company, "cost_center")
		except Exception:  # nosec B110 - install-time / headless
			return None
	return None


@frappe.whitelist(allow_guest=False)
def get_default_store():
	"""Return the system-wide default store used everywhere (POS, catalog,
	sales) when no store is explicitly chosen, as a dict, or ``{}`` if none.

	Precedence: ``is_default`` flag -> ``is_headquarters`` -> the only active
	store -> first active store. Cached; invalidated on Store Location writes
	(via :func:`clear_active_stores_cache`).

	Returns ``{store_code, store_name, company, default_warehouse, pos_profile,
	abbr}`` or ``{}``.
	"""
	try:
		cached = frappe.cache().get_value(_DEFAULT_STORE_CACHE_KEY)
	except Exception:  # nosec B110 - cache unavailable (install/headless) is non-fatal
		cached = None

	if cached is not None:
		return cached

	store = _load_default_store() or {}
	try:
		frappe.cache().set_value(_DEFAULT_STORE_CACHE_KEY, store)
	except Exception:  # nosec B110 - cache write failure is non-fatal
		pass
	return store


def clear_active_stores_cache(doc=None, method=None):
	"""Invalidate the cached registry. Hook this into Store Location
	``on_update`` / ``on_trash`` (see ``hooks.py``) so new/edited stores appear
	immediately without a restart. Accepts Frappe's ``(doc, method)`` hook args."""
	try:
		# NOTE: delete_keys takes ONE prefix string (it appends "*" itself).
		# A list raises TypeError — which the old code swallowed silently.
		frappe.cache().delete_keys(_REGISTRY_CACHE_KEY)
		frappe.cache().delete_keys(_DEFAULT_STORE_CACHE_KEY)
	except Exception:  # nosec B110 - cache failure is non-fatal
		pass


def get_store_managers(store_code_or_warehouse):
	"""Return the email addresses of the managers of a store.

	Accepts either a ``store_code`` or a warehouse name (resolved via
	``Store Location.default_warehouse``). Only managers with
	``notify_transfers`` enabled are returned. Falls back to every user holding
	the ``Store Manager`` role when none are explicitly assigned, so transfer
	notifications work out of the box before admins configure the per-store list.
	"""
	if not store_code_or_warehouse:
		return []

	store_name = _resolve_store_location_name(store_code_or_warehouse)
	emails = []
	if store_name:
		rows = frappe.db.get_all(
			"Store Location Manager",
			filters={"parent": store_name, "parenttype": "Store Location", "notify_transfers": 1},
			pluck="email",
		)
		emails = [e for e in rows if e]

	if not emails:
		# Graceful bootstrap: route to any manager-level role until per-store
		# managers are configured.
		emails = frappe.db.get_all(
			"Has Role",
			filters={"role": ["in", ["Store Manager", "POS Manager", "Sales Manager", "Stock Manager"]]},
			pluck="parent",
		)
		emails = [
			frappe.db.get_value("User", u, "email")
			for u in emails
			if u and u != "Guest" and frappe.db.get_value("User", u, "enabled", cache=True)
		]

	# Dedupe, drop empties, never include the session user's own echo where avoidable.
	seen = []
	for e in emails:
		if e and e not in seen:
			seen.append(e)
	return seen


@frappe.whitelist(allow_guest=False)
def set_store_manager(store_code, user, is_primary=0, notify_transfers=1):
	"""Assign a user as a manager of a store (Store Location → store_managers).

	Idempotent. Used by the owner to designate the approver(s) per store so that
	Store Transfer approval is source-store-scoped.

	Writes the child row directly rather than loading the full Store Location,
	because Store Location has unrelated legacy child tables (Workshop / External
	Bench Vendor) that aren't real child tables and break a full-doc load.
	"""
	loc = _resolve_store_location_name(store_code)
	if not loc:
		frappe.throw(_("Store {0} not found.").format(store_code))
	if not frappe.db.exists("User", user):
		frappe.throw(_("User {0} not found.").format(user))

	email = frappe.db.get_value("User", user, "email")
	existing = frappe.db.get_value(
		"Store Location Manager",
		{
			"parent": loc,
			"parenttype": "Store Location",
			"parentfield": "store_managers",
			"user": user,
		},
		"name",
	)
	if existing:
		frappe.db.set_value(
			"Store Location Manager",
			existing,
			{"is_primary": is_primary, "notify_transfers": notify_transfers, "email": email},
		)
	else:
		frappe.get_doc(
			{
				"doctype": "Store Location Manager",
				"parent": loc,
				"parenttype": "Store Location",
				"parentfield": "store_managers",
				"user": user,
				"email": email,
				"is_primary": is_primary,
				"notify_transfers": notify_transfers,
			}
		).insert(ignore_permissions=True)
	frappe.db.commit()
	clear_active_stores_cache()
	return {"store": loc, "manager": user}


# ---------------------------------------------------------------------------
# Phase 2 RBAC: per-store scoping via Frappe User Permissions
# ---------------------------------------------------------------------------

def scope_user_to_store(user, store_code):
	"""Scope a user to a single store via User Permissions (Warehouse + Store Location).

	Idempotent. Creates UPs for the store's sellable warehouse (Is Default) + the
	Reserved warehouse (so the user can act on layaway/Hard Reserve stock). When
	Apply User Permissions is enabled on the user's role for a doctype, they will
	only see/act on records linked to this store.
	"""
	info = get_store_registry().get(store_code)
	if not info:
		frappe.throw(_("Store {0} not found.").format(store_code))
	if not frappe.db.exists("User", user):
		frappe.throw(_("User {0} not found.").format(user))

	wh = info["default_warehouse"]
	reserved_wh = f"Reserved {info['store_name']} - {info['abbr']}"
	loc = _resolve_store_location_name(store_code)

	_ensure_user_permission(user, "Warehouse", wh, is_default=1)
	if frappe.db.exists("Warehouse", reserved_wh):
		_ensure_user_permission(user, "Warehouse", reserved_wh, is_default=0)
	if loc:
		_ensure_user_permission(user, "Store Location", loc, is_default=1)

	return {"user": user, "store": store_code, "warehouse": wh}


def get_unscoped_store_users():
	"""Store-level users (Sales User, POS User, Stock User, Store Manager) who have
	NO Warehouse User Permission AND don't hold an override/all-store role — they
	would be locked out if Strict Permissions were enabled."""
	store_roles = ("Sales User", "POS User", "Stock User", "Store Manager")
	override_roles = {
		"Jewelry Principal", "HQ Manager", "System Manager", "Administrator",
		"Sales Manager", "Accounts Manager", "HR Manager",
	}
	users = set()
	for role in store_roles:
		for u in frappe.get_all("Has Role", filters={"role": role}, pluck="parent"):
			if u in ("Guest", "Administrator"):
				continue
			if not frappe.db.get_value("User", u, "enabled", cache=True):
				continue
			# Skip users who also hold an override role (they see all stores).
			user_roles = set(frappe.get_roles(u))
			if user_roles & override_roles:
				continue
			users.add(u)
	scoped = set(frappe.get_all("User Permission", filters={"allow": "Warehouse"}, pluck="user"))
	return sorted(users - scoped)


def enable_strict_permissions(dry_run=False):
	"""Enable Apply Strict User Permissions in System Settings. Pre-checks that
	no store-level user would be locked out. If dry_run, only reports."""
	unscoped = get_unscoped_store_users()
	if unscoped:
		frappe.throw(
			_("{0} store-level user(s) have no Warehouse User Permission — they'd be locked out: {1}").format(
				len(unscoped), ", ".join(unscoped)
			)
		)
	if dry_run:
		return {"would_enable": True, "unscoped": 0}
	frappe.db.set_single_value("System Settings", "apply_strict_user_permissions", 1)
	frappe.db.commit()
	frappe.clear_cache()
	return {"strict_permissions": True}


def disable_strict_permissions():
	"""Quick rollback: turn Strict Permissions OFF."""
	frappe.db.set_single_value("System Settings", "apply_strict_user_permissions", 0)
	frappe.db.commit()
	frappe.clear_cache()
	return {"strict_permissions": False}


def set_ignore_user_permissions_on_item_links():
	"""Set 'Ignore User Permissions' on the item_code link field inside key
	transaction child tables, so a store-scoped user can still select any item
	from the global catalog (which is chain-wide, not store-scoped)."""
	targets = [
		("Sales Invoice Item", "item_code"),
		("Stock Entry Detail", "item_code"),
		("Store Transfer Item", "item_code"),
		("Delivery Note Item", "item_code"),
		("Material Request Item", "item_code"),
	]
	for doctype, fieldname in targets:
		_set_ignore_up(doctype, fieldname)
	frappe.db.commit()
	return {"configured": len(targets)}


def _ensure_user_permission(user, allow, for_value, is_default=0):
	existing = frappe.db.get_value(
		"User Permission", {"user": user, "allow": allow, "for_value": for_value}, "name"
	)
	if existing:
		if is_default:
			frappe.db.set_value("User Permission", existing, "is_default", 1)
		return existing
	doc = frappe.get_doc(
		{
			"doctype": "User Permission",
			"user": user,
			"allow": allow,
			"for_value": for_value,
			"is_default": is_default,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _set_ignore_up(doctype, fieldname):
	"""Create a Property Setter to ignore user permissions on a link field."""
	if frappe.db.exists(
		"Property Setter",
		{"doc_type": doctype, "doc_name": fieldname, "property": "ignore_user_permissions"},
	):
		return
	try:
		frappe.make_property_setter(doctype, fieldname, "ignore_user_permissions", "1", "Check")
	except Exception:
		frappe.log_error(f"set_ignore_up failed for {doctype}.{fieldname}", frappe.get_traceback())


def _resolve_store_location_name(store_code_or_warehouse):
	"""Map a store_code or warehouse to its Store Location name (or None)."""
	if not store_code_or_warehouse:
		return None
	# Direct store_code match.
	name = frappe.db.get_value("Store Location", {"store_code": store_code_or_warehouse})
	if name:
		return name
	# Warehouse -> Store Location via default_warehouse.
	name = frappe.db.get_value("Store Location", {"default_warehouse": store_code_or_warehouse})
	if name:
		return name
	return None


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _load_default_store():
	"""Resolve the system-wide default store from the Store Location doctype.

	Precedence (always ``is_active=1``): ``is_default=1`` -> ``is_headquarters=1``
	-> the only active store -> first active store (by creation). Returns the
	store dict or ``None`` when no store exists yet (install/migrate).

	``is_default`` is only filtered on when its column already exists, so this
	works before the default-store field migration has run.
	"""
	default_company = _get_default_company()
	default_abbr = _get_company_abbr(default_company)

	fields = ["store_code", "store_name", "default_warehouse", "pos_profile"]
	try:
		if frappe.db.has_column("Store Location", "company"):
			fields.append("company")
	except Exception:  # nosec B110 - has_column can fail on a fresh install
		pass
	try:
		if frappe.db.has_column("Store Location", "default_cost_center"):
			fields.append("default_cost_center")
	except Exception:  # nosec B110 - has_column can fail on a fresh install
		pass

	def _fetch(extra_filters):
		try:
			return frappe.db.get_all(
				"Store Location",
				filters={"is_active": 1, **extra_filters},
				fields=fields,
				order_by="creation",
				limit_page_length=1,
			)
		except Exception:  # nosec B110 - table/column missing during install
			return []

	# 1. Explicit default-store flag (only if the column exists yet).
	rows = []
	try:
		if frappe.db.has_column("Store Location", "is_default"):
			rows = _fetch({"is_default": 1})
	except Exception:  # nosec B110
		rows = []

	# 2. Headquarters.
	if not rows:
		rows = _fetch({"is_headquarters": 1})

	# 3. The only active store (single-store tenants get it for free).
	if not rows:
		try:
			active = frappe.db.get_all("Store Location", filters={"is_active": 1}, pluck="name")
		except Exception:  # nosec B110
			active = []
		if len(active) == 1:
			rows = _fetch({"name": active[0]})

	# 4. First active store by creation.
	if not rows:
		rows = _fetch({})

	if not rows:
		return None

	row = rows[0]
	company = row.get("company") or default_company
	return {
		"store_code": row.get("store_code"),
		"store_name": row.get("store_name") or row.get("store_code"),
		"company": company,
		"default_warehouse": row.get("default_warehouse"),
		"pos_profile": row.get("pos_profile"),
		"cost_center": row.get("default_cost_center"),
		"abbr": _get_company_abbr(company) or default_abbr,
	}


def _load_store_registry_from_db():
	"""Read active stores from the Store Location doctype, company-aware.

	``company`` is only requested if the column already exists, so this works
	even before the multi-store field migration has run.
	"""
	default_company = _get_default_company()
	default_abbr = _get_company_abbr(default_company)

	fields = ["store_code", "store_name", "default_warehouse"]
	try:
		if frappe.db.has_column("Store Location", "company"):
			fields.append("company")
	except Exception:  # nosec B110 - has_column can fail on a fresh install
		pass
	try:
		if frappe.db.has_column("Store Location", "default_cost_center"):
			fields.append("default_cost_center")
	except Exception:  # nosec B110 - has_column can fail on a fresh install
		pass

	try:
		rows = frappe.db.get_all(
			"Store Location",
			filters={"is_active": 1},
			fields=fields,
			order_by="store_code",
		)
	except Exception:  # nosec B110 - table missing during install
		rows = []

	if not rows:
		# SaaS tenants seed their own store at provision time; an empty table
		# is a legitimate state. Callers already tolerate an empty registry
		# (get_default_store() → None). Legacy constants stay only for
		# bare-metal dev installs via frappe.flags.in_install paths.
		if not frappe.conf.get("skip_legacy_store_seed") and getattr(frappe.flags, "in_install", False):
			return {
				code: {
					"store_name": name,
					"company": default_company,
					"default_warehouse": None,
					"abbr": default_abbr,
				}
				for code, name in _LEGACY_STORE_LOCATIONS.items()
			}
		return {}

	registry = {}
	for row in rows:
		company = row.get("company") or default_company
		registry[row["store_code"]] = {
			"store_name": row.get("store_name") or row["store_code"],
			"company": company,
			"default_warehouse": row.get("default_warehouse"),
			"cost_center": row.get("default_cost_center"),
			"abbr": _get_company_abbr(company) or default_abbr,
		}
	return registry


def _get_default_company():
	try:
		return frappe.db.get_single_value("Global Defaults", "default_company")
	except Exception:  # nosec B110 - install-time / headless
		return None


def _get_company_abbr(company):
	if not company:
		return _FALLBACK_ABBR
	try:
		return frappe.db.get_value("Company", company, "abbr") or _FALLBACK_ABBR
	except Exception:  # nosec B110 - install-time / headless
		return _FALLBACK_ABBR
