"""
Finance auto-provisioning engine (zero-config bootstrap).

Creates every record the money side of Zevar needs to work out of the box:

  * chart accounts (bank / cash / undeposited funds / merchant fees)
  * Bank master entries
  * one placeholder ``Bank Account`` per company ("Default Bank Account" —
	the client edits in real account/routing numbers later)
  * ``Mode of Payment`` -> default account mappings (gap-fill only)
  * per-store cash accounts (``Cash - {store_code} - {abbr}``)

Guarantees:

  * Idempotent — safe to run on every migrate and at any time.
  * Resolves accounts by ``account_type`` under the company's existing chart
	of accounts tree, never by hardcoded names, so it adapts to any COA.
  * Never throws on missing config: gaps are auto-created as clearly-labeled
	placeholders; unresolvable items are logged and skipped, never fatal.
  * Preserves live data: existing ``Mode of Payment Account`` rows are never
	overwritten, so already-running sites keep their current accounting.

``bootstrap_all()`` is registered in hooks.py (after_install / after_migrate);
``ensure_store_accounts()`` is registered on Store Location ``after_insert``
so a new store is provisioned the moment it is created.

This is Phase 0 (T1) of the finance plan. The wizard (T3/T4) and the runtime
resolver (T2) build on the records created here.
"""

from typing import Any

import frappe

# Mode of Payment -> accounting family. Bank/Digital settle to the company's
# bank account; Financing modes post to per-provider A/R receivable accounts;
# the rest follow the legacy install.py defaults (cash).
MOP_TYPES: dict[str, str] = {
	"Cash": "Cash",
	"Credit Card": "Bank",
	"Debit Card": "Bank",
	"Check": "Bank",
	"Wire Transfer": "Bank",
	"Apple Pay": "Bank",
	"Google Pay": "Bank",
	"Zelle": "Digital",
	"Venmo": "Digital",
	"Cash App": "Digital",
	"Synchrony": "Financing",
	"AFF": "Financing",
	"CIMA": "Financing",
	"Progressive": "Financing",
	"Snap": "Financing",
	"In-House Finance": "Financing",
	"Gift Card": "Other",
	"Trade-In": "Other",
}

# Bank master seed. "Default Bank" is the placeholder the auto-created Bank
# Account links to until the client supplies their real bank.
BANK_MASTER_SEED: list[str] = ["Default Bank", "Chase", "Bank of America", "Wells Fargo"]

_BALANCE_SHEET_TYPES = ("Bank", "Cash", "Receivable", "Asset")


# --------------------------------------------------------------------------- #
# Chart of accounts helpers (resolve by type, never by hardcoded names)
# --------------------------------------------------------------------------- #
def _abbr(company: str) -> str:
	return frappe.get_cached_value("Company", company, "abbr") or company


def _group_account(company: str, account_type: str) -> str | None:
	"""The group (parent) account of a type in the company's COA, else None."""
	group = frappe.db.get_value(
		"Account",
		{"company": company, "account_type": account_type, "is_group": 1},
		"name",
	)
	if group:
		return group
	# Fallback: the parent of any existing leaf of that type.
	return frappe.db.get_value(
		"Account",
		{"company": company, "account_type": account_type, "is_group": 0},
		"parent_account",
	)


def _expense_parent(company: str) -> str | None:
	"""The group under which expense accounts hang (parent of an expense leaf)."""
	leaf_parent = frappe.db.get_value(
		"Account",
		{"company": company, "account_type": "Expense Account", "is_group": 0},
		"parent_account",
	)
	if leaf_parent:
		return leaf_parent
	return frappe.db.get_value(
		"Account",
		{"company": company, "account_type": "Expense Account", "is_group": 1},
		"name",
	)


def _asset_parent(company: str) -> str | None:
	"""Group under which receivable/asset accounts hang (parent of the bank group)."""
	bank_group = _group_account(company, "Bank")
	if bank_group:
		parent = frappe.db.get_value("Account", bank_group, "parent_account")
		if parent:
			return parent
	return _group_account(company, "Asset")


def _create_account(
	company: str, account_name: str, account_type: str, parent_account: str | None
) -> str | None:
	"""Create a leaf account if missing; return its name (or None if it can't)."""
	if not parent_account or not frappe.db.exists("Account", parent_account):
		return None
	existing = frappe.db.get_value(
		"Account",
		{"company": company, "account_name": account_name, "is_group": 0},
		"name",
	)
	if existing:
		return existing
	acc = frappe.new_doc("Account")
	acc.account_name = account_name
	acc.company = company
	acc.account_type = account_type
	acc.parent_account = parent_account
	acc.is_group = 0
	acc.report_type = "Balance Sheet" if account_type in _BALANCE_SHEET_TYPES else "Profit and Loss"
	acc.insert(ignore_permissions=True)
	return acc.name


def _most_used_leaf(company: str, account_type: str) -> str | None:
	"""The leaf account of a type that Mode of Payment mappings reference most.

	For existing companies this picks the account the system already posts to
	(e.g. "Chase Bank - ZFJ"), so the placeholder Bank Account master matches
	where money actually lands today. Tie-break: alphabetical.
	"""
	leaves = frappe.get_all(
		"Account",
		filters={"company": company, "account_type": account_type, "is_group": 0},
		pluck="name",
	)
	if not leaves:
		return None
	usage: dict[str, int] = {}
	for row in frappe.get_all(
		"Mode of Payment Account",
		filters={"company": company, "default_account": ["in", leaves]},
		fields=["default_account"],
	):
		usage[row.default_account] = usage.get(row.default_account, 0) + 1
	if usage:
		return max(usage, key=lambda a: (usage[a], a))
	return sorted(leaves)[0]


# --------------------------------------------------------------------------- #
# Provisioning functions (all idempotent)
# --------------------------------------------------------------------------- #
def ensure_chart_accounts(company: str) -> dict[str, str | None]:
	"""Create the missing chart accounts for a company.

	Existing leaves are reused (bank/cash are resolved by usage so live
	mappings keep their targets). Returns the resolved account map.
	"""
	bank_leaf = _most_used_leaf(company, "Bank") or _create_account(
		company, "Bank", "Bank", _group_account(company, "Bank")
	)
	cash_leaf = _most_used_leaf(company, "Cash") or _create_account(
		company, "Cash", "Cash", _group_account(company, "Cash")
	)
	return {
		"bank_account": bank_leaf,
		"cash_account": cash_leaf,
		"undeposited_funds": _create_account(
			company, "Undeposited Funds", "Cash", _group_account(company, "Cash")
		),
		"merchant_fees": _create_account(
			company, "Merchant Fees", "Expense Account", _expense_parent(company)
		),
		"misc_store_expenses": _create_account(
			company, "Misc Store Expenses", "Expense Account", _expense_parent(company)
		),
	}


def ensure_bank_master() -> list[str]:
	"""Seed the Bank master with the standard set (missing entries only)."""
	created: list[str] = []
	for bank_name in BANK_MASTER_SEED:
		if frappe.db.exists("Bank", bank_name):
			continue
		bank = frappe.new_doc("Bank")
		bank.bank_name = bank_name
		bank.insert(ignore_permissions=True)
		created.append(bank_name)
	return created


def ensure_default_bank_accounts(company: str) -> dict[str, str] | None:
	"""One placeholder Bank Account per company, linked to the default bank leaf.

	If a Bank Account already exists for the company it is returned untouched.
	The placeholder ("Default Bank Account", no account numbers) is what the
	client edits when the real bank details arrive — every downstream record
	links through this one.
	"""
	existing = frappe.get_all(
		"Bank Account",
		filters={"company": company, "disabled": 0},
		fields=["name", "account"],
		limit=1,
	)
	if existing:
		return {"name": existing[0]["name"], "account": existing[0]["account"]}

	chart = ensure_chart_accounts(company)
	if not chart["bank_account"]:
		return None

	ensure_bank_master()
	# NOTE: BankAccount.autoname() sets name = account_name + " - " + bank
	# (erpnext accounts/doctype/bank_account/bank_account.py), so the
	# account_name must be company-unique or two companies collide on PK.
	ba = frappe.new_doc("Bank Account")
	ba.account_name = f"Default Bank Account - {_abbr(company)}"
	ba.bank = "Default Bank"
	ba.company = company
	ba.account = chart["bank_account"]
	ba.is_default = 1
	ba.is_company_account = 1
	ba.insert(ignore_permissions=True)
	return {"name": ba.name, "account": ba.account}


def _ensure_receivable_account(company: str, provider: str) -> str | None:
	"""Per-provider financing receivable: ``Asset — A/R {Provider} - {abbr}``."""
	name = f"Asset — A/R {provider} - {_abbr(company)}"
	if frappe.db.exists("Account", name):
		return name
	return _create_account(company, f"Asset — A/R {provider}", "Receivable", _asset_parent(company))


def _mop_target_account(
	mode: str, mop_type: str, company: str, chart: dict[str, str | None]
) -> str | None:
	"""The default Account a Mode of Payment row should map to."""
	if mop_type == "Financing":
		return _ensure_receivable_account(company, mode) or chart["bank_account"]
	if mop_type in ("Bank", "Digital"):
		return chart["bank_account"]
	return chart["cash_account"]  # Cash, Gift Card, Trade-In, In-House Finance


def ensure_mop_mappings(company: str) -> dict[str, list[str]]:
	"""Gap-fill Mode of Payment -> default account rows for all supported MOPs.

	Rows that already exist for the company are never touched (preserves live
	accounting behavior); only missing rows are created.
	"""
	chart = ensure_chart_accounts(company)
	result: dict[str, list[str]] = {"created": [], "existing": [], "skipped": []}
	for mode, mop_type in MOP_TYPES.items():
		if not frappe.db.exists("Mode of Payment", mode):
			continue
		if frappe.db.exists("Mode of Payment Account", {"parent": mode, "company": company}):
			result["existing"].append(mode)
			continue
		target = _mop_target_account(mode, mop_type, company, chart)
		if not target:
			result["skipped"].append(mode)
			continue
		doc = frappe.get_doc("Mode of Payment", mode)
		doc.append("accounts", {"company": company, "default_account": target})
		doc.save(ignore_permissions=True)
		result["created"].append(mode)
	return result


def ensure_store_accounts(store, method: str | None = None) -> dict[str, Any]:
	"""Provision a Store Location: per-store cash account + default bank link.

	Called on Store Location ``after_insert`` (hook) and by ``bootstrap_all()``.
	Never raises on partial data (e.g. a store with no company yet).
	"""
	company = store.get("company") or frappe.db.get_single_value("Global Defaults", "default_company")
	if not company:
		return {"store": store.name, "cash_account": None, "reason": "no_company"}

	chart = ensure_chart_accounts(company)  # noqa: F841 - parent accounts must exist before the store leaf
	store_code = store.get("store_code") or store.name
	cash_account = _create_account(company, f"Cash - {store_code}", "Cash", _group_account(company, "Cash"))

	if not store.get("default_bank_account"):
		default = ensure_default_bank_accounts(company)
		if default and frappe.db.exists("Store Location", store.name):
			frappe.db.set_value("Store Location", store.name, "default_bank_account", default["name"])

	return {"store": store.name, "cash_account": cash_account}


# --------------------------------------------------------------------------- #
# Orchestration + health check
# --------------------------------------------------------------------------- #
def bootstrap_all(args: dict[str, Any] | None = None) -> dict[str, Any]:
	"""Provision everything for every company and store. Idempotent, never raises."""
	result: dict[str, Any] = {"banks_created": ensure_bank_master(), "companies": {}, "stores": []}
	for company in frappe.get_all("Company", pluck="name"):
		try:
			result["companies"][company] = {
				"chart": ensure_chart_accounts(company),
				"bank_account": ensure_default_bank_accounts(company),
				"mop": ensure_mop_mappings(company),
			}
		except Exception:
			frappe.log_error(f"finance_bootstrap: failed for company {company}", frappe.get_traceback())
			result["companies"][company] = {"error": "see Error Log"}

	if frappe.db.exists("DocType", "Store Location"):
		for store_name in frappe.get_all("Store Location", pluck="name"):
			try:
				result["stores"].append(ensure_store_accounts(frappe.get_doc("Store Location", store_name)))
			except Exception:
				frappe.log_error(f"finance_bootstrap: failed for store {store_name}", frappe.get_traceback())
				result["stores"].append({"store": store_name, "error": "see Error Log"})
	return result


def health_check() -> dict[str, Any]:
	"""Setup completion checklist (self-healing: fills gaps, then reports).

	Consumed by the Finance Setup wizard (T3/T4) and any health page — a
	company/store entry is "done" when its checklist fields are all present.
	"""
	out: dict[str, Any] = {"companies": [], "stores": [], "gateways": {}}
	for company in frappe.get_all("Company", pluck="name"):
		chart = ensure_chart_accounts(company)
		bank_accounts = frappe.get_all(
			"Bank Account",
			filters={"company": company, "disabled": 0},
			fields=["name", "bank", "account", "bank_account_no", "is_default"],
		)
		mop_rows = frappe.get_all("Mode of Payment Account", filters={"company": company}, pluck="default_account")
		placeholders = [b["name"] for b in bank_accounts if not b.get("bank_account_no")]
		out["companies"].append(
			{
				"company": company,
				"chart": chart,
				"bank_accounts": bank_accounts,
				"mop_mapped": len(mop_rows),
				"mop_total": len(MOP_TYPES),
				"placeholders": placeholders,
			}
		)

	if frappe.db.exists("DocType", "Store Location"):
		for store in frappe.get_all(
			"Store Location", fields=["name", "store_code", "company", "default_bank_account"]
		):
			abbr = _abbr(store.company) if store.company else ""
			expected = f"Cash - {store.store_code or store.name} - {abbr}" if abbr else None
			out["stores"].append(
				{
					"store": store.name,
					"cash_account": expected if expected and frappe.db.exists("Account", expected) else None,
					"default_bank_account": store.get("default_bank_account"),
				}
			)

	if frappe.db.exists("DocType", "Payment Gateway Settings"):
		pgs = frappe.get_single("Payment Gateway Settings")
		out["gateways"] = {
			"stripe_enabled": bool(pgs.get("stripe_enabled")),
			"square_enabled": bool(pgs.get("square_enabled")),
		}
	return out


def execute() -> dict[str, Any]:
	"""CLI/console entry point: bootstrap everything and commit."""
	result = bootstrap_all()
	frappe.db.commit()  # nosemgrep (explicit CLI/migrate-hook commit)
	return result
