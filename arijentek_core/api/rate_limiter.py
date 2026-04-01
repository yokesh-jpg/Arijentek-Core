from functools import wraps

import frappe
from frappe import _


def user_rate_limit(limit=20, seconds=60):
	"""Rate limit per logged-in user (frappe.session.user), not per IP.

	Frappe's built-in ``@rate_limit`` uses IP-based identity by default,
	which means all employees behind the same office NAT/proxy share one
	rate-limit bucket.  On a busy day (e.g. month-end clock-out) 10+
	employees easily exceed ``limit=10`` within 60 seconds.

	This decorator keys on ``frappe.session.user`` instead, giving every
	logged-in user their own independent bucket.
	"""

	def decorator(fn):
		@wraps(fn)
		def wrapper(*args, **kwargs):
			if not frappe.request:
				return fn(*args, **kwargs)

			_limit = limit() if callable(limit) else limit
			user = frappe.session.user

			if not user or user == "Guest":
				frappe.throw(_("Authentication required"))

			cache_key = frappe.cache.make_key(f"rl_user:{frappe.form_dict.cmd}:{user}:{seconds}")

			value = frappe.cache.incrby(cache_key, 1)
			if int(value) == 1 or frappe.cache.ttl(cache_key) == -1:
				frappe.cache.expire(cache_key, seconds)

			if int(value) > _limit:
				frappe.throw(
					_("You hit the rate limit. Please try after sometime."),
					frappe.RateLimitExceededError,
				)

			return fn(*args, **kwargs)

		return wrapper

	return decorator
