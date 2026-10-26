import frappe
from frappe import _


STANDARD_EXPENSE_TYPES = ["Calls", "Food", "Medical", "Others", "Travel"]


def get_administrative_expenses_account(company_name: str) -> str | None:
	"""
	Resolves the 'Administrative Expenses' account for a company.
	Checks exact account_name, then fuzzy name pattern.
	"""
	if not frappe.db.exists("DocType", "Account"):
		return None

	# 1. Exact match on account_name for the company
	acc = frappe.db.get_value(
		"Account",
		{
			"account_name": "Administrative Expenses",
			"company": company_name,
			"is_group": 0,
		},
		"name",
	)
	if acc:
		return acc

	# 2. Case-insensitive or like match on account_name
	acc = frappe.db.get_value(
		"Account",
		{
			"account_name": ("like", "%Administrative Expenses%"),
			"company": company_name,
			"is_group": 0,
		},
		"name",
	)
	if acc:
		return acc

	# 3. Match by name convention (e.g. 'Administrative Expenses - <abbr>')
	abbr = frappe.db.get_value("Company", company_name, "abbr")
	if abbr:
		acc = frappe.db.get_value(
			"Account",
			{
				"name": ("like", f"Administrative Expenses% - {abbr}"),
				"company": company_name,
				"is_group": 0,
			},
			"name",
		)
		if acc:
			return acc

	return None


@frappe.whitelist()
def update_standard_expense_types(company: str | None = None) -> dict:
	"""
	Ensures default Frappe Expense Claim Types (Calls, Food, Medical, Others, Travel)
	exist and are linked with the 'Administrative Expenses' account for each company.
	Also updates any existing Expense Claim Types that lack a default account.
	"""
	# Check permissions if called via web/API request
	if frappe.request and frappe.session.user and frappe.session.user not in ("Administrator",):
		roles = frappe.get_roles(frappe.session.user)
		if not ("System Manager" in roles or "HR Manager" in roles or "HR User" in roles or "Accounts Manager" in roles):
			frappe.throw(_("You do not have permission to configure Expense Claim Types"), frappe.PermissionError)

	if not frappe.db.exists("DocType", "Expense Claim Type"):
		frappe.logger().warning("Expense Claim Type DocType is not available. Skipping setup.")
		return {"status": "skipped", "message": "Expense Claim Type DocType not found"}

	try:
		companies = [company] if company else frappe.get_all("Company", pluck="name")
		if not companies:
			frappe.logger().warning("No companies found. Skipping expense claim types setup.")
			return {"status": "skipped", "message": "No companies found"}

		# Ensure default types exist in the database
		for type_name in STANDARD_EXPENSE_TYPES:
			if not frappe.db.exists("Expense Claim Type", type_name):
				new_type = frappe.get_doc({
					"doctype": "Expense Claim Type",
					"name": type_name,
					"expense_type": type_name,
					"description": f"Standard {type_name} expense claim",
				})
				new_type.flags.ignore_permissions = True
				new_type.insert(ignore_permissions=True)

		# Fetch all Expense Claim Types (standard + custom)
		all_types = frappe.get_all("Expense Claim Type", pluck="name")
		updated_types = []

		for type_name in all_types:
			doc = frappe.get_doc("Expense Claim Type", type_name)
			modified = False

			existing_companies = {row.company: row for row in (doc.accounts or [])}

			for comp in companies:
				admin_account = get_administrative_expenses_account(comp)
				if not admin_account:
					frappe.logger().warning(
						f"Could not find Administrative Expenses account for company '{comp}'."
					)
					continue

				if comp in existing_companies:
					row = existing_companies[comp]
					# Update if account is empty or if it's one of the standard default types
					if not row.default_account or type_name in STANDARD_EXPENSE_TYPES:
						if row.default_account != admin_account:
							row.default_account = admin_account
							modified = True
				else:
					doc.append("accounts", {
						"company": comp,
						"default_account": admin_account,
					})
					modified = True

			if modified:
				doc.flags.ignore_permissions = True
				doc.save(ignore_permissions=True)
				updated_types.append(type_name)

		frappe.logger().info(f"Configured Expense Claim Types with Administrative Expenses: {updated_types}")
		return {
			"status": "success",
			"updated_types": updated_types,
			"all_types": all_types,
		}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Setup Standard Expense Types Error")
		frappe.logger().error(f"Failed to setup Expense Claim Types: {e}")
		if frappe.flags.in_migrate or frappe.flags.in_install:
			return {"status": "error", "message": str(e)}
		raise e


def setup_standard_expense_types():
	"""Hook entry point for after_install and after_migrate."""
	return update_standard_expense_types()
