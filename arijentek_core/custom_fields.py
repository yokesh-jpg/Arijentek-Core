import frappe
from frappe.custom.doctype.custom_field.custom_field import (
	create_custom_fields as frappe_create_custom_fields,
)


def create_custom_fields(app=None):
	"""Centralized custom fields definition for Employee Portal and HRMS.

	Executed on `after_install` and `after_migrate` hooks.
	"""
	custom_fields = {
		"HR Settings": [
			{
				"fieldname": "timesheet_with_clockin",
				"label": "Timesheet with clockin",
				"fieldtype": "Check",
				"insert_after": "auto_attendance_settings_section",
				"default": "0",
				"description": "Automatically create or update draft Timesheet when employees clock in.",
			},
			{
				"fieldname": "mark_present_on_clock_out",
				"label": "Make Present while Clock Out",
				"fieldtype": "Check",
				"insert_after": "timesheet_with_clockin",
				"default": "0",
				"description": "Automatically mark attendance status as Present when employees clock out.",
			},
			{
				"fieldname": "disable_auto_attendance",
				"label": "Disable Auto Attendance",
				"fieldtype": "Check",
				"insert_after": "mark_present_on_clock_out",
				"default": "0",
				"description": "Disable automatic attendance creation from clock-in/out logs.",
			},
		],
		"Attendance": [
			{
				"fieldname": "custom_ot_approved",
				"label": "OT Approved",
				"fieldtype": "Check",
				"insert_after": "actual_overtime_duration",
				"default": "0",
				"description": "Checked once a manager approves this overtime for payroll push.",
			},
			{
				"fieldname": "custom_approved_ot_hours",
				"label": "Approved OT Hours",
				"fieldtype": "Float",
				"insert_after": "custom_ot_approved",
				"default": "0",
				"description": "Overtime hours approved by a manager (defaults to actual_overtime_duration).",
			},
			{
				"fieldname": "custom_ot_approver",
				"label": "OT Approver",
				"fieldtype": "Link",
				"options": "User",
				"insert_after": "custom_approved_ot_hours",
				"description": "Manager who approved this overtime.",
				"read_only": 1,
			},
			{
				"fieldname": "custom_ot_pushed",
				"label": "OT Pushed to Payroll",
				"fieldtype": "Check",
				"insert_after": "custom_ot_approver",
				"default": "0",
				"description": "Checked once this overtime has been pushed to payroll as an Additional Salary.",
				"read_only": 1,
			},
		],
		"Employee": [
			{
				"fieldname": "custom_commission_rate",
				"label": "Commission Rate (%)",
				"fieldtype": "Float",
				"insert_after": "employment_type",
			},
			{
				"fieldname": "custom_sales_level",
				"label": "Sales Level",
				"fieldtype": "Data",
				"insert_after": "custom_commission_rate",
			},
			{
				"fieldname": "custom_discount_permission",
				"label": "Max Discount (%)",
				"fieldtype": "Float",
				"insert_after": "custom_sales_level",
			},
			{
				"fieldname": "custom_ytd_sales",
				"label": "YTD Sales",
				"fieldtype": "Currency",
				"insert_after": "custom_discount_permission",
			},
			{
				"fieldname": "custom_sales_goal",
				"label": "Sales Goal",
				"fieldtype": "Currency",
				"insert_after": "custom_ytd_sales",
			},
			{
				"fieldname": "custom_initials",
				"label": "Initials",
				"fieldtype": "Data",
				"insert_after": "custom_sales_goal",
			},
			{
				"fieldname": "custom_is_manager",
				"label": "Is Manager",
				"fieldtype": "Check",
				"insert_after": "custom_initials",
			},
		],
		"Role Profile": [
			{
				"fieldname": "custom_is_custom_persona",
				"label": "Is Custom Persona (Team Hub)",
				"fieldtype": "Check",
				"insert_after": "roles",
				"default": "0",
				"read_only": 1,
			},
			{
				"fieldname": "custom_persona_description",
				"label": "Persona Description",
				"fieldtype": "Small Text",
				"insert_after": "custom_is_custom_persona",
			},
			{
				"fieldname": "custom_landing_route",
				"label": "Landing Route",
				"fieldtype": "Data",
				"insert_after": "custom_persona_description",
			},
		],
	}

	for doctype, fields in custom_fields.items():
		if not frappe.db.exists("DocType", doctype):
			continue
		try:
			frappe_create_custom_fields({doctype: fields}, ignore_validate=True, update=True)
		except Exception as e:
			frappe.log_error(f"Error creating custom fields for {doctype}: {e}", "Arijentek Custom Fields Setup")


def execute():
	create_custom_fields()
	frappe.db.commit()


# Alias referenced by hooks.py
setup_custom_fields = create_custom_fields
