"""
Expense API - Expense claim management for employee portal

Provides endpoints for listing expense claims, expense types,
creating new claims, and submitting them for approval.
"""

import frappe
from frappe import _
from frappe.utils import flt, get_first_day, get_last_day, today


@frappe.whitelist()
def get_expense_claims(
	employee: str | None = None,
	status: str | None = None,
	start_date: str | None = None,
	end_date: str | None = None,
) -> list:
	"""
	Get expense claims for an employee.

	Args:
		employee: Employee ID to filter claims
		status: Optional status filter (Draft, Pending, Approved, Rejected, Paid)
		start_date: Optional posting start date
		end_date: Optional posting end date

	Returns:
		List of expense claim dicts
	"""
	if not employee:
		user = frappe.session.user
		employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
		if not employee:
			return []

	filters = {"employee": employee, "docstatus": ["!=", 2]}
	if status:
		filters["status"] = status
	if start_date and end_date:
		filters["posting_date"] = ["between", [start_date, end_date]]
	elif start_date:
		filters["posting_date"] = [">=", start_date]
	elif end_date:
		filters["posting_date"] = ["<=", end_date]

	claims = frappe.get_all(
		"Expense Claim",
		filters=filters,
		fields=[
			"name",
			"employee",
			"employee_name",
			"expense_approver",
			"payable_account",
			"total_claimed_amount",
			"total_sanctioned_amount",
			"status",
			"posting_date",
			"company",
			"remark",
			"creation",
		],
		order_by="name desc",
	)

	for claim in claims:
		claim.expenses = frappe.get_all(
			"Expense Claim Detail",
			filters={"parent": claim.name},
			fields=[
				"expense_date",
				"expense_type",
				"description",
				"amount",
				"sanctioned_amount",
				"cost_center",
			],
		)

	return claims


@frappe.whitelist()
def get_expense_types() -> list:
	"""
	Get available expense claim types.

	Returns:
		List of expense type dicts with name and description
	"""
	types = frappe.get_all(
		"Expense Claim Type",
		fields=["name", "expense_type as label"],
		order_by="name asc",
	)
	return types


@frappe.whitelist(methods=["POST"])
def create_expense_claim(
	employee: str | None = None,
	expenses: str | list | None = None,
	remark: str | None = None,
	company: str | None = None,
) -> dict:
	"""
	Create a new expense claim (in Draft state).

	Args:
		employee: Employee ID (auto-detected if not provided)
		expenses: JSON list of expense items with expense_type, amount, description
		remark: Optional remark
		company: Company (auto-detected if not provided)

	Returns:
		Dict with success flag and claim name
	"""
	if not can_create_expense_claim():
		frappe.throw(_("Not authorized to create Expense Claims."), frappe.PermissionError)
	if not employee:
		user = frappe.session.user
		employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
		if not employee:
			frappe.throw(_("No Employee record found for current user."))

	if not company:
		company = frappe.db.get_value("Employee", employee, "company")
	if not company:
		company = frappe.db.get_single_value("Global Defaults", "default_company")

	expenses_list = frappe.parse_json(expenses) if isinstance(expenses, str) else expenses
	if not expenses_list:
		frappe.throw(_("At least one expense item is required."))

	cost_center = frappe.db.get_value("Company", company, "cost_center")

	try:
		claim = frappe.new_doc("Expense Claim")
		claim.employee = employee
		claim.company = company
		claim.remark = remark or ""
		claim.posting_date = today()
		claim.currency = frappe.db.get_value("Company", company, "default_currency") or "INR"
		claim.exchange_rate = 1.0

		for exp in expenses_list:
			if not exp.get("expense_type"):
				frappe.throw(_("Expense type is required for each item."))
			amount = flt(exp.get("amount", 0))
			if amount <= 0:
				frappe.throw(_("Expense amount must be greater than zero."))

			claim.append(
				"expenses",
				{
					"expense_type": exp.get("expense_type"),
					"description": exp.get("description", ""),
					"amount": amount,
					"sanctioned_amount": amount,
					"cost_center": cost_center,
				},
			)

		claim.insert(ignore_permissions=True)

		try:
			from arijentek_core.api.notifications import notify_approvers
			emp_name = frappe.db.get_value("Employee", claim.employee, "employee_name") or claim.employee
			title = "New Expense Claim"
			body = f"{emp_name} has submitted a new expense claim."
			notify_approvers(claim, title, body, module="hrm", route="/expense?tab=dashboard")
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Expense Notification Error")

		return {
			"success": True,
			"name": claim.name,
			"status": claim.status,
			"message": _("Expense Claim {0} created successfully.").format(claim.name),
		}
	except frappe.ValidationError as e:
		frappe.db.rollback()
		raise e
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error("Expense Claim Creation Failed", frappe.get_traceback())
		frappe.throw(_("Failed to create expense claim: {0}").format(str(e)))


@frappe.whitelist()
def get_expense_summary(employee_id: str | None = None, employee: str | None = None) -> dict:
	"""
	Get expense summary statistics for an employee.

	Args:
		employee_id: Employee ID to filter (optional, fallback to logged-in employee)
		employee: Alternative parameter name for employee ID

	Returns:
		Dict containing monthly summary stats:
		- monthly_total_count: Number of claims this month
		- monthly_total_amount: Sum of claimed amount this month
		- monthly_approved_count: Number of approved/paid claims this month
		- monthly_approved_amount: Sum of sanctioned amount for approved/paid claims this month
		- monthly_rejected_count: Number of rejected claims this month
		- monthly_rejected_amount: Sum of claimed amount for rejected claims this month
	"""
	emp = employee_id or employee
	if not emp:
		user = frappe.session.user
		emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
		if not emp:
			return {
				"monthly_total_count": 0,
				"monthly_total_amount": 0.0,
				"monthly_approved_count": 0,
				"monthly_approved_amount": 0.0,
				"monthly_rejected_count": 0,
				"monthly_rejected_amount": 0.0,
			}

	# Get start and end dates of the current month
	first_day = get_first_day(today())
	last_day = get_last_day(today())

	# Get all non-cancelled expense claims for this employee in the current month
	claims = frappe.get_all(
		"Expense Claim",
		filters={
			"employee": emp,
			"docstatus": ["!=", 2],
			"posting_date": ["between", [first_day, last_day]],
		},
		fields=["status", "total_claimed_amount", "total_sanctioned_amount"],
	)

	monthly_total_count = 0
	monthly_total_amount = 0.0
	monthly_approved_count = 0
	monthly_approved_amount = 0.0
	monthly_rejected_count = 0
	monthly_rejected_amount = 0.0

	for claim in claims:
		status = claim.get("status")
		claimed_amt = flt(claim.get("total_claimed_amount", 0.0))
		sanctioned_amt = flt(claim.get("total_sanctioned_amount", 0.0))

		# Total claims this month
		monthly_total_count += 1
		monthly_total_amount += claimed_amt

		# Approved claims (Paid or Unpaid)
		if status in ["Paid", "Unpaid"]:
			monthly_approved_count += 1
			monthly_approved_amount += sanctioned_amt

		# Rejected claims
		elif status == "Rejected":
			monthly_rejected_count += 1
			monthly_rejected_amount += claimed_amt

	return {
		"monthly_total_count": monthly_total_count,
		"monthly_total_amount": flt(monthly_total_amount),
		"monthly_approved_count": monthly_approved_count,
		"monthly_approved_amount": flt(monthly_approved_amount),
		"monthly_rejected_count": monthly_rejected_count,
		"monthly_rejected_amount": flt(monthly_rejected_amount),
	}


@frappe.whitelist(methods=["GET", "POST"])
def get_payable_accounts(company: str | None = None) -> list:
	"""Get non-group payable accounts for a company."""
	if not company:
		user = frappe.session.user
		employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
		if employee:
			company = frappe.db.get_value("Employee", employee, "company")
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


@frappe.whitelist(methods=["GET", "POST"])
def get_expense_approvers(employee: str | None = None) -> dict:
	"""Get expense approval details for an employee."""
	if not employee:
		return {}
	from hrms.api import get_expense_approval_details
	return get_expense_approval_details(employee)


@frappe.whitelist(methods=["GET", "POST"])
def get_company_defaults(company: str | None = None) -> dict:
	"""Get default cost center and payable account for a company."""
	if not company:
		user = frappe.session.user
		employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
		if employee:
			company = frappe.db.get_value("Employee", employee, "company")
		if not company:
			company = frappe.db.get_single_value("Global Defaults", "default_company")
	if not company:
		return {}
	from hrms.api import get_company_cost_center_and_expense_account
	return get_company_cost_center_and_expense_account(company)


@frappe.whitelist(methods=["POST"])
def submit_new_expense_claim(
	employee: str,
	posting_date: str,
	payable_account: str | None = None,
	expense_approver: str | None = None,
	expenses: str | list | None = None,
	remark: str | None = None,
	name: str | None = None,
) -> dict:
	"""
	Create and insert or update a new/existing Expense Claim document.
	"""
	# Permission gate (matches the update_expense_claim_status pattern).
	if name:
		if not can_edit_expense_claim():
			frappe.throw(_("Not authorized to edit Expense Claims."), frappe.PermissionError)
	elif not can_create_expense_claim():
		frappe.throw(_("Not authorized to create Expense Claims."), frappe.PermissionError)

	if not employee:
		frappe.throw(_("Employee is required."))

	company = frappe.db.get_value("Employee", employee, "company")
	if not company:
		company = frappe.db.get_single_value("Global Defaults", "default_company")

	expenses_list = frappe.parse_json(expenses) if isinstance(expenses, str) else expenses
	if not expenses_list:
		frappe.throw(_("At least one expense line is required."))

	try:
		if name:
			claim = frappe.get_doc("Expense Claim", name)
			if claim.docstatus != 0:
				frappe.throw(_("Only Draft expense claims can be updated."))
			claim.posting_date = posting_date
			if payable_account:
				claim.payable_account = payable_account
			if expense_approver:
				claim.expense_approver = expense_approver
			claim.remark = remark or ""
			claim.set("expenses", [])
		else:
			claim = frappe.new_doc("Expense Claim")
			claim.employee = employee
			claim.company = company
			claim.posting_date = posting_date
			if payable_account:
				claim.payable_account = payable_account
			if expense_approver:
				claim.expense_approver = expense_approver
			claim.remark = remark or ""
			claim.currency = frappe.db.get_value("Company", company, "default_currency") or "INR"
			claim.exchange_rate = 1.0

		cost_center = frappe.db.get_value("Company", company, "cost_center")

		for exp in expenses_list:
			if not exp.get("expense_type"):
				frappe.throw(_("Expense type is required for each line."))
			amount = flt(exp.get("amount", 0.0))
			if amount <= 0:
				frappe.throw(_("Expense amount must be greater than zero."))

			claim.append(
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
			claim.save(ignore_permissions=True)
		else:
			claim.insert(ignore_permissions=True)

		try:
			from arijentek_core.api.notifications import notify_approvers
			emp_name = frappe.db.get_value("Employee", claim.employee, "employee_name") or claim.employee
			title = "New Expense Claim"
			body = f"{emp_name} has submitted an expense claim."
			notify_approvers(claim, title, body, module="hrm", route="/expense?tab=dashboard")
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Expense Notification Error")

		return {
			"success": True,
			"name": claim.name,
			"status": claim.status,
			"message": _("Expense Claim {0} saved successfully.").format(claim.name),
		}
	except frappe.ValidationError as e:
		frappe.db.rollback()
		raise e
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error("Expense Claim Submission Failed", frappe.get_traceback())
		frappe.throw(_("Failed to submit expense claim: {0}").format(str(e)))


@frappe.whitelist()
def get_expense_status_options() -> list:
	"""Return allowed status options for Expense Claim from the DocType."""
	options = frappe.get_meta("Expense Claim").get_field("status").options or ""
	if isinstance(options, str):
		return [opt for opt in options.split("\n") if opt.strip()]
	return options or []


@frappe.whitelist()
def is_user_expense_approver(employee_id: str = None) -> dict:
	"""Check if current user is an expense approver and return accessible employees."""
	user = frappe.session.user
	has_approver_role = frappe.has_permission("Expense Claim", "submit")
	has_global_approver = has_approver_role and not frappe.permissions.get_user_permissions(user).get("Employee")

	# Employees this user is explicitly assigned as approver for
	special_employees = frappe.db.get_all(
		"Employee",
		filters={"expense_approver": user, "status": ["in", ["Active", "Suspended"]]},
		fields=["name", "employee_name"],
		order_by="employee_name ASC"
	)

	# Also add themselves to the list if they are an employee
	my_employee = frappe.db.get_value("Employee", {"user_id": user}, ["name", "employee_name"], as_dict=True)

	is_approver = has_approver_role or bool(special_employees)

	if not is_approver:
		prevent_self = frappe.db.get_single_value("HR Settings", "prevent_self_expense_approval")
		return {
			"is_approver": False,
			"type": "none",
			"employees": [],
			"is_global_approver": False,
			"prevent_self_expense_approval": prevent_self,
		}

	if has_global_approver:
		employees = frappe.get_list(
			"Employee",
			filters={"status": ["in", ["Active", "Suspended"]]},
			fields=["name", "employee_name"],
			order_by="employee_name ASC",
		)
		existing = {e["name"] for e in employees}
		for emp in special_employees:
			if emp["name"] not in existing:
				employees.append(emp)
				existing.add(emp["name"])
	else:
		employees = list(special_employees)

	# Ensure self is at the front if not already present
	if my_employee and not any(e["name"] == my_employee.name for e in employees):
		employees.insert(0, my_employee)

	prevent_self = frappe.db.get_single_value("HR Settings", "prevent_self_expense_approval")

	approver_type = "global" if has_global_approver else "special"
	return {
		"is_approver": True,
		"type": approver_type,
		"employees": employees,
		"is_global_approver": has_global_approver,
		"prevent_self_expense_approval": prevent_self,
	}


@frappe.whitelist()
def get_expense_claims_for_all(
	status: str | None = None,
	start_date: str | None = None,
	end_date: str | None = None,
) -> list[dict]:
	"""Return all expense claims for employees the current user can access."""
	user = frappe.session.user

	special_employees = frappe.get_list(
		"Employee",
		filters={"expense_approver": user, "status": ["in", ["Active", "Suspended"]]},
		fields=["name", "employee_name"],
		order_by="employee_name ASC",
	)

	my_employee = frappe.db.get_value(
		"Employee", {"user_id": user}, ["name", "employee_name"], as_dict=True
	)

	permission_employees = frappe.get_list(
		"Employee",
		filters={"status": ["in", ["Active", "Suspended"]]},
		fields=["name", "employee_name"],
		order_by="employee_name ASC",
	)

	existing = {e["name"] for e in permission_employees}
	for emp in special_employees:
		if emp["name"] not in existing:
			permission_employees.append(emp)
			existing.add(emp["name"])

	if my_employee and not any(e["name"] == my_employee.name for e in permission_employees):
		permission_employees.insert(0, my_employee)

	if not permission_employees:
		return []

	employee_names = [e["name"] for e in permission_employees]

	# Build filters based on status
	filters = {
		"employee": ["in", employee_names],
		"docstatus": ["<", 2]
	}
	if status:
		filters["status"] = status
	if start_date and end_date:
		filters["posting_date"] = ["between", [start_date, end_date]]
	elif start_date:
		filters["posting_date"] = [">=", start_date]
	elif end_date:
		filters["posting_date"] = ["<=", end_date]

	claims = frappe.get_all(
		"Expense Claim",
		filters=filters,
		fields=[
			"name",
			"employee",
			"employee_name",
			"expense_approver",
			"payable_account",
			"total_claimed_amount",
			"total_sanctioned_amount",
			"status",
			"posting_date",
			"company",
			"remark",
			"creation",
		],
		order_by="name desc",
	)

	for claim in claims:
		claim.expenses = frappe.get_all(
			"Expense Claim Detail",
			filters={"parent": claim.name},
			fields=[
				"expense_date",
				"expense_type",
				"description",
				"amount",
				"sanctioned_amount",
				"cost_center",
			],
		)

	return claims


@frappe.whitelist()
def delete_expense_claim(name: str):
	if not can_delete_expense_claim():
		frappe.throw(_("Not authorized to delete Expense Claims."), frappe.PermissionError)
	try:
		doc = frappe.get_doc("Expense Claim", name)
		if doc.docstatus == 1:
			doc.cancel()
		frappe.delete_doc("Expense Claim", name)
		frappe.db.commit()
		return {"success": True}
	except Exception as e:
		frappe.db.rollback()
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def update_expense_claim_status(name: str, status: str):
	"""Approve or reject an Expense Claim by setting approval_status and submitting it."""
	try:
		doc = frappe.get_doc("Expense Claim", name)
		if not can_approve_expense_claim():
			return {"success": False, "error": "Not authorized to approve/reject this Expense Claim."}

		if status == "Approved":
			frappe.db.sql("""
				UPDATE `tabExpense Claim`
				SET approval_status = 'Approved', status = 'Submitted', docstatus = 1
				WHERE name = %s
			""", (name,))
		else:
			frappe.db.sql("""
				UPDATE `tabExpense Claim`
				SET approval_status = 'Rejected', status = 'Rejected', docstatus = 1
				WHERE name = %s
			""", (name,))

		frappe.db.commit()

		try:
			from arijentek_core.api.notifications import notify_owner
			title = f"Expense Claim {status}"
			body = f"Your expense claim {name} has been {status}."
			notify_owner(doc, title, body, module="hrm", route="/expense?tab=dashboard")
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Expense Notification Error")

		return {"success": True}
	except Exception as e:
		frappe.db.rollback()
		return {"success": False, "error": str(e)}


@frappe.whitelist(methods=["POST"])
def disburse_expense_claim(claim_name: str, mode_of_payment: str = "Bank Transfer") -> dict:
	"""Create a Payment Entry to pay an approved Expense Claim to the employee.

	Only works on submitted claims with ``approval_status='Approved'`` that are not
	already paid. The PE references the Expense Claim (so ERPNext reconciles it); the
	claim is then marked ``Paid``. Permission matches the approve gate.
	"""
	from arijentek_core.services.bank_registry import resolve_bank_account

	if not can_approve_expense_claim():
		frappe.throw(_("Not authorized to disburse Expense Claims."), frappe.PermissionError)

	doc = frappe.get_doc("Expense Claim", claim_name)
	if doc.docstatus != 1 or doc.approval_status != "Approved":
		frappe.throw(_("Only approved, submitted claims can be disbursed."))
	if doc.status == "Paid":
		frappe.throw(_("This claim has already been paid."))

	amount = flt(doc.total_sanctioned_amount)
	if amount <= 0:
		frappe.throw(_("Claim has no sanctioned amount to disburse."))

	company = doc.company or frappe.db.get_single_value("Global Defaults", "default_company")
	if not company:
		frappe.throw(_("No company found on the claim."))

	paid_from = resolve_bank_account(company=company)
	if not paid_from:
		frappe.throw(_("Cannot resolve bank account for {0}. Complete Finance Setup.").format(company))

	payable = doc.payable_account or frappe.db.get_value(
		"Account", {"account_type": "Payable", "company": company, "is_group": 0}, "name"
	)
	if not payable:
		frappe.throw(_("No Payable account found for {0}.").format(company))

	try:
		pe = frappe.get_doc(
			{
				"doctype": "Payment Entry",
				"payment_type": "Pay",
				"company": company,
				"posting_date": today(),
				"mode_of_payment": mode_of_payment,
				"party_type": "Employee",
				"party": doc.employee,
				"paid_from": paid_from,
				"paid_to": payable,
				"paid_amount": amount,
				"received_amount": amount,
				"reference_no": claim_name,
				"reference_date": today(),
				"remark": f"Expense claim disbursement - {claim_name}",
				"references": [
					{
						"reference_doctype": "Expense Claim",
						"reference_name": claim_name,
						"allocated_amount": amount,
					}
				],
			}
		)
		pe.flags.ignore_permissions = True
		pe.insert()
		pe.submit()

		# ERPNext auto-updates the claim via the reference; set explicitly so the
		# status reflects the disbursement regardless of native-hook timing.
		frappe.db.set_value("Expense Claim", claim_name, {"status": "Paid", "is_paid": 1})
		return {"success": True, "payment_entry": pe.name, "amount": amount}
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error("Expense Claim Disbursement Failed", frappe.get_traceback())
		frappe.throw(_("Failed to disburse expense claim: {0}").format(str(e)))


@frappe.whitelist()
def can_read_expense_claim():
	"""
	Returns True if the current user has permission to read Expense Claim.
	This is true for 'HR Manager', 'System Manager', or users with explicit read permissions on the 'Expense Claim' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Expense Claim", "read"):
		return True

	return False


@frappe.whitelist()
def can_create_expense_claim():
	"""
	Returns True if the current user has permission to create a Expense Claim.
	This is true for 'HR Manager', 'System Manager', or users with explicit create permissions on the 'Expense Claim' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Expense Claim", "create"):
		return True

	return False


@frappe.whitelist()
def can_edit_expense_claim():
	"""
	Returns True if the current user has permission to edit (write) an Expense Claim.
	This is true for 'HR Manager', 'System Manager', or users with explicit write permissions on the 'Expense Claim' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Expense Claim", "write"):
		return True

	return False


@frappe.whitelist()
def can_delete_expense_claim():
	"""
	Returns True if the current user has permission to delete an Expense Claim.
	This is true for 'HR Manager', 'System Manager', or users with explicit delete permissions on the 'Expense Claim' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Expense Claim", "delete"):
		return True

	return False


@frappe.whitelist()
def can_approve_expense_claim():
	"""
	Returns True if the current user has permission to approve (submit) an Expense Claim.
	This is true for 'HR Manager', 'System Manager', or users with explicit submit permissions on the 'Expense Claim' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Expense Claim", "submit"):
		return True

	return False


@frappe.whitelist()
def can_read_expense_types():
	"""
	Returns True if the current user has permission to read Expense Claim Types.
	This is true for 'HR Manager', 'System Manager', or users with explicit read permissions on the 'Expense Claim Type' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Expense Claim Type", "read"):
		return True

	return False


@frappe.whitelist()
def can_create_expense_types():
	"""
	Returns True if the current user has permission to create an Expense Claim Type.
	This is true for 'HR Manager', 'System Manager', or users with explicit create permissions on the 'Expense Claim Type' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Expense Claim Type", "create"):
		return True

	return False


@frappe.whitelist()
def can_delete_expense_types():
	"""
	Returns True if the current user has permission to delete an Expense Claim Type.
	This is true for 'HR Manager', 'System Manager', or users with explicit delete permissions on the 'Expense Claim Type' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Expense Claim Type", "delete"):
		return True

	return False


@frappe.whitelist()
def can_edit_expense_types():
	"""
	Returns True if the current user has permission to edit an Expense Claim Type.
	This is true for 'HR Manager', 'System Manager', or users with explicit write permissions on the 'Expense Claim Type' Doctype.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("Expense Claim Type", "write"):
		return True

	return False


@frappe.whitelist(methods=["GET", "POST"])
def get_employee_list():
	"""Get list of active employees."""
	return frappe.get_all(
		"Employee",
		filters={"status": "Active"},
		fields=["name", "employee_name", "company"],
		order_by="employee_name asc"
	)


@frappe.whitelist()
def get_expense_claim(
	name: str | None = None,
	employee: str | None = None,
	status: str | None = None,
	start_date: str | None = None,
	end_date: str | None = None,
	search_text: str | None = None,
	page: int = 1,
	page_size: int = 0,
):
	"""
	Return expense claims based on filters.

	`page_size` > 0 returns a single page (LIMIT/OFFSET) plus the total of the
	full filtered set and the dashboard stats (COUNT + SUM over the full filtered
	set); `page_size` = 0 keeps the legacy behaviour (all rows as a list).
	"""
	user = frappe.session.user

	# Determine allowed employees
	if can_approve_expense_claim():
		# User can see everyone.
		allowed_employees = frappe.get_all("Employee", filters={"status": "Active"}, pluck="name")
	else:
		# User can only see themselves.
		my_employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
		if not my_employee:
			return []
		allowed_employees = [my_employee]

	if not allowed_employees:
		return []

	# Build filters
	filters = []
	params = []
	if employee:
		if employee in allowed_employees:
			filters.append("employee = %s")
			params.append(employee)
		else:
			return []
	else:
		filters.append("employee IN ({})".format(", ".join(["%s"] * len(allowed_employees))))
		params.extend(allowed_employees)
	filters.append("docstatus < 2")
	if name:
		filters.append("name = %s")
		params.append(name)
	elif search_text:
		filters.append("name LIKE %s")
		params.append(f"%{search_text}%")
	if status:
		if status == "Open":
			status = "Draft"
		elif status == "Approved":
			status = "Submitted"
		filters.append("status = %s")
		params.append(status)
	if start_date and end_date:
		filters.append("posting_date BETWEEN %s AND %s")
		params.extend([start_date, end_date])
	elif start_date:
		filters.append("posting_date >= %s")
		params.append(start_date)
	elif end_date:
		filters.append("posting_date <= %s")
		params.append(end_date)

	where_clause = " AND ".join(filters)

	# Server-side paging: page_size > 0. The total and the stats come from
	# the full filtered set (COUNT and SUM), so they are not affected
	# by which page is being returned.
	if page_size > 0:
		total = frappe.db.sql(
			"SELECT COUNT(*) AS count FROM `tabExpense Claim` WHERE {}".format(where_clause),
			params,
			as_dict=True,
		)[0].count

		stats = frappe.db.sql(
			"""
			SELECT
				SUM(total_claimed_amount) AS total_amount,
				SUM(CASE WHEN status IN ('Submitted', 'Approved') THEN total_claimed_amount ELSE 0 END) AS approved_amount,
				SUM(CASE WHEN status = 'Rejected' THEN total_claimed_amount ELSE 0 END) AS rejected_amount
			FROM `tabExpense Claim`
			WHERE {}
			""".format(where_clause),
			params,
			as_dict=True,
		)
		stats = stats[0] if stats else {}

		offset = (max(1, page) - 1) * page_size
		claims = frappe.db.sql(
			"""
			SELECT name, employee, employee_name, expense_approver, payable_account,
				total_claimed_amount, total_sanctioned_amount, status, posting_date,
				remark, is_paid
			FROM `tabExpense Claim`
			WHERE {}
			ORDER BY name DESC
			LIMIT %s OFFSET %s
			""".format(where_clause),
			params + [page_size, offset],
			as_dict=True,
		)
		if name and claims:
			# If a specific claim is requested, fetch its line items
			for claim in claims:
				claim["expenses"] = frappe.get_all(
					"Expense Claim Detail",
					filters={"parent": claim["name"]},
					fields=["expense_date", "expense_type", "amount", "sanctioned_amount", "description"],
					order_by="idx ASC"
				)
		return {
			"data": claims,
			"total": total,
			"page": page,
			"page_size": page_size,
			"stats": {
				"count": total,
				"total_amount": stats.get("total_amount") or 0,
				"approved_amount": stats.get("approved_amount") or 0,
				"rejected_amount": stats.get("rejected_amount") or 0,
			},
		}

	# Legacy: no limit, return all records.
	claims = frappe.db.sql(
		"""
		SELECT name, employee, employee_name, expense_approver, payable_account,
			total_claimed_amount, total_sanctioned_amount, status, posting_date,
			remark, is_paid
		FROM `tabExpense Claim`
		WHERE {}
		ORDER BY name DESC
		""".format(where_clause),
		params,
		as_dict=True,
	)

	if name and claims:
		# If a specific claim is requested, fetch its line items
		for claim in claims:
			claim["expenses"] = frappe.get_all(
				"Expense Claim Detail",
				filters={"parent": claim["name"]},
				fields=["expense_date", "expense_type", "amount", "sanctioned_amount", "description"],
				order_by="idx ASC"
			)

	return claims

@frappe.whitelist()
def get_expense_types(name=None, page: int = 1, page_size: int = 0):
	"""
	Get expense claim types.

	`page_size` > 0 returns a single page (LIMIT/OFFSET) plus the total of the
	full filtered set; `page_size` = 0 keeps the legacy behaviour (all rows).
	"""
	if not can_read_expense_types():
		frappe.throw("Not permitted")

	filters = {}
	if name:
		filters['name'] = ['like', f'%{name}%']

	types = frappe.get_all(
		"Expense Claim Type",
		filters=filters,
		fields=["name", "description"],
		order_by="name ASC",
		limit_page_length=page_size if page_size > 0 else 0,
		limit_start=(max(1, page) - 1) * page_size if page_size > 0 else 0,
	)

	company = frappe.defaults.get_user_default("Company")
	if not company:
		company = frappe.get_all("Company", limit=1)[0].name

	for t in types:
		account = frappe.db.get_value("Expense Claim Account", {"parent": t.name, "company": company}, "default_account")
		t["default_account"] = account

	if page_size > 0:
		# Total comes from the full filtered set (same filters), so it is
		# not affected by which page is being returned.
		total = frappe.db.count("Expense Claim Type", filters=filters)
		return {
			"data": types,
			"total": total,
			"page": page,
			"page_size": page_size,
		}

	return types

@frappe.whitelist()
def save_expense_type(name, description=None, default_account=None, original_name=None):
	"""
	Save or update an Expense Claim Type.
	"""
	if original_name:
		if not frappe.has_permission("Expense Claim Type", "write") and not can_edit_expense_types():
			frappe.throw("Not permitted to edit")
	else:
		if not frappe.has_permission("Expense Claim Type", "create") and not can_create_expense_types():
			frappe.throw("Not permitted to create")

	if original_name and original_name != name:
		frappe.rename_doc("Expense Claim Type", original_name, name)

	if frappe.db.exists("Expense Claim Type", name):
		doc = frappe.get_doc("Expense Claim Type", name)
	else:
		doc = frappe.new_doc("Expense Claim Type")
		doc.expense_type = name

	doc.description = description

	if default_account:
		company = frappe.defaults.get_user_default("Company")
		if not company:
			company = frappe.get_all("Company", limit=1)[0].name

		doc.set("accounts", [])
		doc.append("accounts", {
			"company": company,
			"default_account": default_account
		})

	doc.save()
	return doc.as_dict()

@frappe.whitelist()
def delete_expense_type(name):
	"""
	Delete an Expense Claim Type.
	"""
	if not frappe.has_permission("Expense Claim Type", "delete") and not can_delete_expense_types():
		frappe.throw("Not permitted to delete Expense Claim Type.")

	if frappe.db.exists("Expense Claim Type", name):
		frappe.delete_doc("Expense Claim Type", name)
	else:
		frappe.throw("Expense Claim Type does not exist.")
	return True

@frappe.whitelist()
def get_default_expense_accounts():
	"""
	Get list of expense accounts for expense claim types.
	Filters: is_group = 0, root_type = "Expense", company = "Zevar Core"
	"""
	if frappe.session.user == "Guest":
		frappe.throw("Not permitted")

	company = frappe.defaults.get_user_default("Company")
	if not company:
		company = frappe.get_all("Company", limit=1)[0].name

	return frappe.get_all(
		"Account",
		filters={
			"is_group": 0,
			"root_type": "Expense",
			"company": company
		},
		fields=["name", "account_name"],
		order_by="account_name ASC"
	)


@frappe.whitelist()
def get_expense_claim_report_filter_options():
	"""
	Returns dropdown options for Employee and Status for the Expense Claim report.
	"""
	employees = frappe.get_all("Employee", fields=["name as id", "employee_name as name"], order_by="name asc")
	statuses = [
		{"id": "Draft", "name": "Draft"},
		{"id": "Approved", "name": "Approved"},
		{"id": "Rejected", "name": "Rejected"}
	]

	return {
		"employees": [{"id": e.id, "name": f"{e.name} ({e.id})"} for e in employees],
		"statuses": statuses
	}


@frappe.whitelist()
def report_expense_claim_list(from_date=None, to_date=None, employee=None, status=None, export=0, pdf=0):
	"""
	Returns Expense Claim list for report based on filters.
	"""
	import frappe
	from frappe.utils import flt, getdate, now_datetime
	from frappe.utils.pdf import get_pdf
	from frappe.utils.xlsxutils import build_xlsx_response

	conditions = ["ec.docstatus < 2"]
	params = {}

	if employee:
		conditions.append("ec.employee = %(employee)s")
		params["employee"] = employee

	if status and status.lower() != "all":
		if status == "Draft":
			conditions.append("ec.docstatus = 0")
		elif status == "Approved":
			conditions.append("(ec.approval_status = 'Approved' OR (ec.docstatus = 1 AND COALESCE(ec.approval_status, '') != 'Rejected'))")
		elif status == "Rejected":
			conditions.append("(ec.approval_status = 'Rejected' OR ec.status = 'Rejected')")
		else:
			conditions.append("(ec.status = %(status)s OR ec.approval_status = %(status)s)")
			params["status"] = status

	if from_date and to_date:
		conditions.append("ec.posting_date BETWEEN %(from_date)s AND %(to_date)s")
		params["from_date"] = getdate(from_date)
		params["to_date"] = getdate(to_date)
	elif from_date:
		conditions.append("ec.posting_date >= %(from_date)s")
		params["from_date"] = getdate(from_date)
	elif to_date:
		conditions.append("ec.posting_date <= %(to_date)s")
		params["to_date"] = getdate(to_date)

	where_clause = " AND ".join(conditions)

	query = f"""
		SELECT
			ec.name,
			DATE_FORMAT(ec.posting_date, '%%Y-%%m-%%d') as posting_date,
			ec.employee,
			COALESCE(ec.employee_name, e.employee_name, '') AS employee_name,
			COALESCE(ec.total_claimed_amount, ec.grand_total, 0) AS amount,
			CASE
				WHEN ec.approval_status = 'Rejected' OR ec.status = 'Rejected' THEN 'Rejected'
				WHEN ec.approval_status = 'Approved' OR ec.docstatus = 1 THEN 'Approved'
				WHEN ec.docstatus = 0 THEN 'Draft'
				ELSE COALESCE(ec.approval_status, ec.status, 'Draft')
			END as status
		FROM `tabExpense Claim` ec
		LEFT JOIN `tabEmployee` e ON ec.employee = e.name
		WHERE {where_clause}
		ORDER BY ec.posting_date DESC, ec.name DESC
	"""


	data = frappe.db.sql(query, params, as_dict=True)

	result = []
	for r in data:
		emp_id = r.get("employee") or ""
		emp_name = r.get("employee_name") or ""
		emp_display = f"{emp_id} - {emp_name}" if (emp_id and emp_name) else (emp_id or emp_name or "-")

		result.append({
			"name": r.name,
			"posting_date": r.posting_date or "",
			"employee": emp_id,
			"employee_name": emp_name,
			"employee_str": emp_display,
			"amount": flt(r.amount, 2),
			"status": r.status or "Draft"
		})

	if int(export):
		xlsx_data = [["Expense ID", "Date", "Employee", "Amount", "Status"]]
		for r in result:
			xlsx_data.append([
				r["name"],
				r["posting_date"],
				r["employee_str"],
				r["amount"],
				r["status"]
			])

		build_xlsx_response(xlsx_data, "Expense_Claim_Report")
		return

	if int(pdf):
		context = {
			"data": result,
			"filters": {
				"from_date": from_date,
				"to_date": to_date,
				"employee": employee,
				"status": status
			}
		}

		html = frappe.render_template("arijentek_core/templates/reports/expense_claim_report.html", context)
		pdf_binary = get_pdf(html, {
			"page-size": "A4",
			"orientation": "Landscape",
			"margin-top": "10mm",
			"margin-bottom": "10mm",
			"margin-left": "8mm",
			"margin-right": "8mm"
		})

		frappe.local.response.filename = f"Expense_Claim_Report_{now_datetime().strftime('%Y%m%d')}.pdf"
		frappe.local.response.filecontent = pdf_binary
		frappe.local.response.type = "pdf"
		return

	return result


@frappe.whitelist()
def get_expense_type_report_filter_options():
	"""
	Returns dropdown options for Account for the Expense Type report.
	"""
	accounts = frappe.get_all(
		"Account",
		filters={"is_group": 0, "root_type": "Expense"},
		fields=["name as id", "account_name as name"],
		order_by="name asc"
	)
	if not accounts:
		accounts = frappe.get_all(
			"Expense Claim Account",
			fields=["DISTINCT default_account as id", "default_account as name"],
			order_by="default_account asc"
		)

	return {
		"accounts": [{"id": a.id, "name": a.name or a.id} for a in accounts if a.id]
	}


@frappe.whitelist()
def report_expense_type_list(account=None, export=0, pdf=0):
	"""
	Returns Expense Claim Type list for report based on filters.
	"""
	import frappe
	from frappe.utils import now_datetime
	from frappe.utils.pdf import get_pdf
	from frappe.utils.xlsxutils import build_xlsx_response

	conditions = []
	params = {}

	if account:
		conditions.append("eca.default_account = %(account)s")
		params["account"] = account

	where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

	query = f"""
		SELECT
			ect.name,
			COALESCE(ect.expense_type, ect.name) AS expense_type,
			ect.description,
			GROUP_CONCAT(DISTINCT eca.default_account ORDER BY eca.default_account SEPARATOR ', ') AS default_account
		FROM `tabExpense Claim Type` ect
		LEFT JOIN `tabExpense Claim Account` eca ON eca.parent = ect.name
		{where_clause}
		GROUP BY ect.name
		ORDER BY ect.name ASC
	"""

	data = frappe.db.sql(query, params, as_dict=True)

	result = []
	for r in data:
		result.append({
			"name": r.name,
			"expense_type": r.expense_type or r.name,
			"default_account": r.default_account or "-",
			"description": r.description or "-"
		})

	if int(export):
		xlsx_data = [["Type Name", "Default Account", "Description"]]
		for r in result:
			xlsx_data.append([
				r["expense_type"],
				r["default_account"],
				r["description"]
			])

		build_xlsx_response(xlsx_data, "Expense_Type_Report")
		return

	if int(pdf):
		context = {
			"data": result,
			"filters": {
				"account": account
			}
		}

		html = frappe.render_template("arijentek_core/templates/reports/expense_type_report.html", context)
		pdf_binary = get_pdf(html, {
			"page-size": "A4",
			"orientation": "Landscape",
			"margin-top": "10mm",
			"margin-bottom": "10mm",
			"margin-left": "8mm",
			"margin-right": "8mm"
		})

		frappe.local.response.filename = f"Expense_Type_Report_{now_datetime().strftime('%Y%m%d')}.pdf"
		frappe.local.response.filecontent = pdf_binary
		frappe.local.response.type = "pdf"
		return

	return result


