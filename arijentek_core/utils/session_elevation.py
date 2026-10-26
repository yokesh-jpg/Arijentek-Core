"""Safe in-request user switching.

Shared by the Team Hub services (staff_access, custom_personas) so elevation
never needs a bare ``frappe.set_user`` in HTTP context.
"""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy

import frappe


@contextmanager
def session_as(user: str):
	"""Run the block as ``user`` without wrecking the request's session.

	``frappe.set_user`` clobbers ``frappe.local.session`` in place (sid=user,
	data={}). That dict is the live ``Session`` object's data, so
	``Session.update()`` at request teardown writes the clobbered dict under
	the request's real sid — every following request with that cookie resumes
	as Guest. Restore the session contents on exit, in place, so both the
	teardown write and any later read see the real session again.
	"""
	snapshot = deepcopy(frappe.local.session)
	frappe.set_user(user)
	try:
		yield
	finally:
		frappe.local.session.clear()
		frappe.local.session.update(snapshot)
