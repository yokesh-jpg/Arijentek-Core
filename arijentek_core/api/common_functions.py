import frappe

@frappe.whitelist()
def get_currencies():
	return frappe.get_all("Currency", fields=["name", "currency_name"])

@frappe.whitelist()
def get_payment_terms():
	return frappe.get_all("Payment Term", fields=["name"])

@frappe.whitelist()
def get_countries():
	return frappe.get_all("Country", fields=["name"])

@frappe.whitelist()
def get_default_company() -> str | None:
	"""
	Resolve the default company safely without throwing IndexError.
	Hierarchy:
	1. User default "Company"
	2. Global default "company"
	3. Global Defaults doctype "default_company"
	4. Any existing Company record
	"""
	return (
		frappe.defaults.get_user_default("Company")
		or frappe.defaults.get_global_default("company")
		or frappe.db.get_single_value("Global Defaults", "default_company")
		or frappe.db.get_value("Company", {}, "name")
	)

@frappe.whitelist(allow_guest=False)
def get_company_name() -> dict:
	"""Display name of the site's default company, for client-side branding.

	The employee portal calls this instead of hardcoding a brand label.
	Preference order: Global Defaults default_company, else the first Company.
	The DBA name (custom_dba_name) wins over the legal company_name when set.
	"""
	company = get_default_company()
	if not company:
		return {"company_name": ""}

	fields = ["company_name"]
	if frappe.get_meta("Company").has_field("custom_dba_name"):
		fields.append("custom_dba_name")
	row = frappe.db.get_value("Company", company, fields, as_dict=True) or {}
	return {"company_name": row.get("custom_dba_name") or row.get("company_name") or company}
