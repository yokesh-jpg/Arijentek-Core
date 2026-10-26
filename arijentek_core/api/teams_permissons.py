import re
import frappe
from frappe import _

from arijentek_core.services.internal_access import (
	get_internal_user_names,
	is_internal_user,
)
from arijentek_core.services.permissions import (
	DESK_ROLES,
	PLATFORM_ROLES,
	can_grant_desk_roles,
	require_desk_grant_right,
)
from arijentek_core.services.role_profile_catalog import ROLE_PROFILE_CATALOG, _is_admin_tier


def has_role_permission(doctype, ptype):
	user = frappe.session.user
	if user == "Administrator":
		return True
	roles = frappe.get_roles(user)
	if not roles:
		return False

	# Check standard DocPerm for permlevel 0 or 1
	has_perm = frappe.db.sql(f"""
		SELECT name FROM `tabDocPerm`
		WHERE parent=%s AND role IN %s AND `{ptype}`=1 AND permlevel IN (0, 1)
		LIMIT 1
	""", (doctype, tuple(roles)))

	if has_perm:
		return True

	# Check Custom DocPerm for permlevel 0 or 1
	has_custom = frappe.db.sql(f"""
		SELECT name FROM `tabCustom DocPerm`
		WHERE parent=%s AND role IN %s AND `{ptype}`=1 AND permlevel IN (0, 1)
		LIMIT 1
	""", (doctype, tuple(roles)))

	return bool(has_custom)


def _count_records(doctype, filters=None, or_filters=None):
	try:
		if not frappe.db.table_exists(doctype):
			return 0
		if or_filters:
			return len(frappe.get_all(doctype, filters=filters, or_filters=or_filters, pluck="name"))
		if filters:
			return len(frappe.get_all(doctype, filters=filters, pluck="name"))
		return frappe.db.count(doctype)
	except Exception:
		return 0


@frappe.whitelist()
def can_create_employee():
	"""
	Returns True if the current user has permission to create an Employee.
	This is true for 'HR Manager', 'System Manager', or users with explicit create permissions on the 'Employee' Doctype.
	"""
	user = frappe.session.user

	# Check specific roles
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	# Check explicit doctype permissions
	if has_role_permission("Employee", "create"):
		return True

	return False

@frappe.whitelist()
def can_create_user():
	"""
	Returns True if the current user has permission to create a User.
	"""
	user = frappe.session.user

	# Check specific roles
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	# Check explicit doctype permissions
	if has_role_permission("User", "create"):
		return True

	return False

@frappe.whitelist()
def can_read_employee():
	"""
	Returns True if the current user has permission to read an Employee.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if has_role_permission("Employee", "read"):
		return True
	return False

@frappe.whitelist()
def can_read_users():
	"""
	Returns True if the current user has permission to read the User doctype.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if has_role_permission("User", "read"):
		return True
	return False

@frappe.whitelist()
def can_edit_employee():
	"""
	Returns True if the current user has permission to edit an Employee.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if has_role_permission("Employee", "write"):
		return True
	return False

@frappe.whitelist()
def can_delete_employee():
	"""
	Returns True if the current user has permission to delete an Employee.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if has_role_permission("Employee", "delete"):
		return True
	return False

@frappe.whitelist()
def can_edit_user():
	"""
	Returns True if the current user has permission to edit a User.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if has_role_permission("User", "write"):
		return True
	return False

@frappe.whitelist()
def can_delete_user():
	"""
	Returns True if the current user has permission to delete a User.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if has_role_permission("User", "delete"):
		return True
	return False

@frappe.whitelist()
def can_read_department():
	"""
	Returns True if the current user has permission to read a Department.
	"""
	user = frappe.session.user
	if has_role_permission("Department", "read"):
		return True
	return False

@frappe.whitelist()
def can_create_department():
	"""
	Returns True if the current user has permission to create a Department.
	"""
	user = frappe.session.user
	if has_role_permission("Department", "create"):
		return True
	return False

@frappe.whitelist()
def can_edit_department():
	"""
	Returns True if the current user has permission to edit a Department.
	"""
	user = frappe.session.user
	if has_role_permission("Department", "write"):
		return True
	return False

@frappe.whitelist()
def can_delete_department():
	"""
	Returns True if the current user has permission to delete a Department.
	"""
	user = frappe.session.user
	if has_role_permission("Department", "delete"):
		return True
	return False

@frappe.whitelist()
def can_read_designation():
	"""
	Returns True if the current user has permission to read a Designation.
	"""
	user = frappe.session.user
	if has_role_permission("Designation", "read"):
		return True
	return False

@frappe.whitelist()
def can_create_designation():
	"""
	Returns True if the current user has permission to create a Designation.
	"""
	user = frappe.session.user
	if has_role_permission("Designation", "create"):
		return True
	return False

@frappe.whitelist()
def can_edit_designation():
	"""
	Returns True if the current user has permission to edit a Designation.
	"""
	user = frappe.session.user
	if has_role_permission("Designation", "write"):
		return True
	return False

@frappe.whitelist()
def can_delete_designation():
	"""
	Returns True if the current user has permission to delete a Designation.
	"""
	user = frappe.session.user
	if has_role_permission("Designation", "delete"):
		return True
	return False

@frappe.whitelist()
def can_read_branch():
	user = frappe.session.user
	if has_role_permission("Branch", "read"):
		return True
	return False

@frappe.whitelist()
def can_create_branch():
	user = frappe.session.user
	if has_role_permission("Branch", "create"):
		return True
	return False

@frappe.whitelist()
def can_edit_branch():
	user = frappe.session.user
	if has_role_permission("Branch", "write"):
		return True
	return False

@frappe.whitelist()
def can_delete_branch():
	user = frappe.session.user
	if has_role_permission("Branch", "delete"):
		return True
	return False

@frappe.whitelist()
def can_read_gender():
	user = frappe.session.user
	if has_role_permission("Gender", "read"):
		return True
	return False

@frappe.whitelist()
def can_create_gender():
	user = frappe.session.user
	if has_role_permission("Gender", "create"):
		return True
	return False

@frappe.whitelist()
def can_edit_gender():
	user = frappe.session.user
	if has_role_permission("Gender", "write"):
		return True
	return False

@frappe.whitelist()
def can_delete_gender():
	user = frappe.session.user
	if has_role_permission("Gender", "delete"):
		return True
	return False

@frappe.whitelist()
def can_read_salutation():
	user = frappe.session.user
	if has_role_permission("Salutation", "read"):
		return True
	return False

@frappe.whitelist()
def can_create_salutation():
	user = frappe.session.user
	if has_role_permission("Salutation", "create"):
		return True
	return False

@frappe.whitelist()
def can_edit_salutation():
	user = frappe.session.user
	if has_role_permission("Salutation", "write"):
		return True
	return False

@frappe.whitelist()
def can_delete_salutation():
	user = frappe.session.user
	if has_role_permission("Salutation", "delete"):
		return True
	return False

@frappe.whitelist()
def can_read_employee_grade():
	user = frappe.session.user
	if has_role_permission("Employee Grade", "read"):
		return True
	return False

@frappe.whitelist()
def can_create_employee_grade():
	user = frappe.session.user
	if has_role_permission("Employee Grade", "create"):
		return True
	return False

@frappe.whitelist()
def can_edit_employee_grade():
	user = frappe.session.user
	if has_role_permission("Employee Grade", "write"):
		return True
	return False

@frappe.whitelist()
def can_delete_employee_grade():
	user = frappe.session.user
	if has_role_permission("Employee Grade", "delete"):
		return True
	return False

@frappe.whitelist()
def can_read_employee_type():
	user = frappe.session.user
	if has_role_permission("Employment Type", "read"):
		return True
	return False

@frappe.whitelist()
def can_create_employee_type():
	user = frappe.session.user
	if has_role_permission("Employment Type", "create"):
		return True
	return False

@frappe.whitelist()
def can_edit_employee_type():
	user = frappe.session.user
	if has_role_permission("Employment Type", "write"):
		return True
	return False

@frappe.whitelist()
def can_delete_employee_type():
	user = frappe.session.user
	if has_role_permission("Employment Type", "delete"):
		return True
	return False

@frappe.whitelist()
def get_employee_list(employee_id="", search_term="", department="", designation="", gender="", employment_type="", page=1, page_size=0):
	if not can_read_employee():
		return {} if employee_id else []

	filters = {}
	has_employment_type = frappe.db.has_column("Employee", "employment_type")
	fields = ["name", "employee_name", "department", "designation", "gender", "cell_number", "image", "status"]
	if has_employment_type:
		fields.append("employment_type")

	if employee_id:
		filters["name"] = employee_id
		fields = ["*"]
	else:
		if department:
			filters["department"] = department
		if designation:
			filters["designation"] = designation
		if gender:
			filters["gender"] = gender
		if employment_type and has_employment_type:
			filters["employment_type"] = employment_type

	or_filters = []
	if search_term and not employee_id:
		or_filters = [
			["name", "like", f"%{search_term}%"],
			["employee_name", "like", f"%{search_term}%"],
			["cell_number", "like", f"%{search_term}%"]
		]

	page = int(page or 1)
	page_size = int(page_size or 0)

	if not employee_id and page_size > 0:
		total = _count_records("Employee", filters=filters, or_filters=or_filters)
		start = (page - 1) * page_size
		employees = frappe.get_all(
			"Employee",
			filters=filters,
			or_filters=or_filters,
			fields=fields,
			limit_start=start,
			limit_page_length=page_size,
			order_by="employee_name asc"
		)
		return {"rows": employees, "total": total}

	employees = frappe.get_all(
		"Employee",
		filters=filters,
		or_filters=or_filters,
		fields=fields,
		order_by="employee_name asc"
	)

	if employee_id and employees:
		employee_doc = employees[0]
		if employee_doc.get("user_id"):
			employee_doc["user_full_name"] = frappe.db.get_value("User", employee_doc.get("user_id"), "full_name") or employee_doc.get("user_id")

		if employee_doc.get("reports_to"):
			employee_doc["reports_to_user_id"] = frappe.db.get_value("Employee", employee_doc.get("reports_to"), "user_id")
			employee_doc["reports_to_name"] = frappe.db.get_value("Employee", employee_doc.get("reports_to"), "employee_name") or employee_doc.get("reports_to")

		if employee_doc.get("expense_approver"):
			employee_doc["expense_approver_name"] = frappe.db.get_value("User", employee_doc.get("expense_approver"), "full_name") or employee_doc.get("expense_approver")

		if employee_doc.get("shift_request_approver"):
			employee_doc["shift_approver_name"] = frappe.db.get_value("User", employee_doc.get("shift_request_approver"), "full_name") or employee_doc.get("shift_request_approver")

		if employee_doc.get("leave_approver"):
			employee_doc["leave_approver_name"] = frappe.db.get_value("User", employee_doc.get("leave_approver"), "full_name") or employee_doc.get("leave_approver")

		return employee_doc

	return employees

@frappe.whitelist()
def get_departments():
	return [d.name for d in frappe.get_all("Department", order_by="name asc")]

@frappe.whitelist()
def get_designations():
	return [d.name for d in frappe.get_all("Designation", order_by="name asc")]

@frappe.whitelist()
def get_employment_types():
	return [d.name for d in frappe.get_all("Employment Type", order_by="name asc")]

@frappe.whitelist()
def get_genders():
	try:
		return [d.name for d in frappe.get_all("Gender", order_by="name asc")]
	except Exception:
		meta = frappe.get_meta("Employee")
		field = meta.get_field("gender")
		if field and field.options:
			return [opt for opt in field.options.split("\n") if opt]
		return ["Male", "Female", "Other"]

@frappe.whitelist()
def get_users_details(user_id="", search_term="", page=1, page_size=0):
	if not can_read_users():
		return {} if user_id else []

	filters = {}
	fields = ["name", "email", "username", "first_name", "middle_name", "last_name", "full_name", "user_image", "enabled"]

	# Platform accounts are never tenant-visible (get_all bypasses the
	# permission_query_conditions).
	internal_users = get_internal_user_names()

	if user_id:
		if user_id in internal_users:
			return {}
		filters["name"] = user_id
		fields = ["*"]
	else:
		filters["name"] = ["not in", internal_users]

	or_filters = []
	if search_term and not user_id:
		or_filters = [
			["name", "like", f"%{search_term}%"],
			["email", "like", f"%{search_term}%"],
			["username", "like", f"%{search_term}%"],
			["first_name", "like", f"%{search_term}%"],
			["middle_name", "like", f"%{search_term}%"],
			["last_name", "like", f"%{search_term}%"]
		]

	page = int(page or 1)
	page_size = int(page_size or 0)

	if not user_id and page_size > 0:
		total = _count_records("User", filters=filters, or_filters=or_filters)
		start = (page - 1) * page_size
		users = frappe.get_all(
			"User",
			filters=filters,
			or_filters=or_filters,
			fields=fields,
			limit_start=start,
			limit_page_length=page_size,
			order_by="name asc"
		)
		return {"rows": users, "total": total}

	users = frappe.get_all(
		"User",
		filters=filters,
		or_filters=or_filters,
		fields=fields,
		order_by="name asc"
	)

	if user_id and users:
		user_doc = users[0]
		user_roles = frappe.get_all("Has Role", filters={"parent": user_id}, pluck="role")
		user_doc["roles"] = user_roles
		emp = frappe.db.get_value("Employee", {"user_id": user_id}, ["name", "employee_name"], as_dict=True)
		if emp:
			user_doc["employee_id"] = emp.name
			user_doc["employee_name"] = emp.employee_name
		return user_doc

	return users

@frappe.whitelist()
def get_salutations():
	return [d.name for d in frappe.get_all("Salutation", order_by="name asc")]

@frappe.whitelist()
def get_branches():
	return [d.name for d in frappe.get_all("Branch", order_by="name asc")]

@frappe.whitelist()
def get_employee_grades():
	return [d.name for d in frappe.get_all("Employee Grade", order_by="name asc")]

@frappe.whitelist()
def get_users_list(no_employees=False):
	if not can_read_users():
		return []

	filters = {"enabled": 1}

	# Platform accounts are never tenant-visible.
	exclude = set(get_internal_user_names())

	if isinstance(no_employees, str):
		no_employees = frappe.parse_json(no_employees)

	if no_employees:
		linked_users = frappe.get_all("Employee", filters={"user_id": ("is", "set")}, pluck="user_id")
		exclude.update(linked_users)

	filters["name"] = ["not in", sorted(exclude)]

	users = frappe.get_all("User", filters=filters, fields=["name", "full_name"], order_by="name asc")
	return [{"value": u.name, "label": f"{u.name} - {u.full_name}"} for u in users]

@frappe.whitelist()
def get_unlinked_employees():
	if not can_read_employee():
		return []

	employees = frappe.db.sql("""
		SELECT name, employee_name 
		FROM `tabEmployee` 
		WHERE (user_id IS NULL OR user_id = '') AND status = 'Active'
		ORDER BY employee_name ASC
	""", as_dict=True)

	return [{"value": e.name, "label": f"{e.name} - {e.employee_name}" if e.employee_name else e.name} for e in employees]

@frappe.whitelist()
def link_user_to_employee(user_id, employee_id):
	if not can_edit_employee():
		frappe.throw("Not permitted to edit Employee", frappe.PermissionError)

	if not frappe.db.exists("User", user_id):
		frappe.throw(f"User {user_id} does not exist.")

	if not frappe.db.exists("Employee", employee_id):
		frappe.throw(f"Employee {employee_id} does not exist.")

	emp = frappe.get_doc("Employee", employee_id)
	emp.user_id = user_id
	emp.save(ignore_permissions=True)
	return emp.name

@frappe.whitelist()
def get_all_pos_profiles():
	return frappe.get_all(
		"POS Profile",
		filters={"disabled": 0},
		fields=["name", "company", "warehouse"],
		order_by="name asc"
	)

@frappe.whitelist()
def get_user_pos_profiles(user_email):
	if not user_email:
		return []
	return frappe.get_all(
		"POS Profile User",
		filters={"user": user_email},
		pluck="parent"
	)

@frappe.whitelist()
def assign_user_pos_profiles(user_email, pos_profiles):
	if not user_email:
		return {"success": False, "message": "user_email is required"}

	if isinstance(pos_profiles, str):
		pos_profiles = frappe.parse_json(pos_profiles) or []

	all_profiles = frappe.get_all("POS Profile", pluck="name")
	for p_name in all_profiles:
		p_doc = frappe.get_doc("POS Profile", p_name)
		if p_name in pos_profiles:
			if not any(row.user == user_email for row in p_doc.applicable_for_users):
				p_doc.append("applicable_for_users", {"user": user_email, "default": 1 if len(pos_profiles) == 1 else 0})
				p_doc.save(ignore_permissions=True)
		else:
			orig_len = len(p_doc.applicable_for_users)
			p_doc.applicable_for_users = [row for row in p_doc.applicable_for_users if row.user != user_email]
			if len(p_doc.applicable_for_users) != orig_len:
				p_doc.save(ignore_permissions=True)

	frappe.db.commit()
	return {"success": True}

@frappe.whitelist()
def get_roles(search_term="", page=1, page_size=0):
	roles = [r.name for r in frappe.get_all("Role", order_by="name asc")]
	# Platform roles (desk tier + System Manager + Gemora Admin) are hidden
	# from anyone not allowed to grant them — the write endpoints and the
	# User.validate firewall enforce this too; hiding here is UX only.
	hidden = PLATFORM_ROLES - {"Administrator"}
	if not can_grant_desk_roles():
		roles = [r for r in roles if r not in hidden]

	if search_term:
		st = search_term.lower()
		roles = [r for r in roles if st in r.lower()]

	page = int(page or 1)
	page_size = int(page_size or 0)

	if page_size > 0:
		total = len(roles)
		start = (page - 1) * page_size
		sliced = roles[start:start + page_size]
		rows = [{"name": r, "role": r} for r in sliced]
		return {"rows": rows, "total": total}

	return roles

@frappe.whitelist()
def create_employee(employee_data):
	if isinstance(employee_data, str):
		employee_data = frappe.parse_json(employee_data)

	is_new = not employee_data.get("name")
	if is_new:
		if not can_create_employee():
			frappe.throw("Not permitted to create Employee", frappe.PermissionError)
	else:
		if not can_edit_employee():
			frappe.throw("Not permitted to edit Employee", frappe.PermissionError)

	if isinstance(employee_data, str):
		employee_data = frappe.parse_json(employee_data)

	reports_to_emp = employee_data.get("reports_to")
	if reports_to_emp:
		if not frappe.db.exists("Employee", reports_to_emp):
			frappe.throw(f"Employee {reports_to_emp} does not exist.")

	company = employee_data.get("company") or frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")

	# Prepare doc fields
	doc_fields = {
		"doctype": "Employee",
		"company": company,
		"first_name": employee_data.get("first_name"),
		"middle_name": employee_data.get("middle_name"),
		"last_name": employee_data.get("last_name"),
		"user_id": employee_data.get("user_id"),
		"gender": employee_data.get("gender"),
		"date_of_birth": employee_data.get("date_of_birth"),
		"salutation": employee_data.get("salutation"),
		"employee_number": employee_data.get("employee_number"),
		"date_of_joining": employee_data.get("date_of_joining"),
		"designation": employee_data.get("designation"),
		"branch": employee_data.get("branch"),
		"department": employee_data.get("department"),
		"reports_to": reports_to_emp,
		"grade": employee_data.get("grade"),
		"employment_type": employee_data.get("employee_type"),
		"cell_number": employee_data.get("cell_number"),
		"company_email": employee_data.get("company_email"),
		"personal_email": employee_data.get("personal_email"),
		"current_address": employee_data.get("current_address"),
		"permanent_address": employee_data.get("permanent_address"),
		"emergency_phone_number": employee_data.get("emergency_phone_number"),
		"relation": employee_data.get("emergency_relation"),
		"person_to_be_contacted": employee_data.get("emergency_contact_name"),
		"expense_approver": employee_data.get("expense_approver"),
		"shift_request_approver": employee_data.get("shift_approver"),
		"leave_approver": employee_data.get("leave_approver"),
		"default_shift": employee_data.get("default_shift"),
		"image": employee_data.get("image"),
		"status": employee_data.get("status") or "Active"
	}

	if is_new:
		# Remove empty fields to let frappe handle defaults for new docs
		doc_fields = {k: v for k, v in doc_fields.items() if v}
		doc = frappe.get_doc(doc_fields)
		doc.insert()
	else:
		doc = frappe.get_doc("Employee", employee_data.get("name"))
		if not doc_fields.get("user_id"):
			doc_fields.pop("user_id", None) # Do not overwrite user_id if we don't have it
		doc.update(doc_fields)
		doc.save()

	return doc.name

@frappe.whitelist()
def create_user(user_data):
	if isinstance(user_data, str):
		user_data = frappe.parse_json(user_data)

	is_new = not user_data.get("name")
	if is_new:
		if not can_create_user():
			frappe.throw("Not permitted to create User", frappe.PermissionError)
	else:
		if not can_edit_user():
			frappe.throw("Not permitted to edit User", frappe.PermissionError)

	email = (user_data.get("email") or "").strip().lower()
	if not email:
		frappe.throw("Email is required")

	doc_fields = {
		"doctype": "User",
		"email": email,
		"first_name": user_data.get("first_name"),
		"middle_name": user_data.get("middle_name"),
		"last_name": user_data.get("last_name"),
		"username": user_data.get("username"),
		"gender": user_data.get("gender"),
		"birth_date": user_data.get("date_of_birth"),
		"new_password": user_data.get("password"),
		"send_welcome_email": 0,
		"enabled": 1,
		"user_image": user_data.get("user_image"),
		"time_zone": user_data.get("time_zone")
	}

	roles = user_data.get("roles")

	# Desk roles are platform-controlled: only current desk-role holders (or
	# the site Administrator) may grant or revoke them (grant OR revoke on
	# edit — either changes who can reach /app).
	if roles is not None and isinstance(roles, list) and set(roles) & DESK_ROLES:
		require_desk_grant_right()
	if not is_new:
		_doc = frappe.get_doc("User", user_data.get("name"))
		if {r.role for r in _doc.roles} & DESK_ROLES:
			require_desk_grant_right()

	# Privilege-escalation firewall (the User.validate hook
	# guard_user_roles enforces the same rules on every write surface;
	# these early checks keep the SPA errors clean and immediate):
	# - platform roles are never assignable from a tenant session
	# - the owner grant ("Admin User") needs the admin tier
	# - platform accounts are not editable by tenants
	from arijentek_core.services.internal_access import _is_platform_actor

	requested = set(roles) if isinstance(roles, list) else set()
	if requested & PLATFORM_ROLES and not _is_platform_actor(frappe.session.user):
		frappe.throw("Platform roles are assigned by Gemora only.", frappe.PermissionError)
	if "Admin User" in requested and not _is_admin_tier():
		frappe.throw(
			"The owner persona may only be assigned by an administrator.",
			frappe.PermissionError,
		)
	if not is_new and (
		user_data.get("name") == "Administrator" or is_internal_user(user_data.get("name"))
	):
		frappe.throw("Platform accounts may only be managed by Gemora.", frappe.PermissionError)

	if is_new:
		if frappe.db.exists("User", email):
			frappe.throw(f"User with email '{email}' already exists.")
		if roles and isinstance(roles, list):
			doc_fields["roles"] = [{"role": role} for role in roles if frappe.db.exists("Role", role)]
		doc_fields = {k: v for k, v in doc_fields.items() if v is not None}
		doc = frappe.get_doc(doc_fields)
		doc.insert(ignore_permissions=True)
	else:
		doc = frappe.get_doc("User", user_data.get("name"))
		if not doc_fields.get("new_password"):
			doc_fields.pop("new_password", None)
		doc.update(doc_fields)
		if roles is not None and isinstance(roles, list):
			doc.set("roles", [])
			for role in roles:
				if frappe.db.exists("Role", role):
					doc.append("roles", {"role": role})
		doc.save(ignore_permissions=True)

	return doc.name

@frappe.whitelist()
def create_department(department_data):
	if isinstance(department_data, str):
		department_data = frappe.parse_json(department_data)

	is_new = not department_data.get("name")
	if is_new:
		if not can_create_department():
			frappe.throw("Not permitted to create Department", frappe.PermissionError)
	else:
		if not can_edit_department():
			frappe.throw("Not permitted to edit Department", frappe.PermissionError)

	doc_fields = {
		"doctype": "Department",
		"department_name": department_data.get("department_name")
	}

	if is_new:
		doc_fields = {k: v for k, v in doc_fields.items() if v}
		doc = frappe.get_doc(doc_fields)
	else:
		old_name = department_data.get("name")
		new_name = department_data.get("department_name")
		if old_name and new_name and old_name != new_name:
			frappe.flags.ignore_permissions = True
			try:
				frappe.rename_doc("Department", old_name, new_name)
			finally:
				frappe.flags.ignore_permissions = False
			old_name = new_name

		doc = frappe.get_doc("Department", old_name)
		doc.update(doc_fields)

	doc.set("expense_approvers", [])
	if department_data.get("expense_approver"):
		doc.append("expense_approvers", {"approver": department_data.get("expense_approver")})

	doc.set("shift_request_approver", [])
	if department_data.get("shift_approver"):
		doc.append("shift_request_approver", {"approver": department_data.get("shift_approver")})

	doc.set("leave_approvers", [])
	if department_data.get("leave_approver"):
		doc.append("leave_approvers", {"approver": department_data.get("leave_approver")})

	if is_new:
		dept_name = department_data.get("department_name")
		if dept_name and frappe.db.exists("Department", dept_name):
			frappe.throw(_("Department '{0}' already exists.").format(dept_name), frappe.DuplicateEntryError)
		try:
			doc.insert()
		except frappe.DuplicateEntryError:
			frappe.throw(_("Department '{0}' already exists.").format(dept_name))
	else:
		doc.save()

	return doc.name

@frappe.whitelist()
def create_designation(designation_data):
	if isinstance(designation_data, str):
		designation_data = frappe.parse_json(designation_data)

	is_new = not designation_data.get("name")
	if is_new:
		if not can_create_designation():
			frappe.throw("Not permitted to create Designation", frappe.PermissionError)
	else:
		if not can_edit_designation():
			frappe.throw("Not permitted to edit Designation", frappe.PermissionError)

	doc_fields = {
		"doctype": "Designation",
		"designation_name": designation_data.get("designation_name"),
		"description": designation_data.get("description")
	}

	if is_new:
		desig_name = designation_data.get("designation_name")
		if desig_name and frappe.db.exists("Designation", desig_name):
			frappe.throw(_("Designation '{0}' already exists.").format(desig_name), frappe.DuplicateEntryError)
		doc_fields = {k: v for k, v in doc_fields.items() if v}
		doc = frappe.get_doc(doc_fields)
		try:
			doc.insert()
		except frappe.DuplicateEntryError:
			frappe.throw(_("Designation '{0}' already exists.").format(desig_name))
	else:
		old_name = designation_data.get("name")
		new_name = designation_data.get("designation_name")
		if old_name and new_name and old_name != new_name:
			frappe.flags.ignore_permissions = True
			try:
				frappe.rename_doc("Designation", old_name, new_name)
			finally:
				frappe.flags.ignore_permissions = False
			old_name = new_name

		doc = frappe.get_doc("Designation", old_name)
		doc.update(doc_fields)
		doc.save()

	return doc.name

@frappe.whitelist()
def save_gender(gender_data):
	if isinstance(gender_data, str):
		gender_data = frappe.parse_json(gender_data)

	is_new = not gender_data.get("name")
	if is_new:
		if not can_create_gender():
			frappe.throw("Not permitted to create Gender", frappe.PermissionError)
	else:
		if not can_edit_gender():
			frappe.throw("Not permitted to edit Gender", frappe.PermissionError)

	gender_name = gender_data.get("gender_name")
	if not gender_name:
		frappe.throw("Gender name is required")

	if is_new:
		if frappe.db.exists("Gender", gender_name):
			frappe.throw(_("Gender '{0}' already exists.").format(gender_name), frappe.DuplicateEntryError)
		doc = frappe.get_doc({
			"doctype": "Gender",
			"gender": gender_name
		})
		try:
			doc.insert(ignore_permissions=True)
		except frappe.DuplicateEntryError:
			frappe.throw(_("Gender '{0}' already exists.").format(gender_name))
	else:
		old_name = gender_data.get("name")
		if old_name != gender_name:
			frappe.flags.ignore_permissions = True
			try:
				frappe.rename_doc("Gender", old_name, gender_name)
			finally:
				frappe.flags.ignore_permissions = False
			old_name = gender_name
		doc = frappe.get_doc("Gender", old_name)
		doc.save(ignore_permissions=True)
	return doc.name

@frappe.whitelist()
def save_salutation(salutation_data):
	if isinstance(salutation_data, str):
		salutation_data = frappe.parse_json(salutation_data)

	is_new = not salutation_data.get("name")
	if is_new:
		if not can_create_salutation():
			frappe.throw("Not permitted to create Salutation", frappe.PermissionError)
	else:
		if not can_edit_salutation():
			frappe.throw("Not permitted to edit Salutation", frappe.PermissionError)

	salutation_name = salutation_data.get("salutation_name")
	if not salutation_name:
		frappe.throw("Salutation name is required")

	if is_new:
		if frappe.db.exists("Salutation", salutation_name):
			frappe.throw(_("Salutation '{0}' already exists.").format(salutation_name), frappe.DuplicateEntryError)
		doc = frappe.get_doc({
			"doctype": "Salutation",
			"salutation": salutation_name
		})
		try:
			doc.insert(ignore_permissions=True)
		except frappe.DuplicateEntryError:
			frappe.throw(_("Salutation '{0}' already exists.").format(salutation_name))
	else:
		old_name = salutation_data.get("name")
		if old_name != salutation_name:
			frappe.flags.ignore_permissions = True
			try:
				frappe.rename_doc("Salutation", old_name, salutation_name)
			finally:
				frappe.flags.ignore_permissions = False
			old_name = salutation_name
		doc = frappe.get_doc("Salutation", old_name)
		doc.save(ignore_permissions=True)
	return doc.name

@frappe.whitelist()
def save_branch(branch_data):
	if isinstance(branch_data, str):
		branch_data = frappe.parse_json(branch_data)

	is_new = not branch_data.get("name")
	if is_new:
		if not can_create_branch():
			frappe.throw("Not permitted to create Branch", frappe.PermissionError)
	else:
		if not can_edit_branch():
			frappe.throw("Not permitted to edit Branch", frappe.PermissionError)

	branch_name = branch_data.get("branch_name")
	if not branch_name:
		frappe.throw("Branch name is required")

	if is_new:
		if frappe.db.exists("Branch", branch_name):
			frappe.throw(_("Branch '{0}' already exists.").format(branch_name), frappe.DuplicateEntryError)
		doc = frappe.get_doc({
			"doctype": "Branch",
			"branch": branch_name
		})
		try:
			doc.insert(ignore_permissions=True)
		except frappe.DuplicateEntryError:
			frappe.throw(_("Branch '{0}' already exists.").format(branch_name))
	else:
		old_name = branch_data.get("name")
		if old_name != branch_name:
			frappe.flags.ignore_permissions = True
			try:
				frappe.rename_doc("Branch", old_name, branch_name)
			finally:
				frappe.flags.ignore_permissions = False
			old_name = branch_name
		doc = frappe.get_doc("Branch", old_name)
		doc.save(ignore_permissions=True)
	return doc.name

@frappe.whitelist()
def save_employee_grade(grade_data):
	if isinstance(grade_data, str):
		grade_data = frappe.parse_json(grade_data)

	is_new = not grade_data.get("name")
	if is_new:
		if not can_create_employee_grade():
			frappe.throw("Not permitted to create Employee Grade", frappe.PermissionError)
	else:
		if not can_edit_employee_grade():
			frappe.throw("Not permitted to edit Employee Grade", frappe.PermissionError)

	grade_name = grade_data.get("grade_name")
	if not grade_name:
		frappe.throw("Employee Grade name is required")

	if is_new:
		if frappe.db.exists("Employee Grade", grade_name):
			frappe.throw(_("Employee Grade '{0}' already exists.").format(grade_name), frappe.DuplicateEntryError)
		doc = frappe.get_doc({
			"doctype": "Employee Grade",
			"name": grade_name
		})
		try:
			doc.insert(ignore_permissions=True)
		except frappe.DuplicateEntryError:
			frappe.throw(_("Employee Grade '{0}' already exists.").format(grade_name))
	else:
		old_name = grade_data.get("name")
		if old_name != grade_name:
			frappe.flags.ignore_permissions = True
			try:
				frappe.rename_doc("Employee Grade", old_name, grade_name)
			finally:
				frappe.flags.ignore_permissions = False
			old_name = grade_name
		doc = frappe.get_doc("Employee Grade", old_name)
		doc.save(ignore_permissions=True)
	return doc.name

@frappe.whitelist()
def get_department_list(department_id="", search_term="", page=1, page_size=0):
	if not can_read_department():
		return {} if department_id else []

	if department_id:
		doc = frappe.get_doc("Department", department_id)

		def get_first_approver(child_table_name):
			approvers = doc.get(child_table_name)
			if approvers and len(approvers) > 0:
				return approvers[0].approver
			return None

		expense_approver = get_first_approver("expense_approvers")
		shift_approver = get_first_approver("shift_request_approver")
		leave_approver = get_first_approver("leave_approvers")

		expense_approver_name = frappe.db.get_value("User", expense_approver, "full_name") if expense_approver else None
		shift_approver_name = frappe.db.get_value("User", shift_approver, "full_name") if shift_approver else None
		leave_approver_name = frappe.db.get_value("User", leave_approver, "full_name") if leave_approver else None

		return {
			"name": doc.name,
			"department_name": doc.department_name,
			"expense_approver": expense_approver,
			"expense_approver_name": expense_approver_name,
			"shift_approver": shift_approver,
			"shift_approver_name": shift_approver_name,
			"leave_approver": leave_approver,
			"leave_approver_name": leave_approver_name
		}

	filters = {}
	or_filters = []
	if search_term:
		or_filters = [
			["name", "like", f"%{search_term}%"],
			["department_name", "like", f"%{search_term}%"]
		]

	page = int(page or 1)
	page_size = int(page_size or 0)
	total = 0

	if page_size > 0:
		total = _count_records("Department", or_filters=or_filters)
		start = (page - 1) * page_size
		departments = frappe.get_all("Department",
			or_filters=or_filters,
			fields=["name", "department_name"],
			limit_start=start,
			limit_page_length=page_size,
			order_by="name asc"
		)
	else:
		departments = frappe.get_all("Department",
			or_filters=or_filters,
			fields=["name", "department_name"],
			order_by="name asc"
		)

	if departments:
		dept_names = [d.name for d in departments]
		approvers = frappe.get_all("Department Approver",
			filters={"parent": ("in", dept_names)},
			fields=["parent", "approver", "parentfield"]
		)

		user_ids = list(set([a.approver for a in approvers if a.approver]))
		user_names = {}
		if user_ids:
			users = frappe.get_all("User", filters={"name": ("in", user_ids)}, fields=["name", "full_name"])
			user_names = {u.name: u.full_name for u in users}

		dept_approvers = {}
		for a in approvers:
			if a.parent not in dept_approvers:
				dept_approvers[a.parent] = {}
			if a.parentfield not in dept_approvers[a.parent]:
				dept_approvers[a.parent][a.parentfield] = a.approver

		for d in departments:
			d_app = dept_approvers.get(d.name, {})

			exp_app = d_app.get("expense_approvers")
			d["expense_approver"] = exp_app
			d["expense_approver_name"] = user_names.get(exp_app) if exp_app else None

			shift_app = d_app.get("shift_request_approver")
			d["shift_approver"] = shift_app
			d["shift_approver_name"] = user_names.get(shift_app) if shift_app else None

			leave_app = d_app.get("leave_approvers")
			d["leave_approver"] = leave_app
			d["leave_approver_name"] = user_names.get(leave_app) if leave_app else None

	if page_size > 0:
		return {"rows": departments, "total": total}

	return departments

def _safe_delete_doc(doctype, docname):
	try:
		frappe.delete_doc(doctype, docname)
		return {"success": True, "message": f"{doctype} deleted successfully"}
	except frappe.LinkExistsError as e:
		frappe.clear_messages()
		clean_msg = frappe.utils.strip_html(str(e)).strip()
		clean_msg = re.sub(r"\s+", " ", clean_msg)
		return {"success": False, "error": clean_msg}
	except Exception as e:
		frappe.clear_messages()
		clean_msg = frappe.utils.strip_html(str(e)).strip()
		clean_msg = re.sub(r"\s+", " ", clean_msg)
		return {"success": False, "error": clean_msg or str(e)}

@frappe.whitelist()
def delete_employee(employee_id):
	if not can_delete_employee():
		return {"success": False, "error": "Not permitted to delete Employee"}

	if not employee_id:
		return {"success": False, "error": "Employee ID is required"}

	return _safe_delete_doc("Employee", employee_id)

@frappe.whitelist()
def delete_users(user_id):
	if not can_delete_user():
		return {"success": False, "error": "Not permitted to delete User"}

	if not user_id:
		return {"success": False, "error": "User ID is required"}

	if user_id == frappe.session.user:
		return {"success": False, "error": "You cannot delete your own user account"}

	return _safe_delete_doc("User", user_id)

@frappe.whitelist()
def delete_department(department_id):
	if not can_delete_department():
		return {"success": False, "error": "Not permitted to delete Department"}

	if not department_id:
		return {"success": False, "error": "Department ID is required"}

	return _safe_delete_doc("Department", department_id)

@frappe.whitelist()
def get_designation_list(designation_id="", search_term="", page=1, page_size=0):
	if not can_read_designation():
		return {} if designation_id else []

	if designation_id:
		doc = frappe.get_doc("Designation", designation_id)

		return {
			"name": doc.name,
			"designation_name": doc.designation_name,
			"description": doc.description
		}

	filters = {}
	or_filters = []
	if search_term:
		or_filters = [
			["name", "like", f"%{search_term}%"],
			["designation_name", "like", f"%{search_term}%"]
		]

	page = int(page or 1)
	page_size = int(page_size or 0)

	if page_size > 0:
		total = _count_records("Designation", or_filters=or_filters)
		start = (page - 1) * page_size
		designations = frappe.get_all("Designation",
			or_filters=or_filters,
			fields=["name", "designation_name", "description"],
			limit_start=start,
			limit_page_length=page_size,
			order_by="name asc"
		)
		return {"rows": designations, "total": total}

	designations = frappe.get_all("Designation",
		or_filters=or_filters,
		fields=["name", "designation_name", "description"],
		order_by="name asc"
	)

	return designations

@frappe.whitelist()
def delete_designation(designation_id):
	if not can_delete_designation():
		return {"success": False, "error": "Not permitted to delete Designation"}

	if not designation_id:
		return {"success": False, "error": "Designation ID is required"}

	return _safe_delete_doc("Designation", designation_id)

@frappe.whitelist()
def get_branch_list(branch_id="", search_term="", page=1, page_size=0):
	if not can_read_branch():
		return {} if branch_id else []

	if branch_id:
		doc = frappe.get_doc("Branch", branch_id)
		return {
			"name": doc.name,
			"branch_name": doc.branch
		}

	or_filters = []
	if search_term:
		or_filters = [
			["name", "like", f"%{search_term}%"]
		]

	page = int(page or 1)
	page_size = int(page_size or 0)

	if page_size > 0:
		total = _count_records("Branch", or_filters=or_filters)
		start = (page - 1) * page_size
		branches = frappe.get_all("Branch",
			or_filters=or_filters,
			fields=["name"],
			limit_start=start,
			limit_page_length=page_size,
			order_by="name asc"
		)
		for b in branches:
			b["branch_name"] = b.name
		return {"rows": branches, "total": total}

	branches = frappe.get_all("Branch",
		or_filters=or_filters,
		fields=["name"],
		order_by="name asc"
	)
	for b in branches:
		b["branch_name"] = b.name
	return branches

@frappe.whitelist()
def get_gender_list(gender_id="", search_term="", page=1, page_size=0):
	if not can_read_gender():
		return {} if gender_id else []

	if gender_id:
		doc = frappe.get_doc("Gender", gender_id)
		return {
			"name": doc.name,
			"gender_name": doc.gender
		}

	or_filters = []
	if search_term:
		or_filters = [
			["name", "like", f"%{search_term}%"]
		]

	page = int(page or 1)
	page_size = int(page_size or 0)

	if page_size > 0:
		total = _count_records("Gender", or_filters=or_filters)
		start = (page - 1) * page_size
		genders = frappe.get_all("Gender",
			or_filters=or_filters,
			fields=["name"],
			limit_start=start,
			limit_page_length=page_size,
			order_by="name asc"
		)
		for g in genders:
			g["gender_name"] = g.name
		return {"rows": genders, "total": total}

	genders = frappe.get_all("Gender",
		or_filters=or_filters,
		fields=["name"],
		order_by="name asc"
	)
	for g in genders:
		g["gender_name"] = g.name
	return genders

@frappe.whitelist()
def get_salutation_list(salutation_id="", search_term="", page=1, page_size=0):
	if not can_read_salutation():
		return {} if salutation_id else []

	if salutation_id:
		doc = frappe.get_doc("Salutation", salutation_id)
		return {
			"name": doc.name,
			"salutation_name": doc.salutation
		}

	or_filters = []
	if search_term:
		or_filters = [
			["name", "like", f"%{search_term}%"]
		]

	page = int(page or 1)
	page_size = int(page_size or 0)

	if page_size > 0:
		total = _count_records("Salutation", or_filters=or_filters)
		start = (page - 1) * page_size
		salutations = frappe.get_all("Salutation",
			or_filters=or_filters,
			fields=["name"],
			limit_start=start,
			limit_page_length=page_size,
			order_by="name asc"
		)
		for s in salutations:
			s["salutation_name"] = s.name
		return {"rows": salutations, "total": total}

	salutations = frappe.get_all("Salutation",
		or_filters=or_filters,
		fields=["name"],
		order_by="name asc"
	)
	for s in salutations:
		s["salutation_name"] = s.name
	return salutations

@frappe.whitelist()
def get_employee_grade_list(grade_id="", search_term="", page=1, page_size=0):
	if not can_read_employee_grade():
		return {} if grade_id else []

	if grade_id:
		doc = frappe.get_doc("Employee Grade", grade_id)
		return {
			"name": doc.name,
			"grade_name": doc.name
		}

	filters = {}
	if search_term:
		filters["name"] = ["like", f"%{search_term}%"]

	page = int(page or 1)
	page_size = int(page_size or 0)

	if not frappe.db.table_exists("Employee Grade"):
		return {"rows": [], "total": 0} if page_size > 0 else []

	if page_size > 0:
		total = _count_records("Employee Grade", filters=filters)
		start = (page - 1) * page_size
		grades = frappe.get_all(
			"Employee Grade",
			filters=filters,
			fields=["name"],
			limit_start=start,
			limit_page_length=page_size,
			order_by="name asc"
		)
		for grade in grades:
			grade["grade_name"] = grade["name"]
		return {"rows": grades, "total": total}

	grades = frappe.get_all(
		"Employee Grade",
		filters=filters,
		fields=["name"],
		order_by="name asc"
	)

	for grade in grades:
		grade["grade_name"] = grade["name"]

	return grades

@frappe.whitelist()
def get_employee_type_list(type_id="", search_term="", page=1, page_size=0):
	if not can_read_employee_type():
		return {} if type_id else []

	if type_id:
		doc = frappe.get_doc("Employment Type", type_id)
		return {
			"name": doc.name,
			"employee_type_name": doc.employee_type_name
		}

	filters = {}
	if search_term:
		filters["employee_type_name"] = ["like", f"%{search_term}%"]

	page = int(page or 1)
	page_size = int(page_size or 0)

	if not frappe.db.table_exists("Employment Type"):
		return {"rows": [], "total": 0} if page_size > 0 else []

	if page_size > 0:
		total = _count_records("Employment Type", filters=filters)
		start = (page - 1) * page_size
		types = frappe.get_all(
			"Employment Type",
			filters=filters,
			fields=["name", "employee_type_name"],
			limit_start=start,
			limit_page_length=page_size,
			order_by="name asc"
		)
		return {"rows": types, "total": total}

	types = frappe.get_all(
		"Employment Type",
		filters=filters,
		fields=["name", "employee_type_name"],
		order_by="name asc"
	)

	return types

@frappe.whitelist()
def delete_branch(branch_id):
	if not can_delete_branch():
		return {"success": False, "error": "Not permitted to delete Branch"}
	if not branch_id:
		return {"success": False, "error": "Branch ID is required"}
	return _safe_delete_doc("Branch", branch_id)

@frappe.whitelist()
def delete_gender(gender_id):
	if not can_delete_gender():
		return {"success": False, "error": "Not permitted to delete Gender"}
	if not gender_id:
		return {"success": False, "error": "Gender ID is required"}
	return _safe_delete_doc("Gender", gender_id)

@frappe.whitelist()
def delete_salutation(salutation_id):
	if not can_delete_salutation():
		return {"success": False, "error": "Not permitted to delete Salutation"}
	if not salutation_id:
		return {"success": False, "error": "Salutation ID is required"}
	return _safe_delete_doc("Salutation", salutation_id)

@frappe.whitelist()
def delete_employee_grade(grade_id):
	if not can_delete_employee_grade():
		return {"success": False, "error": "Not permitted to delete Employee Grade"}
	if not grade_id:
		return {"success": False, "error": "Employee Grade ID is required"}
	return _safe_delete_doc("Employee Grade", grade_id)

@frappe.whitelist()
def save_employee_type(type_data):
	if isinstance(type_data, str):
		type_data = frappe.parse_json(type_data)

	is_new = not type_data.get("name")
	if is_new:
		if not can_create_employee_type():
			frappe.throw("Not permitted to create Employee Type", frappe.PermissionError)
	else:
		if not can_edit_employee_type():
			frappe.throw("Not permitted to edit Employee Type", frappe.PermissionError)

	type_name = type_data.get("employee_type_name")
	if not type_name:
		frappe.throw("Employee Type name is required")

	if is_new:
		if frappe.db.exists("Employment Type", type_name):
			frappe.throw(_("Employee Type '{0}' already exists.").format(type_name), frappe.DuplicateEntryError)
		doc = frappe.get_doc({
			"doctype": "Employment Type",
			"employee_type_name": type_name
		})
		try:
			doc.insert(ignore_permissions=True)
		except frappe.DuplicateEntryError:
			frappe.throw(_("Employee Type '{0}' already exists.").format(type_name))
	else:
		old_name = type_data.get("name")
		if old_name != type_name:
			frappe.flags.ignore_permissions = True
			try:
				frappe.rename_doc("Employment Type", old_name, type_name)
			finally:
				frappe.flags.ignore_permissions = False
			old_name = type_name
		doc = frappe.get_doc("Employment Type", old_name)
		doc.save(ignore_permissions=True)
	return doc.name

@frappe.whitelist()
def delete_employee_type(type_id):
	if not can_delete_employee_type():
		return {"success": False, "error": "Not permitted to delete Employee Type"}
	if not type_id:
		return {"success": False, "error": "Employee Type ID is required"}
	return _safe_delete_doc("Employment Type", type_id)

@frappe.whitelist()
def can_read_role():
	"""
	Returns True if the current user has permission to read a Role.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if has_role_permission("Role", "read"):
		return True
	return False

@frappe.whitelist()
def can_create_role():
	"""
	Returns True if the current user has permission to create a Role.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if has_role_permission("Role", "create"):
		return True
	return False

@frappe.whitelist()
def can_edit_role():
	"""
	Returns True if the current user has permission to edit a Role.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if has_role_permission("Role", "write"):
		return True
	return False

@frappe.whitelist()
def can_delete_role():
	"""
	Returns True if the current user has permission to delete a Role.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True
	if has_role_permission("Role", "delete"):
		return True
	return False

# --- Role & Permission matrix -------------------------------------------------
# Full set of DocPerm flags the admin UI can toggle. The first 14 match
# frappe.permissions.std_rights; "mask" is a per-row DocPerm field outside
# std_rights and is applied via direct Custom DocPerm writes.
_PERMISSION_PTYPES = [
	"select", "read", "write", "create", "delete", "submit", "cancel", "amend",
	"print", "email", "report", "import", "export", "share", "mask",
]

# Roles that must never be deleted or stripped by the admin UI.
_PROTECTED_ROLES = [
	"System Manager",
	"Administrator",
	"Guest",
	"All",
	"HR Manager",
	"HR User",
	# Customer owner role (v1_5): it IS the admin grant — editable nowhere
	# in the SPA, only via personas/patches.
	"Admin User",
	# Desk tier: never editable/deletable from the SPA permission studio —
	# desk admins manage these in the Frappe Desk.
	"Gemora Super Admin",
	"Gemora Developer",
]
# Users that must never be the target of row-level / role-profile changes.
_PROTECTED_USERS = ("Administrator", "Guest")


@frappe.whitelist()
def get_doctypes(detail=False):
	"""Return DocType names, or [{name, module, has_custom_perms}] when detail is truthy."""
	if str(detail).lower() in ("1", "true"):
		custom = set(frappe.get_all("Custom DocPerm", pluck="parent", distinct=True))
		rows = frappe.get_all("DocType", fields=["name", "module"], order_by="name asc")
		return [{"name": r.name, "module": r.module, "has_custom_perms": r.name in custom} for r in rows]
	return [d.name for d in frappe.get_all("DocType", order_by="name asc")]


@frappe.whitelist()
def list_editable_roles():
	"""Return roles the admin can manage (excludes built-in / protected roles)."""
	if not can_read_role():
		frappe.throw("Not permitted to view roles", frappe.PermissionError)
	rows = frappe.get_all("Role", fields=["name", "disabled", "desk_access"], order_by="name asc")
	return [
		{"name": r.name, "disabled": bool(r.disabled), "desk_access": bool(r.desk_access)}
		for r in rows
		if r.name not in _PROTECTED_ROLES
	]


def _get_or_create_custom_docperm(role, doctype, permlevel):
	"""Return the Custom DocPerm row for (role, doctype, permlevel, if_owner=0),
	creating it if missing. Rows are never deleted (see _zero_custom_docperm)."""
	existing = frappe.db.get_value(
		"Custom DocPerm",
		{"parent": doctype, "role": role, "permlevel": permlevel, "if_owner": 0},
	)
	if existing:
		return frappe.get_doc("Custom DocPerm", existing)
	cd = frappe.get_doc({
		"doctype": "Custom DocPerm",
		"parent": doctype,
		"parenttype": "DocType",
		"parentfield": "permissions",
		"role": role,
		"permlevel": permlevel,
		"if_owner": 0,
	})
	cd.insert(ignore_permissions=True)
	return cd


def _apply_doctype_perms(role, doctype, levels):
	"""Authoritatively set every (permlevel, ptype) flag for ``role`` on ``doctype``.

	``levels`` = {permlevel: {ptype: 0/1}}. Flags absent from a level are cleared,
	so the saved matrix is the single source of truth.
	"""
	from frappe.core.doctype.doctype.doctype import validate_permissions_for_doctype
	from frappe.permissions import setup_custom_perms

	setup_custom_perms(doctype)
	for raw_level, flags in levels.items():
		try:
			permlevel = int(raw_level)
		except (TypeError, ValueError):
			permlevel = 0
		if not isinstance(flags, dict):
			continue
		cd = _get_or_create_custom_docperm(role, doctype, permlevel)
		for ptype in _PERMISSION_PTYPES:
			setattr(cd, ptype, 1 if flags.get(ptype) else 0)
		cd.save(ignore_permissions=True)  # on_update clears the doctype meta cache
	# Re-validate and clear the permissions cache (separate from the meta cache).
	validate_permissions_for_doctype(doctype)
	frappe.clear_cache(doctype=doctype)


def _zero_custom_docperm(name, doctype=None):
	"""Clear every flag on a Custom DocPerm row.

	Never delete: deleting a Custom DocPerm re-exposes the shadowed standard
	DocPerm and would silently re-grant access.
	"""
	cd = frappe.get_doc("Custom DocPerm", name)
	for ptype in _PERMISSION_PTYPES:
		setattr(cd, ptype, 0)
	cd.save(ignore_permissions=True)
	if doctype:
		frappe.clear_cache(doctype=doctype)


@frappe.whitelist()
def save_role_permissions(role_name, matrix):
	"""Save a role's full permission matrix.

	matrix = {doctype: {permlevel: {ptype: 0/1, ...}}} (permlevel may be str/int).
	The role is created if missing. Custom DocPerm rows are set authoritatively;
	doctypes dropped from the matrix are zeroed out (rows are never deleted).
	"""
	import json

	if not (can_create_role() or can_edit_role()):
		frappe.throw("Not permitted to manage roles", frappe.PermissionError)
	if not role_name:
		frappe.throw("Role name is required")
	if isinstance(matrix, str):
		matrix = json.loads(matrix)

	if not frappe.db.exists("Role", role_name):
		frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)

	payload_doctypes = set()
	for doctype, levels in (matrix or {}).items():
		if not isinstance(levels, dict):
			continue
		payload_doctypes.add(doctype)
		_apply_doctype_perms(role_name, doctype, levels)

	# Zero out Custom DocPerm rows for doctypes removed from the matrix.
	existing = frappe.get_all(
		"Custom DocPerm", filters={"role": role_name}, fields=["name", "parent"]
	)
	for row in existing:
		if row.parent not in payload_doctypes:
			_zero_custom_docperm(row.name, doctype=row.parent)

	return {"role": role_name, "doctypes": len(payload_doctypes)}


@frappe.whitelist()
def create_role(role_name, permissions):
	"""Legacy alias for :func:`save_role_permissions`.

	Accepts the original {doctype: {read,write,create,delete,submit}} shape
	(permlevel 0 only) used by the employee_portal role editor.
	"""
	import json

	if isinstance(permissions, str):
		permissions = json.loads(permissions)
	matrix = {}
	for doctype, flags in (permissions or {}).items():
		matrix[doctype] = {0: {
			"read": flags.get("read"),
			"write": flags.get("write"),
			"create": flags.get("create"),
			"delete": flags.get("delete"),
			"submit": flags.get("submit"),
		}}
	return save_role_permissions(role_name, matrix)


@frappe.whitelist()
def delete_role(role_name):
	if not can_delete_role():
		frappe.throw("Not permitted to delete a Role", frappe.PermissionError)

	if not role_name:
		frappe.throw("Role name is required")

	if role_name in _PROTECTED_ROLES:
		frappe.throw(f"Cannot delete core role: {role_name}")

	# Check if assigned to any users
	assigned_roles = frappe.get_all("Has Role", filters={"role": role_name, "parenttype": "User"}, fields=["parent"])
	if assigned_roles:
		users_list = [u.parent for u in assigned_roles]
		users_str = ", ".join(users_list)
		frappe.throw(f"Cannot delete role '{role_name}' because it is assigned to the following user(s): {users_str}. Please unassign them first.")

	frappe.db.delete("Custom DocPerm", {"role": role_name})
	frappe.delete_doc("Role", role_name, ignore_permissions=True)

	return True


@frappe.whitelist()
def get_role_permission_matrix(role_name):
	"""Return {doctype: {permlevel: {ptype: bool}}} for a role.

	Uses frappe.permissions.get_all_perms, which already merges standard DocPerm
	and Custom DocPerm with correct override semantics (once a doctype has any
	Custom DocPerm, only custom rows are returned for it).
	"""
	from frappe.permissions import get_all_perms

	if not can_read_role():
		frappe.throw("Not permitted to view roles", frappe.PermissionError)
	if not role_name:
		frappe.throw("Role name is required")
	if not frappe.db.exists("Role", role_name):
		frappe.throw(f"Role {role_name} not found", frappe.DoesNotExistError)

	matrix = {}
	for p in get_all_perms(role_name):
		doctype = p.parent
		permlevel = int(p.permlevel or 0)
		matrix.setdefault(doctype, {}).setdefault(permlevel, {})
		for ptype in _PERMISSION_PTYPES:
			matrix[doctype][permlevel][ptype] = bool(p.get(ptype))
	return matrix


@frappe.whitelist()
def get_roles_for_edit_and_view(role_name):
	"""Legacy alias: {doctype: {read,write,create,delete,submit}} at permlevel 0,
	matching the shape the employee_portal role editor expects."""
	matrix = get_role_permission_matrix(role_name)
	legacy = {}
	for doctype, levels in matrix.items():
		flags = levels.get(0, {})
		legacy[doctype] = {k: bool(flags.get(k, 0)) for k in ("read", "write", "create", "delete", "submit")}
	return legacy


@frappe.whitelist()
def get_timezones():
	from frappe.utils.data import get_system_timezone
	from frappe.utils.momentjs import get_all_timezones
	return {
		"timezones": get_all_timezones(),
		"default_timezone": get_system_timezone()
	}



# --- Row-level User Permissions (data scoping) --------------------------------


@frappe.whitelist()
def list_user_permissions(user):
	"""Return a user's User Permission rows (row-level data scoping)."""
	frappe.only_for("System Manager", "Administrator")
	if not user:
		frappe.throw("User is required")
	return frappe.get_all(
		"User Permission",
		filters={"user": user},
		fields=["name", "allow", "for_value", "is_default", "apply_to_all_doctypes", "applicable_for", "hide_descendants"],
		order_by="allow asc",
	)


@frappe.whitelist()
def save_user_permission(user, allow, for_value, is_default=False, applicable_for=None, hide_descendants=False):
	"""Add a row-level User Permission (restricts the user to specific records)."""
	from frappe.permissions import add_user_permission

	frappe.only_for("System Manager", "Administrator")
	if user in _PROTECTED_USERS:
		frappe.throw(f"Cannot manage permissions for protected user: {user}")
	if not (user and allow and for_value):
		frappe.throw("user, allow (DocType) and for_value are required")

	add_user_permission(
		doctype=allow,
		name=for_value,
		user=user,
		applicable_for=applicable_for or None,
		is_default=1 if is_default else 0,
		hide_descendants=1 if hide_descendants else 0,
		ignore_permissions=True,
	)
	frappe.clear_cache(user=user)
	return frappe.db.get_value(
		"User Permission", {"user": user, "allow": allow, "for_value": for_value}, "name"
	)


@frappe.whitelist()
def remove_user_permission(name):
	"""Remove a User Permission row by its document name."""
	frappe.only_for("System Manager", "Administrator")
	if not name:
		frappe.throw("User Permission name is required")
	owner = frappe.db.get_value("User Permission", name, "user")
	frappe.delete_doc("User Permission", name, force=True)
	if owner:
		frappe.clear_cache(user=owner)
	return True


@frappe.whitelist()
def get_effective_permissions(user):
	"""Return a user's effective access: roles, merged doctype perms, row-level scoping."""
	from frappe.permissions import get_all_perms

	frappe.only_for("System Manager", "Administrator")
	if not user:
		frappe.throw("User is required")

	roles = [r for r in frappe.get_roles(user) if r not in ("All", "Guest", "Desk User")]
	doctype_perms = {}
	for role in roles:
		for p in get_all_perms(role):
			dt = p.parent
			lvl = int(p.permlevel or 0)
			cell = doctype_perms.setdefault(dt, {}).setdefault(lvl, {})
			for ptype in _PERMISSION_PTYPES:
				if bool(p.get(ptype)):
					cell[ptype] = True
				else:
					cell.setdefault(ptype, False)

	user_permissions = frappe.get_all(
		"User Permission",
		filters={"user": user},
		fields=["allow", "for_value", "applicable_for", "is_default"],
	)
	return {"roles": roles, "doctype_perms": doctype_perms, "user_permissions": user_permissions}


# --- Field-level restrictions (permlevel) -------------------------------------


@frappe.whitelist()
def get_permlevel_fields(doctype):
	"""Return [{permlevel, fields: [{fieldname, label}]}] for fields with permlevel > 0."""
	if not doctype:
		frappe.throw("DocType is required")
	meta = frappe.get_meta(doctype)
	grouped = {}
	for df in (meta.high_permlevel_fields or []):
		grouped.setdefault(int(df.permlevel), []).append(
			{"fieldname": df.fieldname, "label": df.label or df.fieldname}
		)
	return [{"permlevel": lvl, "fields": fields} for lvl, fields in sorted(grouped.items())]


# --- Role Profiles (bulk role bundles) ----------------------------------------


@frappe.whitelist()
def list_role_profiles():
	"""Return Role Profiles with their bundled roles."""
	frappe.only_for("System Manager", "Administrator")
	profiles = frappe.get_all(
		"Role Profile",
		fields=["name", "custom_persona_description"] if frappe.db.has_column("Role Profile", "custom_persona_description") else ["name"],
		order_by="name asc",
	)
	out = []
	for p in profiles:
		roles = frappe.get_all(
			"Has Role", filters={"parent": p.name, "parenttype": "Role Profile"}, pluck="role"
		)
		spec = ROLE_PROFILE_CATALOG.get(p.name) or {}
		label = spec.get("label", p.name)
		description = spec.get("description") or getattr(p, "custom_persona_description", "") or ""
		out.append({"name": p.name, "label": label, "description": description, "roles": roles})
	return out


@frappe.whitelist()
def save_role_profile(name, roles, is_new=False):
	"""Create or update a Role Profile with the given role bundle."""
	frappe.only_for("System Manager", "Administrator")
	if not name:
		frappe.throw("Role Profile name is required")
	if name in ROLE_PROFILE_CATALOG:
		frappe.throw(
			f"'{name}' is a curated Team persona — its bundle is managed on the Team page "
			"(a migrate re-sync would revert manual edits here)"
		)
	if isinstance(roles, str):
		import json

		roles = json.loads(roles)

	# Upsert: create if missing, otherwise replace the role bundle. This avoids
	# DuplicateEntryError when an admin re-saves an existing profile name.
	existed = frappe.db.exists("Role Profile", name)
	if existed:
		doc = frappe.get_doc("Role Profile", name)
		doc.set("roles", [])
	else:
		doc = frappe.new_doc("Role Profile")
		doc.role_profile = name

	for role in roles or []:
		if frappe.db.exists("Role", role):
			doc.append("roles", {"role": role})
	doc.save(ignore_permissions=True)
	return {"name": doc.name, "roles": [r.role for r in doc.roles], "created": not existed}


@frappe.whitelist()
def delete_role_profile(name):
	"""Delete a Role Profile (blocked if any user is still assigned to it)."""
	frappe.only_for("System Manager", "Administrator")
	if not name:
		frappe.throw("Role Profile name is required")
	if name in ROLE_PROFILE_CATALOG:
		frappe.throw(f"'{name}' is a curated Team persona and cannot be deleted here")
	assigned = frappe.get_all(
		"User Role Profile", filters={"role_profile": name, "parenttype": "User"}, pluck="parent"
	)
	if assigned:
		frappe.throw(
			f"Cannot delete Role Profile '{name}' — assigned to user(s): {', '.join(assigned)}. Unassign them first."
		)
	frappe.delete_doc("Role Profile", name, force=True)
	return True


@frappe.whitelist()
def assign_role_profile_to_user(user, role_profile):
	"""Assign a Role Profile to a user.

	Uses the ``role_profiles`` child table; User.validate() then syncs the user's
	roles from the profile (``populate_role_profile_roles``). Note: assigning a
	profile replaces the user's roles with the profile's bundle (Frappe behaviour).
	"""
	frappe.only_for("System Manager", "Administrator")
	if user in _PROTECTED_USERS:
		frappe.throw(f"Cannot manage protected user: {user}")
	if not frappe.db.exists("Role Profile", role_profile):
		frappe.throw(f"Role Profile {role_profile} not found", frappe.DoesNotExistError)
	doc = frappe.get_doc("User", user)
	current = {r.role_profile for r in (doc.role_profiles or [])}
	if role_profile not in current:
		doc.append("role_profiles", {"role_profile": role_profile})
		doc.save(ignore_permissions=True)
		frappe.clear_cache(user=user)
	return True

@frappe.whitelist()
def report_employee_list(department=None, branch=None, designation=None, status=None, employee=None, export=False, pdf=False):
	"""
	Returns detailed employee list for Teams Master Report, supporting Excel and PDF exports.
	Enterprise-grade, optimized query execution avoiding redundant DB calls.
	"""
	import frappe
	from frappe import _
	from frappe.utils import cint, flt, now_datetime
	from frappe.utils.pdf import get_pdf
	from frappe.utils.xlsxutils import build_xlsx_response

	columns = [
		{"label": "Employee ID", "fieldname": "employee"},
		{"label": "Employee Name", "fieldname": "employee_name"},
		{"label": "Department", "fieldname": "department"},
		{"label": "Designation", "fieldname": "designation"},
		{"label": "Branch", "fieldname": "branch"},
		{"label": "Employment Type", "fieldname": "employment_type"},
		{"label": "Company Email", "fieldname": "company_email"},
		{"label": "Phone Number", "fieldname": "cell_number"},
		{"label": "Date of Joining", "fieldname": "date_of_joining"},
		{"label": "Salary Structure", "fieldname": "salary_structure"},
		{"label": "Base Pay", "fieldname": "base_pay"},
		{"label": "Status", "fieldname": "status"},
	]

	conditions = []
	params = {}

	if department:
		conditions.append("emp.department = %(department)s")
		params["department"] = department

	if branch:
		conditions.append("emp.branch = %(branch)s")
		params["branch"] = branch

	if designation:
		conditions.append("emp.designation = %(designation)s")
		params["designation"] = designation

	if status and status.lower() != "all":
		conditions.append("emp.status = %(status)s")
		params["status"] = status

	if employee:
		conditions.append("emp.name = %(employee)s")
		params["employee"] = employee

	where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

	query = f"""
		SELECT
			emp.name as employee,
			emp.employee_name,
			COALESCE(emp.department, '-') as department,
			COALESCE(emp.designation, '-') as designation,
			COALESCE(emp.branch, '-') as branch,
			COALESCE(emp.employment_type, '-') as employment_type,
			COALESCE(emp.company_email, '-') as company_email,
			COALESCE(emp.cell_number, '-') as cell_number,
			DATE_FORMAT(emp.date_of_joining, '%%Y-%%m-%%d') as date_of_joining,
			COALESCE(latest_ssa.salary_structure, '-') as salary_structure,
			ROUND(COALESCE(latest_ssa.base, 0), 2) as base_pay,
			emp.status
		FROM `tabEmployee` emp
		LEFT JOIN (
			SELECT ssa1.employee, ssa1.salary_structure, ssa1.base
			FROM `tabSalary Structure Assignment` ssa1
			INNER JOIN (
				SELECT employee, MAX(from_date) as max_date
				FROM `tabSalary Structure Assignment`
				WHERE docstatus = 1
				GROUP BY employee
			) ssa2 ON ssa1.employee = ssa2.employee AND ssa1.from_date = ssa2.max_date
			WHERE ssa1.docstatus = 1
		) latest_ssa ON emp.name = latest_ssa.employee
		{where_clause}
		ORDER BY emp.name ASC
	"""

	data = frappe.db.sql(query, params, as_dict=True)

	is_export = cint(export) if isinstance(export, (int, str)) and str(export).isdigit() else frappe.parse_json(export)
	is_pdf = cint(pdf) if isinstance(pdf, (int, str)) and str(pdf).isdigit() else frappe.parse_json(pdf)

	company_name = frappe.db.get_single_value("Global Defaults", "default_company") or "Company"
	company_currency = frappe.get_cached_value("Company", company_name, "default_currency") or "USD"
	currency_symbol = frappe.db.get_value("Currency", company_currency, "symbol") or "$"

	if is_export:
		xlsx_data = [[c["label"] for c in columns]]
		for row in data:
			xlsx_data.append([row.get(c["fieldname"], "") for c in columns])
		return build_xlsx_response(xlsx_data, "Employee_Directory_Report")

	if is_pdf:
		context = {
			"report_title": _("Employee Directory & Master Report"),
			"company_name": company_name,
			"currency_symbol": currency_symbol,
			"selected_department": department,
			"selected_branch": branch,
			"selected_designation": designation,
			"selected_status": status,
			"selected_employee": employee,
			"generated_on": now_datetime().strftime("%Y-%m-%d %H:%M"),
			"columns": columns,
			"data": data
		}

		html_content = frappe.render_template("arijentek_core/templates/reports/employee_master_report.html", context)

		pdf_options = {
			"page-size": "A4",
			"orientation": "Landscape",
			"margin-top": "10mm",
			"margin-bottom": "10mm",
			"margin-left": "8mm",
			"margin-right": "8mm",
			"encoding": "UTF-8"
		}

		pdf_binary = get_pdf(html_content, options=pdf_options)

		frappe.local.response.filename = f"Employee_Directory_Report_{now_datetime().strftime('%Y%m%d')}.pdf"
		frappe.local.response.filecontent = pdf_binary
		frappe.local.response.type = "pdf"
		return

	return {
		"columns": columns,
		"data": data,
		"count": len(data)
	}


@frappe.whitelist()
def report_user_list(role=None, status=None, search=None, export=False, pdf=False):
	"""
	Returns user directory & assigned roles for Users Master Report, supporting Excel and PDF exports.
	Enterprise-grade, optimized query execution avoiding redundant DB calls.
	"""
	import frappe
	from frappe import _
	from frappe.utils import cint, now_datetime
	from frappe.utils.pdf import get_pdf
	from frappe.utils.xlsxutils import build_xlsx_response

	columns = [
		{"label": "User ID", "fieldname": "user_id"},
		{"label": "Full Name", "fieldname": "full_name"},
		{"label": "Email Address", "fieldname": "email"},
		{"label": "Username", "fieldname": "username"},
		{"label": "Status", "fieldname": "status"},
		{"label": "Assigned Roles", "fieldname": "roles"},
	]

	conditions = []
	params = {}

	# Platform accounts never appear in the tenant directory report.
	conditions.append("u.name NOT IN %(internal_users)s")
	params["internal_users"] = tuple(get_internal_user_names())

	if status and status.lower() != "all":
		if status.lower() in ("active", "enabled", "1"):
			conditions.append("u.enabled = 1")
		elif status.lower() in ("disabled", "inactive", "0"):
			conditions.append("u.enabled = 0")

	if search:
		conditions.append("(u.name LIKE %(search)s OR u.full_name LIKE %(search)s OR u.email LIKE %(search)s OR u.username LIKE %(search)s)")
		params["search"] = f"%{search}%"

	where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

	users = frappe.db.sql(f"""
		SELECT
			u.name as user_id,
			u.full_name,
			COALESCE(u.email, u.name) as email,
			COALESCE(u.username, '-') as username,
			u.enabled
		FROM `tabUser` u
		{where_clause}
		ORDER BY u.full_name ASC
	""", params, as_dict=True)

	if not users:
		if cint(export):
			return build_xlsx_response([[c["label"] for c in columns]], "User_Directory_Report")
		if cint(pdf):
			context = {
				"report_title": _("User Directory & Roles Report"),
				"company_name": frappe.db.get_single_value("Global Defaults", "default_company") or "Company",
				"selected_role": role,
				"selected_status": status,
				"search_term": search,
				"generated_on": now_datetime().strftime("%Y-%m-%d %H:%M"),
				"columns": columns,
				"data": []
			}
			html_content = frappe.render_template("arijentek_core/templates/reports/user_master_report.html", context)
			pdf_binary = get_pdf(html_content, options={"page-size": "A4", "orientation": "Landscape", "margin-top": "10mm", "margin-bottom": "10mm", "margin-left": "8mm", "margin-right": "8mm", "encoding": "UTF-8"})
			frappe.local.response.filename = f"User_Directory_Report_{now_datetime().strftime('%Y%m%d')}.pdf"
			frappe.local.response.filecontent = pdf_binary
			frappe.local.response.type = "pdf"
			return
		return {"columns": columns, "data": [], "count": 0}

	# Single batch fetch for assigned roles
	user_ids = [u.user_id for u in users]
	role_records = frappe.get_all(
		"Has Role",
		filters={"parent": ("in", user_ids), "parenttype": "User"},
		fields=["parent", "role"]
	)
	roles_map = {}
	for r in role_records:
		roles_map.setdefault(r.parent, []).append(r.role)

	# Filter by specific role if requested
	filtered_users = []
	for u in users:
		u["roles_list"] = roles_map.get(u.user_id, [])
		u["roles"] = ", ".join(u["roles_list"]) if u["roles_list"] else "No Roles"
		u["status"] = "Active" if u.enabled else "Disabled"

		if role and role.lower() != "all":
			if role not in u["roles_list"]:
				continue
		filtered_users.append(u)

	is_export = cint(export) if isinstance(export, (int, str)) and str(export).isdigit() else frappe.parse_json(export)
	is_pdf = cint(pdf) if isinstance(pdf, (int, str)) and str(pdf).isdigit() else frappe.parse_json(pdf)

	company_name = frappe.db.get_single_value("Global Defaults", "default_company") or "Company"

	if is_export:
		xlsx_data = [[c["label"] for c in columns]]
		for row in filtered_users:
			xlsx_data.append([row.get(c["fieldname"], "") for c in columns])
		return build_xlsx_response(xlsx_data, "User_Directory_Report")

	if is_pdf:
		context = {
			"report_title": _("User Directory & Roles Report"),
			"company_name": company_name,
			"selected_role": role,
			"selected_status": status,
			"search_term": search,
			"generated_on": now_datetime().strftime("%Y-%m-%d %H:%M"),
			"columns": columns,
			"data": filtered_users
		}

		html_content = frappe.render_template("arijentek_core/templates/reports/user_master_report.html", context)

		pdf_options = {
			"page-size": "A4",
			"orientation": "Landscape",
			"margin-top": "10mm",
			"margin-bottom": "10mm",
			"margin-left": "8mm",
			"margin-right": "8mm",
			"encoding": "UTF-8"
		}

		pdf_binary = get_pdf(html_content, options=pdf_options)

		frappe.local.response.filename = f"User_Directory_Report_{now_datetime().strftime('%Y%m%d')}.pdf"
		frappe.local.response.filecontent = pdf_binary
		frappe.local.response.type = "pdf"
		return

	return {
		"columns": columns,
		"data": filtered_users,
		"count": len(filtered_users)
	}


@frappe.whitelist()
def generate_employee_profile_pdf(employee: str):
	"""
	Generates a 1-page comprehensive PDF profile report for a specific employee.
	"""
	import frappe
	from frappe import _
	from frappe.utils import now_datetime
	from frappe.utils.pdf import get_pdf

	if not employee:
		frappe.throw(_("Employee ID is required"), frappe.ValidationError)

	if not frappe.has_permission("Employee", "read", employee):
		frappe.throw(_("You are not authorized to view this employee profile"), frappe.PermissionError)

	doc = frappe.get_doc("Employee", employee)

	# Helper function to get employee name from ID or User ID
	def get_emp_name(emp_id_or_user):
		if not emp_id_or_user:
			return ""
		name = frappe.db.get_value("Employee", emp_id_or_user, "employee_name")
		if name:
			return name
		# Try looking up by user_id
		name = frappe.db.get_value("Employee", {"user_id": emp_id_or_user}, "employee_name")
		if name:
			return name
		# Try User full_name
		user_name = frappe.db.get_value("User", emp_id_or_user, "full_name")
		if user_name:
			return user_name
		return emp_id_or_user

	company_name = doc.company or frappe.db.get_single_value("Global Defaults", "default_company") or "Company"

	context = {
		"doc": doc,
		"company_name": company_name,
		"reports_to_name": get_emp_name(doc.reports_to),
		"expense_approver_name": get_emp_name(doc.expense_approver),
		"shift_approver_name": get_emp_name(doc.shift_request_approver),
		"leave_approver_name": get_emp_name(doc.leave_approver),
		"generated_on": now_datetime().strftime("%Y-%m-%d %H:%M"),
	}

	html_content = frappe.render_template("arijentek_core/templates/reports/employee_profile_report.html", context)

	pdf_options = {
		"page-size": "A4",
		"orientation": "Portrait",
		"margin-top": "8mm",
		"margin-bottom": "8mm",
		"margin-left": "10mm",
		"margin-right": "10mm",
		"encoding": "UTF-8"
	}

	pdf_binary = get_pdf(html_content, options=pdf_options)

	safe_emp_id = str(employee).replace('/', '_')
	frappe.local.response.filename = f"Employee_Profile_{safe_emp_id}.pdf"
	frappe.local.response.filecontent = pdf_binary
	frappe.local.response.type = "pdf"
	return


@frappe.whitelist()
def generate_user_profile_pdf(user_id: str):
	"""
	Generates a 1-page comprehensive PDF profile report for a specific system user.
	"""
	import frappe
	from frappe import _
	from frappe.utils import now_datetime
	from frappe.utils.pdf import get_pdf

	if not user_id:
		frappe.throw(_("User ID is required"), frappe.ValidationError)

	roles_of_caller = frappe.get_roles(frappe.session.user)
	has_access = (
		frappe.session.user == "Administrator"
		or "System Manager" in roles_of_caller
		or "HR Manager" in roles_of_caller
		or frappe.session.user == user_id
		or frappe.has_permission("User", "read", user_id)
	)
	if not has_access:
		frappe.throw(_("You are not authorized to view this user profile"), frappe.PermissionError)

	doc = frappe.get_doc("User", user_id)

	# Fetch assigned roles
	user_roles = frappe.get_roles(user_id)

	# Fetch linked employee details
	linked_emp = frappe.db.get_value(
		"Employee",
		{"user_id": user_id},
		["name", "employee_name", "department", "designation"],
		as_dict=True
	) or {}

	company_name = frappe.db.get_single_value("Global Defaults", "default_company") or "Company"

	context = {
		"doc": doc,
		"roles": user_roles,
		"linked_employee": linked_emp,
		"company_name": company_name,
		"generated_on": now_datetime().strftime("%Y-%m-%d %H:%M"),
	}

	html_content = frappe.render_template("arijentek_core/templates/reports/user_profile_report.html", context)

	pdf_options = {
		"page-size": "A4",
		"orientation": "Portrait",
		"margin-top": "8mm",
		"margin-bottom": "8mm",
		"margin-left": "10mm",
		"margin-right": "10mm",
		"encoding": "UTF-8"
	}

	pdf_binary = get_pdf(html_content, options=pdf_options)

	safe_user_id = str(user_id).replace('/', '_').replace('@', '_at_')
	frappe.local.response.filename = f"User_Profile_{safe_user_id}.pdf"
	frappe.local.response.filecontent = pdf_binary
	frappe.local.response.type = "pdf"
	return







