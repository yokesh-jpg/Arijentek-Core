"""
Payroll Account Setup and Migration API.

Ensures that all Payroll Payable accounts across companies have account_type = 'Payable'
to prevent HRMS validation errors when creating or submitting Payroll Entries:
'Account type should be set Payable for payroll payable account Payroll Payable - ZG, please set and try again'
"""

import frappe
from frappe import _


MIGRATION_KEY = "payroll_payable_account_type_migrated"


@frappe.whitelist()
def update_payroll_payable_account_type(company: str | None = None, force: bool = False) -> dict:
	"""
	Custom update API to ensure payroll payable accounts have account_type = 'Payable'.
	Checks if already migrated, and only processes unmigrated accounts to avoid duplicates.

	Can be called:
	- Via API: arijentek_core.api.payroll_account.update_payroll_payable_account_type
	- Via Hooks: after_install, after_migrate
	"""
	# Permission check if called over HTTP
	if frappe.request and frappe.session.user and frappe.session.user != "Administrator":
		roles = frappe.get_roles(frappe.session.user)
		if not ("System Manager" in roles or "HR Manager" in roles or "Accounts Manager" in roles):
			frappe.throw(_("Not permitted to configure payroll payable accounts"), frappe.PermissionError)

	if not frappe.db.exists("DocType", "Account"):
		return {"status": "skipped", "message": "Account DocType not available"}

	# Avoid duplicate run if already migrated, unless force=True or company specific filter
	already_migrated = frappe.db.get_default(MIGRATION_KEY)
	if already_migrated == "1" and not force and not company:
		# Check if any new or unmigrated account exists
		unmigrated_count = frappe.db.sql("""
			SELECT count(name)
			FROM `tabAccount`
			WHERE (
				account_name = 'Payroll Payable'
				OR name LIKE %(pattern)s
				OR name IN (
					SELECT default_payroll_payable_account
					FROM `tabCompany`
					WHERE default_payroll_payable_account IS NOT NULL AND default_payroll_payable_account != ''
				)
			)
			AND (account_type IS NULL OR account_type != 'Payable')
		""", {"pattern": "Payroll Payable%"})[0][0]

		if unmigrated_count == 0:
			return {
				"status": "already_migrated",
				"message": "Payroll payable accounts are already migrated and set to Payable.",
				"updated": [],
			}

	# Build query for accounts to update
	condition = """
		(
			account_name = 'Payroll Payable'
			OR name LIKE %(pattern)s
			OR name IN (
				SELECT default_payroll_payable_account
				FROM `tabCompany`
				WHERE default_payroll_payable_account IS NOT NULL AND default_payroll_payable_account != ''
			)
		)
		AND (account_type IS NULL OR account_type != 'Payable')
	"""
	values = {"pattern": "Payroll Payable%"}
	if company:
		condition += " AND company = %(company)s"
		values["company"] = company

	accounts_to_update = frappe.db.sql(f"""
		SELECT name, account_name, account_type, company
		FROM `tabAccount`
		WHERE {condition}
	""", values, as_dict=True)

	if not accounts_to_update:
		if not company:
			frappe.db.set_default(MIGRATION_KEY, "1")
			frappe.db.commit()
		return {
			"status": "already_migrated",
			"message": "No payroll payable accounts needed updating.",
			"updated": [],
		}

	updated = []
	for acc in accounts_to_update:
		frappe.db.set_value("Account", acc.name, "account_type", "Payable", update_modified=False)
		updated.append(acc.name)

	if not company:
		frappe.db.set_default(MIGRATION_KEY, "1")
	frappe.db.commit()

	frappe.logger().info(f"Updated payroll payable accounts to account_type='Payable': {updated}")
	return {
		"status": "success",
		"message": f"Successfully updated {len(updated)} payroll payable account(s) to Payable.",
		"updated": updated,
	}


def setup_payroll_payable_account():
	"""Hook entry point for after_install and after_migrate."""
	try:
		return update_payroll_payable_account_type(force=False)
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Setup Payroll Payable Account Error")
		frappe.logger().error(f"Failed to setup payroll payable accounts: {e}")
		if getattr(frappe.flags, "in_migrate", False) or getattr(frappe.flags, "in_install", False):
			return {"status": "error", "message": str(e)}
		raise e
