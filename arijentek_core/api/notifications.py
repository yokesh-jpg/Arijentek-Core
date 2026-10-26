"""
Notification & Alert System API — Unified alert engine for all dashboard types.

Combines anomaly detection, inventory alerts, cash management alerts, and
sales alerts into a single real-time notification stream.
"""

from typing import Any

import frappe
from frappe import _
from frappe.utils import add_days, cint, cstr, flt, getdate, now_datetime, today

# ──────────────────────────────────────────────────
# 1. Unified Alert Engine
# ──────────────────────────────────────────────────


@frappe.whitelist(allow_guest=False)
def get_alerts(severity: str | None = None, limit: int = 50) -> dict[str, Any]:
	"""Get all active alerts for the current user, scoped by role.

	Returns alerts from multiple sources: repairs, inventory, cash, sales.
	Each alert has: severity, type, title, message, timestamp, reference.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	is_admin = bool(set(roles) & {"System Manager", "Accounts Manager"})
	is_manager = bool(set(roles) & {"Store Manager", "Store Supervisor"}) or is_admin

	alerts: list[dict] = []

	# ── Repair Alerts (all authenticated users see their own; managers see all) ──
	alerts.extend(_get_repair_alerts(is_manager))

	# ── Inventory Alerts (managers and admins) ──
	if is_manager:
		alerts.extend(_get_inventory_alerts())

	# ── Cash Alerts (managers and admins) ──
	if is_manager:
		alerts.extend(_get_cash_alerts())

	# ── Sales Alerts (all staff) ──
	alerts.extend(_get_sales_alerts(is_manager))

	# Sort by severity then timestamp
	severity_order = {"critical": 0, "warning": 1, "info": 2}
	alerts.sort(key=lambda a: (severity_order.get(a.get("severity"), 9), a.get("timestamp", "")))

	if severity:
		alerts = [a for a in alerts if a.get("severity") == severity]

	return {
		"alerts": alerts[: cint(limit)],
		"total": len(alerts),
		"unread_count": len([a for a in alerts if a.get("severity") in ("critical", "warning")]),
		"timestamp": str(now_datetime()),
	}


@frappe.whitelist(allow_guest=False)
def get_alert_summary() -> dict[str, Any]:
	"""Lightweight summary for the notification bell badge.

	Returns counts by severity and the 3 most recent alerts.
	"""
	data = get_alerts(limit=10)
	alerts = data["alerts"]
	return {
		"critical": len([a for a in alerts if a.get("severity") == "critical"]),
		"warning": len([a for a in alerts if a.get("severity") == "warning"]),
		"info": len([a for a in alerts if a.get("severity") == "info"]),
		"total": data["total"],
		"recent": alerts[:3],
	}


# ──────────────────────────────────────────────────
# 2. Alert Source: Repairs
# ──────────────────────────────────────────────────


def _get_repair_alerts(is_manager: bool) -> list[dict]:
	"""Repair-related alerts: overdue, stuck, unassigned, no deposit."""
	alerts: list[dict] = []
	today_date = today()

	# Severely overdue repairs (>7 days past promised date)
	overdue = frappe.db.sql(
		"""
		SELECT name, customer, promised_date, status, warehouse,
		       DATEDIFF(%(today)s, promised_date) as days_overdue
		FROM `tabRepair Order`
		WHERE status NOT IN ('Delivered', 'Cancelled')
		  AND promised_date IS NOT NULL
		  AND DATEDIFF(%(today)s, promised_date) > 7
		ORDER BY days_overdue DESC
		LIMIT 10
	""",
		{"today": today_date},
		as_dict=True,
	)

	for r in overdue:
		alerts.append(
			{
				"severity": "critical",
				"type": "repair_overdue",
				"title": f"Overdue: {r.name}",
				"message": f"{r.customer} — {r.days_overdue} days past due",
				"reference_doctype": "Repair Order",
				"reference_name": r.name,
				"timestamp": str(now_datetime()),
			}
		)

	# Stuck repairs (no activity in 5+ days)
	if is_manager:
		stuck = frappe.db.sql(
			"""
			SELECT name, customer, status, modified, warehouse,
			       DATEDIFF(%(today)s, modified) as days_stuck
			FROM `tabRepair Order`
			WHERE status IN ('In Progress', 'Waiting for Parts', 'Estimated')
			  AND DATEDIFF(%(today)s, modified) >= 5
			ORDER BY days_stuck DESC
			LIMIT 5
		""",
			{"today": today_date},
			as_dict=True,
		)

		for r in stuck:
			alerts.append(
				{
					"severity": "warning",
					"type": "repair_stuck",
					"title": f"Stuck: {r.name}",
					"message": f"No activity for {r.days_stuck} days (status: {r.status})",
					"reference_doctype": "Repair Order",
					"reference_name": r.name,
					"timestamp": str(r.modified),
				}
			)

	# High-value without deposit (>$500)
	if is_manager:
		no_deposit = frappe.db.sql(
			"""
			SELECT name, customer, estimated_cost
			FROM `tabRepair Order`
			WHERE estimated_cost > 500
			  AND (deposit_amount IS NULL OR deposit_amount = 0)
			  AND status NOT IN ('Delivered', 'Cancelled')
			LIMIT 5
		""",
			as_dict=True,
		)

		for r in no_deposit:
			alerts.append(
				{
					"severity": "warning",
					"type": "repair_no_deposit",
					"title": f"No deposit: {r.name}",
					"message": f"${r.estimated_cost:.2f} repair for {r.customer} — no deposit",
					"reference_doctype": "Repair Order",
					"reference_name": r.name,
					"timestamp": str(now_datetime()),
				}
			)

	return alerts


# ──────────────────────────────────────────────────
# 3. Alert Source: Inventory
# ──────────────────────────────────────────────────


def _get_inventory_alerts() -> list[dict]:
	"""Inventory alerts: low stock, overstock, reorder needed."""
	alerts: list[dict] = []

	# Low stock items (actual qty <= reorder_level)
	if not frappe.db.table_exists("Item"):
		return alerts

	low_stock = frappe.db.sql(
		"""
		SELECT i.name, i.item_name, i.item_code,
		       COALESCE(b.actual_qty, 0) as actual_qty,
		       COALESCE(b.warehouse, '') as warehouse
		FROM `tabItem` i
		LEFT JOIN `tabBin` b ON b.item_code = i.item_code
		WHERE i.disabled = 0
		  AND i.is_stock_item = 1
		  AND COALESCE(b.actual_qty, 0) <= COALESCE(i.safety_stock, 0)
		  AND COALESCE(i.safety_stock, 0) > 0
		LIMIT 10
	""",
		as_dict=True,
	)

	for item in low_stock:
		alerts.append(
			{
				"severity": "warning",
				"type": "low_stock",
				"title": f"Low stock: {item.item_name or item.item_code}",
				"message": f"Qty: {item.actual_qty:.0f} at {item.warehouse}",
				"reference_doctype": "Item",
				"reference_name": item.name,
				"timestamp": str(now_datetime()),
			}
		)

	# Items with no stock at all (stocked out)
	stockouts = frappe.db.sql(
		"""
		SELECT i.name, i.item_name, i.item_code
		FROM `tabItem` i
		WHERE i.disabled = 0
		  AND i.is_stock_item = 1
		  AND NOT EXISTS (
		    SELECT 1 FROM `tabBin` b
		    WHERE b.item_code = i.item_code AND b.actual_qty > 0
		  )
		  AND EXISTS (
		    SELECT 1 FROM `tabStock Ledger Entry` sle
		    WHERE sle.item_code = i.item_code
		    AND sle.creation >= DATE_SUB(NOW(), INTERVAL 30 DAY)
		  )
		LIMIT 5
	""",
		as_dict=True,
	)

	for item in stockouts:
		alerts.append(
			{
				"severity": "critical",
				"type": "stockout",
				"title": f"Stockout: {item.item_name or item.item_code}",
				"message": "Previously sold item has zero stock across all locations",
				"reference_doctype": "Item",
				"reference_name": item.name,
				"timestamp": str(now_datetime()),
			}
		)

	return alerts


# ──────────────────────────────────────────────────
# 4. Alert Source: Cash Management
# ──────────────────────────────────────────────────


def _get_cash_alerts() -> list[dict]:
	"""Cash alerts: variance, unclosed registers, blind count discrepancy."""
	alerts: list[dict] = []
	today_date = today()

	# Large cash variance in today's POS Closings
	if frappe.db.table_exists("POS Closing Entry"):
		variances = frappe.db.sql(
			"""
			SELECT pce.name, pce.period_start_date, pce.period_end_date,
			       SUM(pced.difference) as net_difference
			FROM `tabPOS Closing Entry` pce
			JOIN `tabPOS Closing Entry Detail` pced ON pced.parent = pce.name
			WHERE pce.docstatus = 1
			  AND pce.period_end_date = %(today)s
			  AND pced.mode_of_payment = 'Cash'
			GROUP BY pce.name
			HAVING ABS(SUM(pced.difference)) > 20
			ORDER BY ABS(SUM(pced.difference)) DESC
			LIMIT 5
		""",
			{"today": today_date},
			as_dict=True,
		)

		for v in variances:
			variance_amt = flt(v.net_difference or 0, 2)
			alerts.append(
				{
					"severity": "critical" if abs(variance_amt) > 50 else "warning",
					"type": "cash_variance",
					"title": f"Cash variance: ${abs(variance_amt):.2f}",
					"message": f"Closing {v.name} has ${abs(variance_amt):.2f} variance",
					"reference_doctype": "POS Closing Entry",
					"reference_name": v.name,
					"timestamp": str(now_datetime()),
				}
			)

	# Stale open POS Opening Entries (>12 hours without closing)
	if frappe.db.table_exists("POS Opening Entry"):
		stale = frappe.db.sql(
			"""
			SELECT name, period_start_date, pos_profile
			FROM `tabPOS Opening Entry`
			WHERE docstatus = 1
			  AND status = 'Open'
			  AND TIMESTAMPDIFF(HOUR, period_start_date, NOW()) > 12
			LIMIT 5
		""",
			as_dict=True,
		)

		for s in stale:
			alerts.append(
				{
					"severity": "warning",
					"type": "stale_register",
					"title": f"Open register: {s.name}",
					"message": "Register has been open for over 12 hours without closing",
					"reference_doctype": "POS Opening Entry",
					"reference_name": s.name,
					"timestamp": str(now_datetime()),
				}
			)

	return alerts


# ──────────────────────────────────────────────────
# 5. Alert Source: Sales Anomalies
# ──────────────────────────────────────────────────


def _get_sales_alerts(is_manager: bool) -> list[dict]:
	"""Sales alerts: unusual transaction patterns, large returns."""
	alerts: list[dict] = []
	today_date = today()

	if not is_manager:
		return alerts

	# Large returns today (credit notes / returns > $200)
	if frappe.db.table_exists("Sales Invoice"):
		large_returns = frappe.db.sql(
			"""
			SELECT name, customer, grand_total, posting_date
			FROM `tabSales Invoice`
			WHERE docstatus = 1
			  AND is_return = 1
			  AND posting_date = %(today)s
			  AND ABS(grand_total) > 200
			ORDER BY ABS(grand_total) DESC
			LIMIT 5
		""",
			{"today": today_date},
			as_dict=True,
		)

		for r in large_returns:
			alerts.append(
				{
					"severity": "warning",
					"type": "large_return",
					"title": f"Large return: ${abs(flt(r.grand_total)):.2f}",
					"message": f"Return {r.name} for {r.customer}",
					"reference_doctype": "Sales Invoice",
					"reference_name": r.name,
					"timestamp": str(now_datetime()),
				}
			)

	# Unusual: No sales today (if it's a business day and past noon)
	if is_manager:
		now = now_datetime()
		weekday = now.weekday()  # 0=Mon, 6=Sun
		if weekday < 6 and now.hour >= 13:  # Past 1 PM on a weekday/Saturday
			today_sales = cint(
				frappe.db.sql(
					"""
				SELECT COUNT(*) FROM `tabSales Invoice`
				WHERE docstatus = 1 AND posting_date = %(today)s AND is_return = 0
			""",
					{"today": today_date},
				)[0][0]
			)

			if today_sales == 0:
				alerts.append(
					{
						"severity": "info",
						"type": "no_sales",
						"title": "No sales today",
						"message": "It's past 1 PM and no sales have been recorded",
						"reference_doctype": None,
						"reference_name": None,
						"timestamp": str(now_datetime()),
					}
				)

	return alerts


# ──────────────────────────────────────────────────
# 6. Real-time Alert Publishing
# ──────────────────────────────────────────────────


def publish_alert(
	alert_type: str,
	severity: str,
	title: str,
	message: str,
	reference_doctype: str | None = None,
	reference_name: str | None = None,
	target_role: str | None = None,
	users: list[str] | None = None,
) -> None:
	"""Publish a real-time alert via WebSocket.

	Args:
	    alert_type: Category (e.g., 'cash_variance', 'low_stock')
	    severity: 'critical', 'warning', or 'info'
	    title: Short alert title
	    message: Detailed message
	    reference_doctype: Optional DocType for drill-down
	    reference_name: Optional document name for drill-down
	    target_role: If set, only users with this role see the alert
	    users: Optional list of user emails/ids for precise per-user routing
	           (e.g. the two store managers on a transfer). When set, the alert
	           is delivered only to those users' sockets.
	"""
	payload = {
		"severity": severity,
		"type": alert_type,
		"title": title,
		"message": message,
		"reference_doctype": reference_doctype,
		"reference_name": reference_name,
		"timestamp": str(now_datetime()),
	}

	if target_role:
		payload["target_role"] = target_role

	if users:
		# Precise per-user routing (one socket emit per user is the safe form
		# across Frappe versions).
		for user in users:
			if not user:
				continue
			frappe.publish_realtime(
				event="zevar_alert",
				message=payload,
				user=user,
				after_commit=True,
			)
	else:
		frappe.publish_realtime(
			event="zevar_alert",
			message=payload,
			after_commit=True,
		)

	# Persist to the unified feed + browser push (realtime already emitted above).
	try:
		from arijentek_core.services.notification_service import notify, resolve_category

		notify(
			users=users,
			target_role=target_role,
			category=resolve_category(alert_type),
			severity=severity,
			title=title,
			message=message,
			link_doctype=reference_doctype,
			link_name=reference_name,
			source="Event",
			realtime=False,
		)
	except Exception:
		frappe.log_error(title="publish_alert feed fan-out failed", message=frappe.get_traceback())


# ──────────────────────────────────────────────────
# 6b. Unified persisted feed (Zevar Notification)
# ──────────────────────────────────────────────────


@frappe.whitelist(allow_guest=False)
def get_notification_feed(limit: int = 50, unread_only: int = 0, category: str | None = None) -> dict:
	"""Merged notification feed for the current user.

	Union of persisted Zevar Notification rows and unread Frappe Notification
	Log rows (CRM leads, abandoned registers, repair portal actions), newest
	first.
	"""
	from frappe.utils import cint

	user = frappe.session.user
	limit = cint(limit) or 50

	filters = {"user": user}
	if cint(unread_only):
		filters["read"] = 0
	if category:
		filters["category"] = category

	feed = [
		{
			"id": row.name,
			"source": "feed",
			"category": row.category,
			"severity": (row.severity or "info").lower(),
			"title": row.title,
			"message": row.message or "",
			"link_doctype": row.link_doctype,
			"link_name": row.link_name,
			"read": bool(row.read),
			"timestamp": str(row.creation),
		}
		for row in frappe.get_all(
			"Zevar Notification",
			filters=filters,
			fields=[
				"name",
				"category",
				"severity",
				"title",
				"message",
				"link_doctype",
				"link_name",
				"read",
				"creation",
			],
			order_by="creation desc",
			limit_page_length=limit,
		)
	]

	# Frappe Notification Log rows for this user (never surfaced in the Vue bell before)
	log_filters = {"for_user": user}
	if cint(unread_only):
		log_filters["read"] = 0
	log_rows = frappe.get_all(
		"Notification Log",
		filters=log_filters,
		fields=["name", "subject", "email_content", "document_type", "document_name", "read", "creation"],
		order_by="creation desc",
		limit_page_length=limit,
	)
	feed.extend(
		{
			"id": row.name,
			"source": "notification_log",
			"category": _category_for_log_row(row.document_type),
			"severity": "info",
			"title": row.subject or "Notification",
			"message": (row.email_content or "")[:300],
			"link_doctype": row.document_type,
			"link_name": row.document_name,
			"read": bool(row.read),
			"timestamp": str(row.creation),
		}
		for row in log_rows
	)

	feed.sort(key=lambda item: item["timestamp"], reverse=True)
	return {"success": True, "feed": feed[:limit]}


def _category_for_log_row(doctype: str | None) -> str:
	"""Best-effort category for a Frappe Notification Log row."""
	if not doctype:
		return "System"
	mapping = {
		"Lead": "CRM",
		"Opportunity": "CRM",
		"Quotation": "CRM",
		"Repair Order": "Repair",
		"Special Order": "Special Order",
		"POS Opening Entry": "Security",
		"POS Closing Entry": "Finance",
		"Customer": "CRM",
	}
	return mapping.get(doctype, "System")


@frappe.whitelist(allow_guest=False)
def mark_notification_read(name: str) -> dict:
	"""Mark one feed row as read (own rows only)."""
	from frappe.utils import now_datetime

	user = frappe.session.user
	row = frappe.db.get_value("Zevar Notification", name, ["user", "read"], as_dict=True)
	if not row:
		frappe.throw(_("Notification not found"), frappe.DoesNotExistError)
	if row.user != user and user != "Administrator":
		frappe.throw(_("Not your notification"), frappe.PermissionError)
	if not row.read:
		frappe.db.set_value("Zevar Notification", name, {"read": 1, "read_on": now_datetime()})
		frappe.db.commit()
	return {"success": True}


@frappe.whitelist(allow_guest=False)
def mark_all_notifications_read() -> dict:
	"""Mark every unread feed row of the current user as read."""
	from frappe.utils import now_datetime

	user = frappe.session.user
	frappe.db.set_value(
		"Zevar Notification", {"user": user, "read": 0}, {"read": 1, "read_on": now_datetime()}
	)
	# also clear Frappe's own Notification Log unread badge source
	for row in frappe.get_all("Notification Log", filters={"for_user": user, "read": 0}, pluck="name"):
		try:
			frappe.db.set_value("Notification Log", row, "read", 1)
		except Exception:
			pass
	frappe.db.commit()
	return {"success": True}


@frappe.whitelist(allow_guest=False)
def get_unread_notification_counts() -> dict:
	"""Per-category unread counts for the bell's filter chips."""
	user = frappe.session.user
	from frappe.query_builder.functions import Count

	zn = frappe.qb.DocType("Zevar Notification")
	rows = (
		frappe.qb.from_(zn)
		.select(zn.category, zn.severity, Count(zn.name).as_("n"))
		.where((zn.user == user) & (zn.read == 0))
		.groupby(zn.category, zn.severity)
	).run(as_dict=True)
	by_category: dict[str, int] = {}
	critical = warning = 0
	for row in rows:
		by_category[row.category] = by_category.get(row.category, 0) + row.n
		if row.severity == "Critical":
			critical += row.n
		elif row.severity == "Warning":
			warning += row.n
	return {
		"success": True,
		"total": sum(by_category.values()),
		"critical": critical,
		"warning": warning,
		"by_category": by_category,
	}


@frappe.whitelist(allow_guest=False)
def get_notification_preferences() -> dict:
	"""Current user's per-category in-app/push toggles (+ defaults flag)."""
	from arijentek_core.services.notification_service import CATEGORIES, _get_setting_defaults

	user = frappe.session.user
	row = frappe.db.get_value(
		"Zevar Notification Preference", {"user": user}, ["use_defaults", "preferences"], as_dict=True
	)
	import json as _json

	prefs = {}
	use_defaults = True
	if row:
		use_defaults = cstr(row.use_defaults) in ("1", "True", True)
		try:
			prefs = _json.loads(row.preferences) if row.preferences else {}
		except Exception:
			prefs = {}
	defaults = _get_setting_defaults()
	resolved = {}
	for category in CATEGORIES:
		entry = (prefs if not use_defaults else defaults).get(category) or {}
		resolved[category] = {
			"in_app": bool(entry.get("in_app", True)),
			"push": bool(entry.get("push", True)),
		}
	return {"success": True, "use_defaults": use_defaults, "categories": CATEGORIES, "preferences": resolved}


@frappe.whitelist(allow_guest=False)
def save_notification_preferences(preferences: dict | str | None = None, use_defaults: int = 0) -> dict:
	"""Save the current user's per-category toggles ({category: {in_app, push}})."""
	import json as _json

	from arijentek_core.services.notification_service import CATEGORIES

	user = frappe.session.user
	if isinstance(preferences, str):
		preferences = _json.loads(preferences) if preferences else {}
	preferences = preferences or {}

	clean = {}
	for category, entry in preferences.items():
		if category in CATEGORIES and isinstance(entry, dict):
			clean[category] = {
				"in_app": bool(entry.get("in_app", True)),
				"push": bool(entry.get("push", True)),
			}

	existing = frappe.db.get_value("Zevar Notification Preference", {"user": user}, "name")
	if existing:
		frappe.db.set_value(
			"Zevar Notification Preference",
			existing,
			{"use_defaults": 1 if cint(use_defaults) else 0, "preferences": _json.dumps(clean)},
		)
	else:
		frappe.get_doc(
			{
				"doctype": "Zevar Notification Preference",
				"user": user,
				"use_defaults": 1 if cint(use_defaults) else 0,
				"preferences": _json.dumps(clean),
			}
		).insert(ignore_permissions=True)
	frappe.db.commit()
	return get_notification_preferences()


# ──────────────────────────────────────────────────
# 7. Web Push Notification Helpers (e.g. for Shift & Attendance Requests)
# ──────────────────────────────────────────────────

def get_users_with_submit_permission(doctype):
	"""Returns a set of User IDs that have submit permission for a given Doctype."""
	submit_roles = frappe.get_all("DocPerm", filters={"parent": doctype, "submit": 1}, pluck="role")
	submit_roles += frappe.get_all("Custom DocPerm", filters={"parent": doctype, "submit": 1}, pluck="role")

	valid_roles = list(set(submit_roles + ["HR Manager", "System Manager"]))

	notifiable_users = frappe.get_all("Has Role",
		filters={
			"role": ["in", valid_roles],
			"parenttype": "User"
		},
		fields=["parent as user"],
		distinct=True
	)

	return {u.user for u in notifiable_users if u.user}

def notify_approvers(doc, title, body, module="hrm", route=""):
	"""Notifies users who have submit access for the document, excluding the document owner."""
	from arijentek_core.api.web_push import send_push_notification

	users_to_notify = get_users_with_submit_permission(doc.doctype)

	if doc.owner in users_to_notify:
		users_to_notify.remove(doc.owner)

	if not users_to_notify:
		return

	base_url = "/employee-portal#" if module == "hrm" else "/pos#"
	url = f"{base_url}{route}"

	for user in users_to_notify:
		try:
			send_push_notification(user=user, title=title, body=body, url=url)
		except Exception as e:
			frappe.log_error(f"Failed to send {doc.doctype} push to {user}: {e!s}", "Web Push Error")

def notify_owner(doc, title, body, module="hrm", route=""):
	"""Notifies the document owner directly."""
	from arijentek_core.api.web_push import send_push_notification

	if not doc.owner:
		return

	base_url = "/employee-portal#" if module == "hrm" else "/pos#"
	url = f"{base_url}{route}"

	try:
		send_push_notification(user=doc.owner, title=title, body=body, url=url)
	except Exception as e:
		frappe.log_error(f"Failed to send {doc.doctype} push to {doc.owner}: {e!s}", "Web Push Error")
