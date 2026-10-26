import frappe
from frappe import _
from frappe.utils import cint, cstr, flt

from arijentek_core.api.realtime.bus import publish_settings_update
from arijentek_core.services.internal_access import get_internal_user_names, is_internal_user
from arijentek_core.services.permissions import (
	DESK_ROLES,
	PLATFORM_ROLES,
	require_desk_grant_right,
	require_permission,
)
from arijentek_core.services.role_profile_catalog import _is_admin_tier


@frappe.whitelist(allow_guest=False)
def get_settings():
	require_permission("settings.read")

	company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value(
		"Company", {}, "name"
	)

	pos_profiles_filters = {"disabled": 0}
	if company:
		pos_profiles_filters["company"] = company

	pos_profiles = frappe.get_all(
		"POS Profile",
		filters=pos_profiles_filters,
		fields=[
			"name",
			"company",
			"warehouse",
			"customer",
			"selling_price_list",
			"cost_center",
			"income_account",
			"expense_account",
			"write_off_account",
			"write_off_cost_center",
		],
		order_by="name asc",
	)

	wh_filters = {"disabled": 0, "is_group": 0}
	if company:
		wh_filters["company"] = company

	warehouses = frappe.get_all(
		"Warehouse",
		filters=wh_filters,
		fields=["name", "warehouse_name", "parent_warehouse"],
		order_by="name asc",
	)

	customers = frappe.get_all(
		"Customer",
		filters={"disabled": 0},
		fields=["name", "customer_name", "customer_group"],
		order_by="customer_name asc",
		limit=200,
	)

	suppliers = frappe.get_all(
		"Supplier",
		filters={"disabled": 0},
		fields=["name", "supplier_name", "supplier_group"],
		order_by="supplier_name asc",
		limit=200,
	)

	price_lists = frappe.get_all(
		"Price List",
		filters={"enabled": 1},
		fields=["name", "price_list_name", "buying", "selling", "currency"],
		order_by="name asc",
	)

	modes = frappe.get_all(
		"Mode of Payment",
		filters={},
		fields=["name", "type"],
		order_by="name asc",
	)

	tax_filters = {"disabled": 0}
	if company:
		tax_filters["company"] = company

	tax_templates = frappe.get_all(
		"Sales Taxes and Charges Template",
		filters=tax_filters,
		fields=["name", "title", "company", "tax_category", "disabled"],
		order_by="name asc",
	)
	for tax in tax_templates:
		taxes_rows = frappe.db.get_all(
			"Sales Taxes and Charges",
			filters={"parent": tax["name"]},
			fields=["account_head", "rate", "charge_type", "description"],
		)
		tax["rate"] = flt(taxes_rows[0].rate) if taxes_rows else 0.0
		tax["account_head"] = taxes_rows[0].account_head if taxes_rows else ""
		tax["taxes"] = taxes_rows

	cc_filters = {"disabled": 0, "is_group": 0}
	if company:
		cc_filters["company"] = company

	cost_centers = frappe.get_all(
		"Cost Center",
		filters=cc_filters,
		fields=["name", "cost_center_name", "parent_cost_center"],
		order_by="lft asc",
	)

	acc_filters = {"disabled": 0, "is_group": 0}
	if company:
		acc_filters["company"] = company

	accounts = frappe.get_all(
		"Account",
		filters=acc_filters,
		fields=["name", "account_name", "account_type", "root_type"],
		order_by="lft asc",
		limit=300,
	)

	users = frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User"},
		fields=["name", "full_name", "email", "user_image"],
		order_by="full_name asc",
	)

	roles = frappe.get_all(
		"Role",
		filters={"disabled": 0},
		fields=["name"],
		order_by="name asc",
	)

	print_formats = frappe.get_all(
		"Print Format",
		filters={},
		fields=["name", "doc_type", "standard"],
		order_by="name asc",
	)

	item_groups = frappe.get_all(
		"Item Group",
		filters={"is_group": 0},
		fields=["name", "parent_item_group"],
		order_by="lft asc",
	)

	brands = frappe.get_all(
		"Brand",
		filters={},
		fields=["name"],
		order_by="name asc",
	)

	zevar_settings = {}
	if frappe.db.exists("Property Setter", {"doc_type": "POS Profile", "property": "default"}):
		zevar_settings["default_pos_profile"] = frappe.db.get_value(
			"Property Setter", {"doc_type": "POS Profile", "property": "default"}, "value"
		)

	stores = frappe.get_all(
		"Store Location",
		fields=[
			"name",
			"store_code",
			"store_name",
			"county",
			"county_tax_rate",
			"store_type",
			"is_active",
			"is_default",
			"default_warehouse",
			"pos_profile",
		],
		order_by="is_default desc, is_active desc, store_name asc",
	)

	require_open_close_register = 0
	if frappe.db.exists("DocType", "POS Settings"):
		try:
			val = frappe.db.get_single_value("POS Settings", "require_open_close_register")
			if val is not None:
				require_open_close_register = cint(val)
		except Exception:
			pass

	require_associate_pin = 0
	if frappe.get_meta("POS Settings").has_field("custom_require_associate_pin"):
		try:
			val = frappe.db.get_single_value("POS Settings", "custom_require_associate_pin")
			if val is not None:
				require_associate_pin = cint(val)
		except Exception:
			pass

	return {
		"success": True,
		"company": company,
		"pos_profiles": pos_profiles,
		"warehouses": warehouses,
		"customers": customers,
		"suppliers": suppliers,
		"price_lists": price_lists,
		"modes_of_payment": modes,
		"tax_templates": tax_templates,
		"cost_centers": cost_centers,
		"accounts": accounts,
		"users": users,
		"roles": roles,
		"print_formats": print_formats,
		"item_groups": item_groups,
		"brands": brands,
		"stores": stores,
		"zevar_settings": zevar_settings,
		"require_open_close_register": require_open_close_register,
		"require_associate_pin": require_associate_pin,
	}


@frappe.whitelist(allow_guest=False)
def toggle_require_open_close_register(require: bool | int | str = True):
	"""Toggle whether opening and closing register is enforced before checkout."""
	if frappe.session.user != "Administrator" and "System Manager" not in frappe.get_roles():
		frappe.throw(
			_("Only Administrators and System Managers can activate or deactivate the POS Register feature."),
			frappe.PermissionError,
		)

	val = 1 if cstr(require).lower() in ("1", "true", "yes") else 0

	# POS Settings is a Single DocType stored in tabSingles
	if frappe.db.exists("DocType", "POS Settings"):
		try:
			custom_field_exists = frappe.db.exists(
				"Custom Field", {"dt": "POS Settings", "fieldname": "require_open_close_register"}
			)
			if not custom_field_exists:
				from frappe.custom.doctype.custom_field.custom_field import create_custom_field

				create_custom_field(
					"POS Settings",
					{
						"fieldname": "require_open_close_register",
						"label": "Require Open & Close Register",
						"fieldtype": "Check",
						"default": "0",
					},
				)
			frappe.db.set_single_value("POS Settings", "require_open_close_register", val)
		except Exception as e:
			frappe.log_error(f"Error saving to POS Settings: {e}")

	if frappe.db.exists("DocType", "Zevar Business Settings"):
		try:
			frappe.db.set_single_value("Zevar Business Settings", "require_open_close_register", val)
		except Exception:
			pass

	frappe.db.commit()
	publish_settings_update("pos_settings", "update")
	return {"success": True, "require_open_close_register": val}


@frappe.whitelist(allow_guest=False)
def toggle_require_associate_pin(require: bool | int | str = True):
	"""Toggle whether selling associates must authenticate with their PIN at checkout."""
	require_permission("settings.manage")
	val = 1 if cstr(require).lower() in ("1", "true", "yes") else 0

	if frappe.db.exists("DocType", "POS Settings"):
		if not frappe.get_meta("POS Settings").has_field("custom_require_associate_pin"):
			from frappe.custom.doctype.custom_field.custom_field import create_custom_field

			create_custom_field(
				"POS Settings",
				{
					"fieldname": "custom_require_associate_pin",
					"label": "Require Associate PIN at Checkout",
					"fieldtype": "Check",
					"default": "0",
				},
			)
		frappe.db.set_single_value("POS Settings", "custom_require_associate_pin", val)

	frappe.db.commit()
	publish_settings_update("pos_settings", "update")
	return {"success": True, "require_associate_pin": val}


@frappe.whitelist(allow_guest=False)
def get_active_store_locations():
	"""Return active Store Location records for frontend store selectors.

	Lightweight endpoint consumed by the centralized Pinia store so that
	every component in the SPA shares one source of truth for which stores
	are currently enabled.
	"""
	stores = frappe.get_all(
		"Store Location",
		filters={"is_active": 1},
		fields=[
			"name",
			"store_code",
			"store_name",
			"default_warehouse",
			"pos_profile",
			"company",
			"county",
			"county_tax_rate",
			"tax_template",
			"store_type",
			"time_zone",
			"is_headquarters",
			"is_default",
		],
		order_by="store_name asc",
	)
	return stores


@frappe.whitelist(allow_guest=False)
def toggle_store_active(store_code: str, is_active: bool | int | str = True):
	"""Toggle a Store Location on/off (admin self-service, no developer needed).

	is_active=1 -> store shows in POS store selector + 'All Stores' aggregation.
	is_active=0 -> hidden from selectors and catalog aggregation (record kept).
	"""
	require_permission("settings.stores")
	store_code = cstr(store_code).strip()
	if not frappe.db.exists("Store Location", store_code):
		frappe.throw(_("Store not found: {0}").format(store_code))
	active = cstr(is_active) in ("1", "true", "True", "on")
	frappe.db.set_value("Store Location", store_code, "is_active", 1 if active else 0)

	# Invalidate the backend store registry cache so callers of
	# get_active_stores() / get_store_registry() see the change immediately.
	try:
		from arijentek_core.services.store_registry import clear_active_stores_cache

		clear_active_stores_cache()
	except Exception:
		pass

	publish_settings_update("store", "toggle")
	return {"success": True, "store_code": store_code, "is_active": 1 if active else 0}


# Fields an admin may edit on an existing Store Location (whitelist).
_STORE_EDITABLE_FIELDS = {
	"store_name",
	"store_type",
	"time_zone",
	"address_line1",
	"address_line2",
	"city",
	"pincode",
	"phone",
	"email",
	"store_manager_name",
	"receipt_footer_override",
	"county",
	"county_tax_rate",
	"tax_template",
	"default_warehouse",
	"default_cost_center",
	"pos_profile",
	"is_headquarters",
	"is_active",
}


@frappe.whitelist(allow_guest=False)
def set_default_store(store_code: str):
	"""Set a single Store Location as the system-wide default (is_default=1),
	unset all others. Enforces the at-most-one rule from store_location.py.
	"""
	require_permission("settings.stores")
	store_code = cstr(store_code).strip()
	if not frappe.db.exists("Store Location", store_code):
		frappe.throw(_("Store not found: {0}").format(store_code))

	# Clear any existing defaults, then set this one.
	for other in frappe.db.get_all("Store Location", filters={"is_default": 1}, pluck="name"):
		if other != store_code:
			frappe.db.set_value("Store Location", other, "is_default", 0, update_modified=False)
	frappe.db.set_value("Store Location", store_code, "is_default", 1, update_modified=False)

	try:
		from arijentek_core.services.store_registry import clear_active_stores_cache

		clear_active_stores_cache()
	except Exception:
		pass

	return {"success": True, "default_store": store_code}


@frappe.whitelist(allow_guest=False)
def update_store(store_code: str, updates: dict | str | None = None):
	"""Edit an existing Store Location (admin). Field-level updates only — a
	full get_doc/save is unsafe here because Store Location has legacy child
	tables (Workshop / External Bench Vendor) that break a full-doc load.

	``updates`` is a JSON string or dict of {field: value}. ``is_default`` is
	routed through :func:`set_default_store` to enforce the <=1 rule.
	"""
	require_permission("settings.stores")
	store_code = cstr(store_code).strip()
	if not frappe.db.exists("Store Location", store_code):
		frappe.throw(_("Store not found: {0}").format(store_code))

	if isinstance(updates, str):
		updates = frappe.parse_json(updates) if updates else {}
	if not isinstance(updates, dict) or not updates:
		frappe.throw(_("No updates provided."))

	# is_default is handled separately to keep the at-most-one invariant.
	if "is_default" in updates:
		want_default = cstr(updates.pop("is_default")) in ("1", "true", "True")
		if want_default:
			set_default_store(store_code)
		else:
			frappe.db.set_value("Store Location", store_code, "is_default", 0)

	for field, value in updates.items():
		if field not in _STORE_EDITABLE_FIELDS:
			continue
		if field == "default_warehouse" and value and not frappe.db.exists("Warehouse", value):
			frappe.throw(_("Warehouse not found: {0}").format(value))
		if field == "pos_profile" and value and not frappe.db.exists("POS Profile", value):
			frappe.throw(_("POS Profile not found: {0}").format(value))
		frappe.db.set_value("Store Location", store_code, field, value)

	try:
		from arijentek_core.services.store_registry import clear_active_stores_cache

		clear_active_stores_cache()
	except Exception:
		pass

	publish_settings_update("store", "update")
	return {"success": True, "store_code": store_code}


def _resolve_profile_users(users_json):
	"""Parse a users_json argument (list or JSON string) into canonical User names."""
	import json

	users = json.loads(users_json) if isinstance(users_json, str) else users_json
	resolved = []
	for u in users or []:
		user_str = cstr(u).strip()
		if not user_str:
			continue
		user_name = (
			user_str
			if frappe.db.exists("User", user_str)
			else frappe.db.get_value("User", {"email": user_str}, "name")
		)
		if user_name and user_name not in resolved:
			resolved.append(user_name)
	return resolved


def _profile_user_allocations(profile_name: str, new_users: list) -> list:
	"""Desired-state allocations making ``profile_name``'s user list equal
	``new_users`` WITHOUT touching anyone's memberships in OTHER POS Profiles.

	The store-allocation reconciler applies replace semantics per user, so
	feeding it only this profile's list would silently demote multi-profile
	users. Existing default flags survive; a user's first membership makes
	this profile their default.
	"""
	current_users = set(
		frappe.get_all(
			"POS Profile User",
			filters={"parent": profile_name, "parenttype": "POS Profile"},
			pluck="user",
		)
	)
	affected = current_users | set(new_users)

	others_by_user = {}
	default_by_user = {}
	if affected:
		for row in frappe.get_all(
			"POS Profile User",
			filters={"user": ["in", list(affected)], "parenttype": "POS Profile"},
			fields=["user", "parent", "default"],
		):
			if row.parent != profile_name:
				others_by_user.setdefault(row.user, []).append(row.parent)
			if row.default and row.user not in default_by_user:
				default_by_user[row.user] = row.parent

	allocations = []
	for uid in affected:
		desired = [profile_name] if uid in new_users else []
		others = sorted(set(others_by_user.get(uid, [])))
		existing_default = default_by_user.get(uid)
		if existing_default and existing_default in others:
			# Keep the user's current default first so the reconciler
			# doesn't reassign it to whichever profile sorts first.
			others = [existing_default] + [o for o in others if o != existing_default]
		allocations.append({"user_id": uid, "pos_profiles": desired + others})
	return allocations


@frappe.whitelist(allow_guest=False)
def get_pos_profile(name: str):
	require_permission("settings.read")
	name = cstr(name).strip()

	if not frappe.db.exists("POS Profile", name):
		frappe.throw(_("POS Profile not found"))

	doc = frappe.get_doc("POS Profile", name)

	# POS issue #1: child tables can load as None (e.g. the posawesome
	# posa_idx_items_groups custom field on a profile with no rows), which
	# crashed the whole payload with TypeError before users/payments could be
	# returned. `or []` keeps the endpoint whole on any profile shape.
	payment_methods = []
	for row in doc.get("payments") or []:
		payment_methods.append(
			{
				"mode_of_payment": row.mode_of_payment,
				"default": row.default,
			}
		)

	item_groups_list = []
	for row in doc.get("posa_idx_items_groups") or []:
		item_groups_list.append(
			{
				"item_group": row.get("item_group", ""),
			}
		)

	users_list = []
	for row in doc.get("applicable_for_users") or []:
		if row.get("user"):
			users_list.append(row.get("user"))

	# Store enrichment (POS issues #14/#17/#11) — same resolution order as
	# api/pos_profile.py: Store Location by default_warehouse first, then by
	# pos_profile, so the edit form shows the store label, not the warehouse.
	store_location = None
	if doc.warehouse:
		store_location = frappe.db.get_value(
			"Store Location",
			{"default_warehouse": doc.warehouse},
			["name", "store_code", "store_name"],
			as_dict=True,
		)
	if not store_location:
		store_location = frappe.db.get_value(
			"Store Location",
			{"pos_profile": doc.name},
			["name", "store_code", "store_name"],
			as_dict=True,
		)

	return {
		"success": True,
		"profile": {
			"name": doc.name,
			"company": doc.company,
			"warehouse": doc.warehouse,
			"customer": doc.customer,
			"selling_price_list": doc.selling_price_list,
			"cost_center": doc.cost_center,
			"income_account": doc.income_account,
			"expense_account": doc.expense_account,
			"write_off_account": getattr(doc, "write_off_account", None),
			"write_off_cost_center": getattr(doc, "write_off_cost_center", None),
			"blind_close": bool(doc.get("custom_blind_close")) if doc.get("custom_blind_close") is not None else True,
			"require_open_close_register": bool(doc.get("custom_require_open_close_register")) if doc.get("custom_require_open_close_register") is not None else True,
			"variance_alert_threshold": flt(doc.get("custom_variance_alert_threshold") or 0) or 5,
			"disabled": doc.disabled,
			"currency": getattr(doc, "currency", ""),
			"payment_methods": payment_methods,
			"item_groups": item_groups_list,
			"users": users_list,
			"store_location": store_location.name if store_location else None,
			"store_code": store_location.store_code if store_location else None,
			"store_name": store_location.store_name if store_location else None,
		},
	}


@frappe.whitelist(allow_guest=False)
def get_write_off_accounts(company: str | None = None):
	require_permission("settings.read")
	company = (
		cstr(company).strip()
		or frappe.db.get_single_value("Global Defaults", "default_company")
		or frappe.db.get_value("Company", {}, "name")
	)
	filters = {"disabled": 0, "is_group": 0, "root_type": "Expense"}
	if company:
		filters["company"] = company

	accounts = frappe.get_all(
		"Account",
		filters=filters,
		fields=["name", "account_name"],
		order_by="account_name asc",
	)
	default_account = frappe.get_cached_value("Company", company, "write_off_account") if company else None
	return {"accounts": accounts, "default": default_account}


@frappe.whitelist(allow_guest=False)
def get_write_off_cost_centers(company: str | None = None):
	require_permission("settings.read")
	company = (
		cstr(company).strip()
		or frappe.db.get_single_value("Global Defaults", "default_company")
		or frappe.db.get_value("Company", {}, "name")
	)
	filters = {"disabled": 0, "is_group": 0}
	if company:
		filters["company"] = company

	cost_centers = frappe.get_all(
		"Cost Center",
		filters=filters,
		fields=["name", "cost_center_name"],
		order_by="cost_center_name asc",
	)
	default_cc = frappe.get_cached_value("Company", company, "cost_center") if company else None
	return {"cost_centers": cost_centers, "default": default_cc}


@frappe.whitelist(allow_guest=False)
def create_pos_profile(
	company: str,
	warehouse: str,
	customer: str | None = None,
	selling_price_list: str | None = None,
	cost_center: str | None = None,
	income_account: str | None = None,
	expense_account: str | None = None,
	write_off_account: str | None = None,
	write_off_cost_center: str | None = None,
	payments_json: str | list | None = None,
	users_json: str | list | None = None,
	name_override: str | None = None,
	blind_close: int | bool = 1,
	require_open_close_register: int | bool = 0,
	variance_alert_threshold: float = 5,
	**kwargs,
):
	require_permission("settings.stores")

	import json

	company = cstr(company).strip()
	if not company:
		frappe.throw(_("Company is required"))

	is_admin = frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles()

	profile = frappe.new_doc("POS Profile")
	profile.company = company
	profile.warehouse = cstr(warehouse).strip()
	profile.custom_blind_close = cint(blind_close)
	profile.custom_require_open_close_register = cint(require_open_close_register) if is_admin else 0
	profile.custom_variance_alert_threshold = flt(variance_alert_threshold) or 5
	if name_override:
		profile.name = cstr(name_override).strip()
		profile.posa_pos_profile_name = cstr(name_override).strip()
	if customer:
		profile.customer = cstr(customer).strip()
	if selling_price_list:
		profile.selling_price_list = cstr(selling_price_list).strip()
	if cost_center:
		profile.cost_center = cstr(cost_center).strip()
	if income_account:
		profile.income_account = cstr(income_account).strip()
	if expense_account:
		profile.expense_account = cstr(expense_account).strip()

	if write_off_account:
		profile.write_off_account = cstr(write_off_account).strip()
	else:
		profile.write_off_account = (
			frappe.get_cached_value("Company", company, "write_off_account")
			or frappe.db.get_value("Account", {"company": company, "account_name": "Write Off"}, "name")
			or frappe.db.get_value("Account", {"company": company, "account_name": "Round Off"}, "name")
		)

	if write_off_cost_center:
		profile.write_off_cost_center = cstr(write_off_cost_center).strip()
	else:
		profile.write_off_cost_center = (
			profile.cost_center or frappe.get_cached_value("Company", company, "cost_center")
		)

	if payments_json:
		payments = json.loads(payments_json) if isinstance(payments_json, str) else payments_json
		for p in payments:
			mode = cstr(p.get("mode_of_payment", "")).strip()
			if not mode:
				continue
			profile.append(
				"payments",
				{
					"mode_of_payment": mode,
					"default": cint(p.get("default", 0)),
				},
			)

	profile.insert()

	if users_json:
		# Route membership writes through the one reconciler (POS issues
		# #14/#17/#11) — it also maintains Employee home stores, which a bare
		# child-table append never did.
		new_users = _resolve_profile_users(users_json)
		if new_users:
			from arijentek_core.api.store_allocation import _apply_store_allocations

			_apply_store_allocations(_profile_user_allocations(profile.name, new_users))

	publish_settings_update("pos_profile", "create")
	return {"success": True, "name": profile.name}


@frappe.whitelist(allow_guest=False)
def update_pos_profile(name: str, **kwargs):
	require_permission("settings.stores")
	name = cstr(name).strip()

	if not frappe.db.exists("POS Profile", name):
		frappe.throw(_("POS Profile not found"))

	doc = frappe.get_doc("POS Profile", name)

	updatable = [
		"warehouse",
		"customer",
		"selling_price_list",
		"cost_center",
		"income_account",
		"expense_account",
		"write_off_account",
		"write_off_cost_center",
		"disabled",
		"posa_pos_profile_name",
	]

	for field in updatable:
		if field in kwargs:
			setattr(doc, field, kwargs[field])

	# Register-close policy (blind close + variance threshold + open/close enforcement)
	if "blind_close" in kwargs:
		doc.custom_blind_close = cint(kwargs["blind_close"])
	if "require_open_close_register" in kwargs:
		is_admin = frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles()
		if not is_admin:
			frappe.throw(
				_("Only Administrators and System Managers can modify the register enforcement policy."),
				frappe.PermissionError,
			)
		doc.custom_require_open_close_register = cint(kwargs["require_open_close_register"])
	if "variance_alert_threshold" in kwargs:
		doc.custom_variance_alert_threshold = flt(kwargs["variance_alert_threshold"]) or 5

	if "payments_json" in kwargs:
		import json

		doc.payments = []
		payments = (
			json.loads(kwargs["payments_json"])
			if isinstance(kwargs["payments_json"], str)
			else kwargs["payments_json"]
		)
		for p in payments:
			mode = cstr(p.get("mode_of_payment", "")).strip()
			if not mode:
				continue
			doc.append(
				"payments",
				{
					"mode_of_payment": mode,
					"default": cint(p.get("default", 0)),
				},
			)

	doc.save()

	if "users_json" in kwargs:
		# Delegate to the reconciler AFTER doc.save() — the doc loaded above
		# still holds the pre-reconcile user list in memory, so saving it later
		# would undo the reconciler's membership writes. The reconciler also
		# keeps each user's memberships in OTHER profiles and maintains
		# Employee home stores (POS issues #14/#17/#11).
		new_users = _resolve_profile_users(kwargs["users_json"])
		from arijentek_core.api.store_allocation import _apply_store_allocations

		_apply_store_allocations(_profile_user_allocations(name, new_users))

	publish_settings_update("pos_profile", "update")
	return {"success": True, "name": doc.name}


@frappe.whitelist(allow_guest=False)
def delete_pos_profile(name: str):
	require_permission("settings.stores")
	name = cstr(name).strip()

	if not frappe.db.exists("POS Profile", name):
		frappe.throw(_("POS Profile not found"))

	has_invoices = frappe.db.count("POS Invoice", {"pos_profile": name})

	# 1. Unlink from any active Store Location records
	linked_stores = frappe.db.get_all("Store Location", filters={"pos_profile": name}, pluck="name")
	if linked_stores:
		for st_name in linked_stores:
			frappe.db.set_value("Store Location", st_name, "pos_profile", None)

	# Every exit below is a success (delete or safe-disable); deferred
	# publish means a rollback suppresses the event.
	publish_settings_update("pos_profile", "delete")

	if has_invoices > 0:
		frappe.db.set_value("POS Profile", name, "disabled", 1)
		return {
			"success": True,
			"action": "disabled",
			"has_transactions": True,
			"message": f"POS Profile '{name}' has recorded sales transactions. It has been unlinked from stores and disabled to preserve accounting audit compliance.",
		}

	# 2. Attempt hard deletion; fallback to disabling if referenced by historical invoices/transactions
	try:
		frappe.delete_doc("POS Profile", name, ignore_permissions=True)
		return {
			"success": True,
			"action": "deleted",
			"has_transactions": False,
			"message": f"POS Profile '{name}' deleted successfully.",
		}
	except frappe.LinkExistsError:
		frappe.db.set_value("POS Profile", name, "disabled", 1)
		return {
			"success": True,
			"action": "disabled",
			"has_transactions": True,
			"message": f"POS Profile '{name}' is linked with historical transaction records. It has been unlinked from stores and disabled.",
		}


@frappe.whitelist(allow_guest=False)
def delete_store(store_code: str, force_disable: int = 0):
	"""
	Deletes a store if it has 0 recorded transactions.
	If transactions exist, deactivates and hides the store location to protect accounting audit trails.
	"""
	require_permission("settings.stores")
	store_code = cstr(store_code).strip()

	if not frappe.db.exists("Store Location", store_code):
		frappe.throw(_("Store Location not found"))

	store_name = frappe.db.get_value("Store Location", store_code, "store_name") or store_code
	warehouse = frappe.db.get_value("Store Location", store_code, "default_warehouse")
	pos_profile = frappe.db.get_value("Store Location", store_code, "pos_profile")

	# Count historical transactions
	has_pos_invoices = frappe.db.count("POS Invoice", {"pos_profile": pos_profile}) if pos_profile else 0
	has_sales_invoices = frappe.db.count("Sales Invoice", {"set_warehouse": warehouse}) if warehouse else 0
	has_stock_entries = (
		(
			frappe.db.count("Stock Entry", {"from_warehouse": warehouse})
			+ frappe.db.count("Stock Entry", {"to_warehouse": warehouse})
		)
		if warehouse
		else 0
	)

	total_txns = has_pos_invoices + has_sales_invoices + has_stock_entries

	if total_txns > 0 or force_disable:
		frappe.db.set_value("Store Location", store_code, "is_active", 0)
		if pos_profile and frappe.db.exists("POS Profile", pos_profile):
			frappe.db.set_value("POS Profile", pos_profile, "disabled", 1)

		from arijentek_core.services.store_registry import clear_active_stores_cache

		clear_active_stores_cache()
		publish_settings_update("store", "delete")

		return {
			"success": True,
			"action": "disabled",
			"has_transactions": True,
			"message": f"Store '{store_name}' has {total_txns} historical record(s). To maintain tax and accounting audit compliance, the store has been deactivated and hidden from POS terminals.",
		}

	# 0 transactions: hard delete
	try:
		frappe.db.set_value("Store Location", store_code, "pos_profile", None)
		frappe.delete_doc("Store Location", store_code, force=True, ignore_permissions=True)

		if pos_profile and frappe.db.exists("POS Profile", pos_profile):
			try:
				frappe.delete_doc("POS Profile", pos_profile, force=True, ignore_permissions=True)
			except Exception:
				pass

		from arijentek_core.services.store_registry import clear_active_stores_cache

		clear_active_stores_cache()
		publish_settings_update("store", "delete")

		return {
			"success": True,
			"action": "deleted",
			"has_transactions": False,
			"message": f"Store '{store_name}' ({store_code}) had 0 transactions and has been permanently deleted.",
		}
	except Exception as e:
		frappe.log_error(f"Failed to delete store {store_code}: {e}")
		frappe.db.set_value("Store Location", store_code, "is_active", 0)
		from arijentek_core.services.store_registry import clear_active_stores_cache

		clear_active_stores_cache()
		publish_settings_update("store", "delete")
		return {
			"success": True,
			"action": "disabled",
			"has_transactions": True,
			"message": f"Store '{store_name}' has been deactivated and hidden from POS terminals.",
		}


@frappe.whitelist(allow_guest=False)
def get_users_with_roles(page: int = 1, page_size: int = 50):
	require_permission("settings.users")

	page = max(1, cint(page))
	page_size = min(100, max(1, cint(page_size)))
	limit_start = (page - 1) * page_size

	# Platform accounts are never tenant-visible (get_all bypasses the
	# permission_query_conditions).
	user_filters = {
		"enabled": 1,
		"user_type": "System User",
		"name": ["not in", get_internal_user_names()],
	}

	users = frappe.get_all(
		"User",
		filters=user_filters,
		fields=["name", "full_name", "email", "user_image", "creation"],
		order_by="full_name asc",
		limit_start=limit_start,
		limit=page_size,
	)
	total = frappe.db.count("User", user_filters)

	for u in users:
		roles = frappe.get_all(
			"Has Role",
			filters={"parent": u["name"], "parenttype": "User"},
			fields=["role"],
		)
		u["roles"] = [r["role"] for r in roles]

	return {"success": True, "users": users, "total": total, "page": page, "page_size": page_size}


@frappe.whitelist(allow_guest=False)
def update_user_roles(user_email: str, roles_json: str | list | None = None):
	require_permission("settings.users")

	import json

	user_email = cstr(user_email).strip()
	if not frappe.db.exists("User", user_email):
		frappe.throw(_("User not found"))

	roles = json.loads(roles_json) if isinstance(roles_json, str) else roles_json

	doc = frappe.get_doc("User", user_email)

	# Platform accounts are not editable from a tenant session (the
	# User.validate firewall guard_user_roles covers desk/REST writes).
	if user_email == "Administrator" or is_internal_user(user_email):
		frappe.throw(_("Platform accounts may only be managed by Gemora."), frappe.PermissionError)

	# Desk roles are platform-controlled: only current desk-role holders (or
	# the site Administrator) may grant or revoke them.
	if set(roles) & DESK_ROLES or {r.role for r in doc.roles} & DESK_ROLES:
		require_desk_grant_right()

	# Platform roles are never assignable from a tenant session; the owner
	# grant ("Admin User") needs the admin tier.
	from arijentek_core.services.internal_access import _is_platform_actor

	if set(roles) & PLATFORM_ROLES and not _is_platform_actor(frappe.session.user):
		frappe.throw(_("Platform roles are assigned by Gemora only."), frappe.PermissionError)
	if "Admin User" in set(roles) and not _is_admin_tier():
		frappe.throw(
			_("The owner persona may only be assigned by an administrator."),
			frappe.PermissionError,
		)

	existing_roles = {r.role for r in doc.roles}
	new_roles = set(roles)

	for role in new_roles - existing_roles:
		if frappe.db.exists("Role", role):
			doc.append("roles", {"role": role})

	for role in existing_roles - new_roles:
		if role in ("Administrator", "Guest"):
			continue
		doc.roles = [r for r in doc.roles if r.role != role]

	doc.save(ignore_permissions=True)
	return {"success": True}


@frappe.whitelist(allow_guest=False)
def create_user(
	email: str,
	first_name: str,
	last_name: str | None = None,
	roles_json: str | list | None = None,
	send_welcome_email: int = 1,
	password: str | None = None,
):
	require_permission("settings.users")

	import json

	email = cstr(email).strip().lower()
	first_name = cstr(first_name).strip()
	if not email or not first_name:
		frappe.throw(_("Email and first name are required"))

	if frappe.db.exists("User", email):
		frappe.throw(_("User already exists"))

	user = frappe.new_doc("User")
	user.email = email
	user.first_name = first_name
	user.last_name = cstr(last_name).strip() if last_name else ""
	user.send_welcome_email = cint(send_welcome_email)
	if password:
		user.send_welcome_email = 0
	user.user_type = "System User"

	if roles_json:
		roles = json.loads(roles_json) if isinstance(roles_json, str) else roles_json
		# Desk roles are platform-controlled (see update_user_roles).
		if set(roles) & DESK_ROLES:
			require_desk_grant_right()
		# Platform roles are never assignable from a tenant session; the
		# owner grant ("Admin User") needs the admin tier.
		from arijentek_core.services.internal_access import _is_platform_actor

		if set(roles) & PLATFORM_ROLES and not _is_platform_actor(frappe.session.user):
			frappe.throw(_("Platform roles are assigned by Gemora only."), frappe.PermissionError)
		if "Admin User" in set(roles) and not _is_admin_tier():
			frappe.throw(
				_("The owner persona may only be assigned by an administrator."),
				frappe.PermissionError,
			)
		for role in roles:
			if frappe.db.exists("Role", role):
				user.append("roles", {"role": role})

	user.insert(ignore_permissions=True)

	if password:
		from frappe.utils.password import update_password

		update_password(user.name, password)

	return {"success": True, "name": user.name}


@frappe.whitelist(methods=["POST"])
def change_own_password(current_password: str = "", new_password: str = "", logout_all_sessions: int = 1):
	"""Self-service password change for the logged-in user.

	Verifies the CURRENT password, then delegates to frappe's ``update_password``
	(which enforces strength policy and re-hashes). The My Profile panel
	previously called ``set_user_password`` — an admin-only method — so every
	non-admin user hit a PermissionError changing their own password.
	"""
	from frappe.core.doctype.user.user import update_password
	from frappe.utils.password import check_password

	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if not current_password or not new_password:
		frappe.throw(_("Current and new password are required."))

	try:
		check_password(user, current_password)
	except frappe.AuthenticationError:
		frappe.throw(_("Current password is incorrect."))

	if new_password == current_password:
		frappe.throw(_("The new password must be different from the current one."))

	update_password(new_password=new_password, old_password=current_password, logout_all_sessions=logout_all_sessions)
	return {"success": True, "message": _("Password updated.")}


@frappe.whitelist(methods=["POST"])
def set_user_password(email: str | None = None, user: str | None = None, password: str = ""):
	require_permission("settings.users")

	target_user = (user or email or "").strip()
	if not target_user:
		frappe.throw(_("User or email is required"))

	if not password or len(password) < 4:
		frappe.throw(_("Password must be at least 4 characters long."))

	user_name = frappe.db.get_value("User", {"name": target_user}) or frappe.db.get_value("User", {"email": target_user})
	if not user_name:
		frappe.throw(_("User not found"))

	# No tenant session may reset a platform account's password.
	if user_name == "Administrator" or is_internal_user(user_name):
		frappe.throw(_("Platform accounts may only be managed by Gemora."), frappe.PermissionError)

	from frappe.utils.password import update_password

	update_password(user_name, password)

	return {"success": True, "message": "Password updated successfully"}


@frappe.whitelist(allow_guest=False)
def get_print_formats(doctype: str | None = None):
	require_permission("settings.read")

	filters = {}
	if doctype:
		filters["doc_type"] = cstr(doctype).strip()

	formats = frappe.get_all(
		"Print Format",
		filters=filters,
		fields=["name", "doc_type", "standard", "custom_format", "print_style"],
		order_by="doc_type, name asc",
	)

	return {"success": True, "print_formats": formats}


@frappe.whitelist(allow_guest=False)
def get_company_settings():
	require_permission("settings.read")

	company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value(
		"Company", {}, "name"
	)
	if not company:
		return {"success": True, "company": None, "settings": {}}

	doc = frappe.get_doc("Company", company)

	return {
		"success": True,
		"company": company,
		"settings": {
			"company_name": doc.company_name,
			"abbr": doc.abbr,
			"default_currency": doc.default_currency,
			"country": doc.country,
			"tax_id": getattr(doc, "tax_id", ""),
			"registration_number": getattr(doc, "registration_number", ""),
		},
	}


@frappe.whitelist(allow_guest=False)
def get_system_info():
	require_permission("settings.system")

	from frappe.utils.user import get_system_managers

	return {
		"success": True,
		"system_info": {
			"frappe_version": frappe.__version__,
			"installed_apps": frappe.get_installed_apps(),
			"site_name": frappe.local.site,
			"default_company": frappe.db.get_single_value("Global Defaults", "default_company"),
			"system_managers": get_system_managers(),
			"maintenance_mode": frappe.conf.get("maintenance_mode", False),
		},
	}


@frappe.whitelist(allow_guest=False)
def create_store(
	store_name: str,
	store_code: str,
	company: str | None = None,
	store_type: str | None = None,
	county: str | None = None,
	county_tax_rate: float = 0.0,
	clone_from_store: str | None = None,
	seed_inventory: int = 0,
	terminal_count: int | str = 1,
):
	"""
	Provisions a new store:
	1. Warehouse
	1b. Cost Center (per-store accounting dimension)
	2. POS Profile (cloning settings if requested)
	3. Store Location (linked to warehouse + cost center + pos_profile)
	4. Optional draft stock transfer for initial inventory seeding
	"""
	require_permission("settings.stores")
	company = (
		company
		or frappe.defaults.get_user_default("Company")
		or frappe.db.get_single_value("Global Defaults", "default_company")
	)

	if not company:
		frappe.throw(_("Default Company is required to provision a store."))

	store_name = cstr(store_name).strip()
	store_code = cstr(store_code).strip()
	if not store_name or not store_code:
		frappe.throw(_("Store Name and Store Code are required"))

	# 1. Warehouse
	company_abbr = frappe.get_cached_value("Company", company, "abbr") or "ZFJ"
	parent_warehouse = (
		frappe.db.get_value("Warehouse", {"warehouse_name": "Store Warehouses", "company": company}, "name")
		or frappe.db.get_value("Warehouse", {"warehouse_name": "All Warehouses", "company": company}, "name")
		or frappe.db.get_value("Warehouse", {"is_group": 1, "parent_warehouse": ["in", ["", None]], "company": company}, "name")
		or frappe.db.get_value("Warehouse", {"is_group": 1, "company": company}, "name")
		or f"All Warehouses - {company_abbr}"
	)

	wh_name = f"{store_name} - {company_abbr}"

	if not frappe.db.exists("Warehouse", wh_name):
		wh = frappe.new_doc("Warehouse")
		wh.warehouse_name = store_name
		wh.company = company
		wh.parent_warehouse = parent_warehouse
		wh.insert(ignore_permissions=True)
		warehouse_id = wh.name
	else:
		warehouse_id = wh_name

	# 1b. Cost Center — accounting dimension
	cost_center = (
		frappe.db.get_value("Cost Center", {"company": company, "is_group": 0}, "name")
		or f"Main - {company_abbr}"
	)

	# 1c. Ensure standard payment modes have default accounts configured for this company
	cash_account = (
		frappe.db.get_value("Account", {"company": company, "account_type": "Cash", "is_group": 0}, "name")
		or f"Cash - {company_abbr}"
	)
	bank_account = (
		frappe.db.get_value("Account", {"company": company, "account_type": "Bank", "is_group": 0}, "name")
		or f"Bank - {company_abbr}"
	)

	standard_modes = ["Cash", "Credit Card", "Debit Card", "Check", "Wire Transfer", "Zelle"]
	for m_name in standard_modes:
		if frappe.db.exists("Mode of Payment", m_name):
			has_acc = frappe.db.exists("Mode of Payment Account", {"parent": m_name, "company": company})
			if not has_acc:
				target_acc = cash_account if m_name == "Cash" else (bank_account or cash_account)
				if target_acc and frappe.db.exists("Account", target_acc):
					try:
						mop_doc = frappe.get_doc("Mode of Payment", m_name)
						mop_doc.append("accounts", {"company": company, "default_account": target_acc})
						mop_doc.save(ignore_permissions=True)
					except Exception:
						pass

	# Ensure company-specific float GL account exists and is linked
	float_account = f"Asset — Cash Drawer Float - {company_abbr}"
	if not frappe.db.exists("Account", float_account):
		cash_in_hand = (
			frappe.db.get_value("Account", {"company": company, "account_type": "Cash", "is_group": 1}, "name")
			or f"Cash In Hand - {company_abbr}"
		)
		if not frappe.db.exists("Account", cash_in_hand):
			cash_in_hand = f"Current Assets - {company_abbr}"
		if frappe.db.exists("Account", cash_in_hand):
			try:
				frappe.get_doc({
					"doctype": "Account",
					"account_name": "Asset — Cash Drawer Float",
					"parent_account": cash_in_hand,
					"company": company,
					"account_type": "Cash",
					"is_group": 0,
				}).insert(ignore_permissions=True)
			except Exception:
				pass
	if not frappe.db.exists("Account", float_account):
		float_account = cash_account

	# 2. POS Profile
	profile_name = f"{store_name} POS"
	src_store_name = None
	source_profile_name = None
	if clone_from_store:
		src_store_name = (
			frappe.db.get_value("Store Location", clone_from_store, "name")
			or frappe.db.get_value("Store Location", {"store_code": clone_from_store}, "name")
			or frappe.db.get_value("Store Location", {"store_name": clone_from_store}, "name")
		)
		if src_store_name:
			source_profile_name = frappe.db.get_value("Store Location", src_store_name, "pos_profile")
	if not source_profile_name:
		source_profile_name = frappe.db.get_value("POS Profile", {"company": company}, "name")

	if not frappe.db.exists("POS Profile", profile_name):
		if source_profile_name and frappe.db.exists("POS Profile", source_profile_name):
			profile = frappe.copy_doc(frappe.get_doc("POS Profile", source_profile_name))
			profile.name = profile_name
			profile.pos_profile_name = profile_name
			profile.warehouse = warehouse_id
			profile.cost_center = cost_center
			profile.posa_pos_profile_name = store_name
			profile.custom_float_gl_account = float_account
			profile.set("applicable_for_users", [])
			profile.insert(ignore_permissions=True)
		else:
			profile = frappe.new_doc("POS Profile")
			profile.name = profile_name
			profile.pos_profile_name = profile_name
			profile.posa_pos_profile_name = store_name
			profile.company = company
			profile.warehouse = warehouse_id
			profile.cost_center = cost_center
			profile.custom_float_gl_account = float_account
			profile.currency = frappe.db.get_value("Company", company, "default_currency") or "USD"
			profile.selling_price_list = (
				frappe.db.get_value("Price List", {"selling": 1}, "name") or "Standard Selling"
			)
			write_off = (
				frappe.db.get_value("Account", {"company": company, "account_name": ["like", "%Write Off%"]}, "name")
				or f"Write Off - {company_abbr}"
			)
			profile.write_off_account = write_off if frappe.db.exists("Account", write_off) else ""
			profile.write_off_cost_center = cost_center

			# Add payment methods
			for m_name in standard_modes:
				if frappe.db.exists("Mode of Payment", m_name):
					profile.append("payments", {
						"mode_of_payment": m_name,
						"default": 1 if m_name == "Cash" else 0,
					})

			profile.insert(ignore_permissions=True)

	# 3. Store Location
	existing_loc = (
		frappe.db.get_value("Store Location", {"store_code": store_code}, "name")
		or frappe.db.get_value("Store Location", store_code, "name")
	)
	if not existing_loc:
		sl = frappe.new_doc("Store Location")
		sl.store_code = store_code
		sl.store_name = store_name
		sl.company = company
		sl.default_warehouse = warehouse_id
		sl.default_cost_center = cost_center
		sl.pos_profile = profile_name
		sl.is_active = 1
		if store_type:
			sl.store_type = cstr(store_type)
		if county:
			sl.county = cstr(county)
		if county_tax_rate:
			sl.county_tax_rate = flt(county_tax_rate)
		if src_store_name and frappe.db.exists("Store Location", src_store_name):
			src_loc = frappe.get_doc("Store Location", src_store_name)
			if src_loc.tax_system:
				sl.tax_system = src_loc.tax_system
			if src_loc.tax_components:
				sl.set("tax_components", [])
				for c in src_loc.tax_components:
					sl.append(
						"tax_components",
						{
							"component": c.component,
							"rate": c.rate,
							"charge_type": c.charge_type,
							"row_id": c.row_id,
							"included_in_print_rate": getattr(c, "included_in_print_rate", 0),
						},
					)
			if src_loc.tax_template and frappe.db.exists("Sales Taxes and Charges Template", src_loc.tax_template):
				sl.tax_template = src_loc.tax_template
			if not sl.county and src_loc.county:
				sl.county = src_loc.county
			if not sl.county_tax_rate and src_loc.county_tax_rate:
				sl.county_tax_rate = src_loc.county_tax_rate
		sl.insert(ignore_permissions=True)
	else:
		sl = frappe.get_doc("Store Location", existing_loc)
		sl.default_warehouse = warehouse_id
		sl.default_cost_center = cost_center
		sl.pos_profile = profile_name
		sl.is_active = 1
		if store_type:
			sl.store_type = cstr(store_type)
		if county:
			sl.county = cstr(county)
		if county_tax_rate:
			sl.county_tax_rate = flt(county_tax_rate)
		sl.save(ignore_permissions=True)

	# Link Store Location tax_template to POS Profile taxes_and_charges
	if sl.tax_template and frappe.db.exists("POS Profile", profile_name):
		frappe.db.set_value("POS Profile", profile_name, "taxes_and_charges", sl.tax_template)

	# 4. Initial Stock Entry Seeding if requested
	transfer_name = None
	if seed_inventory and src_store_name:
		src_wh = frappe.db.get_value("Store Location", src_store_name, "default_warehouse")
		if src_wh and src_wh != warehouse_id:
			items_with_qty = frappe.db.sql(
				"""
				SELECT item_code, actual_qty
				FROM `tabBin`
				WHERE warehouse = %s AND actual_qty > 0
			""",
				(src_wh,),
				as_dict=True,
			)

			if items_with_qty:
				try:
					se = frappe.new_doc("Stock Entry")
					se.purpose = "Material Transfer"
					se.company = company
					se.from_warehouse = src_wh
					se.to_warehouse = warehouse_id
					for item in items_with_qty:
						se.append(
							"items",
							{
								"item_code": item.item_code,
								"qty": float(item.actual_qty),
								"s_warehouse": src_wh,
								"t_warehouse": warehouse_id,
							},
						)
					se.insert(ignore_permissions=True)
					try:
						se.submit()
					except Exception as sub_err:
						frappe.log_error(f"Stock Entry inserted but submit failed: {sub_err}")
					transfer_name = se.name
				except Exception as e:
					frappe.log_error(f"Failed to create initial stock transfer: {e}")

	# 5. Provision requested POS Terminals (shared-terminal kiosks)
	provisioned_terminals = []
	term_count = max(0, cint(terminal_count)) if terminal_count is not None else 1
	if term_count > 0:
		import re

		from arijentek_core.api.terminals import create_terminal_user

		clean_code = re.sub(r"[^a-zA-Z0-9]", "", store_code).lower() or "store"
		domain = "zevar.local"
		if "@" in frappe.session.user:
			u_dom = frappe.session.user.split("@")[-1].strip().lower()
			if u_dom and "." in u_dom and u_dom != "example.com":
				domain = u_dom

		for i in range(1, term_count + 1):
			t_code = f"{store_code}-T{i}"
			t_name = f"{store_name} Terminal {i}"
			kiosk_email = f"terminal-{clean_code}-{i}@{domain}"

			try:
				t_res = create_terminal_user(
					email=kiosk_email,
					first_name=t_name,
					terminal_code=t_code,
					terminal_name=t_name,
					store_location=sl.name,
					pos_profile=profile_name,
				)
				provisioned_terminals.append(
					{
						"terminal_code": t_code,
						"terminal_name": t_name,
						"user": t_res.get("user") or kiosk_email,
						"generated_password": t_res.get("generated_password"),
					}
				)
			except Exception as e:
				frappe.log_error(f"Failed to auto-provision terminal {t_code} for store {store_code}: {e}")

	from arijentek_core.services.store_registry import clear_active_stores_cache

	clear_active_stores_cache()

	publish_settings_update("store", "create")

	return {
		"success": True,
		"message": f"Store '{store_name}' ({store_code}) successfully provisioned.",
		"warehouse": warehouse_id,
		"cost_center": cost_center,
		"pos_profile": profile_name,
		"initial_transfer": transfer_name,
		"terminals": provisioned_terminals,
	}


@frappe.whitelist(allow_guest=False)
def create_tax_template(
	title: str, rate: float = 0.0, account_head: str | None = None, company: str | None = None
):
	require_permission("settings.finance")
	title = cstr(title).strip()
	if not title:
		frappe.throw(_("Tax Template Title is required"))

	company = (
		company
		or frappe.db.get_single_value("Global Defaults", "default_company")
		or frappe.db.get_value("Company", {}, "name")
	)
	if not company:
		frappe.throw(_("Company is required"))

	company_abbr = frappe.get_cached_value("Company", company, "abbr") or "ZFJ"
	if not account_head or frappe.db.get_value("Account", account_head, "is_group"):
		account_head = frappe.db.get_value("Account", {"company": company, "account_type": "Tax", "is_group": 0}, "name")

	clean_title = title[:-len(f"- {company_abbr}")].strip() if title.endswith(f"- {company_abbr}") else title
	template_name = f"{clean_title} - {company_abbr}"
	if frappe.db.exists("Sales Taxes and Charges Template", template_name):
		frappe.throw(f"Tax template '{template_name}' already exists.")

	doc = frappe.new_doc("Sales Taxes and Charges Template")
	doc.title = clean_title
	doc.company = company
	doc.append(
		"taxes",
		{
			"charge_type": "On Net Total",
			"account_head": account_head,
			"description": clean_title,
			"rate": flt(rate),
		},
	)
	doc.insert(ignore_permissions=True)

	return {"success": True, "name": doc.name, "title": doc.title, "rate": flt(rate)}


@frappe.whitelist(allow_guest=False)
def update_tax_template(
	name: str,
	title: str | None = None,
	rate: float | None = None,
	account_head: str | None = None,
	disabled: int | None = None,
):
	require_permission("settings.finance")
	name = cstr(name).strip()
	if not frappe.db.exists("Sales Taxes and Charges Template", name):
		frappe.throw(f"Tax Template '{name}' not found.")

	doc = frappe.get_doc("Sales Taxes and Charges Template", name)
	if title:
		doc.title = cstr(title).strip()
	if disabled is not None:
		doc.disabled = cint(disabled)

	if rate is not None or account_head is not None:
		if doc.taxes:
			if rate is not None:
				doc.taxes[0].rate = flt(rate)
			if account_head:
				doc.taxes[0].account_head = cstr(account_head).strip()
		else:
			company = doc.company
			acct = account_head or frappe.db.get_value(
				"Account", {"company": company, "account_type": "Tax", "is_group": 0}, "name"
			)
			doc.append(
				"taxes",
				{
					"charge_type": "On Net Total",
					"account_head": acct,
					"description": doc.title,
					"rate": flt(rate or 0.0),
				},
			)

	doc.save(ignore_permissions=True)
	return {"success": True, "name": doc.name}


@frappe.whitelist(allow_guest=False)
def delete_tax_template(name: str):
	require_permission("settings.finance")
	name = cstr(name).strip()
	if not frappe.db.exists("Sales Taxes and Charges Template", name):
		frappe.throw(f"Tax Template '{name}' not found.")

	try:
		frappe.delete_doc("Sales Taxes and Charges Template", name, ignore_permissions=True)
	except frappe.LinkExistsError:
		frappe.db.set_value("Sales Taxes and Charges Template", name, "disabled", 1)
		return {
			"success": True,
			"disabled": True,
			"message": "Template is linked to transactions and was disabled instead of deleted.",
		}

	return {"success": True, "deleted": True}


@frappe.whitelist(allow_guest=False)
def get_setup_checklist():
	"""Admin setup progress: each step links to where it gets completed."""
	require_permission("settings.read")

	company = (
		frappe.db.get_single_value("Global Defaults", "default_company")
		or frappe.db.get_value("Company", {}, "name")
	)

	company_ok = False
	if company:
		company_doc = frappe.db.get_value(
			"Company",
			company,
			["tax_id", "custom_business_phone", "custom_company_address_line1", "company_logo"],
			as_dict=True,
		)
		company_ok = bool(
			company_doc
			and (company_doc.custom_company_address_line1 or company_doc.custom_business_phone)
		)

	stores_with_address = 0
	active_stores = 0
	if frappe.db.exists("DocType", "Store Location"):
		active_stores = frappe.db.count("Store Location", {"is_active": 1})
		stores_with_address = frappe.db.count("Store Location", {"is_active": 1, "address_line1": ["is", "set"]})

	policies_ok = bool(frappe.db.get_single_value("Zevar Business Settings", "return_policy_text"))
	legal_reviewed = (
		frappe.db.get_single_value("Zevar Business Settings", "legal_review_status") or "Not Reviewed"
	) != "Not Reviewed"

	finance_healthy = False
	try:
		from arijentek_core.services.finance_resolver import pending_placeholders

		finance_healthy = not pending_placeholders()
	except Exception:
		pass

	mop_mapped = False
	try:
		mapped = frappe.db.count("Mode of Payment Account", {"company": company or "%"})
		mop_mapped = mapped > 0
	except Exception:
		pass

	pos_profiles = frappe.db.count("POS Profile", {"disabled": 0}) if company else 0

	users_with_roles = 0
	if frappe.db.exists("DocType", "User"):
		users_with_roles = len(
			{
				parent
				for parent in frappe.get_all(
					"Has Role",
					filters={
						"role": ["in", ["Store Manager", "Sales Manager", "Sales User"]],
						"parenttype": "User",
					},
					pluck="parent",
					limit=100,
				)
				if parent not in ("Administrator", "Guest")
			}
		)

	print_formats_ok = False
	try:
		from arijentek_core.api.printing import get_print_gallery

		print_formats_ok = all(
			e.get("available")
			for e in (get_print_gallery().get("formats") or [])
			if e.get("format") in ("pos_receipt_thermal", "layaway_contract", "z_report")
		)
	except Exception:
		pass

	push_ready = False
	try:
		push_ready = bool(frappe.db.get_single_value("Web Push Settings", "vapid_public_key"))
	except Exception:
		pass

	manager_pin_ready = False
	try:
		from arijentek_core.api.permissions import get_manager_pin_status

		manager_pin_ready = get_manager_pin_status().get("any_manager_has_pin")
	except Exception:
		pass

	steps = [
		{
			"key": "identity",
			"label": "Business identity (address, phone, logo)",
			"done": company_ok and stores_with_address >= max(active_stores, 1),
			"link": "/account",
		},
		{
			"key": "manager_pin",
			"label": "Manager PIN set (overrides & drawer close)",
			"done": manager_pin_ready,
			"link": "/settings?tab=account",
		},
		{
			"key": "policies",
			"label": "Customer-facing policies set",
			"done": policies_ok,
			"link": "/account",
		},
		{
			"key": "legal",
			"label": "Policies reviewed (attorney sign-off)",
			"done": legal_reviewed,
			"link": "/account",
		},
		{
			"key": "banks",
			"label": "Real bank accounts (no placeholders)",
			"done": finance_healthy,
			"link": "/finance-setup",
		},
		{
			"key": "payments",
			"label": "Payment methods mapped to accounts",
			"done": mop_mapped,
			"link": "/settings?tab=payments",
		},
		{
			"key": "pos",
			"label": "At least one POS profile",
			"done": pos_profiles > 0,
			"link": "/settings?tab=pos",
		},
		{
			"key": "staff",
			"label": "Staff users have roles",
			"done": users_with_roles > 0,
			"link": "/settings?tab=users",
		},
		{
			"key": "prints",
			"label": "Core print formats ready",
			"done": print_formats_ok,
			"link": "/settings?tab=printing",
		},
		{
			"key": "push",
			"label": "Browser notifications configured",
			"done": push_ready,
			"link": "/settings?tab=integrations",
		},
	]
	return {"success": True, "steps": steps, "completed": sum(1 for s in steps if s["done"]), "total": len(steps)}
