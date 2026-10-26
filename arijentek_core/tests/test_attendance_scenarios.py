import json
import unittest

import frappe
from frappe.utils import add_to_date, get_datetime, getdate

from arijentek_core.api.attendance import (
	_mark_attendance_for_date,
	_process_auto_attendance,
	_process_employee_date,
	calculate_completed_shift_hours,
	calculate_late_early,
	get_active_sessions_for_reconciliation,
	get_today_checkin_status,
	is_auto_attendance_disabled,
	mark_daily_attendance,
	reconcile_active_sessions,
)


class TestAttendanceScenarios(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		site = getattr(frappe.local, "site", None) or "arijentek.local"
		frappe.init(site)
		frappe.connect()
		frappe.db.rollback()
		cls.setup_company()
		cls.setup_shifts()
		cls.setup_employees()

	@classmethod
	def setup_company(cls):
		company = frappe.db.get_value("Company", {}, "name")
		if not company:
			doc = frappe.get_doc({
				"doctype": "Company",
				"company_name": "Zervar HRM",
				"default_currency": "USD",
				"country": "United States"
			})
			doc.insert(ignore_permissions=True)
			cls.company_name = doc.name
		else:
			cls.company_name = company
			# Ensure country field is populated to prevent MandatoryError
			country = frappe.db.get_value("Company", company, "country")
			if not country:
				frappe.db.set_value("Company", company, "country", "United States")

		if not frappe.db.exists("Holiday List", "Standard Holiday List 2026"):
			hl = frappe.get_doc({
				"doctype": "Holiday List",
				"holiday_list_name": "Standard Holiday List 2026",
				"from_date": "2026-01-01",
				"to_date": "2026-12-31",
				"weekly_off": "Sunday"
			})
			hl.insert(ignore_permissions=True)

		frappe.db.set_value("Company", cls.company_name, "default_holiday_list", "Standard Holiday List 2026")

		if not frappe.db.exists("Holiday List Assignment", {"assigned_to": cls.company_name, "docstatus": 1}):
			hla = frappe.get_doc({
				"doctype": "Holiday List Assignment",
				"applicable_for": "Company",
				"assigned_to": cls.company_name,
				"holiday_list": "Standard Holiday List 2026",
				"from_date": "2026-01-01",
				"docstatus": 1
			})
			hla.insert(ignore_permissions=True)


	@classmethod
	def setup_shifts(cls):
		if not frappe.db.exists("Shift Type", "Standard Day Shift"):
			doc = frappe.get_doc({
				"doctype": "Shift Type",
				"name": "Standard Day Shift",
				"shift_name": "Standard Day Shift",
				"start_time": "09:00:00",
				"end_time": "18:00:00",
				"late_entry_grace_period": 15,
				"early_exit_grace_period": 15,
				"enable_auto_attendance": 1,
				"determine_check_in_and_check_out": "Strictly based on Log Type in Employee Checkin"
			})
			doc.insert(ignore_permissions=True)

		if not frappe.db.exists("Shift Type", "Standard Night Shift"):
			doc = frappe.get_doc({
				"doctype": "Shift Type",
				"name": "Standard Night Shift",
				"shift_name": "Standard Night Shift",
				"start_time": "22:00:00",
				"end_time": "07:00:00",
				"late_entry_grace_period": 15,
				"early_exit_grace_period": 15,
				"enable_auto_attendance": 1,
				"determine_check_in_and_check_out": "Strictly based on Log Type in Employee Checkin"
			})
			doc.insert(ignore_permissions=True)

	@classmethod
	def setup_employees(cls):
		cls.employees = {
			"naruto": "naruto@example.com",
			"gaara": "gaara@example.com",
			"sasuke": "sasuke@example.com",
			"hinata": "hinata@example.com",
			"shikamaru": "shikamaru@example.com",
			"kiba": "kiba@example.com",
			"neji": "neji@example.com",
			"rocklee": "rocklee@example.com",
			"choji": "choji@example.com",
			"sakura": "sakura@example.com",
			"kakashi": "kakashi@example.com",
			"tsunade": "tsunade@example.com",
			"jiraiya": "jiraiya@example.com"
		}
		for key, email in cls.employees.items():
			if not frappe.db.exists("User", email):
				user = frappe.get_doc({
					"doctype": "User",
					"email": email,
					"first_name": key.capitalize(),
					"send_welcome_email": 0,
					"roles": [{"role": "Employee"}]
				})
				user.insert(ignore_permissions=True)

			emp_name = frappe.db.get_value("Employee", {"user_id": email}, "name")
			if not emp_name:
				emp = frappe.get_doc({
					"doctype": "Employee",
					"first_name": key.capitalize(),
					"company": cls.company_name,
					"user_id": email,
					"gender": "Male",
					"date_of_birth": "1995-01-01",
					"date_of_joining": "2020-01-01",
					"status": "Active",
					"holiday_list": "Standard Holiday List 2026"
				})
				emp.insert(ignore_permissions=True)
			else:
				frappe.db.set_value("Employee", emp_name, "holiday_list", "Standard Holiday List 2026")
		frappe.db.commit()

	def cleanup_user_records(self, user_email):
		emp_id = frappe.db.get_value("Employee", {"user_id": user_email}, "name")
		if emp_id:
			frappe.db.delete("Employee Checkin", {"employee": emp_id})
			frappe.db.delete("Attendance", {"employee": emp_id})
			frappe.db.delete("Leave Application", {"employee": emp_id})
			frappe.db.commit()

	def test_01_naruto_regular_day_shift(self):
		"""
		Test One: Regular Shift user (naruto@example.com)
		Clock in 09:00 AM on 03-08-2026, Clock Out at 20:00 PM on 03-08-2026.
		Verify clock resets after clock out.
		"""
		user = self.employees["naruto"]
		self.cleanup_user_records(user)
		emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")

		frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": emp_id,
			"log_type": "IN",
			"time": "2026-08-03 09:00:00",
			"device_id": "HRMS Portal",
			"shift": "Standard Day Shift"
		}).insert(ignore_permissions=True)

		frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": emp_id,
			"log_type": "OUT",
			"time": "2026-08-03 20:00:00",
			"device_id": "HRMS Portal",
			"shift": "Standard Day Shift"
		}).insert(ignore_permissions=True)

		frappe.db.commit()

		status = get_today_checkin_status(employee_id=emp_id, for_date="2026-08-03")
		self.assertFalse(status.get("checked_in"), "Clock should reset (checked_in=False) after clock out")
		self.assertEqual(status.get("last_log_type"), "OUT")

	def test_02_gaara_forgot_clock_out(self):
		"""
		Test Two: gaara@example.com clock in 09:00 AM on 03-08-2026, forgot to clock out.
		Scheduler runs for 03-08-2026. Check UI status at 04-08-2026 09:00 AM.
		"""
		user = self.employees["gaara"]
		self.cleanup_user_records(user)
		emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")

		frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": emp_id,
			"log_type": "IN",
			"time": "2026-08-03 09:00:00",
			"device_id": "Manual Entry",
			"shift": "Standard Day Shift"
		}).insert(ignore_permissions=True)

		_mark_attendance_for_date("2026-08-03")

		att = frappe.db.exists("Attendance", {"employee": emp_id, "attendance_date": "2026-08-03"})
		self.assertTrue(att, "Attendance record should be created by scheduler for 03-08-2026")

		status = get_today_checkin_status(employee_id=emp_id, for_date="2026-08-04")
		self.assertFalse(status.get("checked_in"), "Clock UI should reset to checked_in=False for next day")

	def test_03_sasuke_night_shift_normal(self):
		"""
		Test Three: sasuke@example.com Night Shift.
		Clock In 22:00 on 03-08-2026, Clock Out 07:00 on 04-08-2026.
		Verify attendance created and clock resets.
		"""
		user = self.employees["sasuke"]
		self.cleanup_user_records(user)
		emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")

		frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": emp_id,
			"log_type": "IN",
			"time": "2026-08-03 22:00:00",
			"device_id": "HRMS Portal",
			"shift": "Standard Night Shift"
		}).insert(ignore_permissions=True)

		frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": emp_id,
			"log_type": "OUT",
			"time": "2026-08-04 07:00:00",
			"device_id": "HRMS Portal",
			"shift": "Standard Night Shift"
		}).insert(ignore_permissions=True)

		frappe.db.commit()

		status = get_today_checkin_status(employee_id=emp_id, for_date="2026-08-04")
		self.assertFalse(status.get("checked_in"), "Clock UI should reset after night shift clock out")

	def test_04_hinata_night_shift_forgot_clock_out_consecutive(self):
		"""
		Test Four: hinata@example.com Night Shift on 03-08-2026.
		Clocked in 22:00 on 03-08-2026, forgot to clock out.
		Scheduler runs for 03-08-2026.
		Next shift on 04-08-2026, clocks in 22:00 on 04-08-2026 and clocks out 07:00 on 05-08-2026.
		Check no conflict occurs with open clock-in of 03-08-2026.
		"""
		user = self.employees["hinata"]
		self.cleanup_user_records(user)
		emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")

		frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": emp_id,
			"log_type": "IN",
			"time": "2026-08-03 22:00:00",
			"device_id": "HRMS Portal",
			"shift": "Standard Night Shift"
		}).insert(ignore_permissions=True)

		_mark_attendance_for_date("2026-08-03")

		ci2 = frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": emp_id,
			"log_type": "IN",
			"time": "2026-08-04 22:00:00",
			"device_id": "HRMS Portal",
			"shift": "Standard Night Shift"
		}).insert(ignore_permissions=True)

		co2 = frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": emp_id,
			"log_type": "OUT",
			"time": "2026-08-05 07:00:00",
			"device_id": "HRMS Portal",
			"shift": "Standard Night Shift"
		}).insert(ignore_permissions=True)

		frappe.db.commit()

		self.assertEqual(ci2.log_type, "IN")
		self.assertEqual(co2.log_type, "OUT")
		status = get_today_checkin_status(employee_id=emp_id, for_date="2026-08-05")
		self.assertFalse(status.get("checked_in"), "Clock UI should reset cleanly after Shift 2 clock out")

	def test_05_shikamaru_multiple_checkins_lunch_break(self):
		"""
		Test Five: shikamaru@example.com Intra-Day Multiple Checkins / Lunch Break.
		09:00 IN to 13:00 OUT (Break Start), 14:00 IN (Break End) to 18:00 OUT.
		Verify net working hours equal 8.0 hours.
		"""
		user = self.employees["shikamaru"]
		self.cleanup_user_records(user)
		emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")

		l1 = frappe.get_doc({"doctype": "Employee Checkin", "employee": emp_id, "log_type": "IN", "time": "2026-08-03 09:00:00", "device_id": "HRMS Portal"}).insert(ignore_permissions=True)
		l2 = frappe.get_doc({"doctype": "Employee Checkin", "employee": emp_id, "log_type": "OUT", "time": "2026-08-03 13:00:00", "device_id": "HRMS Portal", "device_id": "HRMS Portal Break Start"}).insert(ignore_permissions=True)
		l3 = frappe.get_doc({"doctype": "Employee Checkin", "employee": emp_id, "log_type": "IN", "time": "2026-08-03 14:00:00", "device_id": "HRMS Portal", "device_id": "HRMS Portal Break End"}).insert(ignore_permissions=True)
		l4 = frappe.get_doc({"doctype": "Employee Checkin", "employee": emp_id, "log_type": "OUT", "time": "2026-08-03 18:00:00", "device_id": "HRMS Portal"}).insert(ignore_permissions=True)

		frappe.db.commit()

		logs = [l1, l2, l3, l4]
		total_hours, total_seconds = calculate_completed_shift_hours(logs)
		self.assertEqual(round(total_hours, 1), 8.0, "Total hours across lunch break should equal 8.0")

	def test_06_kiba_pre_scheduler_open_checkin(self):
		"""
		Test Six: kiba@example.com Pre-Scheduler Same-Day Forgotten Clock-Out.
		Clock In at 09:00 on 03-08-2026, no clock out.
		Access UI at 08:30 on 04-08-2026 before scheduler runs.
		"""
		user = self.employees["kiba"]
		self.cleanup_user_records(user)
		emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")

		frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": emp_id,
			"log_type": "IN",
			"time": "2026-08-03 09:00:00",
			"device_id": "HRMS Portal",
			"shift": "Standard Day Shift"
		}).insert(ignore_permissions=True)

		frappe.db.commit()

		status = get_today_checkin_status(employee_id=emp_id, for_date="2026-08-04")
		self.assertFalse(status.get("checked_in"), "Over 23.5 hours since clock in should allow fresh clock in")

	def test_07_neji_leave_and_holiday_override(self):
		"""
		Test Seven: neji@example.com Approved Leave Override.
		Create approved leave application for 03-08-2026. Run scheduler.
		Verify employee is NOT marked absent.
		"""
		user = self.employees["neji"]
		self.cleanup_user_records(user)
		emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")

		if not frappe.db.exists("Leave Type", "Casual Leave"):
			frappe.get_doc({"doctype": "Leave Type", "leave_type_name": "Casual Leave"}).insert(ignore_permissions=True)

		la = frappe.get_doc({
			"doctype": "Leave Application",
			"employee": emp_id,
			"leave_type": "Casual Leave",
			"from_date": "2026-08-03",
			"to_date": "2026-08-03",
			"total_leave_days": 1.0,
			"status": "Approved",
			"docstatus": 1
		})
		la.flags.ignore_validate = True
		la.flags.ignore_mandatory = True
		la.insert(ignore_permissions=True)

		_process_employee_date(emp_id, getdate("2026-08-03"))

		att = frappe.db.exists("Attendance", {"employee": emp_id, "attendance_date": "2026-08-03", "status": "Absent"})
		self.assertFalse(att, "Employee on approved leave should not be marked Absent by auto-attendance")

	def test_08_rocklee_portal_reconciler(self):
		"""
		Test Eight: rocklee@example.com Portal Reconciler Synthetic Session Closure.
		Clock In at 09:00 on 03-08-2026 (no OUT log).
		Reconcile via Portal Reconciler.
		"""
		user = self.employees["rocklee"]
		self.cleanup_user_records(user)
		emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")

		frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": emp_id,
			"log_type": "IN",
			"time": "2026-08-03 09:00:00",
			"device_id": "HRMS Portal",
			"shift": "Standard Day Shift"
		}).insert(ignore_permissions=True)

		rec_data = json.dumps([{
			"employee": emp_id,
			"date": "2026-08-03",
			"status": "Present",
			"checkin_time": "2026-08-03 09:00:00",
			"shift": "Standard Day Shift"
		}])

		reconcile_active_sessions(rec_data)

		out_log = frappe.db.exists("Employee Checkin", {"employee": emp_id, "log_type": "OUT", "device_id": "Portal Reconciler"})
		self.assertTrue(out_log, "Synthetic OUT log should be created by Portal Reconciler")
		att = frappe.db.exists("Attendance", {"employee": emp_id, "attendance_date": "2026-08-03", "status": "Present"})
		self.assertTrue(att, "Attendance should be marked Present by Portal Reconciler")

	def test_09_choji_late_entry_early_exit(self):
		"""
		Test Nine: choji@example.com Late Entry & Early Exit Threshold.
		Shift starts 09:00 (15 min grace), ends 18:00 (15 min grace).
		Clock In 09:25 (Late), Clock Out 17:30 (Early).
		"""
		user = self.employees["choji"]
		self.cleanup_user_records(user)
		emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")

		# Assign Shift to Employee via Shift Assignment
		if not frappe.db.exists("Shift Assignment", {"employee": emp_id, "start_date": "2026-08-03", "docstatus": 1}):
			frappe.get_doc({
				"doctype": "Shift Assignment",
				"employee": emp_id,
				"shift_type": "Standard Day Shift",
				"start_date": "2026-08-03",
				"docstatus": 1
			}).insert(ignore_permissions=True)

		in_dt = get_datetime("2026-08-03 09:25:00")
		out_dt = get_datetime("2026-08-03 17:30:00")

		late_entry, early_exit = calculate_late_early(emp_id, getdate("2026-08-03"), in_dt, out_dt)
		self.assertEqual(late_entry, 1, "Clock in past grace period should set late_entry = 1")
		self.assertEqual(early_exit, 1, "Clock out before shift end minus grace should set early_exit = 1")

	def test_10_make_present_on_clock_out_setting(self):
		"""
		S2: Test 'Make Present while Clock Out' toggle (Enabled vs Disabled).
		- ENABLED: Attendance record is created on Clock Out.
		- DISABLED: Attendance record is created immediately on Clock In.
		"""
		user = self.employees["sakura"]
		self.cleanup_user_records(user)
		emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")

		# Sub-case A: Enabled
		frappe.db.set_single_value("HR Settings", "mark_present_on_clock_out", 1)
		frappe.db.commit()

		frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": emp_id,
			"log_type": "IN",
			"time": "2026-08-03 09:00:00",
			"device_id": "HRMS Portal",
			"shift": "Standard Day Shift"
		}).insert(ignore_permissions=True)

		att_before = frappe.db.exists("Attendance", {"employee": emp_id, "attendance_date": "2026-08-03"})
		self.assertFalse(att_before, "Attendance should NOT be created on clock in when mark_present_on_clock_out is Enabled")

		frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": emp_id,
			"log_type": "OUT",
			"time": "2026-08-03 18:00:00",
			"device_id": "HRMS Portal",
			"shift": "Standard Day Shift"
		}).insert(ignore_permissions=True)

		_process_auto_attendance(emp_id, "2026-08-03")

		att_after = frappe.db.exists("Attendance", {"employee": emp_id, "attendance_date": "2026-08-03", "status": "Present"})
		self.assertTrue(att_after, "Attendance Present should be created on Clock Out when setting is Enabled")

		# Sub-case B: Disabled
		self.cleanup_user_records(user)
		frappe.db.set_single_value("HR Settings", "mark_present_on_clock_out", 0)
		frappe.db.commit()

		frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": emp_id,
			"log_type": "IN",
			"time": "2026-08-04 09:00:00",
			"device_id": "HRMS Portal",
			"shift": "Standard Day Shift"
		}).insert(ignore_permissions=True)

		_process_employee_date(emp_id, getdate("2026-08-04"))
		att_disabled = frappe.db.exists("Attendance", {"employee": emp_id, "attendance_date": "2026-08-04"})
		self.assertTrue(att_disabled, "Attendance record should be created immediately when setting is Disabled")

		# Verify active sessions reconciler detects active clock-in with mark_present_on_clock_out = 0
		from frappe.utils import now_datetime
		frappe.set_user("Administrator")
		self.cleanup_user_records(user)
		now_dt = now_datetime()
		frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": emp_id,
			"log_type": "IN",
			"time": now_dt,
			"device_id": "HRMS Portal",
			"shift": "Standard Day Shift"
		}).insert(ignore_permissions=True)
		_process_auto_attendance(emp_id, now_dt.date())

		sessions = get_active_sessions_for_reconciliation()
		active_emp_ids = [s["employee"] for s in sessions]
		self.assertIn(emp_id, active_emp_ids, "Clocked-in employee must appear in active sessions when mark_present_on_clock_out is 0")

	def test_11_timesheet_automation_setting(self):
		"""
		S4: Test 'Timesheet Automation' setting toggle (Enabled vs Disabled).
		- ENABLED: Clock-in/clock-out triggers Timesheet log creation & submission.
		- DISABLED: Normal attendance processing without Timesheet document creation.
		"""
		user = self.employees["kakashi"]
		self.cleanup_user_records(user)
		emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")

		# Sub-case A: Enabled (1)
		frappe.db.set_single_value("HR Settings", "timesheet_with_clockin", 1)
		frappe.db.commit()

		val_enabled = frappe.db.get_single_value("HR Settings", "timesheet_with_clockin")
		self.assertEqual(val_enabled, 1, "Timesheet automation should be Enabled")

		# Sub-case B: Disabled (0)
		frappe.db.set_single_value("HR Settings", "timesheet_with_clockin", 0)
		frappe.db.commit()

		val_disabled = frappe.db.get_single_value("HR Settings", "timesheet_with_clockin")
		self.assertEqual(val_disabled, 0, "Timesheet automation should be Disabled")

	def test_12_night_login_without_shift(self):
		"""
		S5: Test Night Login at 18:00 (06:00 PM) WITHOUT Shift Assignment.
		Verify checkin and checkout process correctly without throwing missing shift error.
		"""
		user = self.employees["tsunade"]
		self.cleanup_user_records(user)
		emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")

		ci = frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": emp_id,
			"log_type": "IN",
			"time": "2026-08-03 18:00:00",
			"device_id": "HRMS Portal"
		}).insert(ignore_permissions=True)

		co = frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": emp_id,
			"log_type": "OUT",
			"time": "2026-08-04 02:00:00",
			"device_id": "HRMS Portal"
		}).insert(ignore_permissions=True)

		frappe.db.commit()

		self.assertEqual(ci.log_type, "IN")
		self.assertEqual(co.log_type, "OUT")

		_process_employee_date(emp_id, getdate("2026-08-03"))
		status = get_today_checkin_status(employee_id=emp_id, for_date="2026-08-04")
		self.assertFalse(status.get("checked_in"), "UI status should reset after night checkout without shift")

	def test_13_overnight_night_shift_consecutive(self):
		"""
		S6: Test Night Shift (22:00 to 07:00 next morning) connecting one night to another.
		Night 1: Clock In 22:00 (03-08-2026), Clock Out 07:00 (04-08-2026).
		Night 2: Clock In 22:00 (04-08-2026), Clock Out 07:00 (05-08-2026).
		"""
		user = self.employees["jiraiya"]
		self.cleanup_user_records(user)
		emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")

		# Night 1
		frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": emp_id,
			"log_type": "IN",
			"time": "2026-08-03 22:00:00",
			"device_id": "HRMS Portal",
			"shift": "Standard Night Shift"
		}).insert(ignore_permissions=True)

		frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": emp_id,
			"log_type": "OUT",
			"time": "2026-08-04 07:00:00",
			"device_id": "HRMS Portal",
			"shift": "Standard Night Shift"
		}).insert(ignore_permissions=True)

		# Night 2
		frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": emp_id,
			"log_type": "IN",
			"time": "2026-08-04 22:00:00",
			"device_id": "HRMS Portal",
			"shift": "Standard Night Shift"
		}).insert(ignore_permissions=True)

		frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": emp_id,
			"log_type": "OUT",
			"time": "2026-08-05 07:00:00",
			"device_id": "HRMS Portal",
			"shift": "Standard Night Shift"
		}).insert(ignore_permissions=True)

		frappe.db.commit()

		status_day1 = get_today_checkin_status(employee_id=emp_id, for_date="2026-08-04")
		status_day2 = get_today_checkin_status(employee_id=emp_id, for_date="2026-08-05")
		self.assertFalse(status_day1.get("checked_in"), "Night 1 checkout should reset status")
		self.assertFalse(status_day2.get("checked_in"), "Night 2 checkout should reset status")

	def test_14_disable_auto_attendance_setting(self):
		"""
		S7: Test 'Disable auto attendance' setting toggle (Enabled vs Disabled).
		- ENABLED (disable_auto_attendance = 1):
		  - Check-in logs have skip_auto_attendance = 1
		  - _process_auto_attendance does NOT create/update Attendance records
		  - _process_employee_date does NOT create/update Attendance records
		- DISABLED (disable_auto_attendance = 0):
		  - Check-in logs process normally and create Attendance Present record
		"""
		from arijentek_core.api.hr_settings import update_disable_auto_attendance

		frappe.set_user("Administrator")
		user = self.employees["sakura"]
		self.cleanup_user_records(user)
		emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")

		# Sub-case A: Disable Auto Attendance Enabled (1)
		update_disable_auto_attendance(1)
		self.assertTrue(is_auto_attendance_disabled())

		test_date = "2026-08-10"
		frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": emp_id,
			"log_type": "IN",
			"time": f"{test_date} 09:00:00",
			"device_id": "HRMS Portal",
			"shift": "Standard Day Shift"
		}).insert(ignore_permissions=True)

		frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": emp_id,
			"log_type": "OUT",
			"time": f"{test_date} 18:00:00",
			"device_id": "HRMS Portal",
			"shift": "Standard Day Shift"
		}).insert(ignore_permissions=True)

		frappe.db.commit()

		# Explicitly invoke auto-attendance processing
		_process_auto_attendance(emp_id, test_date)

		att_exists = frappe.db.exists("Attendance", {"employee": emp_id, "attendance_date": test_date})
		self.assertFalse(att_exists, "Attendance record must NOT be created when disable_auto_attendance is 1")

		_process_employee_date(emp_id, getdate(test_date))
		att_exists_after_cron = frappe.db.exists("Attendance", {"employee": emp_id, "attendance_date": test_date})
		self.assertFalse(att_exists_after_cron, "Daily attendance processor must NOT create Attendance when disable_auto_attendance is 1")

		# Sub-case B: Disable Auto Attendance Disabled (0) -> Auto attendance should work
		self.cleanup_user_records(user)
		update_disable_auto_attendance(0)
		self.assertFalse(is_auto_attendance_disabled())

		test_date_enabled = "2026-08-11"
		frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": emp_id,
			"log_type": "IN",
			"time": f"{test_date_enabled} 09:00:00",
			"device_id": "HRMS Portal",
			"shift": "Standard Day Shift"
		}).insert(ignore_permissions=True)

		frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": emp_id,
			"log_type": "OUT",
			"time": f"{test_date_enabled} 18:00:00",
			"device_id": "HRMS Portal",
			"shift": "Standard Day Shift"
		}).insert(ignore_permissions=True)

		frappe.db.commit()

		_process_auto_attendance(emp_id, test_date_enabled)

		att_created = frappe.db.exists("Attendance", {"employee": emp_id, "attendance_date": test_date_enabled, "status": "Present"})
		self.assertTrue(att_created, "Attendance Present record MUST be created when disable_auto_attendance is 0")
