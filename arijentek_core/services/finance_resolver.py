# Copyright (c) 2026, Gemora 360
# License: GNU General Public License v3.0

"""
Finance placeholder resolver (T2).

T1 (``finance_bootstrap``) auto-provisions a placeholder ``Bank Account``
per company ("Default Bank Account - {abbr}" linked to the "Default Bank"
master) so the system works the day it is installed, with zero client input.

This module converts those placeholders into real accounts the moment the
client supplies actual bank details — through ``resolve_bank_account()``
(directly by the wizard, or via ``zevar_core.api.finance_setup``).

Guarantees:

  * Idempotent: resolving the same account twice with the same details is a
	no-op; re-resolving with corrected details updates in place.
  * Never destroys data: the COA leaf the company posts to is never changed
	unless explicitly passed; Mode of Payment mappings are untouched.
  * Renames the master to ``{account_name} - {bank}`` so every reference
	(Store Location, Payment Entry, Journal Entry, ...) follows via
	``frappe.rename_doc`` link updates.
  * Blocks duplicates: refuses to create a second master with the same
	bank + account number, and refuses to collide on the target name.
  * Self-heals: a company with no Bank Account at all gets a placeholder
	provisioned before resolution, so resolve never needs manual prep.

``pending_placeholders()`` feeds the wizard's "what still needs bank
details?" screen.
"""

import frappe
from frappe import _

PLACEHOLDER_BANK = "Default Bank"


def _clean(value, max_len: int | None = None) -> str | None:
	"""Strip and normalize an optional string argument."""
	if value is None:
		return None
	value = str(value).strip()
	if not value:
		return None
	return value[:max_len] if max_len else value


def _is_placeholder(bank_account_doc) -> bool:
	"""A record is a placeholder until it has a real bank and a number."""
	return (
		bank_account_doc.get("bank") == PLACEHOLDER_BANK
		or not bank_account_doc.get("bank_account_no")
	)


def _ensure_bank(bank_name: str) -> str:
	"""The Bank master row for a (possibly new) bank name."""
	existing = frappe.db.exists("Bank", bank_name)
	if existing:
		return existing
	bank = frappe.new_doc("Bank")
	bank.bank_name = bank_name
	bank.insert(ignore_permissions=True)
	return bank.name


def _find_target(company: str) -> str | None:
	"""The Bank Account a company's money lands in: default first, else any.

	Missing entirely -> provision the placeholder (self-heal) and re-find.
	"""
	filters = {"company": company, "disabled": 0}
	default = frappe.db.get_value(
		"Bank Account", {**filters, "is_default": 1}, "name"
	)
	if default:
		return default
	any_account = frappe.db.get_value("Bank Account", filters, "name")
	if any_account:
		return any_account
	from arijentek_core.services.finance_bootstrap import ensure_default_bank_accounts

	result = ensure_default_bank_accounts(company)
	if result:
		return result["name"]
	return None


def resolve_bank_account(
	company: str,
	*,
	bank: str,
	account_name: str | None = None,
	bank_account_no: str | None = None,
	iban: str | None = None,
	branch_code: str | None = None,
	account: str | None = None,
	party_type: str | None = None,
	party: str | None = None,
) -> dict:
	"""Convert the company's placeholder Bank Account into a real one.

	All keyword arguments are optional except ``company`` and ``bank``;
	omitted fields keep their current value, so the wizard can fill the
	form across multiple saves.

	Raises ``frappe.ValidationError`` on unknown company, unknown bank
	account, duplicate details/name, or an ``account`` that does not
	belong to the company.
	"""
	# -- validate inputs ---------------------------------------------------- #
	if not frappe.db.exists("Company", company):
		frappe.throw(_("Company '{0}' does not exist.").format(company))
	bank_name = _clean(bank, 140)
	if not bank_name:
		frappe.throw(_("Bank name is required."))
	account_name = _clean(account_name, 140)
	bank_account_no = _clean(bank_account_no, 40)
	iban = _clean(iban, 34)
	branch_code = _clean(branch_code, 40)
	account = _clean(account, 140)
	party_type = _clean(party_type, 140)
	party = _clean(party, 140)

	# -- locate target ------------------------------------------------------ #
	target_name = _find_target(company)
	if not target_name:
		frappe.throw(
			_("No Bank Account exists for {0}. Run the finance bootstrap first.").format(company)
		)
	target = frappe.get_doc("Bank Account", target_name)
	was_placeholder = _is_placeholder(target)

	# -- duplicate guards --------------------------------------------------- #
	if account and not frappe.db.exists(
		"Account", {"name": account, "company": company}
	):
		frappe.throw(_("Account '{0}' does not exist for {1}.").format(account, company))
	if bank_account_no:
		clash = frappe.db.get_value(
			"Bank Account",
			{
				"company": company,
				"disabled": 0,
				"bank": bank_name,
				"bank_account_no": bank_account_no,
				"name": ["!=", target.name],
			},
			"name",
		)
		if clash:
			frappe.throw(
				_(
					"Bank Account '{0}' already has bank {1} and account number {2}. "
					"Delete it or resolve that record instead."
				).format(clash, bank_name, bank_account_no)
			)

	# -- enrich the record -------------------------------------------------- #
	new_label = account_name or target.account_name or f"Bank Account - {company}"
	new_name = f"{new_label} - {bank_name}"
	if new_name != target.name and frappe.db.exists("Bank Account", new_name):
		frappe.throw(
			_("A Bank Account named '{0}' already exists. Pick a different account name.").format(
				new_name
			)
		)

	real_bank = _ensure_bank(bank_name)
	target.bank = real_bank
	if account_name:
		target.account_name = account_name
	if bank_account_no:
		target.bank_account_no = bank_account_no
	if iban:
		target.iban = iban
	if branch_code:
		target.branch_code = branch_code
	if account:
		target.account = account
	if party_type and party:
		target.party_type = party_type
		target.party = party
	target.is_company_account = 1
	target.save(ignore_permissions=True)

	# -- rename so references follow ---------------------------------------- #
	if new_name != target.name:
		frappe.rename_doc("Bank Account", target.name, new_name, force=False)

	# -- audit trail --------------------------------------------------------- #
	from arijentek_core.api.audit_log import log_event_safely

	log_event_safely(
		event_type="finance_bank_updated",
		details={
			"bank_account": new_name,
			"company": company,
			"bank": bank_name,
			"account_no": target.bank_account_no,
			"was_placeholder": was_placeholder,
			"resolved_by": frappe.session.user,
		},
		reference_document=new_name,
		reference_type="Bank Account",
	)

	return {
		"name": new_name,
		"company": company,
		"bank": bank_name,
		"account_name": new_label,
		"bank_account_no": target.bank_account_no,
		"iban": target.iban,
		"branch_code": target.branch_code,
		"account": target.account,
		"resolved": was_placeholder,
	}


def pending_placeholders() -> dict:
	"""Companies still waiting for real bank details.

	Returns:
		{
			"pending": [ {company, abbr, name, bank, account_name, account,
			             is_default, bank_account_no} ... ],  # placeholders
			"unprovisioned": [ {company, abbr} ... ],  # no Bank Account at all
			"resolved": [ same shape as pending ... ],  # real accounts
			"count": int,
		}
	"""
	rows = frappe.get_all(
		"Bank Account",
		filters={"disabled": 0},
		fields=[
			"name",
			"company",
			"bank",
			"account_name",
			"account",
			"is_default",
			"bank_account_no",
		],
	)
	pending = [r for r in rows if _is_placeholder(r)]
	resolved = [r for r in rows if not _is_placeholder(r)]
	with_accounts = {r["company"] for r in rows}
	unprovisioned = [
		{
			"company": name,
			"abbr": frappe.get_cached_value("Company", name, "abbr") or name,
		}
		for name in frappe.get_all("Company", pluck="name")
		if name not in with_accounts
	]
	for row in pending + resolved:
		row["abbr"] = frappe.get_cached_value("Company", row["company"], "abbr") or row["company"]
	return {
		"pending": pending,
		"unprovisioned": unprovisioned,
		"resolved": resolved,
		"count": len(pending) + len(unprovisioned),
	}
