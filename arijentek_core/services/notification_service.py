"""
Notification service — the single funnel every notification flows through.

One call, ``notify(...)``, fans out to all channels:
  1. persisted feed rows (Zevar Notification) with per-user read state + dedup
  2. browser/OS web push (reuses zevar_core.api.web_push.send_push_notification)
  3. in-app realtime (``zevar_alert`` socket event, same payload shape the
	 NotificationCenter already listens to)

Per-user preferences (Zevar Notification Preference, falling back to
Zevar Notification Settings defaults) decide in-app vs push per category.
Never raises — a notification failure must never break the business flow
that triggered it (same contract as services/transfer_notifications.py).
"""

import json

import frappe
from frappe.utils import cstr, now_datetime

CATEGORIES = (
	"Security",
	"Inventory",
	"Layaway",
	"Repair",
	"Appraisal",
	"Memo",
	"Special Order",
	"CRM",
	"Compliance",
	"Finance",
	"HR",
	"System",
)

SEVERITIES = ("info", "warning", "critical")

# alert_type (computed engine / publish_alert) → feed category
CATEGORY_BY_ALERT_TYPE = {
	"cash_variance": "Finance",
	"stale_register": "Security",
	"large_return": "Finance",
	"no_sales": "Finance",
	"low_stock": "Inventory",
	"stockout": "Inventory",
	"negative_stock": "Inventory",
	"orphan_reservations": "Inventory",
	"transfer": "Inventory",
	"repair_overdue": "Repair",
	"repair_stuck": "Repair",
	"repair_no_deposit": "Repair",
}

MANAGER_ROLES = ("Store Manager", "Sales Manager", "System Manager", "Accounts Manager")


def resolve_category(alert_type: str | None, fallback: str = "System") -> str:
	"""Map a computed alert_type onto a feed category."""
	if not alert_type:
		return fallback
	if alert_type in CATEGORY_BY_ALERT_TYPE:
		return CATEGORY_BY_ALERT_TYPE[alert_type]
	prefix = alert_type.split("_")[0]
	for category in CATEGORIES:
		if prefix.lower() == category.split()[0].lower():
			return category
	return fallback


def _get_setting_defaults() -> dict:
	"""{category: {"in_app": bool, "push": bool}} from the settings singleton."""
	defaults = {}
	try:
		raw = frappe.db.get_single_value("Zevar Notification Settings", "default_preferences")
		if raw:
			defaults = json.loads(raw) if isinstance(raw, str) else (raw or {})
	except Exception:
		defaults = {}
	return defaults if isinstance(defaults, dict) else {}


def _prefs_for(user: str) -> dict:
	"""Per-category preference map for a user ({} = use defaults)."""
	defaults = _get_setting_defaults()

	# raw SQL read: value_cache returns stale results around test-suite
	# inserts/deletes on this bench (see memory: zevar-bench-test-environment)
	try:
		rows = frappe.db.sql(
			"SELECT use_defaults, preferences FROM `tabZevar Notification Preference` "
			"WHERE user=%s LIMIT 1",
			(user,),
			as_dict=True,
		)
	except Exception:
		rows = []
	row = rows[0] if rows else None
	if not row or cstr(row.use_defaults) in ("1", "True", True):
		return defaults
	try:
		prefs = json.loads(row.preferences) if row.preferences else defaults
	except Exception:
		prefs = defaults
	return prefs if isinstance(prefs, dict) else {}


def _channels_enabled(user: str, category: str) -> tuple[bool, bool]:
	"""(in_app, push) for a user+category. Default: both enabled."""
	prefs = _prefs_for(user)
	entry = prefs.get(category) or {}
	return bool(entry.get("in_app", True)), bool(entry.get("push", True))


def _push_globally_enabled() -> bool:
	try:
		return cstr(
			frappe.db.get_single_value("Zevar Notification Settings", "push_enabled")
		) in ("1", "True", True, "")
	except Exception:
		return True


def _has_unread_duplicate(user: str, dedup_key: str) -> bool:
	if not dedup_key:
		return False
	# raw SQL existence check: value_cache can return stale results after deletes
	# (`read` is a MariaDB reserved word — must stay backticked)
	return bool(
		frappe.db.sql(
			"SELECT name FROM `tabZevar Notification` "
			"WHERE user=%s AND dedup_key=%s AND `read`=0 LIMIT 1",
			(user, dedup_key),
		)
	)


def users_with_role(role: str) -> list[str]:
	"""Enabled users holding a role (excluding Administrator/Guest)."""
	try:
		holders = frappe.get_all(
			"Has Role",
			filters={"role": role, "parenttype": "User"},
			pluck="parent",
		)
	except Exception:
		return []
	if not holders:
		return []
	disabled = {
		u.name for u in frappe.get_all("User", filters={"enabled": 0}, pluck="name")
	}
	return [u for u in holders if u not in ("Administrator", "Guest") and u not in disabled]


def _dedupe(seq: list[str]) -> list[str]:
	seen, out = set(), []
	for item in seq:
		if item and item not in seen and item not in ("Administrator", "Guest"):
			seen.add(item)
			out.append(item)
	return out


def notify(
	users: list[str] | None = None,
	target_role: str | None = None,
	category: str = "System",
	severity: str = "info",
	title: str = "",
	message: str = "",
	link_doctype: str | None = None,
	link_name: str | None = None,
	dedup_key: str | None = None,
	source: str = "Event",
	push: bool = True,
	push_url: str | None = None,
	realtime: bool = True,
) -> list[str]:
	"""Fan one notification out to all channels. Returns notified users.

	 :param users: explicit recipient user ids
	 :param target_role: notify every enabled user holding this role
	 :param category: one of CATEGORIES (drives per-user prefs + filter chips)
	 :param severity: info | warning | critical
	 :param dedup_key: skip users who already have an UNREAD row with this key
	 :param source: Event | Computed | Notification Log
	 :param push_url: deep link used by the OS notification click
	 :param realtime: emit the socket event (set False when the caller already
	     publishes the same event, e.g. publish_alert)
	"""
	recipients = _dedupe(list(users or []))
	if target_role:
		recipients = _dedupe(recipients + users_with_role(target_role))
	if not recipients:
		return []

	if category not in CATEGORIES:
		category = resolve_category(category)
	severity = severity.lower()
	if severity not in SEVERITIES:
		severity = "info"
	# Select field stores capitalized options (Info / Warning / Critical)
	severity = severity.title()

	notified = []
	push_enabled_global = _push_globally_enabled() and push

	for user in recipients:
		try:
			if _has_unread_duplicate(user, dedup_key):
				continue

			in_app, push_user = _channels_enabled(user, category)

			if in_app:
				try:
					_insert_feed_row(
						user, category, severity, title, message,
						link_doctype, link_name, dedup_key, source,
					)
				except Exception:
					# A stale/deleted link reference must not lose the notification
					# entirely — retry without the link.
					_insert_feed_row(
						user, category, severity, title, message,
						None, None, dedup_key, source,
					)

			# Realtime bell event — same payload shape publish_alert emits.
			if in_app and realtime:
				frappe.publish_realtime(
					event="zevar_alert",
					message={
						"severity": severity,
						"type": category,
						"category": category,
						"title": title,
						"message": message,
						"reference_doctype": link_doctype,
						"reference_name": link_name,
						"timestamp": str(now_datetime()),
					},
					user=user,
				)

			if push_enabled_global and push_user:
				from arijentek_core.api.web_push import send_push_notification

				send_push_notification(
					user,
					title,
					message,
					url=push_url or _deep_link(link_doctype, link_name),
					app_type="pos",
				)

			if in_app or (push_enabled_global and push_user):
				notified.append(user)
		except Exception:
			frappe.log_error(
				title="Notification Fan-out Failed",
				message=f"user={user} category={category} title={title}\n{frappe.get_traceback()}",
			)

	try:
		frappe.db.commit()
	except Exception:
		pass

	return notified


def _insert_feed_row(
	user: str,
	category: str,
	severity: str,
	title: str,
	message: str,
	link_doctype: str | None,
	link_name: str | None,
	dedup_key: str | None,
	source: str,
):
	frappe.get_doc(
		{
			"doctype": "Zevar Notification",
			"user": user,
			"category": category,
			"severity": severity,
			"title": title,
			"message": message,
			"link_doctype": link_doctype,
			"link_name": link_name,
			"dedup_key": dedup_key,
			"source": source,
			"read": 0,
		}
	).insert(ignore_permissions=True)


def _deep_link(link_doctype: str | None, link_name: str | None) -> str:
	"""POS deep link for a notification click (hash routes the SW understands)."""
	routes = {
		"Layaway Contract": "/pos/#/layaways",
		"Repair Order": "/pos/#/repairs",
		"Item": "/pos/#/stock/manage",
		"Sales Invoice": "/pos/#/transactions",
		"POS Closing Entry": "/pos/#/pos-sessions",
		"Store Transfer": "/pos/#/stock-transfers",
		"Special Order": "/pos/#/special-orders",
		"Quotation": "/pos/#/quotes",
		"Jewelry Appraisal": "/pos/#/appraisals",
		"Memo Contract": "/pos/#/vendors",
	}
	base = routes.get(link_doctype, "/pos/#/reports/live-monitor")
	return f"{base}?doc={link_name}" if link_name and "?" not in base else base
