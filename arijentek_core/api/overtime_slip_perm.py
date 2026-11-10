import frappe
from frappe import _

DOCTYPE = "Overtime Slip"
ROLE = "HR Manager"

# Flags applied to the HR Manager rule (mirrors the portal gate:
# create + submit cover save_overtime_slip insert + auto-submit;
# read/write cover opening and editing slips).
FLAG_VALUES = {
	"read": 1,
	"write": 1,
	"create": 1,
	"submit": 1,
	"delete": 0,
	"cancel": 0,
}


def _ensure_custom_docperm() -> str:
	"""
	Ensures the Custom DocPerm rule for ROLE on DOCTYPE exists (idempotent).

	Custom DocPerm rows completely REPLACE the stock DocPerm rows inside
	meta.permissions (Meta.set_custom_permissions), so when the doctype has
	no custom rows yet, all stock DocPerm rows are copied into Custom DocPerm
	first (frappe.permissions.setup_custom_perms) — preserving the
	permissions of every other role.
	"""
	from frappe.permissions import setup_custom_perms

	setup_custom_perms(DOCTYPE)

	existing = frappe.get_all(
		"Custom DocPerm",
		filters={"parent": DOCTYPE, "role": ROLE, "permlevel": 0, "if_owner": 0},
		fields=["name"],
	)
	if existing:
		# Update in place; on_update clears the doctype permission cache.
		doc = frappe.get_doc("Custom DocPerm", existing[0].name)
		changed = False
		for field, value in FLAG_VALUES.items():
			if doc.get(field) != value:
				doc.set(field, value)
				changed = True
		if changed:
			doc.flags.ignore_permissions = True
			doc.save(ignore_permissions=True)
		return existing[0].name

	doc = frappe.get_doc(
		{
			"doctype": "Custom DocPerm",
			"parent": DOCTYPE,
			"role": ROLE,
			"permlevel": 0,
			"if_owner": 0,
			**FLAG_VALUES,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def ensure_hr_manager_overtime_slip_permission():
	"""
	Ensures (idempotently) that the HR Manager role has read/write/create/submit
	on the stock Overtime Slip doctype via Custom DocPerm, without touching
	any hrms code.
	Whitelisted API and also used in after_install and after_migrate hooks.
	"""
	# Check permissions if called via web/API request
	if frappe.request and frappe.session.user and frappe.session.user not in ("Administrator",):
		roles = frappe.get_roles(frappe.session.user)
		if "System Manager" not in roles:
			frappe.throw(
				_("You do not have permission to configure Overtime Slip permissions"),
				frappe.PermissionError,
			)

	if not frappe.db.exists("DocType", DOCTYPE):
		frappe.logger().warning("Overtime Slip DocType is not available. Skipping permission setup.")
		return {"status": "skipped", "message": "Overtime Slip DocType not found"}

	try:
		name = _ensure_custom_docperm()

		from frappe.core.doctype.doctype.doctype import validate_permissions_for_doctype

		validate_permissions_for_doctype(DOCTYPE)
		frappe.logger().info(f"Custom DocPerm ensured for {ROLE} on {DOCTYPE} ({name}).")
		return {"status": "success", "name": name}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), f"Ensure HR Manager Overtime Slip Permission Error")
		frappe.logger().error(f"Failed to ensure {ROLE} permission on {DOCTYPE}: {e}")
		if frappe.flags.in_migrate or frappe.flags.in_install:
			return {"status": "error", "message": str(e)}
		raise


def setup_overtime_slip_permission():
	"""Hook entry point for after_install and after_migrate."""
	return ensure_hr_manager_overtime_slip_permission()
