"""Regression tests for Phase-5 retest bug R8-1: Employee creation without a Company.

The portal Add Employee dialog historically sent no `company` and the backend
chain (payload -> user default -> Global Defaults) can resolve to nothing for
portal users on a site without a default company. create_employee must then
auto-resolve a single-company site or fail with a clean mandatory error.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch

from arijentek_core.api import teams_permissons as tp
from arijentek_core.api.teams_permissons import (
	create_employee,
	get_employee_company_options,
)


class TestResolveEmployeeCompany(FrappeTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")

	def test_payload_company_wins(self):
		with patch.object(frappe.defaults, "get_user_default", return_value=None):
			self.assertEqual(tp._resolve_employee_company({"company": "Payload Co"}), "Payload Co")

	def test_user_default_fallback(self):
		with patch.object(frappe.defaults, "get_user_default", return_value="Default Co"):
			self.assertEqual(tp._resolve_employee_company({}), "Default Co")

	def test_single_company_site_autoresolves(self):
		with patch.object(frappe.defaults, "get_user_default", return_value=None), patch.object(
			frappe.db, "get_single_value", return_value=None
		), patch.object(frappe, "get_all", lambda *a, **k: ["Only Co"]):
			self.assertEqual(tp._resolve_employee_company({}), "Only Co")

	def test_multi_company_returns_none(self):
		with patch.object(frappe.defaults, "get_user_default", return_value=None), patch.object(
			frappe.db, "get_single_value", return_value=None
		), patch.object(frappe, "get_all", lambda *a, **k: ["Company A", "Company B"]):
			self.assertIsNone(tp._resolve_employee_company({}))


class TestCreateEmployeeCompany(FrappeTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")

	def test_create_without_company_on_single_company_site(self):
		companies = frappe.get_all("Company", pluck="name")
		if len(companies) != 1:
			self.skipTest("site is not single-company")
		name = create_employee(
			employee_data={"first_name": "R81 Repro", "date_of_joining": "2026-01-01", "status": "Active"}
		)
		self.assertEqual(frappe.db.get_value("Employee", name, "company"), companies[0])

	def test_clean_error_when_company_unresolvable(self):
		with patch.object(tp, "_resolve_employee_company", return_value=None):
			with self.assertRaises(frappe.MandatoryError) as ctx:
				create_employee(
					employee_data={"first_name": "R81 Repro", "date_of_joining": "2026-01-01"}
				)
		self.assertIn("Company", str(ctx.exception))

	def test_company_options_endpoint_shape(self):
		res = get_employee_company_options()
		self.assertIn("options", res)
		self.assertIn("default", res)
		if len(res["options"]) == 1:
			self.assertEqual(res["default"], res["options"][0])
