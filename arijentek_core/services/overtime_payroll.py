# Copyright (c) 2026, Gemora 360 and contributors
# License: GNU GPL v3. See license.txt

"""Push approved employee overtime into HRMS payroll as Additional Salary earnings.

Attendance records carry ``actual_overtime_duration`` (hours worked beyond the standard
working hours for the day). This module adds a manager-approval gate on top of that raw
figure, then aggregates *approved* overtime per employee for a period and creates a
one-time HRMS **Additional Salary** (Earning) against an ``Overtime Allowance`` salary
component at 1.5x the employee's base hourly rate. The Additional Salary then flows into
the employee's next Salary Slip for that period.

Wired as a monthly scheduler (``zevar_core.hooks``) and exposed on-demand via the
``push_approved_overtime_to_payroll`` whitelist. Mirrors ``commission_payroll.py``.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_months, flt, get_first_day, get_last_day, getdate, today

OT_COMPONENT = "Overtime Allowance"
OT_COMPONENT_ABBR = "OTA"
OT_MULTIPLIER = 1.5
# 22 standard working days x 8 hours per day.
STANDARD_MONTHLY_HOURS = 176


def ensure_overtime_salary_component() -> str:
	"""Create the 'Overtime Allowance' Earning salary component if it doesn't exist."""
	if frappe.db.exists("Salary Component", OT_COMPONENT):
		return OT_COMPONENT
	try:
		frappe.get_doc(
			{
				"doctype": "Salary Component",
				"salary_component": OT_COMPONENT,
				"salary_component_abbr": OT_COMPONENT_ABBR,
				"type": "Earning",
				"is_tax_applicable": 1,
				"description": "Overtime pay pushed from approved Attendance (arijentek_core).",
			}
		).insert(ignore_permissions=True)
		frappe.db.commit()
	except Exception:
		frappe.log_error("Overtime Salary Component creation failed", frappe.get_traceback())
	return OT_COMPONENT


def get_employee_ot_rate(employee: str) -> float:
	"""Resolve the overtime hourly rate for an employee (already including the 1.5x premium).

	Chain:
	  1. ``Employee.custom_ot_hourly_rate`` override (used verbatim if set).
	  2. ``OT_MULTIPLIER x (active Salary Structure Assignment.base / STANDARD_MONTHLY_HOURS)``.

	Returns ``0.0`` when no override exists and the employee has no active, submitted
	Salary Structure Assignment with a base -- the caller should skip such employees.
	"""
	override = flt(frappe.db.get_value("Employee", employee, "custom_ot_hourly_rate"))
	if override > 0:
		return flt(override, 4)

	base = flt(
		frappe.db.get_value(
			"Salary Structure Assignment",
			{"employee": employee, "docstatus": 1, "from_date": ["<=", today()]},
			"base",
			order_by="from_date desc",
		)
	)
	if base <= 0:
		return 0.0
	return flt(OT_MULTIPLIER * base / STANDARD_MONTHLY_HOURS, 4)


def get_pending_ot_records(from_date, to_date, company: str | None = None) -> list[dict]:
	"""Return Attendance records that carry overtime but still need manager approval.

	Filters submitted Attendance where ``actual_overtime_duration > 0`` and that has not
	yet been approved or pushed to payroll.
	"""
	filters = {
		"docstatus": 1,
		"actual_overtime_duration": [">", 0],
		"custom_ot_approved": 0,
		"custom_ot_pushed": 0,
		"attendance_date": ["between", [from_date, to_date]],
	}
	if company:
		filters["company"] = company

	return frappe.get_all(
		"Attendance",
		filters=filters,
		fields=[
			"name as attendance_name",
			"employee",
			"employee_name",
			"attendance_date as date",
			"actual_overtime_duration as ot_hours",
			"shift",
		],
		order_by="attendance_date, employee",
	)


def _previous_month_range():
	today_dt = getdate(today())
	first = get_first_day(add_months(today_dt, -1))
	return first, get_last_day(first)


def _approve(attendance_name: str, hours: float) -> None:
	"""Stamp a single Attendance record as approved (direct DB write; Attendance is submitted)."""
	frappe.db.set_value(
		"Attendance",
		attendance_name,
		{
			"custom_ot_approved": 1,
			"custom_approved_ot_hours": flt(hours, 2),
			"custom_ot_approver": frappe.session.user,
		},
	)


@frappe.whitelist()
def approve_ot_hours(attendance_name: str, approved_hours: float | None = None) -> dict:
	"""Approve overtime for one Attendance record.

	``approved_hours`` defaults to the attendance's ``actual_overtime_duration`` when
	omitted. Permission: System Manager, HR Manager, Accounts Manager, or Store Manager.
	"""
	frappe.only_for(["System Manager", "HR Manager", "Accounts Manager", "Store Manager"])
	if not frappe.db.exists("Attendance", attendance_name):
		frappe.throw(_("Attendance record {0} not found.").format(attendance_name))

	actual = flt(frappe.db.get_value("Attendance", attendance_name, "actual_overtime_duration"))
	hours = flt(approved_hours) if approved_hours not in (None, "") else actual
	if hours <= 0:
		frappe.throw(
			_("Approved OT hours must be greater than zero (actual on record: {0}).").format(actual)
		)

	_approve(attendance_name, hours)
	return {
		"attendance": attendance_name,
		"approved_hours": flt(hours, 2),
		"approver": frappe.session.user,
	}


@frappe.whitelist()
def bulk_approve_ot(attendance_names: list[str]) -> dict:
	"""Approve multiple Attendance OT records at once, using each one's actual duration."""
	frappe.only_for(["System Manager", "HR Manager", "Accounts Manager", "Store Manager"])
	if isinstance(attendance_names, str):
		attendance_names = frappe.parse_json(attendance_names)

	approved, skipped = [], []
	for name in attendance_names or []:
		if not frappe.db.exists("Attendance", name):
			skipped.append({"attendance": name, "reason": "not found"})
			continue
		actual = flt(frappe.db.get_value("Attendance", name, "actual_overtime_duration"))
		if actual <= 0:
			skipped.append({"attendance": name, "reason": "no actual OT hours"})
			continue
		_approve(name, actual)
		approved.append({"attendance": name, "approved_hours": flt(actual, 2)})

	return {"approved": approved, "skipped": skipped, "count": len(approved)}


@frappe.whitelist()
def push_approved_overtime_to_payroll(from_date: str | None = None, to_date: str | None = None) -> dict:
	"""Aggregate approved overtime per employee for [from_date, to_date] (default: previous
	month), create one Additional Salary per employee at 1.5x base hourly rate, and mark the
	source Attendance records as pushed.

	Idempotent: only ``custom_ot_approved=1`` and ``custom_ot_pushed=0`` records are processed;
	once pushed they are skipped.
	"""
	frappe.only_for(["System Manager", "HR Manager", "Accounts Manager", "Store Manager"])
	ensure_overtime_salary_component()

	if not from_date or not to_date:
		from_date, to_date = _previous_month_range()

	records = frappe.get_all(
		"Attendance",
		filters={
			"docstatus": 1,
			"custom_ot_approved": 1,
			"custom_ot_pushed": 0,
			"attendance_date": ["between", [from_date, to_date]],
		},
		fields=["name", "employee", "employee_name", "custom_approved_ot_hours", "company"],
	)
	if not records:
		return {"pushed": 0, "message": f"No approved OT to push between {from_date} and {to_date}."}

	by_employee: dict[str, dict] = {}
	for r in records:
		bucket = by_employee.setdefault(
			r.employee,
			{
				"hours": 0.0,
				"names": [],
				"company": r.company,
				"employee_name": r.employee_name,
			},
		)
		bucket["hours"] += flt(r.custom_approved_ot_hours)
		bucket["names"].append(r.name)

	default_company = frappe.db.get_single_value("Global Defaults", "default_company")
	pushed, skipped = [], []

	for employee, info in by_employee.items():
		hours = flt(info["hours"], 2)
		if hours <= 0:
			continue
		ot_rate = get_employee_ot_rate(employee)
		if ot_rate <= 0:
			skipped.append(
				{
					"employee": employee,
					"employee_name": info["employee_name"],
					"hours": hours,
					"reason": (
						"no OT rate -- set Employee.custom_ot_hourly_rate or an active "
						"Salary Structure Assignment with a base"
					),
				}
			)
			continue
		amount = flt(hours * ot_rate, 2)
		try:
			company = (
				info["company"]
				or frappe.db.get_value("Employee", employee, "company")
				or default_company
			)
			asal = frappe.get_doc(
				{
					"doctype": "Additional Salary",
					"employee": employee,
					"company": company,
					"salary_component": OT_COMPONENT,
					"type": "Earning",
					"amount": amount,
					"payroll_date": to_date,
					"from_date": from_date,
					"to_date": to_date,
					"is_recurring": 0,
					"overwrite_salary_structure_amount": 0,
					"remarks": (
						f"Overtime pay for {hours} hour(s) @ {ot_rate}/hr "
						f"across {len(info['names'])} attendance day(s)."
					),
				}
			)
			asal.flags.ignore_permissions = True
			asal.insert()
			asal.submit()

			for name in info["names"]:
				frappe.db.set_value("Attendance", name, "custom_ot_pushed", 1)
			pushed.append(asal.name)
		except Exception:
			skipped.append({"employee": employee, "reason": "see error log"})
			frappe.log_error(
				title=f"OT to payroll push failed for employee {employee}",
				message=frappe.get_traceback(),
			)

	frappe.db.commit()
	return {
		"pushed": len(pushed),
		"skipped": len(skipped),
		"additional_salaries": pushed,
		"skipped_details": skipped,
		"period": f"{from_date} to {to_date}",
	}
