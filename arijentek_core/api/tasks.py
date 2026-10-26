"""
Tasks API - Personal todos management
"""

import frappe
from frappe import _
from frappe.utils import getdate, today


@frappe.whitelist()
def get_personal_todos(status: str | None = None, user_filter: str | None = None):
	"""
	Get personal TODO items for current user, supporting all statuses, assignee/assigner name mapping, and administrative user filtering.

	Args:
	    status: Filter by status (optional)
	    user_filter: Filter by target allocated user (optional, only for administrative users)

	Returns:
	    List of TODO items
	"""
	user = frappe.session.user

	# Check permission (exclude AUTOMATIC_ROLES like 'All')
	from frappe.permissions import AUTOMATIC_ROLES
	todo_roles = frappe.permissions.get_doctype_roles("ToDo")
	todo_roles = set(todo_roles) - set(AUTOMATIC_ROLES)
	user_roles = frappe.get_roles(user)
	has_full_access = any(role in todo_roles for role in user_roles)

	filters = []
	or_filters = []
	if not has_full_access:
		# Return tasks assigned to the user OR tasks assigned by the user
		or_filters = [
			["allocated_to", "=", user],
			["assigned_by", "=", user]
		]
	else:
		# Administrative user can filter by user or see all
		if user_filter:
			filters.append(["allocated_to", "=", user_filter])

	if status:
		filters.append(["status", "=", status])

	todos = frappe.get_all(
		"ToDo",
		filters=filters or None,
		or_filters=or_filters or None,
		fields=["name", "description", "date", "creation", "priority", "status", "reference_type", "reference_name", "allocated_to", "assigned_by"],
		order_by="date asc, priority desc",
		limit=150,
		ignore_permissions=True,
	)

	# Batch fetch user full names to avoid N+1 queries
	user_ids = list(set([t.allocated_to for t in todos if t.allocated_to] + [t.assigned_by for t in todos if t.assigned_by]))
	user_names = {}
	if user_ids:
		users = frappe.get_all("User", filters={"name": ["in", user_ids]}, fields=["name", "full_name"])
		user_names = {u.name: u.full_name for u in users}

	return [
		{
			"id": todo.name,
			"description": todo.description,
			"date": str(todo.date) if todo.date else None,
			"creation_date": str(todo.creation.date()) if todo.creation else None,
			"priority": todo.priority,
			"status": todo.status,
			"reference_type": todo.reference_type,
			"reference_name": todo.reference_name,
			"allocated_to": todo.allocated_to,
			"allocated_to_name": user_names.get(todo.allocated_to) or todo.allocated_to,
			"assigned_by": todo.assigned_by,
			"assigned_by_name": user_names.get(todo.assigned_by) or todo.assigned_by,
		}
		for todo in todos
	]


@frappe.whitelist()
def get_todo_creation_metadata():
	"""
	Get metadata for TODO creation including permissions, priorities, active users, statuses, and today's date.
	"""
	user = frappe.session.user

	# Check permission to assign to others (exclude AUTOMATIC_ROLES like 'All')
	from frappe.permissions import AUTOMATIC_ROLES
	todo_roles = frappe.permissions.get_doctype_roles("ToDo")
	todo_roles = set(todo_roles) - set(AUTOMATIC_ROLES)
	user_roles = frappe.get_roles(user)
	can_assign = any(role in todo_roles for role in user_roles)

	# Fetch priority and status choices from ToDo metadata
	meta = frappe.get_meta("ToDo")

	priority_field = meta.get_field("priority")
	priorities = [p.strip() for p in priority_field.options.split("\n") if p.strip()] if priority_field else ["Low", "Medium", "High"]

	status_field = meta.get_field("status")
	statuses = [s.strip() for s in status_field.options.split("\n") if s.strip()] if status_field else ["Open", "Closed", "Cancelled"]

	# Fetch users list if permitted
	users = []
	if can_assign:
		users = frappe.get_all(
			"User",
			filters={"enabled": 1, "user_type": "System User"},
			fields=["name", "full_name"],
			order_by="full_name asc"
		)

	# Current user details
	current_user = {
		"name": user,
		"full_name": frappe.db.get_value("User", user, "full_name") or user
	}

	return {
		"can_assign_to_others": can_assign,
		"priorities": priorities,
		"statuses": statuses,
		"users": users,
		"current_user": current_user,
		"today": today()
	}


@frappe.whitelist()
def create_personal_todo(description: str, date: str | None = None, priority: str = "Medium", allocated_to: str | None = None):
	"""
	Create a personal TODO item.

	Args:
	    description: TODO description (required)
	    date: Target completion date (optional)
	    priority: Priority ('Low', 'Medium', 'High')
	    allocated_to: User to allocate TODO to (optional, defaults to creator)

	Returns:
	    Dict with success status and TODO ID
	"""
	if not description or not description.strip():
		frappe.throw(_("Description is required"))

	user = frappe.session.user

	# Validate priority
	meta = frappe.get_meta("ToDo")
	priority_field = meta.get_field("priority")
	valid_priorities = [p.strip() for p in priority_field.options.split("\n") if p.strip()] if priority_field else ["Low", "Medium", "High"]
	if priority not in valid_priorities:
		priority = "Medium"

	todo = frappe.get_doc(
		{
			"doctype": "ToDo",
			"description": description.strip(),
			"date": date,
			"priority": priority,
			"allocated_to": allocated_to or user,
			"assigned_by": user,
			"status": "Open",
		}
	)
	todo.insert(ignore_permissions=True)

	# Notify assignee if they are different from the creator
	if (allocated_to or user) != user:
		try:
			from arijentek_core.api.web_push import send_push_notification
			creator_name = frappe.db.get_value("User", user, "full_name") or user
			send_push_notification(
				user=allocated_to,
				title="New Task Assigned",
				body=f"{creator_name} assigned you a task: {description.strip()[:80]}",
				url="/employee-portal#/tasks"
			)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Task Assignment Notification Error")

	return {"success": True, "todo_id": todo.name, "message": _("TODO created successfully")}


@frappe.whitelist()
def update_personal_todo(
	todo_id: str,
	description: str,
	date: str | None = None,
	priority: str = "Medium",
	allocated_to: str | None = None,
	status: str = "Open",
):
	"""
	Update an existing personal TODO item.

	Args:
	    todo_id: Name of TODO document to update (required)
	    description: Updated description (required)
	    date: Target completion date (optional)
	    priority: Priority ('Low', 'Medium', 'High')
	    allocated_to: User to allocate TODO to (optional)
	    status: Status ('Open', 'Closed', 'Cancelled')

	Returns:
	    Dict with success status and TODO ID
	"""
	if not todo_id:
		frappe.throw(_("TODO ID is required"))

	if not description or not description.strip():
		frappe.throw(_("Description is required"))

	if not frappe.db.exists("ToDo", todo_id):
		frappe.throw(_("TODO not found"))

	todo = frappe.get_doc("ToDo", todo_id)
	user = frappe.session.user

	# Verify access - only allowed if user is assignee, creator, or has ToDo update role permissions
	from frappe.permissions import AUTOMATIC_ROLES
	todo_roles = frappe.permissions.get_doctype_roles("ToDo")
	todo_roles = set(todo_roles) - set(AUTOMATIC_ROLES)
	user_roles = frappe.get_roles(user)
	has_full_access = any(role in todo_roles for role in user_roles)

	if not has_full_access and todo.allocated_to != user and todo.assigned_by != user:
		frappe.throw(_("You don't have permission to update this TODO"))

	todo.description = description.strip()
	todo.date = date
	todo.priority = priority
	todo.status = status
	if allocated_to:
		todo.allocated_to = allocated_to

	todo.save(ignore_permissions=True)

	try:
		from arijentek_core.api.web_push import send_push_notification
		updater_name = frappe.db.get_value("User", user, "full_name") or user
		creator = todo.assigned_by
		final_assignee = todo.allocated_to
		desc_preview = description.strip()[:80]

		# If the assignee was changed to someone else → notify new assignee
		if final_assignee and final_assignee != user:
			send_push_notification(
				user=final_assignee,
				title="Task Assigned to You",
				body=f"{updater_name} assigned you a task: {desc_preview}",
				url="/employee-portal#/tasks"
			)

		# Status-change bidirectional notifications
		# Creator changed status → notify assignee
		if user == creator and final_assignee and final_assignee != user:
			send_push_notification(
				user=final_assignee,
				title=f"Task Status Updated to {status}",
				body=f"{updater_name} updated the status of your task '{desc_preview}' to {status}.",
				url="/employee-portal#/tasks"
			)
		# Assignee changed status → notify creator
		elif user == final_assignee and creator and creator != user:
			send_push_notification(
				user=creator,
				title=f"Task Status Updated to {status}",
				body=f"{updater_name} marked your task '{desc_preview}' as {status}.",
				url="/employee-portal#/tasks"
			)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Task Update Notification Error")

	return {"success": True, "todo_id": todo.name, "message": _("TODO updated successfully")}


@frappe.whitelist()
def update_todo_status(todo_id: str, status: str = "Closed"):
	"""
	Update TODO status.

	Args:
	    todo_id: Name of TODO document (required)
	    status: New status ('Open', 'Closed', 'Cancelled')

	Returns:
	    Dict with success status
	"""
	if not todo_id:
		frappe.throw(_("TODO ID is required"))

	if not frappe.db.exists("ToDo", todo_id):
		frappe.throw(_("TODO not found"))

	todo = frappe.get_doc("ToDo", todo_id)
	user = frappe.session.user

	# Verify access
	from frappe.permissions import AUTOMATIC_ROLES
	todo_roles = frappe.permissions.get_doctype_roles("ToDo")
	todo_roles = set(todo_roles) - set(AUTOMATIC_ROLES)
	user_roles = frappe.get_roles(user)
	has_full_access = any(role in todo_roles for role in user_roles)

	if not has_full_access and todo.allocated_to != user and todo.assigned_by != user:
		frappe.throw(_("You don't have permission to update this TODO"))

	todo.status = status
	todo.save(ignore_permissions=True)

	# Bidirectional status-change notifications
	creator = todo.assigned_by
	assignee = todo.allocated_to

	try:
		from arijentek_core.api.web_push import send_push_notification
		updater_name = frappe.db.get_value("User", user, "full_name") or user
		desc_preview = (todo.description or todo_id)[:80]

		# Creator changed the status → notify the assignee
		if user == creator and assignee and assignee != user:
			send_push_notification(
				user=assignee,
				title=f"Task Status Updated to {status}",
				body=f"{updater_name} updated the status of your task '{desc_preview}' to {status}.",
				url="/employee-portal#/tasks"
			)

		# Assignee changed the status → notify the creator
		elif user == assignee and creator and creator != user:
			send_push_notification(
				user=creator,
				title=f"Task Status Updated to {status}",
				body=f"{updater_name} marked your task '{desc_preview}' as {status}.",
				url="/employee-portal#/tasks"
			)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Task Status Notification Error")

	return {"success": True, "message": _("Status updated successfully")}


@frappe.whitelist()
def delete_todo(todo_id: str):
	"""
	Delete a personal TODO item.

	Args:
	    todo_id: Name of TODO document to delete (required)

	Returns:
	    Dict with success status
	"""
	if not todo_id:
		frappe.throw(_("TODO ID is required"))

	if not frappe.db.exists("ToDo", todo_id):
		frappe.throw(_("TODO not found"))

	todo = frappe.get_doc("ToDo", todo_id)
	user = frappe.session.user

	# Verify access
	from frappe.permissions import AUTOMATIC_ROLES
	todo_roles = frappe.permissions.get_doctype_roles("ToDo")
	todo_roles = set(todo_roles) - set(AUTOMATIC_ROLES)
	user_roles = frappe.get_roles(user)
	has_full_access = any(role in todo_roles for role in user_roles)

	if not has_full_access and todo.allocated_to != user and todo.assigned_by != user:
		frappe.throw(_("You don't have permission to delete this TODO"))

	frappe.delete_doc("ToDo", todo_id, ignore_permissions=True)

	return {"success": True, "message": _("TODO deleted successfully")}


@frappe.whitelist()
def get_recent_activities(limit: int = 20):
	"""
	Get recent TODO activities for current user.

	Args:
	    limit: Maximum number of activities to return

	Returns:
	    List of recent activities
	"""
	activities = []

	# Get recent TODOs
	todos = frappe.get_all(
		"ToDo",
		filters={"allocated_to": frappe.session.user},
		fields=["name", "description", "status", "modified"],
		order_by="modified desc",
		limit=limit,
	)

	for todo in todos:
		activities.append(
			{
				"type": "todo",
				"id": todo.name,
				"title": todo.description,
				"status": todo.status,
				"date": str(todo.modified),
				"url": None,
			}
		)

	# Sort by date
	activities.sort(key=lambda x: x["date"], reverse=True)

	return activities[:limit]


@frappe.whitelist()
def can_read_todo():
	"""
	Returns True if the current user has permission to read ToDo.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("ToDo", "read"):
		return True

	return False


@frappe.whitelist()
def can_create_todo():
	"""
	Returns True if the current user has permission to create ToDo.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("ToDo", "create"):
		return True

	return False


@frappe.whitelist()
def can_edit_todo():
	"""
	Returns True if the current user has permission to edit ToDo.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("ToDo", "write"):
		return True

	return False


@frappe.whitelist()
def can_delete_todo():
	"""
	Returns True if the current user has permission to delete ToDo.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	if frappe.has_permission("ToDo", "delete"):
		return True

	return False


@frappe.whitelist()
def can_allocate_todo():
	"""
	Returns True if the current user has permission to allocate ToDo.
	"""
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "HR Manager" in roles or "System Manager" in roles:
		return True

	return False


@frappe.whitelist()
def get_allocatable_users():
	"""
	Returns a list of users that can be allocated a ToDo, 
	provided the current user has permission to allocate.
	"""
	if not can_allocate_todo():
		return []

	users = frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User"},
		fields=["name", "full_name"],
		order_by="full_name asc"
	)

	return users


@frappe.whitelist()
def get_task_status():
	"""
	Returns the list of statuses available for the ToDo doctype.
	"""
	meta = frappe.get_meta("ToDo")
	field = meta.get_field("status")
	if field and field.options:
		return [opt.strip() for opt in field.options.split('\n') if opt.strip()]
	return []


def update_todo_status_options(options_list):
	"""
	Helper to update the ToDo status options via Property Setter
	"""
	frappe.make_property_setter({
		'doctype': 'ToDo',
		'doctype_or_field': 'DocField',
		'fieldname': 'status',
		'property': 'options',
		'value': '\n'.join(options_list),
		'property_type': 'Text'
	})
	frappe.clear_cache(doctype="ToDo")


@frappe.whitelist()
def add_task_status(status_name):
	if not can_allocate_todo():
		frappe.throw("Not permitted")

	status_name = status_name.strip()
	statuses = get_task_status()
	if status_name in statuses:
		frappe.throw(f"Status {status_name} already exists")

	statuses.append(status_name)
	update_todo_status_options(statuses)
	return statuses


@frappe.whitelist()
def edit_task_status(old_status, new_status):
	if not can_allocate_todo():
		frappe.throw("Not permitted")

	old_status = old_status.strip()
	new_status = new_status.strip()
	statuses = get_task_status()

	if old_status not in statuses:
		frappe.throw(f"Status {old_status} not found")

	if new_status in statuses:
		frappe.throw(f"Status {new_status} already exists")

	statuses = [new_status if s == old_status else s for s in statuses]

	update_todo_status_options(statuses)

	# Update existing records
	frappe.db.sql("""
		UPDATE `tabToDo` SET status = %s WHERE status = %s
	""", (new_status, old_status))
	frappe.db.commit()

	return statuses


@frappe.whitelist()
def delete_task_status(status_name):
	if not can_allocate_todo():
		frappe.throw("Not permitted")

	status_name = status_name.strip()

	# Cannot delete if tasks are using it
	usage_count = frappe.db.count("ToDo", {"status": status_name})
	if usage_count > 0:
		frappe.throw(f"Cannot delete status '{status_name}' because {usage_count} tasks are using it. Please update them first.")

	statuses = get_task_status()
	if status_name not in statuses:
		frappe.throw(f"Status {status_name} not found")

	statuses.remove(status_name)
	update_todo_status_options(statuses)
	return statuses


@frappe.whitelist()
def reorder_task_status(new_order):
	if not can_allocate_todo():
		frappe.throw("Not permitted")

	if isinstance(new_order, str):
		import json
		new_order = json.loads(new_order)

	current_statuses = get_task_status()

	# Verify that the new order contains exactly the same statuses
	if set(new_order) != set(current_statuses) or len(new_order) != len(current_statuses):
		frappe.throw("Invalid status list for reordering")

	update_todo_status_options(new_order)
	return new_order


@frappe.whitelist()
def get_todo(name: str):
	"""
	Get specific TODO details.
	"""
	if not name:
		frappe.throw(_("Name is required"))

	if not frappe.db.exists("ToDo", name):
		frappe.throw(_("TODO not found"))

	todo = frappe.get_doc("ToDo", name)
	user = frappe.session.user

	# Verify access
	from frappe.permissions import AUTOMATIC_ROLES
	todo_roles = frappe.permissions.get_doctype_roles("ToDo")
	todo_roles = set(todo_roles) - set(AUTOMATIC_ROLES)
	user_roles = frappe.get_roles(user)
	has_full_access = any(role in todo_roles for role in user_roles)

	if not has_full_access and todo.allocated_to != user and todo.assigned_by != user:
		frappe.throw(_("You don't have permission to view this TODO"))

	# Fetch user full names
	user_ids = [uid for uid in [todo.allocated_to, todo.assigned_by] if uid]
	user_names = {}
	if user_ids:
		users = frappe.get_all("User", filters={"name": ["in", user_ids]}, fields=["name", "full_name"])
		user_names = {u.name: u.full_name for u in users}

	return {
		"id": todo.name,
		"description": todo.description,
		"date": str(todo.date) if todo.date else None,
		"creation_date": str(todo.creation.date()) if todo.creation else None,
		"priority": todo.priority,
		"status": todo.status,
		"reference_type": todo.reference_type,
		"reference_name": todo.reference_name,
		"allocated_to": todo.allocated_to,
		"allocated_to_name": user_names.get(todo.allocated_to) or todo.allocated_to,
		"assigned_by": todo.assigned_by,
		"assigned_by_name": user_names.get(todo.assigned_by) or todo.assigned_by,
	}

@frappe.whitelist()
def get_task_report_data(filters=None):
	"""
	Get task data for the Tasks Report.
	Filters:
	- user: Filter by allocated_to
	- priority: Filter by priority
	- status: Filter by status
	"""
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)

	if filters is None:
		filters = {}

	# Check permission
	user = frappe.session.user
	from frappe.permissions import AUTOMATIC_ROLES
	todo_roles = frappe.permissions.get_doctype_roles("ToDo")
	todo_roles = set(todo_roles) - set(AUTOMATIC_ROLES)
	user_roles = frappe.get_roles(user)
	has_full_access = any(role in todo_roles for role in user_roles)

	sql_filters = []
	or_filters = []

	if not has_full_access:
		# Return tasks assigned to the user OR tasks assigned by the user
		or_filters = [
			["allocated_to", "=", user],
			["assigned_by", "=", user]
		]

	if filters.get("user"):
		sql_filters.append(["allocated_to", "=", filters.get("user")])

	if filters.get("priority"):
		sql_filters.append(["priority", "=", filters.get("priority")])

	if filters.get("status"):
		sql_filters.append(["status", "=", filters.get("status")])

	todos = frappe.get_all(
		"ToDo",
		filters=sql_filters or None,
		or_filters=or_filters or None,
		fields=["name", "description", "date", "priority", "status", "allocated_to"],
		order_by="creation desc",
		limit=1000,
		ignore_permissions=True,
	)

	# Batch fetch user full names
	user_ids = list(set([t.allocated_to for t in todos if t.allocated_to]))
	user_names = {}
	if user_ids:
		users = frappe.get_all("User", filters={"name": ["in", user_ids]}, fields=["name", "full_name"])
		user_names = {u.name: u.full_name for u in users}

	return [
		{
			"task_id": todo.name,
			"description": todo.description,
			"assigned_to": todo.allocated_to,
			"assigned_to_name": user_names.get(todo.allocated_to) or todo.allocated_to,
			"priority": todo.priority,
			"status": todo.status,
			"due_date": str(todo.date) if todo.date else None,
		}
		for todo in todos
	]

@frappe.whitelist()
def download_task_report_pdf(filters=None):
	"""
	Generate PDF for Tasks Report.
	"""
	import json

	from frappe.utils.pdf import get_pdf

	if isinstance(filters, str):
		filters = json.loads(filters)

	if not filters:
		filters = {}

	# Fetch data
	data = get_task_report_data(filters)

	# Format user name for filter display if possible
	if filters.get("user"):
		user_doc = frappe.db.get_value("User", filters.get("user"), "full_name")
		if user_doc:
			filters["user"] = user_doc

	# Render template
	html_content = frappe.render_template(
		"arijentek_core/templates/reports/task_report.html",
		{"data": data, "filters": filters}
	)

	pdf_binary = get_pdf(html_content, options={
		"page-size": "A4",
		"orientation": "Landscape",
		"margin-top": "10mm",
		"margin-bottom": "10mm",
		"margin-left": "10mm",
		"margin-right": "10mm",
		"encoding": "UTF-8"
	})

	frappe.local.response.filename = f"Tasks_Report_{frappe.utils.today()}.pdf"
	frappe.local.response.filecontent = pdf_binary
	frappe.local.response.type = "pdf"

