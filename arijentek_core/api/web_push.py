import json

import frappe
from frappe import _


def get_or_generate_vapid_keys():
	if not frappe.db.exists("DocType", "Web Push Settings"):
		return None

	try:
		if frappe.db.exists("DocType", "Web Push Settings"):
			settings = frappe.get_doc("Web Push Settings", "Web Push Settings")
		else:
			return None
	except Exception as e:
		frappe.log_error(f"Web Push Settings load error: {e!s}", "Web Push Error")
		return None

	if not getattr(settings, "vapid_private_key", None) or not getattr(settings, "vapid_public_key", None):
		try:
			import base64

			from cryptography.hazmat.primitives import serialization
			from pywebpush import Vapid
		except ImportError:
			frappe.log_error("pywebpush is not installed. Run bench pip install pywebpush", "Web Push Error")
			return settings

		try:
			v = Vapid()
			v.generate_keys()

			# Export Raw Uncompressed Public Key (URLSafe Base64)
			raw_pub = v.public_key.public_bytes(
				encoding=serialization.Encoding.X962, format=serialization.PublicFormat.UncompressedPoint
			)
			pub_b64 = base64.urlsafe_b64encode(raw_pub).decode("utf-8").rstrip("=")

			# Export Raw Private Key (URLSafe Base64)
			priv_val = v.private_key.private_numbers().private_value
			raw_priv = priv_val.to_bytes(32, byteorder="big")
			priv_b64 = base64.urlsafe_b64encode(raw_priv).decode("utf-8").rstrip("=")

			settings.vapid_private_key = priv_b64
			settings.vapid_public_key = pub_b64

			# We need an admin email for the VAPID claim, e.g. mailto:admin@zevar.com
			if not getattr(settings, "admin_email", None):
				settings.admin_email = "mailto:admin@zevar.com"

			settings.save(ignore_permissions=True)
			frappe.db.commit()  # nosemgrep
		except Exception as e:
			frappe.log_error(f"Failed generating VAPID keys: {e!s}", "Web Push Error")

	return settings


@frappe.whitelist(allow_guest=False)
def get_vapid_public_key():
	try:
		settings = get_or_generate_vapid_keys()
		if not settings:
			return ""
		return getattr(settings, "vapid_public_key", "") or ""
	except Exception as e:
		frappe.log_error(f"get_vapid_public_key failed: {e}", "Web Push Error")
		return ""


@frappe.whitelist(allow_guest=False)
def subscribe(endpoint, auth_key, p256dh_key):
	if not frappe.db.exists("DocType", "Web Push Subscription"):
		return None

	# Check if this endpoint is already subscribed to ANY user
	existing_all = frappe.get_all("Web Push Subscription", filters={"endpoint": endpoint}, fields=["name", "user"])

	already_subscribed_for_current = False
	existing_name = None
	for sub in existing_all:
		if sub.user == frappe.session.user:
			already_subscribed_for_current = True
			existing_name = sub.name
		else:
			# Delete it from other users to prevent cross-account push notifications
			frappe.delete_doc("Web Push Subscription", sub.name, ignore_permissions=True)

	if already_subscribed_for_current and existing_name:
		return existing_name

	doc = frappe.get_doc({
		"doctype": "Web Push Subscription",
		"user": frappe.session.user,
		"endpoint": endpoint,
		"auth_key": auth_key,
		"p256dh_key": p256dh_key,
	})
	doc.insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist(allow_guest=False)
def unsubscribe(endpoint):
	if not frappe.db.exists("DocType", "Web Push Subscription"):
		return False
	# Find and delete the subscription for the current user and endpoint
	existing = frappe.db.get_value(
		"Web Push Subscription", {"endpoint": endpoint, "user": frappe.session.user}, "name"
	)
	if existing:
		frappe.delete_doc("Web Push Subscription", existing, ignore_permissions=True)
		return True
	return False


def send_push_notification(user, title, body, icon=None, url=None, app_type="hrm"):
	try:
		from pywebpush import WebPushException, webpush
	except ImportError:
		frappe.log_error("pywebpush not installed", "Web Push Error")
		return

	settings = get_or_generate_vapid_keys()
	if not settings or not getattr(settings, "vapid_private_key", None):
		return

	subs = frappe.get_all(
		"Web Push Subscription", filters={"user": user}, fields=["name", "endpoint", "auth_key", "p256dh_key"]
	)

	if not icon:
		icon = (
			"/assets/arijentek_core/images/pos_logo.svg"
			if app_type == "pos"
			else "/assets/arijentek_core/images/employee_portal_logo.svg"
		)

	if not url:
		url = "/pos#/" if app_type == "pos" else "/employee-portal#/"

	payload = json.dumps({"title": title, "body": body, "icon": icon, "url": url})

	vapid_claims = {"sub": getattr(settings, "admin_email", "mailto:admin@zevar.com")}

	for sub in subs:
		subscription_info = {"endpoint": sub.endpoint, "keys": {"auth": sub.auth_key, "p256dh": sub.p256dh_key}}

		try:
			webpush(
				subscription_info=subscription_info,
				data=payload,
				vapid_private_key=settings.get_password("vapid_private_key"),
				vapid_claims=vapid_claims,
				ttl=86400,
			)
		except WebPushException as ex:
			# If the subscription is expired or invalid, remove it from the DB
			if ex.response and ex.response.status_code in [404, 410]:
				frappe.delete_doc("Web Push Subscription", sub.name, ignore_permissions=True)
			else:
				frappe.log_error(f"Push Error: {ex!s}", "Web Push Error")
		except Exception as e:
			frappe.log_error(f"Push Error: {e!s}", "Web Push Error")


@frappe.whitelist(allow_guest=False)
def send_test_notification():
	"""Fire a test OS-level push to the CURRENT user (bell 'Test' button).

	Requires an existing web-push subscription for the user — subscribe first
	via the bell's Enable-browser-notifications flow.
	"""
	user = frappe.session.user
	subs = frappe.get_all("Web Push Subscription", filters={"user": user}, pluck="name")
	if not subs:
		frappe.throw(
			_("No browser subscription found. Enable browser notifications first, then retry."),
			frappe.ValidationError,
		)
	send_push_notification(
		user,
		"Zevar test notification",
		"Browser notifications are working. You'll see alerts like this even when the app is closed.",
		url="/pos/#/settings",
		app_type="pos",
	)
	return {"success": True, "sent_to": len(subs)}
