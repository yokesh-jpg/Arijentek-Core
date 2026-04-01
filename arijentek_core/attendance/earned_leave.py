"""
Earned Leave Sync Module
========================

Monthly scheduled task that syncs earned leave allocations for all active
employees. Ensures the Leave Allocation for "Earned Leave" reflects the
actual working days accrual (1 day per 20 working days).

This fixes Bug 4: Earned leave not correctly updated.
"""

import frappe
from frappe.utils import getdate, today, flt, nowdate


def sync_earned_leave_allocations():
	"""Sync earned leave allocations for all active employees.

	Called monthly by scheduler_events in hooks.py.
	Can also be called manually:
	  bench execute arijentek_core.attendance.earned_leave.sync_earned_leave_allocations
	"""
	if not frappe.db.exists("Leave Type", "Earned Leave"):
		return

	employees = frappe.get_all(
		"Employee",
		filters={"status": "Active"},
		fields=["name", "date_of_joining"],
	)

	updated = 0
	for emp in employees:
		try:
			if _sync_employee_earned_leave(emp.name, emp.date_of_joining):
				updated += 1
		except Exception:
			frappe.log_error(
				frappe.get_traceback(),
				f"Earned Leave Sync Error for {emp.name}",
			)

	frappe.db.commit()
	frappe.logger().info(f"Earned Leave Sync: Updated {updated}/{len(employees)} employees")


def _sync_employee_earned_leave(employee, date_of_joining):
	"""Calculate and sync earned leave for a single employee.

	Returns True if allocation was created or updated.
	"""
	if not date_of_joining:
		return False

	today_d = getdate(today())
	doj = getdate(date_of_joining)
	if doj > today_d:
		return False

	year = today_d.year

	# Calculate earned days: 1 per 20 working days
	# Count Present as 1.0, Half Day as 0.5
	present_result = frappe.db.sql(
		"""
		SELECT COUNT(DISTINCT attendance_date) as days
		FROM `tabAttendance`
		WHERE employee = %s
		AND docstatus = 1
		AND attendance_date BETWEEN %s AND %s
		AND status = 'Present'
		""",
		(employee, doj, today_d),
		as_dict=True,
	)
	present_days = flt(present_result[0].days) if present_result else 0

	half_day_result = frappe.db.sql(
		"""
		SELECT COUNT(DISTINCT attendance_date) as days
		FROM `tabAttendance`
		WHERE employee = %s
		AND docstatus = 1
		AND attendance_date BETWEEN %s AND %s
		AND status = 'Half Day'
		""",
		(employee, doj, today_d),
		as_dict=True,
	)
	half_days = flt(half_day_result[0].days) if half_day_result else 0

	working_days = present_days + (half_days * 0.5)
	earned_days = int(working_days // 20)

	if earned_days <= 0:
		return False

	# Find or create Leave Allocation for this year
	alloc_name = frappe.db.get_value(
		"Leave Allocation",
		{
			"employee": employee,
			"leave_type": "Earned Leave",
			"from_date": f"{year}-01-01",
			"to_date": f"{year}-12-31",
			"docstatus": 1,
		},
		"name",
	)

	if alloc_name:
		# Update existing allocation
		current_alloc = frappe.db.get_value(
			"Leave Allocation", alloc_name, "new_leaves_allocated"
		)
		if flt(current_alloc) != earned_days:
			try:
				alloc_doc = frappe.get_doc("Leave Allocation", alloc_name)
				alloc_doc.flags.ignore_permissions = True
				alloc_doc.cancel()

				new_alloc = frappe.new_doc("Leave Allocation")
				new_alloc.update(
					{
						"employee": employee,
						"leave_type": "Earned Leave",
						"from_date": f"{year}-01-01",
						"to_date": f"{year}-12-31",
						"new_leaves_allocated": earned_days,
					}
				)
				new_alloc.insert(ignore_permissions=True)
				new_alloc.flags.ignore_permissions = True
				new_alloc.submit()
				return True
			except Exception:
				frappe.log_error(
					frappe.get_traceback(),
					f"Earned Leave Allocation Update Error for {employee}",
				)
				return False
	else:
		# Check for any draft allocation
		draft_alloc = frappe.db.get_value(
			"Leave Allocation",
			{
				"employee": employee,
				"leave_type": "Earned Leave",
				"from_date": f"{year}-01-01",
				"to_date": f"{year}-12-31",
				"docstatus": 0,
			},
			"name",
		)
		if draft_alloc:
			frappe.delete_doc("Leave Allocation", draft_alloc, ignore_permissions=True)

		# Create new allocation
		try:
			alloc = frappe.new_doc("Leave Allocation")
			alloc.update(
				{
					"employee": employee,
					"leave_type": "Earned Leave",
					"from_date": f"{year}-01-01",
					"to_date": f"{year}-12-31",
					"new_leaves_allocated": earned_days,
				}
			)
			alloc.insert(ignore_permissions=True)
			alloc.flags.ignore_permissions = True
			alloc.submit()
			return True
		except Exception:
			frappe.log_error(
				frappe.get_traceback(),
				f"Earned Leave Allocation Create Error for {employee}",
			)
			return False

	return False
