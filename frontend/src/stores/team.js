import { defineStore } from "pinia";
import { createResource } from "frappe-ui";
import { fetchPortalPermissionsCached } from "./auth";

export const useTeamStore = defineStore("team", () => {
	const permissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_create_employee",
		auto: false,
	});

	const readEmployeePermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_read_employee",
		auto: false,
	});

	const readUsersPermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_read_users",
		auto: false,
	});

	const createUserPermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_create_user",
		auto: false,
	});

	const editEmployeePermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_edit_employee",
		auto: false,
	});

	const deleteEmployeePermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_delete_employee",
		auto: false,
	});

	const editUserPermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_edit_user",
		auto: false,
	});

	const deleteUserPermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_delete_user",
		auto: false,
	});

	const readDepartmentPermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_read_department",
		auto: false,
	});

	const createDepartmentPermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_create_department",
		auto: false,
	});

	const deleteDepartmentPermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_delete_department",
		auto: false,
	});

	const readDesignationPermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_read_designation",
		auto: false,
	});

	const createDesignationPermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_create_designation",
		auto: false,
	});

	const editDesignationPermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_edit_designation",
		auto: false,
	});

	const deleteDesignationPermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_delete_designation",
		auto: false,
	});

	const readBranchPermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_read_branch",
		auto: false,
	});

	const createBranchPermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_create_branch",
		auto: false,
	});

	const editBranchPermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_edit_branch",
		auto: false,
	});

	const deleteBranchPermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_delete_branch",
		auto: false,
	});

	const readGenderPermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_read_gender",
		auto: false,
	});

	const createGenderPermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_create_gender",
		auto: false,
	});

	const editGenderPermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_edit_gender",
		auto: false,
	});

	const deleteGenderPermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_delete_gender",
		auto: false,
	});

	const readSalutationPermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_read_salutation",
		auto: false,
	});

	const createSalutationPermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_create_salutation",
		auto: false,
	});

	const editSalutationPermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_edit_salutation",
		auto: false,
	});

	const deleteSalutationPermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_delete_salutation",
		auto: false,
	});

	const readEmployeeGradePermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_read_employee_grade",
		auto: false,
	});

	const createEmployeeGradePermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_create_employee_grade",
		auto: false,
	});

	const editEmployeeGradePermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_edit_employee_grade",
		auto: false,
	});

	const deleteEmployeeGradePermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_delete_employee_grade",
		auto: false,
	});

	const readEmployeeTypePermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_read_employee_type",
		auto: false,
	});

	const createEmployeeTypePermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_create_employee_type",
		auto: false,
	});

	const editEmployeeTypePermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_edit_employee_type",
		auto: false,
	});

	const deleteEmployeeTypePermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_delete_employee_type",
		auto: false,
	});

	const readRolePermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_read_role",
		auto: false,
	});

	const createRolePermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_create_role",
		auto: false,
	});

	const editRolePermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_edit_role",
		auto: false,
	});

	const deleteRolePermissionResource = createResource({
		url: "arijentek_core.api.teams_permissons.can_delete_role",
		auto: false,
	});

	const departmentsResource = createResource({
		url: "arijentek_core.api.teams_permissons.get_departments",
		auto: false,
	});

	const designationsResource = createResource({
		url: "arijentek_core.api.teams_permissons.get_designations",
		auto: false,
	});

	const employmentTypesResource = createResource({
		url: "arijentek_core.api.teams_permissons.get_employment_types",
		auto: false,
	});

	const gendersResource = createResource({
		url: "arijentek_core.api.teams_permissons.get_genders",
		auto: false,
	});

	const usersListResource = createResource({
		url: "arijentek_core.api.teams_permissons.get_users_list",
		auto: false,
	});

	const employeeListResource = createResource({
		url: "arijentek_core.api.teams_permissons.get_employee_list",
		auto: false,
	});

	const salutationsResource = createResource({
		url: "arijentek_core.api.teams_permissons.get_salutations",
		auto: false,
	});

	const branchesResource = createResource({
		url: "arijentek_core.api.teams_permissons.get_branches",
		auto: false,
	});

	const employeeGradesResource = createResource({
		url: "arijentek_core.api.teams_permissons.get_employee_grades",
		auto: false,
	});

	const shiftTypesResource = createResource({
		url: "arijentek_core.api.roster.get_shift_types",
		auto: false,
	});

	const rolesResource = createResource({
		url: "arijentek_core.api.teams_permissons.get_roles",
		auto: false,
	});

	const unlinkedUsersResource = createResource({
		url: "arijentek_core.api.teams_permissons.get_users_list",
		params: {
			no_employees: "true"
		},
		auto: false,
	});

	const unlinkedEmployeesResource = createResource({
		url: "arijentek_core.api.teams_permissons.get_unlinked_employees",
		auto: false,
	});

	const timezonesResource = createResource({
		url: "arijentek_core.api.teams_permissons.get_timezones",
		auto: false,
	});

	async function loadPermissions(consolidatedPerms = null) {
		let perms = consolidatedPerms;
		if (!perms) {
			const json = await fetchPortalPermissionsCached("arijentek_core");
			perms = json?.team;
		}
		if (perms) {
			permissionResource.data = perms.can_create_employee;
			readEmployeePermissionResource.data = perms.can_read_employee;
			readUsersPermissionResource.data = perms.can_read_users;
			createUserPermissionResource.data = perms.can_create_user;
			editEmployeePermissionResource.data = perms.can_edit_employee;
			deleteEmployeePermissionResource.data = perms.can_delete_employee;
			editUserPermissionResource.data = perms.can_edit_user;
			deleteUserPermissionResource.data = perms.can_delete_user;
			readDepartmentPermissionResource.data = perms.can_read_department;
			createDepartmentPermissionResource.data = perms.can_create_department;
			deleteDepartmentPermissionResource.data = perms.can_delete_department;
			readDesignationPermissionResource.data = perms.can_read_designation;
			createDesignationPermissionResource.data = perms.can_create_designation;
			editDesignationPermissionResource.data = perms.can_edit_designation;
			deleteDesignationPermissionResource.data = perms.can_delete_designation;
			readBranchPermissionResource.data = perms.can_read_branch;
			createBranchPermissionResource.data = perms.can_create_branch;
			editBranchPermissionResource.data = perms.can_edit_branch;
			deleteBranchPermissionResource.data = perms.can_delete_branch;
			readGenderPermissionResource.data = perms.can_read_gender;
			createGenderPermissionResource.data = perms.can_create_gender;
			editGenderPermissionResource.data = perms.can_edit_gender;
			deleteGenderPermissionResource.data = perms.can_delete_gender;
			readSalutationPermissionResource.data = perms.can_read_salutation;
			createSalutationPermissionResource.data = perms.can_create_salutation;
			editSalutationPermissionResource.data = perms.can_edit_salutation;
			deleteSalutationPermissionResource.data = perms.can_delete_salutation;
			readEmployeeGradePermissionResource.data = perms.can_read_employee_grade;
			createEmployeeGradePermissionResource.data = perms.can_create_employee_grade;
			editEmployeeGradePermissionResource.data = perms.can_edit_employee_grade;
			deleteEmployeeGradePermissionResource.data = perms.can_delete_employee_grade;
			readEmployeeTypePermissionResource.data = perms.can_read_employee_type;
			createEmployeeTypePermissionResource.data = perms.can_create_employee_type;
			editEmployeeTypePermissionResource.data = perms.can_edit_employee_type;
			deleteEmployeeTypePermissionResource.data = perms.can_delete_employee_type;
			readRolePermissionResource.data = perms.can_read_role;
			createRolePermissionResource.data = perms.can_create_role;
			editRolePermissionResource.data = perms.can_edit_role;
			deleteRolePermissionResource.data = perms.can_delete_role;
		}
	}

	let fetchListsPromise = null;
	let lastFetchTime = 0;
	function fetchLists(force = false) {
		const now = Date.now();
		if (!force && lastFetchTime && (now - lastFetchTime < 30000)) {
			return fetchListsPromise || Promise.resolve();
		}
		if (fetchListsPromise && !force) {
			return fetchListsPromise;
		}
		lastFetchTime = now;
		fetchListsPromise = Promise.allSettled([
			departmentsResource.fetch().catch(() => {}),
			designationsResource.fetch().catch(() => {}),
			employmentTypesResource.fetch().catch(() => {}),
			gendersResource.fetch().catch(() => {}),
			usersListResource.fetch().catch(() => {}),
			employeeListResource.fetch().catch(() => {}),
			salutationsResource.fetch().catch(() => {}),
			branchesResource.fetch().catch(() => {}),
			employeeGradesResource.fetch().catch(() => {}),
			shiftTypesResource.fetch().catch(() => {}),
			rolesResource.fetch().catch(() => {}),
			unlinkedUsersResource.fetch().catch(() => {}),
			unlinkedEmployeesResource.fetch().catch(() => {}),
			timezonesResource.fetch().catch(() => {}),
		]).finally(() => {
			fetchListsPromise = null;
		});
		return fetchListsPromise;
	}

	return {
		permissionResource,
		readEmployeePermissionResource,
		readUsersPermissionResource,
		createUserPermissionResource,
		editEmployeePermissionResource,
		deleteEmployeePermissionResource,
		editUserPermissionResource,
		deleteUserPermissionResource,
		readDepartmentPermissionResource,
		createDepartmentPermissionResource,
		deleteDepartmentPermissionResource,
		readDesignationPermissionResource,
		createDesignationPermissionResource,
		editDesignationPermissionResource,
		deleteDesignationPermissionResource,
		readBranchPermissionResource,
		createBranchPermissionResource,
		editBranchPermissionResource,
		deleteBranchPermissionResource,
		readGenderPermissionResource,
		createGenderPermissionResource,
		editGenderPermissionResource,
		deleteGenderPermissionResource,
		readSalutationPermissionResource,
		createSalutationPermissionResource,
		editSalutationPermissionResource,
		deleteSalutationPermissionResource,
		readEmployeeGradePermissionResource,
		createEmployeeGradePermissionResource,
		editEmployeeGradePermissionResource,
		deleteEmployeeGradePermissionResource,
		readEmployeeTypePermissionResource,
		createEmployeeTypePermissionResource,
		editEmployeeTypePermissionResource,
		deleteEmployeeTypePermissionResource,
		readRolePermissionResource,
		createRolePermissionResource,
		editRolePermissionResource,
		deleteRolePermissionResource,
		departmentsResource,
		designationsResource,
		employmentTypesResource,
		gendersResource,
		usersListResource,
		employeeListResource,
		salutationsResource,
		branchesResource,
		employeeGradesResource,
		shiftTypesResource,
		rolesResource,
		unlinkedUsersResource,
		unlinkedEmployeesResource,
		timezonesResource,
		loadPermissions,
		fetchLists,
	};
});
