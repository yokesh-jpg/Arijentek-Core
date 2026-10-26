import frappe
from frappe import _


def ensure_salary_component(component_name: str = "OverTime Allowance") -> str:
	"""
	Ensures that the required Salary Component exists.
	Prefers existing component (case-insensitive match), or creates a new one.
	"""
	if not frappe.db.exists("DocType", "Salary Component"):
		return component_name

	# Check exact or case-insensitive match
	existing = frappe.db.exists("Salary Component", component_name)
	if not existing:
		existing = frappe.db.get_value(
			"Salary Component",
			{"name": ("in", ["OverTime Allowance", "Overtime Allowance"])},
			"name"
		)

	if existing:
		return existing

	# Create new Salary Component if none found
	sc = frappe.get_doc({
		"doctype": "Salary Component",
		"salary_component": component_name,
		"salary_component_abbr": "OTA",
		"type": "Earning",
		"description": "Overtime allowance component for overtime payouts",
		"depends_on_payment_days": 1,
		"is_tax_applicable": 1
	})
	sc.flags.ignore_permissions = True
	sc.insert(ignore_permissions=True)
	return sc.name


@frappe.whitelist()
def create_standard_overtime_type(
	name: str = "Standard OverTime",
	applicable_component: str = "OverTime Allowance",
	standard_multiplier: float = 1.5
):
	"""
	Creates or updates the default Standard OverTime Overtime Type.
	Whitelisted API and also used as hook for after_install and after_migrate.
	"""
	# Check permissions if called via web/API request
	if frappe.request and frappe.session.user and frappe.session.user not in ("Administrator",):
		roles = frappe.get_roles(frappe.session.user)
		if not ("System Manager" in roles or "HR Manager" in roles):
			frappe.throw(_("You do not have permission to configure Overtime Types"), frappe.PermissionError)

	if not frappe.db.exists("DocType", "Overtime Type"):
		frappe.logger().warning("Overtime Type DocType is not available. Skipping creation.")
		return {"status": "skipped", "message": "Overtime Type DocType not found"}

	try:
		standard_multiplier = frappe.utils.flt(standard_multiplier, 1.5)
		salary_component = ensure_salary_component(applicable_component)

		if frappe.db.exists("Overtime Type", name):
			ot_doc = frappe.get_doc("Overtime Type", name)
			ot_doc.overtime_salary_component = salary_component
			ot_doc.overtime_calculation_method = "Salary Component Based"
			ot_doc.standard_multiplier = standard_multiplier
			ot_doc.applicable_for_weekend = 0
			ot_doc.applicable_for_public_holiday = 0

			existing_components = [
				row.salary_component for row in (ot_doc.applicable_salary_component or [])
			]
			if salary_component not in existing_components:
				ot_doc.append("applicable_salary_component", {
					"salary_component": salary_component
				})

			ot_doc.flags.ignore_permissions = True
			ot_doc.save(ignore_permissions=True)
		else:
			ot_doc = frappe.get_doc({
				"doctype": "Overtime Type",
				"name": name,
				"overtime_salary_component": salary_component,
				"overtime_calculation_method": "Salary Component Based",
				"standard_multiplier": standard_multiplier,
				"applicable_for_weekend": 0,
				"applicable_for_public_holiday": 0,
				"applicable_salary_component": [
					{"salary_component": salary_component}
				]
			})
			ot_doc.flags.ignore_permissions = True
			ot_doc.insert(ignore_permissions=True)

		frappe.logger().info(
			f"Overtime Type '{name}' ensured with component '{salary_component}' and multiplier {standard_multiplier}."
		)
		return {
			"status": "success",
			"name": ot_doc.name,
			"doc": ot_doc.as_dict()
		}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), f"Create Standard Overtime Type Error - {name}")
		frappe.logger().error(f"Failed to create/update Overtime Type '{name}': {e}")
		if frappe.flags.in_migrate or frappe.flags.in_install:
			return {"status": "error", "message": str(e)}
		raise e


def setup_standard_overtime_type():
	"""Hook entry point for after_install and after_migrate."""
	return create_standard_overtime_type()
