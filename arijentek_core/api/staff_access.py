"""Team Hub API — thin whitelisted layer over services/staff_access.

Every endpoint is session-authenticated (``allow_guest=False``); the
business logic and permission gates live in the service module.
"""

from __future__ import annotations

import frappe

from arijentek_core.services import custom_personas, staff_access


@frappe.whitelist(allow_guest=False)
def get_staff_catalog() -> list[dict]:
	"""Personas the caller may assign (role pills, tier, landing hint)."""
	return staff_access.get_catalog_for_user()


@frappe.whitelist(methods=["POST"], allow_guest=False)
def create_staff_member(payload) -> dict:
	"""Create User + Employee + persona stack (+ store allocation) in one call."""
	if isinstance(payload, str):
		payload = frappe.parse_json(payload)
	return staff_access.create_staff_member(payload or {})


@frappe.whitelist(allow_guest=False)
def get_staff_overview() -> dict:
	"""The whole Team page: staff list, counts and dropdown options."""
	return staff_access.get_staff_overview()


@frappe.whitelist(methods=["POST"], allow_guest=False)
def update_staff_member(payload) -> dict:
	"""Re-persona (stack) / enable / disable / password reset for one user."""
	if isinstance(payload, str):
		payload = frappe.parse_json(payload)
	return staff_access.update_staff_member(payload or {})


@frappe.whitelist(allow_guest=False)
def get_staff_permissions(user: str) -> dict[str, bool]:
	"""Effective permission-key map for the permissions drawer."""
	return staff_access.get_staff_permissions(user)


@frappe.whitelist(allow_guest=False)
def get_persona_builder_options() -> dict:
	"""Role picker + landing routes for the custom-persona builder."""
	return custom_personas.get_persona_builder_options()


@frappe.whitelist(methods=["POST"], allow_guest=False)
def save_custom_persona(payload) -> dict:
	"""Create or update a custom persona (admin tier)."""
	if isinstance(payload, str):
		payload = frappe.parse_json(payload)
	return custom_personas.save_custom_persona(payload or {})


@frappe.whitelist(methods=["POST"], allow_guest=False)
def delete_custom_persona(name: str) -> dict:
	"""Delete a custom persona (blocked while assigned)."""
	return custom_personas.delete_custom_persona(name)
