"""Shared store -> sales-invoice scoping for every report surface."""

from __future__ import annotations

import frappe
from frappe.utils import flt


def store_warehouse(store: str | None) -> str | None:
	"""Resolve a Store Location (or raw POS Profile / warehouse name) to its warehouse."""
	if not store:
		return None

	if frappe.db.exists("Warehouse", store):
		return store

	warehouse = frappe.db.get_value("POS Profile", store, "warehouse")
	if warehouse:
		return warehouse

	if frappe.db.exists("DocType", "Store Location"):
		pos_profile = frappe.db.get_value("Store Location", store, "pos_profile")
		if pos_profile:
			warehouse = frappe.db.get_value("POS Profile", pos_profile, "warehouse")
			if warehouse:
				return warehouse

	return None


def store_pos_profile(store: str | None) -> str | None:
	"""Resolve a store-ish identifier to its POS Profile name."""
	if not store:
		return None
	if frappe.db.exists("POS Profile", store):
		return store
	if frappe.db.exists("DocType", "Store Location"):
		pos_profile = frappe.db.get_value("Store Location", store, "pos_profile")
		if pos_profile:
			return pos_profile
	warehouse = store_warehouse(store)
	if warehouse:
		return frappe.db.get_value("POS Profile", {"warehouse": warehouse}, "pos_profile") or frappe.db.get_value(
			"POS Profile", {"warehouse": warehouse}, "name"
		)
	return None


def store_condition(store: str | None, si_alias: str = "si", sii_alias: str = "sii") -> tuple[str, dict]:
	"""SQL fragment (and params) scoping Sales Invoice rows to a store."""
	warehouse = store_warehouse(store)
	pos_profile = store_pos_profile(store)
	if not warehouse and not pos_profile:
		return "", {}

	conds = []
	if pos_profile:
		conds.append(f"{si_alias}.pos_profile = %(store_pos_profile)s")
	if warehouse:
		conds.append(
			f"({si_alias}.set_warehouse = %(store_warehouse)s OR EXISTS ("
			f"SELECT 1 FROM `tabSales Invoice Item` {sii_alias}_sc "
			f"WHERE {sii_alias}_sc.parent = {si_alias}.name "
			f"AND {sii_alias}_sc.warehouse = %(store_warehouse)s))"
		)

	return "AND (" + " OR ".join(conds) + ") ", {
		"store_pos_profile": pos_profile,
		"store_warehouse": warehouse,
	}


def store_repair_condition(store: str | None, ro_alias: str = "ro") -> tuple[str, dict]:
	"""SQL fragment scoping Repair Order rows to a store."""
	warehouse = store_warehouse(store)
	if not warehouse:
		return "", {}
	return f"AND ({ro_alias}.warehouse = %(store_warehouse)s OR {ro_alias}.warehouse IS NULL) ", {
		"store_warehouse": warehouse,
	}


def store_amount(rows: list) -> float:
	"""Sum a column of {amount}-ish dicts safely."""
	return flt(sum(flt(r.get("amount") if isinstance(r, dict) else r) for r in (rows or [])))
