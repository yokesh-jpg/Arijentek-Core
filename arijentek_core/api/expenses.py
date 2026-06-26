import frappe
from frappe import _
from frappe.utils import flt, nowdate, today

from arijentek_core.api import get_current_employee
from arijentek_core.api.rate_limiter import user_rate_limit


def normalize_url(url: str) -> str:
	if not url:
		return ""
	from urllib.parse import urlparse
	path = urlparse(url).path
	if path and not path.startswith("/"):
		path = "/" + path
	return path


@frappe.whitelist()
def get_expense_types():
	"""Get all Expense Claim Types"""
	return frappe.get_all("Expense Claim Type", pluck="name")


@frappe.whitelist()
def get_my_expenses(status=None, from_date=None, to_date=None):
	"""Get current employee's expense claims with detailed lines and attachments"""
	employee = get_current_employee()
	if not employee:
		return []

	filters = {"employee": employee}
	if status:
		filters["approval_status"] = status
	if from_date and to_date:
		filters["posting_date"] = ["between", [from_date, to_date]]
	elif from_date:
		filters["posting_date"] = [">=", from_date]
	elif to_date:
		filters["posting_date"] = ["<=", to_date]

	expenses = frappe.get_all(
		"Expense Claim",
		filters=filters,
		fields=["name", "employee", "employee_name", "posting_date", "total_claimed_amount", "approval_status", "status", "company", "remark", "expense_approver", "payable_account"],
		order_by="name desc",
	)
	for exp in expenses:
		exp.proofs = frappe.get_all(
			"File",
			filters={"attached_to_doctype": "Expense Claim", "attached_to_name": exp.name},
			pluck="file_url",
		)
		# For backward compatibility
		exp.proof = exp.proofs[0] if exp.proofs else ""
		exp.expenses = frappe.get_all(
			"Expense Claim Detail",
			filters={"parent": exp.name},
			fields=[
				"expense_date",
				"expense_type",
				"description",
				"amount",
				"sanctioned_amount",
				"cost_center",
			],
		)
	return expenses


@frappe.whitelist(methods=["POST"])
@user_rate_limit(limit=10, seconds=60)
def submit_expense_claim(
	posting_date: str,
	expenses: str | list,
	expense_approver: str | None = None,
	remark: str | None = None,
	proof: str | None = None,
	proofs: str | list | None = None,
	name: str | None = None,
):
	"""Submit a new or updated Expense Claim as Draft"""
	employee = get_current_employee()
	if not employee:
		return {"success": False, "error": "Employee not found"}

	expenses_list = frappe.parse_json(expenses) if isinstance(expenses, str) else expenses
	if not expenses_list:
		return {"success": False, "error": "At least one expense line is required"}

	# Consolidate proof and proofs into a unique list of URLs
	proofs_list = []
	if proof:
		proofs_list.append(proof)
	if proofs:
		try:
			parsed_proofs = frappe.parse_json(proofs) if isinstance(proofs, str) else proofs
		except Exception:
			parsed_proofs = proofs
		if isinstance(parsed_proofs, list):
			proofs_list.extend(parsed_proofs)
		elif isinstance(parsed_proofs, str):
			proofs_list.append(parsed_proofs)
	proofs_list = [normalize_url(url) for url in proofs_list if url]
	proofs_list = list(set(proofs_list))

	try:
		# Retrieve employee details
		emp_info = frappe.db.get_value("Employee", employee, ["company"], as_dict=True)
		company = emp_info.get("company")

		if not company:
			return {"success": False, "error": "Company not found for employee"}

		# Retrieve company details
		company_info = frappe.db.get_value(
			"Company",
			company,
			["default_currency", "cost_center"],
			as_dict=True,
		)
		currency = company_info.get("default_currency") or "INR"
		cost_center = company_info.get("cost_center")

		if name:
			doc = frappe.get_doc("Expense Claim", name)
			if doc.employee != employee:
				user_roles = frappe.get_roles()
				emp_approvers = frappe.db.get_value(
					"Employee",
					doc.employee,
					["leave_approver", "shift_request_approver", "reports_to"],
					as_dict=True
				) or {}
				is_approver = (
					frappe.session.user in [emp_approvers.get("leave_approver"), emp_approvers.get("shift_request_approver")]
					or emp_approvers.get("reports_to") == employee
				)
				if not is_approver and "System Manager" not in user_roles and "HR Manager" not in user_roles:
					return {"success": False, "error": "Unauthorized to edit this expense claim"}
			if doc.docstatus != 0:
				return {"success": False, "error": "Only Draft expense claims can be updated"}
			doc.posting_date = posting_date
			doc.expense_approver = expense_approver
			doc.remark = remark or ""
			doc.set("expenses", [])
		else:
			doc = frappe.new_doc("Expense Claim")
			doc.employee = employee
			doc.company = company
			doc.posting_date = posting_date
			doc.currency = currency
			doc.exchange_rate = 1.0
			doc.expense_approver = expense_approver
			doc.remark = remark or ""
			doc.approval_status = "Draft"
			doc.expenses = []

		for exp in expenses_list:
			if not exp.get("expense_type"):
				return {"success": False, "error": "Expense type is required for each line"}
			amount = flt(exp.get("amount", 0.0))
			if amount <= 0:
				return {"success": False, "error": "Expense amount must be greater than zero"}

			doc.append(
				"expenses",
				{
					"expense_date": exp.get("expense_date") or posting_date,
					"expense_type": exp.get("expense_type"),
					"amount": amount,
					"sanctioned_amount": amount,
					"description": exp.get("description", ""),
					"cost_center": cost_center,
				},
			)

		if name:
			doc.save(ignore_permissions=True)
		else:
			doc.insert(ignore_permissions=True)

		# Sync attachments
		current_attachments = frappe.get_all(
			"File",
			filters={"attached_to_doctype": "Expense Claim", "attached_to_name": doc.name},
			fields=["name", "file_url"],
		)
		
		# Delete no longer needed files
		kept_urls = set(proofs_list)
		for att in current_attachments:
			att_url = normalize_url(att.file_url)
			if att_url not in kept_urls:
				frappe.delete_doc("File", att.name, ignore_permissions=True)
				
		# Attach newly added files
		attached_urls = {normalize_url(att.file_url) for att in current_attachments}
		for url in proofs_list:
			if url not in attached_urls:
				file_id = frappe.db.exists("File", {"file_url": url})
				if not file_id and url.startswith("/"):
					file_id = frappe.db.exists("File", {"file_url": url[1:]})
				if file_id:
					file_doc = frappe.get_doc("File", file_id)
					file_doc.attached_to_doctype = "Expense Claim"
					file_doc.attached_to_name = doc.name
					file_doc.save(ignore_permissions=True)

		return {"success": True, "name": doc.name}

	except Exception as e:
		frappe.db.rollback()
		return {"success": False, "error": str(e)}



@frappe.whitelist()
def get_team_expenses(status=None, from_date=None, to_date=None, employee=None):
	"""Get expenses for team with optional filters"""
	current_employee = get_current_employee()
	if not current_employee:
		return []

	user_roles = frappe.get_roles(frappe.session.user)
	if "System Manager" in user_roles or "HR Manager" in user_roles:
		reports = frappe.get_all(
			"Employee",
			filters={"status": "Active"},
			pluck="name",
		)
	else:
		# Get reports based on reports_to or leave/shift approver
		reports = frappe.get_all(
			"Employee",
			filters={"status": "Active"},
			or_filters={
				"reports_to": current_employee,
				"leave_approver": frappe.session.user,
				"shift_request_approver": frappe.session.user,
			},
			pluck="name",
		)
	if not reports:
		return []

	filters = {"docstatus": ["<", 2]}
	if employee:
		if employee in reports:
			filters["employee"] = employee
		else:
			return []
	else:
		filters["employee"] = ["in", reports]

	if status:
		filters["approval_status"] = status

	if from_date and to_date:
		filters["posting_date"] = ["between", [from_date, to_date]]
	elif from_date:
		filters["posting_date"] = [">=", from_date]
	elif to_date:
		filters["posting_date"] = ["<=", to_date]

	expenses = frappe.get_all(
		"Expense Claim",
		filters=filters,
		fields=["name", "employee", "employee_name", "total_claimed_amount", "posting_date", "status", "approval_status", "company", "remark", "expense_approver", "payable_account"],
		order_by="name desc",
	)

	for exp in expenses:
		exp.proofs = frappe.get_all(
			"File",
			filters={"attached_to_doctype": "Expense Claim", "attached_to_name": exp.name},
			pluck="file_url",
		)
		# For backward compatibility
		exp.proof = exp.proofs[0] if exp.proofs else ""
		# Retrieve all details of the expense lines
		exp.expenses = frappe.get_all(
			"Expense Claim Detail",
			filters={"parent": exp.name},
			fields=[
				"expense_date",
				"expense_type",
				"description",
				"amount",
				"sanctioned_amount",
				"cost_center",
			],
		)
		if exp.expenses:
			exp.expense_type = exp.expenses[0].expense_type
			exp.amount = exp.expenses[0].amount
			exp.description = exp.expenses[0].description
		else:
			exp.expense_type = ""
			exp.amount = 0
			exp.description = ""

	# Sort expenses: Draft first, then by posting_date desc (stable sort)
	expenses.sort(key=lambda x: 0 if x.approval_status == "Draft" else 1)

	return expenses



@frappe.whitelist()
def get_payable_accounts(company: str | None = None) -> list:
	"""Get non-group payable accounts for a company."""
	if not company:
		company = frappe.db.get_single_value("Global Defaults", "default_company")
	if not company:
		return []
	accounts = frappe.get_all(
		"Account",
		filters={
			"company": company,
			"account_type": "Payable",
			"is_group": 0,
		},
		fields=["name as value", "account_name as label"],
		order_by="name asc",
	)
	return accounts


@frappe.whitelist()
def get_expense_approvers(employee: str | None = None) -> dict:
	"""Get expense approval details for an employee."""
	if not employee:
		return {}
	from hrms.api import get_expense_approval_details
	return get_expense_approval_details(employee)


@frappe.whitelist()
def get_company_defaults(company: str | None = None) -> dict:
	"""Get default cost center and payable account for a company."""
	if not company:
		return {}
	from hrms.api import get_company_cost_center_and_expense_account
	return get_company_cost_center_and_expense_account(company)


@frappe.whitelist()
def delete_expense_claim(name: str):
	"""Delete a Draft Expense Claim"""
	try:
		frappe.delete_doc("Expense Claim", name)
		return {"success": True}
	except Exception as e:
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def process_expense(name: str, action: str, payable_account: str | None = None):
	"""Approve or Reject expense"""
	if action not in ["Approve", "Reject"]:
		return {"success": False, "error": "Invalid action"}

	employee = get_current_employee()
	if not employee:
		return {"success": False, "error": "Unauthorized"}

	try:
		doc = frappe.get_doc("Expense Claim", name)

		# Verify permission: Current user must be the leave approver, shift request approver, reports_to, or System Manager
		emp_approvers = frappe.db.get_value(
			"Employee",
			doc.employee,
			["leave_approver", "shift_request_approver", "reports_to"],
			as_dict=True
		) or {}

		is_approver = (
			frappe.session.user in [emp_approvers.get("leave_approver"), emp_approvers.get("shift_request_approver")]
			or emp_approvers.get("reports_to") == employee
		)

		if not is_approver and "System Manager" not in frappe.get_roles():
			return {"success": False, "error": "Unauthorized"}

		if doc.docstatus != 0:
			return {"success": False, "error": "Document must be in Draft state"}

		if action == "Approve":
			if payable_account:
				doc.payable_account = payable_account
			doc.approval_status = "Approved"
			doc.status = "Approved"  # Sync status
			doc.flags.ignore_permissions = True
			doc.save(ignore_permissions=True)
			doc.submit()  # Trigger submit to create GL entries
		else:
			if payable_account:
				doc.payable_account = payable_account
			doc.approval_status = "Rejected"
			doc.status = "Rejected"
			doc.flags.ignore_permissions = True
			doc.save(ignore_permissions=True)
			doc.submit()  # Trigger submit to finalize the document as Rejected

		return {"success": True}
	except Exception as e:
		return {"success": False, "error": str(e)}



