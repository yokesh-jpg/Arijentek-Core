import frappe

@frappe.whitelist(allow_guest=False)
def get_company_name() -> dict:
	"""Display name of the site's default company, for client-side branding.

	The employee portal calls this instead of hardcoding a brand label.
	Preference order: Global Defaults default_company, else the first Company.
	The DBA name (custom_dba_name) wins over the legal company_name when set.
	"""
	company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value(
		"Company", {}, "name"
	)
	if not company:
		return {"company_name": ""}

	fields = ["company_name"]
	if frappe.get_meta("Company").has_field("custom_dba_name"):
		fields.append("custom_dba_name")
	row = frappe.db.get_value("Company", company, fields, as_dict=True) or {}
	return {"company_name": row.get("custom_dba_name") or row.get("company_name") or company}
