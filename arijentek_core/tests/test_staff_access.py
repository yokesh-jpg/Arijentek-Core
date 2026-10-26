"""Team Hub tests — services/staff_access.py + role_profile_catalog + custom_personas.

Covers the whole one-click staff flow: catalog sync (idempotent, Bench
Jeweler fix, Store Manager approvals), persona-tier gating on create
(admin / Store Manager / Sales User), the create transaction (User +
Employee + User Role Profile + exact role set + no welcome email +
savepoint rollback), overview shape, and update protections (re-persona
exact-replace, self-disable, protected users, manager vs admin-tier).
v2 adds persona STACKS (create/update with lists, tier = most privileged
member) and the in-app custom-persona builder (gates, tier derivation,
visibility, bundle propagation, delete protection, drift guard).
v3 (v1_5 restructure): 15-persona catalog — clean customer RBAC. No
Gemora role in any standard bundle, Employee + ESS everywhere, the
customer-owner "Admin User" persona/role (admin tier, no desk), Exec
Admin re-tiered to desk, and the platform-role firewall on the builder.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate, today

from arijentek_core.api.auth import get_user_landing_route
from arijentek_core.api.teams_permissons import delete_role_profile, save_role_profile
from arijentek_core.services.custom_personas import (
	delete_custom_persona,
	get_persona_builder_options,
	save_custom_persona,
)
from arijentek_core.services.role_profile_catalog import (
	ROLE_PROFILE_CATALOG,
	sync_catalog_profiles,
)
from arijentek_core.services.staff_access import (
	create_staff_member,
	get_catalog_for_user,
	get_staff_overview,
	get_staff_permissions,
	update_staff_member,
)


def _ensure_user(email: str, roles: list[str]) -> str:
	"""Create (or reuse) a test user with at least the given roles."""
	if not frappe.db.exists("User", email):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0].title(),
				"roles": [],
			}
		).insert(ignore_permissions=True)
		user.add_roles(*roles)
	return email


class TestCatalogSync(FrappeTestCase):
	"""sync_catalog_profiles: exact-set upsert, idempotent, Bench Jeweler fix."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		from arijentek_core.install import create_core_roles

		create_core_roles()  # catalog-referenced Roles must exist first
		sync_catalog_profiles()  # exact-sets the v1_5 catalog in the test txn

	def test_sync_repairs_drifted_profile(self):
		"""Catalog ownership: manual edits to a catalog profile get reverted."""
		doc = frappe.get_doc("Role Profile", "Store Manager")
		doc.roles = [r for r in doc.roles if r.role != "Leave Approver"]
		doc.save(ignore_permissions=True)
		# RoleProfile.on_update queues an after-commit unlock (queue_action);
		# rolled-back test transactions never commit, so unlock explicitly or
		# the orphaned file lock breaks every later save of this profile.
		doc.unlock()
		changed = sync_catalog_profiles()
		self.assertIn("Store Manager", changed)
		self.assertIn(
			"Leave Approver", {r.role for r in frappe.get_doc("Role Profile", "Store Manager").roles}
		)

	def test_sync_is_idempotent(self):
		self.assertEqual(sync_catalog_profiles(), [])

	def test_all_seven_profiles_exist(self):
		for name in ROLE_PROFILE_CATALOG:
			self.assertTrue(frappe.db.exists("Role Profile", name), name)
		self.assertEqual(len(ROLE_PROFILE_CATALOG), 7)

	def test_standard_bundles_are_customer_clean(self):
		"""v1_6: no standard bundle carries a Gemora/platform role, and every
		store persona reaches the employee portal (Employee + ESS)."""
		standard = [n for n, s in ROLE_PROFILE_CATALOG.items() if s["tier"] == "standard"]
		self.assertEqual(len(standard), 4)
		for name in standard:
			bundle = {r.role for r in frappe.get_doc("Role Profile", name).roles}
			self.assertEqual(bundle, set(ROLE_PROFILE_CATALOG[name]["roles"]), name)
			self.assertFalse(
				[r for r in bundle if r.startswith("Gemora ")],
				f"{name} still bundles a Gemora role",
			)
			self.assertFalse(bundle & {"System Manager", "Administrator", "Admin User"}, name)
			self.assertIn("Employee", bundle, name)
			self.assertIn("Employee Self Service", bundle, name)

	def test_admin_user_persona_shape(self):
		"""The customer-owner persona: admin tier, carries the Admin User ROLE
		(assigning the persona IS the admin grant), portal access, no desk."""
		spec = ROLE_PROFILE_CATALOG["Admin User"]
		self.assertEqual(spec["tier"], "admin")
		bundle = {r.role for r in frappe.get_doc("Role Profile", "Admin User").roles}
		self.assertEqual(bundle, set(spec["roles"]))
		self.assertIn("Admin User", bundle)
		self.assertIn("Employee", bundle)
		self.assertIn("Employee Self Service", bundle)
		self.assertFalse(bundle & {"System Manager", "Gemora Super Admin", "Gemora Developer"})

	def test_labels_present_in_catalog(self):
		"""Every catalog persona carries a non-empty UI label."""
		for name, spec in ROLE_PROFILE_CATALOG.items():
			self.assertIn("label", spec, f"{name} missing label")
			self.assertTrue(spec["label"], f"{name} has empty label")

		self.assertEqual(ROLE_PROFILE_CATALOG["Sales"]["label"], "POS Cashier")
		self.assertEqual(ROLE_PROFILE_CATALOG["Admin User"]["label"], "Owner / Admin")
		self.assertEqual(ROLE_PROFILE_CATALOG["Inventory"]["label"], "Inventory & Stock")
		self.assertEqual(ROLE_PROFILE_CATALOG["HR"]["label"], "HR & People Ops")
		self.assertEqual(ROLE_PROFILE_CATALOG["Store Manager"]["label"], "Store Manager")

	def test_catalog_functions_include_label(self):
		"""get_catalog and get_catalog_for_user include label in payloads."""
		from arijentek_core.services.role_profile_catalog import get_catalog
		from arijentek_core.services.staff_access import get_catalog_for_user

		cat = get_catalog()
		self.assertEqual(cat["Sales"]["label"], "POS Cashier")

		user_cat = get_catalog_for_user("Administrator")
		sales_entry = next((p for p in user_cat if p["name"] == "Sales"), None)
		self.assertIsNotNone(sales_entry)
		self.assertEqual(sales_entry["label"], "POS Cashier")

	def test_sales_cashier_bundle(self):
		"""Sales persona bundles Sales User, Employee, and Employee Self Service."""
		bundle = {r.role for r in frappe.get_doc("Role Profile", "Sales").roles}
		self.assertEqual(
			bundle, {"Sales User", "Employee", "Employee Self Service"}
		)

	def test_inventory_bundle(self):
		"""Inventory persona bundles Stock User, Stock Manager, Item Manager, Employee, ESS."""
		bundle = {r.role for r in frappe.get_doc("Role Profile", "Inventory").roles}
		self.assertEqual(
			bundle,
			{"Stock User", "Stock Manager", "Item Manager", "Employee", "Employee Self Service"},
		)

	def test_store_manager_approves_hr(self):
		bundle = {r.role for r in frappe.get_doc("Role Profile", "Store Manager").roles}
		self.assertIn("Leave Approver", bundle)
		self.assertIn("Expense Approver", bundle)


class TestCreateStaff(FrappeTestCase):
	"""create_staff_member: one call = User + Employee + persona (+ rollback)."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		from arijentek_core.install import create_core_roles

		create_core_roles()
		sync_catalog_profiles()
		cls.manager = _ensure_user("t-staff-manager@test.local", ["Store Manager"])
		cls.sales_user = _ensure_user("t-staff-sales@test.local", ["Sales User"])

	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")

	def _payload(self, email="t-staff-new@test.local", **overrides):
		payload = {
			"role_profile": "Sales",
			"first_name": "Jordan",
			"last_name": "Rivera",
			"email": email,
			"password": "Zev!ar-2026-Start",
			"gender": "Male",
			"date_of_birth": "1990-05-01",
			"employee_mode": "create",
		}
		payload.update(overrides)
		return payload

	def test_admin_create_full_flow(self):
		result = create_staff_member(self._payload())

		self.assertEqual(result["user"], "t-staff-new@test.local")
		self.assertEqual(result["role_profile"], "Sales")
		self.assertEqual(result["landing_route"], "/terminal")
		self.assertNotIn("generated_password", result)  # explicit password given

		user = frappe.get_doc("User", "t-staff-new@test.local")
		self.assertEqual(
			{r.role for r in user.roles},
			{"Sales User", "Employee", "Employee Self Service"},
		)
		self.assertEqual(
			[r.role_profile for r in user.role_profiles], ["Sales"]
		)

		employee = frappe.db.get_value(
			"Employee", {"user_id": "t-staff-new@test.local"}, "name"
		)
		self.assertTrue(employee)
		self.assertEqual(result["employee"], employee)

		# No welcome email may be queued (send_welcome_email=0). Recipients
		# live in the Email Queue Recipient child table in this Frappe.
		queued = frappe.get_all(
			"Email Queue Recipient", filters={"recipient": "t-staff-new@test.local"}
		)
		self.assertEqual(queued, [])

	def test_generated_password_is_usable(self):
		result = create_staff_member(self._payload("t-staff-gen@test.local", password=""))
		self.assertTrue(result["generated_password"])
		from frappe.utils.password import check_password

		self.assertEqual(
			check_password("t-staff-gen@test.local", result["generated_password"]),
			"t-staff-gen@test.local",
		)

	def test_optional_profile_fields_carried_over(self):
		"""The unified create form's extras ride the same atomic call — no
		second endpoint, no partial user (username/middle/timezone/approvers)."""
		result = create_staff_member(
			self._payload(
				"t-staff-extras@test.local",
				username="tstaffextras",
				middle_name="Quinn",
				time_zone="America/New_York",
				date_of_joining="2026-01-15",
				expense_approver="Administrator",
				leave_approver="Administrator",
				shift_approver="Administrator",
			)
		)
		self.assertEqual(result["user"], "t-staff-extras@test.local")

		user = frappe.get_doc("User", "t-staff-extras@test.local")
		self.assertEqual(user.username, "tstaffextras")
		self.assertEqual(user.middle_name, "Quinn")
		self.assertEqual(user.time_zone, "America/New_York")

		employee = frappe.get_doc("Employee", {"user_id": "t-staff-extras@test.local"})
		self.assertEqual(employee.date_of_joining, getdate("2026-01-15"))
		self.assertEqual(employee.expense_approver, "Administrator")
		self.assertEqual(employee.leave_approver, "Administrator")
		self.assertEqual(employee.shift_request_approver, "Administrator")

	def test_store_manager_creates_standard_persona(self):
		frappe.set_user(self.manager)
		result = create_staff_member(
			self._payload("t-staff-mgr-created@test.local", role_profile="Inventory")
		)
		self.assertEqual(result["landing_route"], "/inventory")

	def test_store_manager_blocked_from_admin_and_desk_personas(self):
		frappe.set_user(self.manager)
		for persona in ("Admin User", "Gemora Super Admin", "Gemora Developer"):
			with self.assertRaises(frappe.PermissionError):
				create_staff_member(
					self._payload(f"t-staff-blocked-{persona.split()[-1].lower()}@test.local",
						role_profile=persona)
				)

	def test_sales_user_cannot_create(self):
		frappe.set_user(self.sales_user)
		with self.assertRaises(frappe.PermissionError):
			create_staff_member(self._payload("t-staff-denied@test.local"))

	def test_non_catalog_persona_rejected(self):
		frappe.set_user(self.manager)
		with self.assertRaises(frappe.PermissionError):
			create_staff_member(self._payload(role_profile="Made Up Persona"))

	def test_validation_errors(self):
		cases = [
			self._payload(gender=""),  # missing gender
			self._payload(date_of_birth=""),  # missing DOB
			self._payload(email="not-an-email"),  # bad email
			self._payload(password="123"),  # too short
		]
		for payload in cases:
			with self.assertRaises(frappe.ValidationError):
				create_staff_member(payload)

	def test_duplicate_email_rejected(self):
		create_staff_member(self._payload("t-staff-dup@test.local"))
		with self.assertRaises(frappe.ValidationError):
			create_staff_member(self._payload("t-staff-dup@test.local"))

	def test_none_mode_skips_employee_validation(self):
		"""employee_mode="none" must not demand gender/DOB (regression: the
		old else-branch validated employee fields for none-mode users too)."""
		result = create_staff_member(
			self._payload(
				"t-staff-noemp@test.local",
				employee_mode="none",
				gender="",
				date_of_birth="",
			)
		)
		self.assertEqual(result["user"], "t-staff-noemp@test.local")
		self.assertIsNone(result["employee"])
		self.assertFalse(
			frappe.db.exists("Employee", {"user_id": "t-staff-noemp@test.local"})
		)

	def test_link_mode_attaches_existing_employee(self):
		employee = frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": "Prior",
				"company": frappe.db.get_single_value("Global Defaults", "default_company"),
				"status": "Active",
				"gender": "Female",
				"date_of_birth": "1985-01-01",
				"date_of_joining": today(),
			}
		).insert(ignore_permissions=True)

		result = create_staff_member(
			self._payload("t-staff-link@test.local", employee_mode="link", employee_id=employee.name)
		)
		self.assertEqual(result["employee"], employee.name)
		self.assertEqual(frappe.db.get_value("Employee", employee.name, "user_id"),
			"t-staff-link@test.local")

	def test_failure_rolls_back_user(self):
		"""A bad employee link must not leave a half-created User behind."""
		other = _ensure_user("t-staff-other@test.local", ["Sales User"])
		employee = frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": "Taken",
				"company": frappe.db.get_single_value("Global Defaults", "default_company"),
				"status": "Active",
				"gender": "Female",
				"date_of_birth": "1985-01-01",
				"date_of_joining": today(),
			}
		).insert(ignore_permissions=True)
		frappe.db.set_value("Employee", employee.name, "user_id", other)

		with self.assertRaises(frappe.ValidationError):
			create_staff_member(
				self._payload("t-staff-rolledback@test.local",
					employee_mode="link", employee_id=employee.name)
			)
		self.assertFalse(frappe.db.exists("User", "t-staff-rolledback@test.local"))


class TestOverviewAndUpdate(FrappeTestCase):
	"""get_staff_overview shape + update_staff_member protections."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		from arijentek_core.install import create_core_roles

		frappe.flags.is_platform_site = 1
		sync_catalog_profiles()
		cls.manager = _ensure_user("t-staff-manager@test.local", ["Store Manager"])
		cls.customer_admin = _ensure_user("t-staff-cadmin@test.local", ["Admin User"])
		cls.cashier = create_staff_member(
			{
				"role_profile": "Sales",
				"first_name": "Cashier",
				"email": "t-staff-cashier@test.local",
				"password": "Zev!ar-2026-Start",
				"gender": "Male",
				"date_of_birth": "1990-05-01",
			}
		)
		cls.super_admin = create_staff_member(
			{
				"role_profile": "Gemora Super Admin",
				"first_name": "Super",
				"email": "t-staff-super@test.local",
				"password": "Zev!ar-2026-Start",
				"gender": "Female",
				"date_of_birth": "1985-05-01",
				"employee_mode": "none",
			}
		)

	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_overview_shape(self):
		overview = get_staff_overview()
		for key in ("staff", "counts", "caller", "options"):
			self.assertIn(key, overview)

		users = [s["user"] for s in overview["staff"]]
		self.assertNotIn("Administrator", users)
		self.assertNotIn("Guest", users)
		self.assertIn("t-staff-cashier@test.local", users)

		row = next(s for s in overview["staff"] if s["user"] == "t-staff-cashier@test.local")
		self.assertEqual(row["persona"], "Sales")
		self.assertEqual(row["persona_label"], "POS Cashier")
		self.assertEqual(row["persona_tier"], "standard")
		self.assertTrue(row["employee"])
		self.assertIn("Sales User", row["roles"])
		self.assertTrue(overview["caller"]["can_set_pins"])
		for key in ("genders", "departments", "designations", "pos_profiles", "unlinked_employees"):
			self.assertIn(key, overview["options"])

	def test_catalog_visibility_by_tier(self):
		"""7 personas: manager 4 standard, customer admin 5, platform 7. Counts
		scope to the CURATED catalog — sites may also carry user-built custom
		personas (this dev site's 'Super User'), which are user data."""
		admin_catalog = get_catalog_for_user("Administrator")
		self.assertTrue(
			{p["name"] for p in admin_catalog} >= set(ROLE_PROFILE_CATALOG)
		)
		self.assertEqual(len(ROLE_PROFILE_CATALOG), 7)

		manager_catalog = get_catalog_for_user(self.manager)
		manager_curated = [p for p in manager_catalog if p["name"] in ROLE_PROFILE_CATALOG]
		self.assertEqual({p["tier"] for p in manager_catalog}, {"standard"})
		self.assertEqual(len(manager_curated), 4)

		customer_catalog = get_catalog_for_user(self.customer_admin)
		customer_curated = [p for p in customer_catalog if p["name"] in ROLE_PROFILE_CATALOG]
		self.assertEqual({p["tier"] for p in customer_catalog}, {"standard", "admin"})
		self.assertEqual(len(customer_curated), 5)
		self.assertIn("Admin User", {p["name"] for p in customer_catalog})
		self.assertFalse(
			{"Gemora Super Admin", "Gemora Developer"}
			& {p["name"] for p in customer_catalog}
		)

	def test_customer_admin_can_manage_staff(self):
		"""The Admin User role passes staff.manage — full Team access, no desk."""
		from arijentek_core.services.permissions import has_permission

		self.assertTrue(has_permission("staff.manage", user=self.customer_admin))
		perms = get_staff_permissions(self.customer_admin)
		self.assertTrue(perms["staff.manage"])

	def test_reassign_persona_exact_replaces(self):
		result = update_staff_member(
			{"user": "t-staff-cashier@test.local", "role_profile": "Inventory"}
		)
		self.assertEqual(result["role_profile"], "Inventory")
		self.assertNotIn("Sales User", result["roles"])
		user = frappe.get_doc("User", "t-staff-cashier@test.local")
		self.assertEqual(
			{r.role for r in user.roles},
			set(ROLE_PROFILE_CATALOG["Inventory"]["roles"]),
		)

	def test_reset_password(self):
		result = update_staff_member(
			{"user": "t-staff-cashier@test.local", "password": "newpass99"}
		)
		self.assertTrue(result["password_reset"])
		result = update_staff_member({"user": "t-staff-cashier@test.local", "generate_password": 1})
		self.assertTrue(result["generated_password"])

	def test_disable_and_reenable(self):
		update_staff_member({"user": "t-staff-cashier@test.local", "enabled": False})
		self.assertEqual(frappe.db.get_value("User", "t-staff-cashier@test.local", "enabled"), 0)
		update_staff_member({"user": "t-staff-cashier@test.local", "enabled": True})
		self.assertEqual(frappe.db.get_value("User", "t-staff-cashier@test.local", "enabled"), 1)

	def test_self_disable_rejected(self):
		frappe.set_user(self.manager)
		with self.assertRaises(frappe.ValidationError):
			update_staff_member({"user": self.manager, "enabled": False})

	def test_protected_users_rejected(self):
		for protected in ("Administrator", "Guest"):
			with self.assertRaises(frappe.ValidationError):
				update_staff_member({"user": protected, "enabled": False})

	def test_manager_cannot_mutate_admin_tier(self):
		frappe.set_user(self.manager)
		with self.assertRaises(frappe.PermissionError):
			update_staff_member({"user": "t-staff-super@test.local", "password": "mgrset123"})

	def test_manager_can_manage_standard_user(self):
		frappe.set_user(self.manager)
		result = update_staff_member(
			{"user": "t-staff-cashier@test.local", "enabled": False}
		)
		self.assertFalse(result["enabled"])

	def test_staff_permissions_map(self):
		perms = get_staff_permissions("t-staff-cashier@test.local")
		self.assertIsInstance(perms, dict)
		self.assertIn("staff.manage", perms)
		self.assertFalse(perms["staff.manage"])  # bench persona has no staff.manage
		self.assertTrue(all(isinstance(v, bool) for v in perms.values()))


class TestPersonaStacking(FrappeTestCase):
	"""Stacked personas: create/update accept lists; the stack's gate is its
	most privileged member (Frappe unions all profiles into the user's roles)."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		from arijentek_core.install import create_core_roles

		frappe.flags.is_platform_site = 1
		sync_catalog_profiles()
		cls.manager = _ensure_user("t-staff-manager@test.local", ["Store Manager"])
		cls.stack_user = create_staff_member(
			{
				"role_profiles": ["Sales", "Inventory"],
				"first_name": "Stack",
				"email": "t-staff-stack@test.local",
				"password": "Zev!ar-2026-Start",
				"gender": "Female",
				"date_of_birth": "1992-02-02",
			}
		)["user"]

	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")

	def _payload(self, email, **overrides):
		payload = {
			"role_profiles": ["Sales", "Inventory"],
			"first_name": "Duo",
			"email": email,
			"password": "Zev!ar-2026-Start",
			"gender": "Male",
			"date_of_birth": "1990-05-01",
		}
		payload.update(overrides)
		return payload

	def test_create_stack_union_and_landing(self):
		result = create_staff_member(self._payload("t-staff-duo@test.local"))

		self.assertEqual(result["role_profiles"], ["Sales", "Inventory"])
		self.assertEqual(result["role_profile"], "Sales")  # first, for toasts
		expected = set(ROLE_PROFILE_CATALOG["Sales"]["roles"]) | set(
			ROLE_PROFILE_CATALOG["Inventory"]["roles"]
		)
		self.assertEqual(set(result["roles"]), expected)
		user = frappe.get_doc("User", "t-staff-duo@test.local")
		self.assertEqual({r.role for r in user.roles}, expected)  # Frappe materialized the union
		self.assertEqual(
			[r.role_profile for r in user.role_profiles],
			["Sales", "Inventory"],
		)
		self.assertEqual(result["landing_route"], "/terminal")

	def test_empty_and_duplicate_stacks(self):
		with self.assertRaises(frappe.ValidationError):
			create_staff_member(self._payload("t-staff-empty@test.local", role_profiles=[]))
		# duplicate entries collapse; assignment order is preserved
		result = create_staff_member(
			self._payload(
				"t-staff-dupstack@test.local",
				role_profiles=["Sales", "Sales"],
			)
		)
		self.assertEqual(result["role_profiles"], ["Sales"])

	def test_reassign_stack_exact_replaces(self):
		result = update_staff_member(
			{
				"user": self.stack_user,
				"role_profiles": ["Inventory", "HR"],
			}
		)
		self.assertEqual(
			result["role_profiles"], ["Inventory", "HR"]
		)
		self.assertNotIn("Sales User", result["roles"])
		self.assertEqual(
			[r.role_profile for r in frappe.get_doc("User", self.stack_user).role_profiles],
			["Inventory", "HR"],
		)

		# shrink to a single persona → the survivor's bundle, exactly
		result = update_staff_member({"user": self.stack_user, "role_profile": "Sales"})
		self.assertEqual(result["role_profiles"], ["Sales"])
		self.assertEqual(set(result["roles"]), set(ROLE_PROFILE_CATALOG["Sales"]["roles"]))

	def test_manager_blocked_from_admin_persona_in_stack(self):
		frappe.set_user(self.manager)
		with self.assertRaises(frappe.PermissionError):
			create_staff_member(
				self._payload(
					"t-staff-mgrstack@test.local",
					role_profiles=["Sales", "Gemora Super Admin"],
				)
			)

	def test_overview_tier_is_most_privileged_in_stack(self):
		created = create_staff_member(
			self._payload(
				"t-staff-adv@test.local",
				role_profiles=["Sales", "Gemora Super Admin"],
			)
		)
		self.assertEqual(created["landing_route"], "/app")
		overview = get_staff_overview()
		row = next(s for s in overview["staff"] if s["user"] == "t-staff-adv@test.local")
		self.assertEqual(row["persona_tier"], "desk")
		self.assertEqual(row["role_profiles"], ["Gemora Super Admin", "Sales"])
		self.assertTrue(overview["caller"]["can_manage_personas"])

	def test_legacy_string_profile_still_works(self):
		result = create_staff_member(
			self._payload("t-staff-legacy@test.local", role_profiles=None, role_profile="Sales")
		)
		self.assertEqual(result["role_profiles"], ["Sales"])


class TestCustomPersonas(FrappeTestCase):
	"""In-app persona builder: admin-tier gate, read-time tier derivation,
	visibility filtering, bundle propagation to assigned users, delete
	protection, name collisions, and the Settings drift guard.

	FrappeTestCase rolls back once per CLASS here, so methods share one
	transaction — every method uses its own persona NAME and email to stay
	self-contained. Users are created with employee_mode="create": ERPNext's
	validate_employee_role hook strips Employee/Employee Self Service from
	any user without a linked Employee record, which would silently change
	the expected role sets.
	"""

	STANDARD = "T Custom Std"
	ADMIN = "T Custom Admin"
	DESK = "T Custom Desk"
	LANDING = "T Custom Landing"
	PROPAGATE = "T Custom Prop"
	DELETE = "T Custom Del"

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		from arijentek_core.install import create_core_roles

		frappe.flags.is_platform_site = 1
		if not frappe.db.exists("Role", "Gemora Cashier"):
			frappe.get_doc({"doctype": "Role", "role_name": "Gemora Cashier"}).insert(ignore_permissions=True)
		sync_catalog_profiles()
		cls.manager = _ensure_user("t-staff-manager@test.local", ["Store Manager"])
		# The customer owner: real "Admin User" role → admin tier WITHOUT the
		# desk-grant right (no DESK_ROLES). This is exactly the persona the
		# v1_5 restructure gives tenant owners.
		cls.customer_admin = _ensure_user("t-staff-cadmin@test.local", ["Admin User"])

	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")

	def _save(self, name, roles, landing="/", **extra):
		return save_custom_persona(
			{"name": name, "description": "test persona", "roles": roles, "landing": landing, **extra}
		)

	def test_builder_gates(self):
		frappe.set_user(self.manager)
		with self.assertRaises(frappe.PermissionError):
			get_persona_builder_options()
		with self.assertRaises(frappe.PermissionError):
			self._save(self.STANDARD, ["Employee"])
		with self.assertRaises(frappe.PermissionError):
			delete_custom_persona(self.STANDARD)

		frappe.set_user(self.customer_admin)  # admin tier, no desk right → builder opens
		options = get_persona_builder_options()
		role_names = {r["name"] for r in options["roles"]}
		self.assertNotIn("Guest", role_names)
		self.assertNotIn("All", role_names)
		self.assertIn("Sales User", role_names)
		self.assertIn("/terminal", options["landings"])

	def test_builder_platform_role_firewall(self):
		"""v1_5: platform roles never reach a customer admin's builder; a
		desk-grant holder (Administrator) still gets the full list."""
		frappe.set_user(self.customer_admin)
		role_names = {r["name"] for r in get_persona_builder_options()["roles"]}
		for platform in (
			"System Manager", "Admin User", "Gemora Admin",
			"Gemora Super Admin", "Gemora Developer",
			"Gemora Cashier", "Gemora Inventory", "Gemora Manager",  # prefix guard
		):
			self.assertNotIn(platform, role_names, platform)

		frappe.set_user("Administrator")  # desk-grant holder
		admin_names = {r["name"] for r in get_persona_builder_options()["roles"]}
		self.assertIn("System Manager", admin_names)
		self.assertIn("Admin User", admin_names)
		self.assertIn("Gemora Developer", admin_names)

	def test_customer_admin_cannot_bundle_platform_roles(self):
		"""Server-side firewall: minting a platform-granting persona is a
		PermissionError even with direct API access."""
		frappe.set_user(self.customer_admin)
		for roles in (
			["System Manager", "Sales User"],  # platform super-grant
			["Admin User", "Employee"],  # the admin grant itself
			["Gemora Cashier", "Sales User"],  # Gemora-prefix guard
		):
			with self.assertRaises(frappe.PermissionError):
				self._save("T Custom Blocked", roles)

		# The same Administrator save (desk-grant holder) goes through —
		# see test_admin_tier_custom_hidden_from_manager.

	def test_standard_custom_persona_visible_to_manager(self):
		result = self._save(self.STANDARD, ["Sales User", "Employee", "Employee Self Service"])
		self.assertTrue(result["created"])
		self.assertEqual(result["tier"], "standard")

		self.assertIn(self.STANDARD, {p["name"] for p in get_catalog_for_user("Administrator")})
		manager_catalog = get_catalog_for_user(self.manager)
		spec = next(p for p in manager_catalog if p["name"] == self.STANDARD)
		self.assertTrue(spec["custom"])
		self.assertEqual(spec["roles"], ["Employee", "Employee Self Service", "Sales User"])

	def test_admin_tier_custom_hidden_from_manager(self):
		result = self._save(self.ADMIN, ["System Manager", "Employee"])
		self.assertEqual(result["tier"], "admin")  # derived from the bundle at read time
		self.assertIn(self.ADMIN, {p["name"] for p in get_catalog_for_user("Administrator")})
		self.assertNotIn(self.ADMIN, {p["name"] for p in get_catalog_for_user(self.manager)})

	def test_desk_bundle_needs_desk_grant_right(self):
		frappe.set_user(self.customer_admin)  # admin tier but no desk right
		with self.assertRaises(frappe.PermissionError):
			self._save(self.DESK, ["Gemora Developer"])

		frappe.set_user("Administrator")  # the one user the desk gate always passes
		result = self._save(self.DESK, ["Gemora Developer", "Employee"])
		self.assertEqual(result["tier"], "desk")
		self.assertIn(self.DESK, {p["name"] for p in get_catalog_for_user("Administrator")})
		self.assertNotIn(self.DESK, {p["name"] for p in get_catalog_for_user(self.manager)})

	def test_assign_custom_persona_and_landing(self):
		self._save(self.LANDING, ["Employee", "Employee Self Service"], landing="/repairs")
		result = create_staff_member(
			{
				"role_profiles": [self.LANDING],
				"first_name": "Custom",
				"email": "t-staff-custom@test.local",
				"password": "Zev!ar-2026-Start",
				"gender": "Male",
				"date_of_birth": "1990-05-01",
			}
		)
		self.assertEqual(result["role_profiles"], [self.LANDING])
		self.assertEqual(result["roles"], ["Employee", "Employee Self Service"])
		# These roles alone would fall through to /employee-portal — the
		# persona's custom landing must win first.
		self.assertEqual(result["landing_route"], "/repairs")
		self.assertEqual(get_user_landing_route("t-staff-custom@test.local"), "/repairs")

	def test_bundle_edit_propagates_to_assigned_users(self):
		self._save(self.PROPAGATE, ["Sales User", "Employee"])
		create_staff_member(
			{
				"role_profiles": [self.PROPAGATE],
				"first_name": "Prop",
				"email": "t-staff-prop@test.local",
				"password": "Zev!ar-2026-Start",
				"gender": "Male",
				"date_of_birth": "1990-05-01",
			}
		)

		self._save(self.PROPAGATE, ["Sales User", "Employee", "Leave Approver"])
		self.assertIn(
			"Leave Approver",
			{r.role for r in frappe.get_doc("User", "t-staff-prop@test.local").roles},
		)

	def test_delete_blocked_while_assigned_then_ok(self):
		self._save(self.DELETE, ["Sales User", "Employee"])
		user = create_staff_member(
			{
				"role_profiles": [self.DELETE],
				"first_name": "Del",
				"email": "t-staff-del@test.local",
				"password": "Zev!ar-2026-Start",
				"gender": "Male",
				"date_of_birth": "1990-05-01",
			}
		)["user"]
		with self.assertRaises(frappe.ValidationError):
			delete_custom_persona(self.DELETE)

		update_staff_member({"user": user, "role_profile": "Sales"})
		self.assertEqual(delete_custom_persona(self.DELETE), {"deleted": self.DELETE})
		self.assertFalse(frappe.db.exists("Role Profile", self.DELETE))

	def test_name_collisions_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self._save("Sales", ["Sales User"])  # curated catalog persona
		with self.assertRaises(frappe.ValidationError):
			delete_custom_persona("Store Manager")  # curated catalog persona

		plain = frappe.get_doc(
			{"doctype": "Role Profile", "role_profile": "T Plain Profile", "roles": [{"role": "Sales User"}]}
		).insert(ignore_permissions=True)
		plain.unlock()
		with self.assertRaises(frappe.DuplicateEntryError):
			self._save("T Plain Profile", ["Employee"])  # pre-existing non-custom profile

	def test_settings_role_profile_drift_guard(self):
		with self.assertRaises(frappe.ValidationError):
			save_role_profile("Sales", ["Sales User"])  # catalog-owned name
		with self.assertRaises(frappe.ValidationError):
			delete_role_profile("Sales")
