import sys
from datetime import date

import frappe
from frappe import _
from frappe.utils import formatdate, get_link_to_form, getdate

try:
	from hrms.utils.holiday_list import get_assigned_holiday_list
except ImportError:
	get_assigned_holiday_list = None


def get_holiday_list_for_employee(
	employee: str, raise_exception: bool = True, as_on: date | str | None = None, as_dict: bool = False
) -> str | dict | None:
	"""
	Custom holiday list resolver for Employee Portal / HRMS.
	1. Checks active Holiday List Assignment for employee/company on `as_on`.
	2. Gracefully falls back to nearest active assignment or master defaults if no
	   exact match exists for `as_on` (e.g. when called without target date context),
	   preventing spurious validation blocks.
	"""
	if not employee:
		return None

	parsed_as_on = getdate(as_on) if as_on else getdate()
	holiday_list = None
	company = frappe.db.get_value("Employee", employee, "company")

	# 1. Standard assignment check for Employee on `parsed_as_on`
	if get_assigned_holiday_list:
		holiday_list = get_assigned_holiday_list(employee, parsed_as_on, as_dict)

	# 2. Standard assignment check for Company on `parsed_as_on`
	if not holiday_list and company and get_assigned_holiday_list:
		holiday_list = get_assigned_holiday_list(company, parsed_as_on, as_dict)

	# 3. Bypass / Fallback:
	# If no assignment found for this specific date (e.g., today's date was checked
	# instead of transaction date), search for any submitted assignment for employee or company
	if not holiday_list:
		holiday_list = _get_fallback_assigned_holiday_list(employee, company, parsed_as_on, as_dict)

	# 4. Fallback to Employee's or Company's default holiday list master field
	if not holiday_list:
		emp_hl = frappe.db.get_value("Employee", employee, "holiday_list")
		if emp_hl:
			holiday_list = {"holiday_list": emp_hl, "from_date": parsed_as_on} if as_dict else emp_hl
		elif company:
			comp_hl = frappe.get_cached_value("Company", company, "default_holiday_list")
			if comp_hl:
				holiday_list = {"holiday_list": comp_hl, "from_date": parsed_as_on} if as_dict else comp_hl

	# 5. Throw exception only if no holiday list exists anywhere
	if not holiday_list and raise_exception:
		frappe.throw(
			_(
				"No Holiday List was found for Employee {0} or their company {1} for date {2}. Please assign through {3}"
			).format(
				frappe.bold(employee),
				frappe.bold(company or "None"),
				frappe.bold(formatdate(parsed_as_on)),
				get_link_to_form("Holiday List Assignment", label="Holiday List Assignment"),
			)
		)

	return holiday_list


def _get_fallback_assigned_holiday_list(
	employee: str, company: str | None, as_on: date, as_dict: bool = False
) -> str | dict | None:
	"""
	Fetches the latest submitted Holiday List Assignment for employee or company,
	ignoring the date boundary to avoid breaking valid future/past transactions.
	"""
	if not frappe.db.table_exists("Holiday List Assignment"):
		return None

	HLA = frappe.qb.DocType("Holiday List Assignment")

	# Check employee assignment first, then company
	for assigned_to in [employee, company]:
		if not assigned_to:
			continue

		query = (
			frappe.qb.from_(HLA)
			.select(HLA.holiday_list)
			.where(HLA.assigned_to == assigned_to)
			.where(HLA.docstatus == 1)
			.orderby(HLA.from_date, order=frappe.qb.desc)
			.limit(1)
		)
		if as_dict:
			query = query.select(HLA.from_date)
			res = query.run(as_dict=True)
			if res:
				return res[0]
		else:
			res = query.run()
			if res and res[0][0]:
				return res[0][0]

	return None


def patch_is_holiday():
	"""
	Patches erpnext.setup.doctype.employee.employee.is_holiday so that `as_on=date`
	is correctly forwarded to `get_holiday_list_for_employee`, ensuring holiday
	evaluations are checked against the actual transaction date.
	"""
	try:
		import erpnext.setup.doctype.employee.employee as emp_module

		if getattr(emp_module, "_arijentek_is_holiday_patched", False):
			return

		def arijentek_is_holiday(
			employee, date=None, raise_exception=True, only_non_weekly=False, with_description=False
		):
			if not date:
				date = frappe.utils.today()

			holiday_list = emp_module.get_holiday_list_for_employee(
				employee, raise_exception=raise_exception, as_on=date
			)

			if not holiday_list:
				return (False, []) if with_description else False

			filters = {"parent": holiday_list, "holiday_date": date}
			if only_non_weekly:
				filters["weekly_off"] = False

			holidays = frappe.get_all("Holiday", fields=["description"], filters=filters, pluck="description")

			if with_description:
				return len(holidays) > 0, holidays

			return len(holidays) > 0

		emp_module.is_holiday = arijentek_is_holiday
		emp_module._arijentek_is_holiday_patched = True

		# Sync with attendance_request module if already loaded
		if "hrms.hr.doctype.attendance_request.attendance_request" in sys.modules:
			sys.modules["hrms.hr.doctype.attendance_request.attendance_request"].is_holiday = arijentek_is_holiday
	except Exception as e:
		frappe.log_error(title="Arijentek Core: Failed to patch is_holiday", message=str(e))


# Apply runtime patch on module import
patch_is_holiday()


def on_holiday_list_trash(doc, method=None):
	"""
	Hook executed before Holiday List is deleted.
	1. Auto-purges orphaned Leave Ledger Entries (where parent Leave Application was deleted).
	2. If active Leave Applications exist, raises a user-friendly error naming the Leave Application
	   (instead of leaking internal Leave Ledger Entry IDs to the user).
	"""
	if not frappe.db.table_exists("Leave Ledger Entry"):
		return

	entries = frappe.get_all(
		"Leave Ledger Entry",
		filters={"holiday_list": doc.name},
		fields=["name", "transaction_type", "transaction_name", "employee", "employee_name"],
	)

	active_leave_apps = []

	for entry in entries:
		if entry.transaction_type == "Leave Application":
			if not frappe.db.exists("Leave Application", entry.transaction_name):
				# Orphaned ledger entry: parent application was already deleted. Clean it up safely.
				frappe.db.delete("Leave Ledger Entry", {"name": entry.name})
			else:
				lap = frappe.db.get_value(
					"Leave Application",
					entry.transaction_name,
					["name", "status", "docstatus", "employee", "employee_name"],
					as_dict=True,
				)
				if lap and lap.docstatus != 2:
					active_leave_apps.append(lap)
				elif lap and lap.docstatus == 2:
					# Cancelled leave application whose ledger entry was left behind. Safe to remove.
					frappe.db.delete("Leave Ledger Entry", {"name": entry.name})
		elif entry.transaction_type == "Leave Allocation":
			if not frappe.db.exists("Leave Allocation", entry.transaction_name):
				frappe.db.delete("Leave Ledger Entry", {"name": entry.name})

	if active_leave_apps:
		# Commit the cleanup of orphaned entries so they are permanently cleared
		frappe.db.commit()
		app_list_str = ", ".join(
			f"{a.name} ({a.employee_name or a.employee})" for a in active_leave_apps
		)
		frappe.throw(
			_(
				"Cannot delete Holiday List '{0}' because it is currently linked to Leave Application(s): {1}. "
				"Please cancel or delete these Leave Applications first."
			).format(frappe.bold(doc.name), frappe.bold(app_list_str)),
			title=_("Holiday List In Use"),
		)
