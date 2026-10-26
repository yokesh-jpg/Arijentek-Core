# Copyright (c) 2026, Gemora 360
# License: GNU General Public License v3.0

"""
Bank registry — runtime GL account resolver (Phase 1 of finance_setup_phased.md).

The single source of truth for "which COA account does this MOP / store /
expense post to" at GL time. Every GL-posting feature (cash GL, card capture)
routes through here instead of hardcoding account names.

Rules:

  * Cached via ``frappe.cache``; invalidated on Bank Account / Store Location
	writes through :func:`clear_bank_registry_cache` (see ``hooks.py``).
  * **Loud fallback:** if the config chain ends at a placeholder Bank Account
	(``bank = "Default Bank"`` or no account number) the runtime posts to the
	``UNRESOLVED — needs finance setup`` suspense account and logs the miss
	once per company+kind (daily cooldown). Silent placeholder posting is
	never allowed — it produces books that look correct but aren't.
  * Never raises: POS operations must not block on missing config; the GL just
	gets a clearly-labeled suspense account to fix. Callers receive ``None``
	only when even the suspense account cannot be created (no company).

The setup-side resolver (``finance_resolver.resolve_bank_account``) converts
placeholders into real accounts; this module consumes that state at runtime.
"""

from collections.abc import Callable

import frappe

from arijentek_core.services.finance_bootstrap import MOP_TYPES
from arijentek_core.services.finance_resolver import _is_placeholder
from arijentek_core.services.store_registry import get_store_registry

_CACHE_PREFIX = "zevar:bank_registry"
SUSPENSE_LABEL = "UNRESOLVED — needs finance setup"

_BANK_MOP_TYPES = ("Bank", "Digital")


# --------------------------------------------------------------------------- #
# Cache plumbing (cloned from store_registry.py)
# --------------------------------------------------------------------------- #
def clear_bank_registry_cache(doc=None, method=None) -> None:
	"""Invalidate all cached resolutions. Hook into Bank Account and Store
	Location ``on_update`` / ``on_trash`` (see ``hooks.py``) so config edits
	apply immediately. Accepts Frappe's ``(doc, method)`` hook args."""
	try:
		# NOTE: delete_keys takes a single prefix string (it appends "*" and
		# deletes every matching key) — passing a list raises TypeError.
		frappe.cache().delete_keys(_CACHE_PREFIX)
	except Exception:  # nosec B110 - cache failure is non-fatal
		pass


def _cached(kind: str, key: str, loader: Callable[[], str | None]) -> str | None:
	cache_key = f"{_CACHE_PREFIX}:{kind}:{key}"
	try:
		cached = frappe.cache().get_value(cache_key)
	except Exception:  # nosec B110 - cache unavailable (install/headless) is non-fatal
		cached = None
	if cached is not None:
		return cached
	value = loader()
	try:
		frappe.cache().set_value(cache_key, value)
	except Exception:  # nosec B110 - cache write failure is non-fatal
		pass
	return value


# --------------------------------------------------------------------------- #
# Identity helpers
# --------------------------------------------------------------------------- #
def _company(store=None, company=None) -> str | None:
	"""Resolve a company from explicit arg -> store registry -> global default."""
	if company:
		return company
	if store:
		info = get_store_registry().get(store)
		if info and info.get("company"):
			return info["company"]
		if frappe.db.exists("Store Location", store):
			company = frappe.db.get_value("Store Location", store, "company")
			if company:
				return company
	try:
		return frappe.db.get_single_value("Global Defaults", "default_company")
	except Exception:  # nosec B110 - install-time / headless
		return None


def _store_code(store) -> str | None:
	"""Normalize a store_code / Store Location name / warehouse to store_code."""
	if not store:
		return None
	if store in get_store_registry():
		return store
	code = frappe.db.get_value("Store Location", store, "store_code")
	return code or store


def _company_abbr(company: str) -> str:
	return frappe.get_cached_value("Company", company, "abbr") or company


def _group_parent(company: str, root_type: str) -> str | None:
	"""The company's Assets / Expenses group account (resolved by root_type)."""
	return frappe.db.get_value(
		"Account",
		{"company": company, "is_group": 1, "root_type": root_type},
		"name",
		order_by="lft",
	)


def _suspense_account(company: str, root_type: str, kind: str) -> str | None:
	"""Lazily create (and log once) the loud suspense account for a miss.

	``root_type`` is "Asset" for bank/cash money, "Expense" for expense posts.
	Never raises — a failed creation degrades to ``None`` (caller decides).
	"""
	abbr = _company_abbr(company)
	name = f"{SUSPENSE_LABEL} - {abbr}"
	if not frappe.db.exists("Account", name):
		parent = _group_parent(company, root_type)
		if not parent:
			return None
		try:
			account = frappe.new_doc("Account")
			account.company = company
			account.account_name = SUSPENSE_LABEL
			account.account_type = "Temporary" if root_type == "Asset" else "Expense Account"
			account.parent_account = parent
			account.insert(ignore_permissions=True)
		except Exception:
			frappe.log_error(
				f"bank_registry: could not create suspense account for {company} "
				f"({kind})",
				frappe.get_traceback(),
			)
			return None
	_log_once(company, kind)
	return name


def _log_once(company: str, kind: str) -> None:
	"""Log an unresolved miss at most once per day per company+kind."""
	flag = f"zevar:suspense_logged:{company}:{kind}"
	try:
		if frappe.cache().get_value(flag):
			return
		frappe.cache().set_value(flag, 1, expires_in_sec=86400)
	except Exception:  # nosec B110 - cache failure is non-fatal
		pass
	frappe.log_error(
		f"Bank registry: unresolved '{kind}' for {company} — posting to "
		f"'{SUSPENSE_LABEL}' suspense account. Finish Finance Setup.",
		"bank_registry",
	)


# --------------------------------------------------------------------------- #
# Leaf lookups (uncached; wrappers below cache)
# --------------------------------------------------------------------------- #
def _bank_leaf(bank_account_name: str) -> str | None:
	"""The COA leaf of a Bank Account master — None when it's a placeholder."""
	ba = frappe.db.get_value(
		"Bank Account",
		bank_account_name,
		["account", "bank", "bank_account_no"],
		as_dict=True,
	)
	if not ba or not ba.get("account"):
		return None
	if _is_placeholder(ba):
		return None
	return ba["account"]


def _store_bank_leaf(store_code: str) -> str | None:
	loc = frappe.db.get_value(
		"Store Location", {"store_code": store_code}, "default_bank_account"
	)
	if not loc:
		return None
	return _bank_leaf(loc)


def _company_bank_leaf(company: str) -> str | None:
	filters = {"company": company, "disabled": 0}
	default = frappe.db.get_value("Bank Account", {**filters, "is_default": 1}, "name")
	name = default or frappe.db.get_value("Bank Account", filters, "name")
	if not name:
		return None
	return _bank_leaf(name)


def _store_cash_leaf(company: str, store_code: str) -> str | None:
	abbr = _company_abbr(company)
	name = f"Cash - {store_code} - {abbr}"
	if frappe.db.exists("Account", name):
		return name
	return frappe.db.get_value(
		"Account",
		{"company": company, "account_type": "Cash", "name": ["like", f"Cash - {store_code} - %"]},
		"name",
	)


def _company_cash_leaf(company: str) -> str | None:
	# Deterministic preference so a company always posts drawer cash to the
	# same leaf: bootstrap "Cash - {abbr}" (account_name "Cash") first, then
	# the legacy "Cash In Hand", then any real cash account. Undeposited Funds
	# is classified as Cash in the chart but is NOT a drawer account.
	for account_name in ("Cash", "Cash In Hand"):
		leaf = frappe.db.get_value(
			"Account",
			{"company": company, "account_type": "Cash", "account_name": account_name},
			"name",
			order_by="lft",
		)
		if leaf:
			return leaf
	return frappe.db.get_value(
		"Account",
		{
			"company": company,
			"account_type": "Cash",
			"account_name": ["!=", "Undeposited Funds"],
		},
		"name",
		order_by="lft",
	)


def _named_leaf(company: str, account_name: str) -> str | None:
	return frappe.db.get_value("Account", {"company": company, "account_name": account_name}, "name")


def _mop_row_leaf(mop: str, company: str) -> str | None:
	leaf = frappe.db.get_value(
		"Mode of Payment Account", {"parent": mop, "company": company}, "default_account"
	)
	if leaf and frappe.db.exists("Account", leaf):
		return leaf
	return None


# --------------------------------------------------------------------------- #
# Public resolvers (cached)
# --------------------------------------------------------------------------- #
def resolve_bank_account(store=None, company=None) -> str | None:
	"""COA leaf a bank deposit for a store/company lands in.

	Store's ``default_bank_account`` wins over the company default; a
	placeholder chain resolves to the loud suspense account instead.
	"""
	key = f"{_store_code(store) or '-'}:{company or '-'}"

	def loader():
		company_ = _company(store, company)
		if not company_:
			return None
		store_code = _store_code(store)
		if store_code:
			leaf = _store_bank_leaf(store_code)
			if leaf:
				return leaf
		leaf = _company_bank_leaf(company_)
		if leaf:
			return leaf
		return _suspense_account(company_, "Asset", f"bank:{store_code or company_}")

	return _cached("bank", key, loader)


def resolve_cash_account(store=None, company=None) -> str | None:
	"""COA leaf for cash at a store (``Cash - {store_code}``), else company cash."""
	key = f"{_store_code(store) or '-'}:{company or '-'}"

	def loader():
		company_ = _company(store, company)
		if not company_:
			return None
		store_code = _store_code(store)
		if store_code:
			leaf = _store_cash_leaf(company_, store_code)
			if leaf:
				return leaf
		leaf = _company_cash_leaf(company_)
		if leaf:
			return leaf
		return _suspense_account(company_, "Asset", f"cash:{store_code or company_}")

	return _cached("cash", key, loader)


def resolve_undeposited(store=None, company=None) -> str | None:
	"""The company's Undeposited Funds account (receipts waiting for the bank)."""
	key = f"{_store_code(store) or '-'}:{company or '-'}"

	def loader():
		company_ = _company(store, company)
		if not company_:
			return None
		leaf = _named_leaf(company_, "Undeposited Funds")
		if leaf:
			return leaf
		return _suspense_account(company_, "Asset", f"undeposited:{company_}")

	return _cached("undeposited", key, loader)


def resolve_expense_account(store=None, company=None, reason: str | None = None) -> str | None:
	"""COA leaf for a cash-out expense.

	Merchant/processing reasons post to ``Merchant Fees``, everything else to
	``Misc Store Expenses`` (both bootstrap-provisioned).
	"""
	reason = (reason or "").lower()
	if "merchant" in reason or "process" in reason or "fee" in reason:
		leaf_name = "Merchant Fees"
	else:
		leaf_name = "Misc Store Expenses"
	key = f"{_store_code(store) or '-'}:{company or '-'}:{leaf_name}"

	def loader():
		company_ = _company(store, company)
		if not company_:
			return None
		leaf = _named_leaf(company_, leaf_name)
		if leaf:
			return leaf
		return _suspense_account(company_, "Expense", f"expense:{leaf_name}:{company_}")

	return _cached("expense", key, loader)


def resolve_mop_account(mop: str, store=None, company=None) -> str | None:
	"""COA leaf a sale paid with ``mop`` posts to.

	Chain: store bank (bank/digital modes) -> store cash (cash modes) ->
	company bank -> Mode of Payment Account row -> loud suspense. Bank/digital
	modes never resolve through a placeholder Bank Account — they go loud.
	"""
	key = f"{_store_code(store) or '-'}:{company or '-'}:{mop}"

	def loader():
		company_ = _company(store, company)
		if not company_:
			return None
		mop_type = MOP_TYPES.get(mop)
		store_code = _store_code(store)
		if store_code:
			if mop_type in _BANK_MOP_TYPES:
				leaf = _store_bank_leaf(store_code)
				if leaf:
					return leaf
			elif mop_type == "Cash":
				leaf = _store_cash_leaf(company_, store_code)
				if leaf:
					return leaf
		if mop_type in _BANK_MOP_TYPES:
			leaf = _company_bank_leaf(company_)
			if leaf:
				return leaf
		leaf = _mop_row_leaf(mop, company_)
		if leaf:
			return leaf
		return _suspense_account(company_, "Asset", f"mop:{mop}:{company_}")

	return _cached("mop", key, loader)
