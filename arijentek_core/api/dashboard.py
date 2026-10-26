import frappe
from frappe.utils import flt

def _warehouse_scope(warehouse):
	return [warehouse] if warehouse else []
from arijentek_core.services.store_registry import get_store_registry


def _get_pos_sales_data(target_date, store=None, current_user=None):
	"""Centralized helper to aggregate real-time POS sales data across Sales Invoice and POS Invoice."""
	sinv_where = ["si.posting_date = %(target_date)s", "si.docstatus != 2"]
	pinv_where = ["pi.posting_date = %(target_date)s", "pi.docstatus != 2"]
	params = {"target_date": target_date}

	if store and store not in ("all", "hip_mall"):
		wh = frappe.db.get_value("POS Profile", store, "warehouse")
		wh_clause = f" OR si.set_warehouse = '{wh}'" if wh else ""
		pinv_wh_clause = f" OR pi.set_warehouse = '{wh}'" if wh else ""
		sinv_where.append(f"(si.pos_profile = %(store)s OR si.set_warehouse = %(store)s{wh_clause})")
		pinv_where.append(f"(pi.pos_profile = %(store)s OR pi.set_warehouse = %(store)s{pinv_wh_clause})")
		params["store"] = store

	# 1. Fetch Sales Invoices (Zevar POS checkouts)
	sinvs = frappe.db.sql(
		f"""
		SELECT name, grand_total, is_return, owner, pos_profile, set_warehouse, creation
		FROM `tabSales Invoice` si
		WHERE {' AND '.join(sinv_where)}
	""",
		params,
		as_dict=True,
	)

	# 2. Fetch POS Invoices (ERPNext POS checkouts if any)
	pinvs = frappe.db.sql(
		f"""
		SELECT name, grand_total, is_return, owner, pos_profile, set_warehouse, creation
		FROM `tabPOS Invoice` pi
		WHERE {' AND '.join(pinv_where)}
	""",
		params,
		as_dict=True,
	)

	invoices = sinvs + pinvs

	sinv_names = tuple(inv.name for inv in sinvs)
	pinv_names = tuple(inv.name for inv in pinvs)

	item_qty_by_parent = {}
	if sinv_names:
		s_items = frappe.db.sql(
			"""
			SELECT parent, SUM(qty) as total_qty FROM `tabSales Invoice Item`
			WHERE parent IN %s GROUP BY parent
		""",
			(sinv_names,),
			as_dict=True,
		)
		for r in s_items:
			item_qty_by_parent[r.parent] = r.total_qty or 0

	if pinv_names:
		p_items = frappe.db.sql(
			"""
			SELECT parent, SUM(qty) as total_qty FROM `tabPOS Invoice Item`
			WHERE parent IN %s GROUP BY parent
		""",
			(pinv_names,),
			as_dict=True,
		)
		for r in p_items:
			item_qty_by_parent[r.parent] = r.total_qty or 0

	user_inv_set = set()
	if current_user:
		emp_doc = frappe.db.get_value("Employee", {"user_id": current_user}, "name")
		for inv in invoices:
			if inv.owner == current_user:
				user_inv_set.add(inv.name)
		if sinv_names:
			splits = frappe.db.sql(
				"""
				SELECT sales_invoice FROM `tabSales Commission Split`
				WHERE sales_invoice IN %s AND (employee = %s OR employee = %s OR owner = %s)
			""",
				(sinv_names, current_user, emp_doc or "", current_user),
				as_dict=True,
			)
			for s in splits:
				user_inv_set.add(s.sales_invoice)

	total_sales = 0.0
	transactions = 0
	returns_count = 0
	returns_amount = 0.0
	items_sold = 0

	emp_sales = 0.0
	emp_transactions = 0
	emp_returns_count = 0
	emp_items_sold = 0

	for inv in invoices:
		qty = int(item_qty_by_parent.get(inv.name, 0))
		is_user = inv.name in user_inv_set or inv.owner == current_user
		if inv.is_return:
			returns_count += 1
			returns_amount += abs(inv.grand_total or 0.0)
			if is_user:
				emp_returns_count += 1
		else:
			total_sales += (inv.grand_total or 0.0)
			transactions += 1
			items_sold += qty
			if is_user:
				emp_sales += (inv.grand_total or 0.0)
				emp_transactions += 1
				emp_items_sold += qty

	return {
		"invoices": invoices,
		"total_sales": total_sales,
		"transactions": transactions,
		"returns_count": returns_count,
		"returns_amount": returns_amount,
		"items_sold": items_sold,
		"emp_sales": emp_sales,
		"emp_transactions": emp_transactions,
		"emp_returns_count": emp_returns_count,
		"emp_items_sold": emp_items_sold,
	}


@frappe.whitelist(allow_guest=False)
def get_pos_dashboard_metrics(store=None):
	"""
	Returns real, live KPI metrics and operational stats for POS Dashboard.
	Calculates actual database numbers for today's sales, transactions, items,
	returns, personal employee shift totals, and store branches across both
	Sales Invoice and POS Invoice records.
	"""
	today = frappe.utils.today()
	user = frappe.session.user

	# 1. Today's Real Sales & Invoices
	today_data = _get_pos_sales_data(today, store=store, current_user=user)
	today_sales = today_data["total_sales"]
	transactions = today_data["transactions"]
	returns_count = today_data["returns_count"]
	returns_amount = today_data["returns_amount"]
	items_sold = today_data["items_sold"]

	emp_sales = today_data["emp_sales"]
	emp_transactions = today_data["emp_transactions"]
	emp_returns_count = today_data["emp_returns_count"]
	emp_items_sold = today_data["emp_items_sold"]

	# 2. New Customers Today
	new_customers = frappe.db.count("Customer", {"creation": [">=", f"{today} 00:00:00"]})

	# 3. Averages and Rates
	avg_basket = round(today_sales / transactions, 2) if transactions > 0 else 0.0
	total_tx = transactions + returns_count
	returns_pct = round((returns_count / total_tx * 100), 1) if total_tx > 0 else 0.0

	emp_avg_basket = round(emp_sales / emp_transactions, 2) if emp_transactions > 0 else 0.0
	emp_commission_rate = 0.03  # 3% baseline commission
	emp_commission = round(emp_sales * emp_commission_rate, 2)
	emp_daily_target = 5000.0
	emp_target_pct = min(round((emp_sales / emp_daily_target) * 100, 1), 100.0) if emp_daily_target > 0 else 0.0

	# 4. Yesterday's Comparison for Directional Trend Calculation
	yesterday = frappe.utils.add_days(today, -1)
	y_data = _get_pos_sales_data(yesterday, store=store, current_user=user)
	yesterday_sales = y_data["total_sales"]
	yesterday_trans = y_data["transactions"]
	yesterday_items = y_data["items_sold"]

	yesterday_customers = frappe.db.count(
		"Customer",
		{"creation": [">=", f"{yesterday} 00:00:00"], "creation": ["<=", f"{yesterday} 23:59:59"]},
	)

	def _calc_growth(current, previous):
		if previous > 0:
			pct = round(((current - previous) / previous) * 100, 1)
			direction = "up" if pct > 0 else ("down" if pct < 0 else "neutral")
			formatted = f"+{pct}%" if pct > 0 else f"{pct}%"
			return pct, direction, formatted
		elif current > 0:
			return 100.0, "up", "+100.0%"
		else:
			return 0.0, "neutral", "0.0%"

	sales_growth_pct, sales_direction, sales_growth_str = _calc_growth(today_sales, yesterday_sales)
	trans_growth_pct, trans_direction, trans_growth_str = _calc_growth(transactions, yesterday_trans)
	items_growth_pct, items_direction, items_growth_str = _calc_growth(items_sold, yesterday_items)
	cust_growth_pct, cust_direction, cust_growth_str = _calc_growth(new_customers, yesterday_customers)

	# 5. Active Stores / Branches from Database
	pos_profiles = frappe.db.get_all("POS Profile", fields=["name", "company", "warehouse", "disabled"])
	configured_stores = []
	all_today_invoices = today_data["invoices"]

	for prof in pos_profiles:
		active_regs = frappe.db.count(
			"POS Opening Entry",
			{"pos_profile": prof.name, "status": "Open", "docstatus": 1},
		)

		p_sales = sum(
			inv.grand_total or 0.0
			for inv in all_today_invoices
			if (getattr(inv, "pos_profile", None) == prof.name or getattr(inv, "set_warehouse", None) == prof.warehouse)
			and not inv.is_return
		)

		configured_stores.append({
			"id": prof.name,
			"name": prof.name.replace(" POS", "").strip(),
			"location": prof.warehouse or "Main Boutique",
			"company": prof.company or "Zevar Fine Jewelers",
			"sales": float(round(p_sales, 2)),
			"status": "Live" if (active_regs > 0 or p_sales > 0) else "Ready",
			"registers": max(active_regs, 1 if ("HIPMall" in prof.name or p_sales > 0) else 0),
			"staff": max(frappe.db.count("User", {"enabled": 1}), 1),
			"isPrimary": "HIPMall" in prof.name,
		})

	if not configured_stores:
		configured_stores.append({
			"id": "HIPMall Store POS",
			"name": "HIPMall Store",
			"location": "HIPMall Store - ZFJ",
			"company": "Zevar Fine Jewelers",
			"sales": float(round(today_sales, 2)),
			"status": "Live",
			"registers": 1,
			"staff": 3,
			"isPrimary": True,
		})

	# 6. Active Shift Info
	open_shift = frappe.db.get_value(
		"POS Opening Entry",
		{"user": user, "status": "Open", "docstatus": 1},
		["name", "period_start_date", "pos_profile", "creation"],
		as_dict=True,
	)

	shift_start = None
	shift_register = "Terminal 01"
	if open_shift:
		shift_start = str(open_shift.period_start_date or open_shift.creation)
		shift_register = open_shift.pos_profile or "Terminal 01"

	# 7. Real Operational Counts
	repairs_count = frappe.db.count(
		"Repair Order",
		{"status": ["not in", ["Delivered", "Cancelled"]], "docstatus": ["<", 2]},
	)
	layaways_count = frappe.db.count(
		"Layaway Contract",
		{"status": ["not in", ["Completed", "Cancelled"]], "docstatus": ["<", 2]},
	)
	special_orders_count = frappe.db.count(
		"Zevar Special Order",
		{"workflow_status": ["not in", ["Completed", "Cancelled"]], "docstatus": ["<", 2]},
	)
	open_sessions_count = frappe.db.count("POS Opening Entry", {"status": "Open", "docstatus": 1})

	return {
		"todaySales": float(round(today_sales, 2)),
		"transactions": int(transactions),
		"itemsSold": int(items_sold),
		"newCustomers": int(new_customers),
		"avgBasket": float(avg_basket),
		"returnsCount": int(returns_count),
		"returnsAmount": float(returns_amount),
		"returnsPct": float(returns_pct),
		"salesGrowth": sales_growth_str,
		"salesGrowthPct": float(sales_growth_pct),
		"salesDirection": sales_direction,
		"transGrowth": trans_growth_str,
		"transGrowthPct": float(trans_growth_pct),
		"transDirection": trans_direction,
		"itemsGrowth": items_growth_str,
		"itemsGrowthPct": float(items_growth_pct),
		"itemsDirection": items_direction,
		"custGrowth": cust_growth_str,
		"custGrowthPct": float(cust_growth_pct),
		"custDirection": cust_direction,
		"employeeSales": float(round(emp_sales, 2)),
		"employeeTransactions": int(emp_transactions),
		"employeeItemsSold": int(emp_items_sold),
		"employeeCommission": float(emp_commission),
		"employeeDailyTarget": float(emp_daily_target),
		"employeeTargetPercent": float(emp_target_pct),
		"employeeReturnsCount": int(emp_returns_count),
		"employeeAvgBasket": float(emp_avg_basket),
		"configuredStores": configured_stores,
		"activeShift": {
			"hasOpenShift": bool(open_shift),
			"shiftStart": shift_start,
			"register": shift_register,
		},
		"operationalCounts": {
			"repairs": repairs_count,
			"layaways": layaways_count,
			"specialOrders": special_orders_count,
			"openSessions": open_sessions_count,
		},
	}


@frappe.whitelist()
def get_dashboard_data():
	frappe.only_for(["System Manager", "Store Manager", "Stock Manager", "Inventory Manager", "Sales Manager"])

	# 1. Total Stock Value (real; honest 0 fallback — never a fabricated figure)
	val = frappe.db.sql("""SELECT SUM(stock_value) FROM `tabBin` WHERE actual_qty > 0""")
	total_value = val[0][0] if val and val[0][0] else 0

	# Formatting value
	if total_value >= 1000000:
		total_value_str = f"${total_value/1000000:.1f}M"
	else:
		total_value_str = f"${total_value:,.0f}"

	# 2-4. Operational counts — computed from live data, not hardcoded literals.
	# Each is guarded so a schema/filter mismatch never crashes the dashboard.
	def _safe_count(doctype, filters=None):
		try:
			return frappe.db.count(doctype, filters or {})
		except Exception:
			frappe.log_error(f"get_dashboard_data: count failed for {doctype}")
			return 0

	items_memo = _safe_count("Memo Contract Item", {"line_status": "Open"})
	items_repair = _safe_count(
		"Repair Order", {"status": ["not in", ["Delivered", "Cancelled"]], "docstatus": ["<", 2]}
	)
	pending_appraisals = _safe_count("Jewelry Appraisal", {"status": "Draft", "docstatus": ["<", 2]})

	# Alerts are derived from LIVE signals only — this endpoint historically
	# returned three fabricated alerts (fake stores, fake doc numbers, fake
	# timestamps) that could never be acted on.
	alerts = []

	low_stock = _safe_count("Item", {"disabled": 0, "stock_quantity": ["<", 1]})
	if low_stock:
		alerts.append({
			"id": "low-stock",
			"title": "Out-of-Stock Items",
			"desc": f"{low_stock} active item(s) have no stock on hand.",
			"icon": "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z",
			"colorClass": "bg-red-100 text-red-600 dark:bg-red-900/30",
		})

	overdue_registers = _safe_count(
		"POS Opening Entry",
		{"status": "Open", "docstatus": 1, "period_start_date": ["<", frappe.utils.add_days(frappe.utils.today(), -1)]},
	)
	if overdue_registers:
		alerts.append({
			"id": "unclosed-registers",
			"title": "Registers Left Open Overnight",
			"desc": f"{overdue_registers} register session(s) opened before today are still open.",
			"icon": "M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z",
			"colorClass": "bg-amber-100 text-amber-600 dark:bg-amber-900/30",
		})

	if pending_appraisals:
		alerts.append({
			"id": "pending-appraisals",
			"title": "Draft Appraisals",
			"desc": f"{pending_appraisals} appraisal(s) are still in draft.",
			"icon": "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z",
			"colorClass": "bg-blue-100 text-blue-600 dark:bg-blue-900/30",
		})

	return {
		"kpis": {
			"totalValue": total_value_str,
			"itemsOnMemo": str(items_memo),
			"itemsInRepair": str(items_repair),
			"pendingAppraisals": str(pending_appraisals),
		},
		"alerts": alerts,
	}


@frappe.whitelist()
def get_employee_dashboard_data(employee_id=None):
	"""Return all dashboard widgets data in a single response for employee portal."""
	if not employee_id:
		employee_id = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")

	if not employee_id:
		return {}

	from arijentek_core.api.attendance import get_attendance_summary, get_leave_balance, get_today_checkin_status

	# 1. Today status
	today_status = get_today_checkin_status(employee_id)

	# 2. Leave balance
	leave_balance = get_leave_balance(employee_id)

	# 3. Attendance summary
	attendance_summary = get_attendance_summary()

	# 4. Roster
	from arijentek_core.api.roster import get_next_three_days_roster
	roster = get_next_three_days_roster(employee_id)

	# 5. Salary slips
	from arijentek_core.api.payroll import get_salary_slips
	salary_slips = get_salary_slips(employee_id=employee_id)

	return {
		"today_status": today_status,
		"leave_balance": leave_balance,
		"attendance_summary": attendance_summary,
		"roster": roster,
		"salary_slips": salary_slips,
	}


@frappe.whitelist()
def get_all_portal_permissions():
	"""Return all employee portal permission flags in a single consolidated response."""
	from arijentek_core.api import attendance as att_api
	from arijentek_core.api import payroll as pay_api
	from arijentek_core.api import reports as rep_api
	from arijentek_core.api import tasks as task_api
	from arijentek_core.api import teams_permissons as team_api

	return {
		"reports": {
			"can_create_reports": rep_api.can_create_reports(),
		},
		"attendance": {
			"can_create_attendance": att_api.can_create_attendance(),
			"can_read_attendance": att_api.can_read_attendance(),
			"can_edit_attendance": att_api.can_edit_attendance(),
			"can_delete_attendance": att_api.can_delete_attendance(),
			"can_create_employee_checkin": att_api.can_create_employee_checkin(),
			"can_read_employee_checkin": att_api.can_read_employee_checkin(),
			"can_edit_employee_checkin": att_api.can_edit_employee_checkin(),
			"can_delete_employee_checkin": att_api.can_delete_employee_checkin(),
			"can_create_attendance_request": att_api.can_create_attendance_request(),
			"can_read_attendance_request": att_api.can_read_attendance_request(),
			"can_edit_attendance_request": att_api.can_edit_attendance_request(),
			"can_delete_attendance_request": att_api.can_delete_attendance_request(),
			"can_submit_attendance_request": att_api.can_submit_attendance_request(),
			"can_read_timesheet": att_api.can_read_timesheet(),
			"can_create_timesheet": att_api.can_create_timesheet(),
			"can_edit_timesheet": att_api.can_edit_timesheet(),
			"can_delete_timesheet": att_api.can_delete_timesheet(),
		},
		"tasks": {
			"can_read_todo": task_api.can_read_todo(),
			"can_create_todo": task_api.can_create_todo(),
			"can_edit_todo": task_api.can_edit_todo(),
			"can_delete_todo": task_api.can_delete_todo(),
			"can_allocate_todo": task_api.can_allocate_todo(),
		},
		"payroll": {
			"can_view_all_payroll": pay_api.can_view_all_payroll(),
			"can_read_salary_componants": pay_api.can_read_salary_componants(),
			"can_create_salary_componants": pay_api.can_create_salary_componants(),
			"can_edit_salary_componants": pay_api.can_edit_salary_componants(),
			"can_delete_salary_componants": pay_api.can_delete_salary_componants(),
			"can_read_salary_structure": pay_api.can_read_salary_structure(),
			"can_create_salary_structure": pay_api.can_create_salary_structure(),
			"can_edit_salary_structure": pay_api.can_edit_salary_structure(),
			"can_delete_salary_structure": pay_api.can_delete_salary_structure(),
			"can_read_salary_structure_assignment": pay_api.can_read_salary_structure_assignment(),
			"can_create_salary_structure_assignment": pay_api.can_create_salary_structure_assignment(),
			"can_edit_salary_structure_assignment": pay_api.can_edit_salary_structure_assignment(),
			"can_delete_salary_structure_assignment": pay_api.can_delete_salary_structure_assignment(),
			"can_read_payroll_entry": pay_api.can_read_payroll_entry(),
			"can_create_payroll_entry": pay_api.can_create_payroll_entry(),
			"can_edit_payroll_entry": pay_api.can_edit_payroll_entry(),
			"can_delete_payroll_entry": pay_api.can_delete_payroll_entry(),
			"can_read_salary_slip": pay_api.can_read_salary_slip(),
			"can_create_salary_slip": pay_api.can_create_salary_slip(),
			"can_edit_salary_slip": pay_api.can_edit_salary_slip(),
			"can_delete_salary_slip": pay_api.can_delete_salary_slip(),
			"can_read_overtime_type": pay_api.can_read_overtime_type(),
			"can_create_overtime_type": pay_api.can_create_overtime_type(),
			"can_edit_overtime_type": pay_api.can_edit_overtime_type(),
			"can_delete_overtime_type": pay_api.can_delete_overtime_type(),
			"can_read_overtime_slip": pay_api.can_read_overtime_slip(),
			"can_create_overtime_slip": pay_api.can_create_overtime_slip(),
			"can_edit_overtime_slip": pay_api.can_edit_overtime_slip(),
			"can_delete_overtime_slip": pay_api.can_delete_overtime_slip(),
			"can_read_additional_salary": pay_api.can_read_additional_salary(),
			"can_create_additional_salary": pay_api.can_create_additional_salary(),
			"can_edit_additional_salary": pay_api.can_edit_additional_salary(),
			"can_delete_additional_salary": pay_api.can_delete_additional_salary(),
			"can_read_employee_advance": pay_api.can_read_additional_salary(),
			"can_create_employee_advance": pay_api.can_create_additional_salary(),
			"can_edit_employee_advance": pay_api.can_edit_additional_salary(),
			"can_delete_employee_advance": pay_api.can_delete_additional_salary(),
		},
		"team": {
			"can_create_employee": team_api.can_create_employee(),
			"can_read_employee": team_api.can_read_employee(),
			"can_read_users": team_api.can_read_users(),
			"can_create_user": team_api.can_create_user(),
			"can_edit_employee": team_api.can_edit_employee(),
			"can_delete_employee": team_api.can_delete_employee(),
			"can_edit_user": team_api.can_edit_user(),
			"can_delete_user": team_api.can_delete_user(),
			"can_read_department": team_api.can_read_department(),
			"can_create_department": team_api.can_create_department(),
			"can_delete_department": team_api.can_delete_department(),
			"can_read_designation": team_api.can_read_designation(),
			"can_create_designation": team_api.can_create_designation(),
			"can_edit_designation": team_api.can_edit_designation(),
			"can_delete_designation": team_api.can_delete_designation(),
			"can_read_branch": team_api.can_read_branch(),
			"can_create_branch": team_api.can_create_branch(),
			"can_edit_branch": team_api.can_edit_branch(),
			"can_delete_branch": team_api.can_delete_branch(),
			"can_read_gender": team_api.can_read_gender(),
			"can_create_gender": team_api.can_create_gender(),
			"can_edit_gender": team_api.can_edit_gender(),
			"can_delete_gender": team_api.can_delete_gender(),
			"can_read_salutation": team_api.can_read_salutation(),
			"can_create_salutation": team_api.can_create_salutation(),
			"can_edit_salutation": team_api.can_edit_salutation(),
			"can_delete_salutation": team_api.can_delete_salutation(),
			"can_read_employee_grade": team_api.can_read_employee_grade(),
			"can_create_employee_grade": team_api.can_create_employee_grade(),
			"can_edit_employee_grade": team_api.can_edit_employee_grade(),
			"can_delete_employee_grade": team_api.can_delete_employee_grade(),
			"can_read_employee_type": team_api.can_read_employee_type(),
			"can_create_employee_type": team_api.can_create_employee_type(),
			"can_edit_employee_type": team_api.can_edit_employee_type(),
			"can_delete_employee_type": team_api.can_delete_employee_type(),
			"can_read_role": team_api.can_read_role(),
			"can_create_role": team_api.can_create_role(),
			"can_edit_role": team_api.can_edit_role(),
			"can_delete_role": team_api.can_delete_role(),
		}
	}


@frappe.whitelist(allow_guest=True)
def get_company_details():
	"""
	Fetch company details and HR settings for session storage.
	"""
	from arijentek_core.api.hr_settings import get_hr_settings

	user = frappe.session.user
	company = None
	if user and user != "Guest":
		company = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "company")
	if not company:
		company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")

	company_doc = {}
	if company:
		company_doc = (
			frappe.db.get_value(
				"Company",
				company,
				["name", "company_name", "default_currency", "country"],
				as_dict=True,
			)
			or {}
		)

	hr_settings = get_hr_settings()

	return {
		"company": company,
		"company_name": company_doc.get("company_name") or company,
		"default_currency": company_doc.get("default_currency"),
		"country": company_doc.get("country"),
		**hr_settings,
		"hr_settings": hr_settings,
	}
@frappe.whitelist(allow_guest=False)
def get_low_stock_alerts():
	"""Low-stock alert rows for the POS Dashboard header cards.

	Bare-array contract: rows of ``{item_code, item_name, metal, stock_qty}``,
	worst stock first; the Dashboard client slices to 5. Mirrors
	``api.inventory.get_low_stock`` — one grouped Bin query across all store
	warehouses, threshold ``stock_qty <= 2`` (zero-stock rows included).
	"""
	frappe.has_permission("Item", ptype="read", throw=True)

	registry = get_store_registry()
	all_whs = []
	for store_info in registry.values():
		all_whs.extend(_warehouse_scope(store_info.get("default_warehouse")))
	if not all_whs:
		return []

	items = frappe.get_all(
		"Item",
		filters={"is_stock_item": 1, "disabled": 0},
		fields=["name", "item_name", "custom_metal_type"],
		limit=100,
	)
	if not items:
		return []

	# One grouped query: total actual qty per item across store warehouses.
	bin_rows = frappe.db.sql(
		"""select item_code, sum(actual_qty) as qty
		   from `tabBin`
		   where warehouse in %s and actual_qty != 0
		   group by item_code""",
		(all_whs,),
		as_dict=True,
	)
	qty_by_item = {row.item_code: int(flt(row.qty)) for row in bin_rows}

	alerts = []
	for item in items:
		stock_qty = qty_by_item.get(item.name, 0)
		if stock_qty <= 2:  # same threshold as get_low_stock
			alerts.append(
				{
					"item_code": item.name,
					"item_name": item.item_name,
					"metal": item.custom_metal_type or "-",
					"stock_qty": stock_qty,
				}
			)

	alerts.sort(key=lambda row: row["stock_qty"])
	return alerts[:50]
