<template>
	<div class="tab-page relative">
		<TabBar>
			<button
				v-if="teamStore.readEmployeePermissionResource.data"
				@click="activeTab = 'employees'"
				class="tab-item" :class="{ 'tab-item-active': activeTab === 'employees' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">badge</span>
				<span class="tab-label">Employees</span>
			</button>
			<button
				v-if="teamStore.readUsersPermissionResource.data"
				@click="activeTab = 'users'"
				class="tab-item" :class="{ 'tab-item-active': activeTab === 'users' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">person</span>
				<span class="tab-label">Users</span>
			</button>
			<button
				v-if="teamStore.readRolePermissionResource?.data"
				@click="activeTab = 'roles'"
				class="tab-item" :class="{ 'tab-item-active': activeTab === 'roles' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">admin_panel_settings</span>
				<span class="tab-label">Roles</span>
			</button>
			<button
				v-if="teamStore.readDepartmentPermissionResource?.data"
				@click="activeTab = 'departments'"
				class="tab-item" :class="{ 'tab-item-active': activeTab === 'departments' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">corporate_fare</span>
				<span class="tab-label">Departments</span>
			</button>
			<button
				v-if="teamStore.readDesignationPermissionResource?.data"
				@click="activeTab = 'designations'"
				class="tab-item" :class="{ 'tab-item-active': activeTab === 'designations' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">work</span>
				<span class="tab-label">Designations</span>
			</button>
			<button
				v-if="teamStore.readBranchPermissionResource?.data"
				@click="activeTab = 'branches'"
				class="tab-item" :class="{ 'tab-item-active': activeTab === 'branches' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">store</span>
				<span class="tab-label">Branches</span>
			</button>
			<button
				v-if="teamStore.readEmployeeGradePermissionResource?.data"
				@click="activeTab = 'employee_grades'"
				class="tab-item" :class="{ 'tab-item-active': activeTab === 'employee_grades' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">military_tech</span>
				<span class="tab-label">Grades</span>
			</button>
			<button
				v-if="teamStore.readSalutationPermissionResource?.data"
				@click="activeTab = 'salutations'"
				class="tab-item" :class="{ 'tab-item-active': activeTab === 'salutations' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">record_voice_over</span>
				<span class="tab-label">Salutations</span>
			</button>
			<button
				v-if="teamStore.readGenderPermissionResource?.data"
				@click="activeTab = 'genders'"
				class="tab-item" :class="{ 'tab-item-active': activeTab === 'genders' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">wc</span>
				<span class="tab-label">Genders</span>
			</button>
			<button
				v-if="teamStore.readEmployeeTypePermissionResource?.data"
				@click="activeTab = 'employee_types'"
				class="tab-item" :class="{ 'tab-item-active': activeTab === 'employee_types' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">work_history</span>
				<span class="tab-label">Employment types</span>
			</button>
			<button
				v-if="leaveStore.canReadHolidayListAssignment"
				@click="activeTab = 'holiday_list_assignment'"
				class="tab-item" :class="{ 'tab-item-active': activeTab === 'holiday_list_assignment' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">assignment_ind</span>
				<span class="tab-label">Holiday assignment</span>
			</button>
			<button
				v-if="leaveStore.canReadHolidayList"
				@click="activeTab = 'holiday_list'"
				class="tab-item" :class="{ 'tab-item-active': activeTab === 'holiday_list' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">beach_access</span>
				<span class="tab-label">Holidays</span>
			</button>
		</TabBar>

		<div class="pb-20 lg:pb-0 tab-fill">
			<TabEmployees v-if="activeTab === 'employees' && teamStore.readEmployeePermissionResource.data" />
			<TabUsers v-if="activeTab === 'users' && teamStore.readUsersPermissionResource.data" />
			<TabRoles v-if="activeTab === 'roles' && teamStore.readRolePermissionResource?.data" />
			<TabDepartments v-if="activeTab === 'departments' && teamStore.readDepartmentPermissionResource?.data" />
			<TabDesignations v-if="activeTab === 'designations' && teamStore.readDesignationPermissionResource?.data" />
			<TabBranches v-if="activeTab === 'branches' && teamStore.readBranchPermissionResource?.data" />
			<TabEmployeeGrades v-if="activeTab === 'employee_grades' && teamStore.readEmployeeGradePermissionResource?.data" />
			<TabSalutations v-if="activeTab === 'salutations' && teamStore.readSalutationPermissionResource?.data" />
			<TabGenders v-if="activeTab === 'genders' && teamStore.readGenderPermissionResource?.data" />
			<TabEmployeeTypes v-if="activeTab === 'employee_types' && teamStore.readEmployeeTypePermissionResource?.data" />
			<TabHolidayList v-if="activeTab === 'holiday_list' && leaveStore.canReadHolidayList" />
			<TabHolidayListAssignment v-if="activeTab === 'holiday_list_assignment' && leaveStore.canReadHolidayListAssignment" />
		</div>
	</div>
</template>

<script setup>
import { ref, watch, watchEffect, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useTeamStore } from '@/stores/team'
import { useLeaveStore } from '@/stores/leave'
import TabBar from '@/components/TabBar.vue'

import TabEmployees from './tab_settings/teams/tab_employees.vue'
import TabUsers from './tab_settings/teams/tab_users.vue'
import TabRoles from './tab_settings/teams/tab_roles.vue'
import TabDepartments from './tab_settings/teams/tab_departments.vue'
import TabDesignations from './tab_settings/teams/tab_designations.vue'
import TabBranches from './tab_settings/teams/tab_branches.vue'
import TabEmployeeGrades from './tab_settings/teams/tab_employee_grades.vue'
import TabSalutations from './tab_settings/teams/tab_salutations.vue'
import TabGenders from './tab_settings/teams/tab_genders.vue'
import TabEmployeeTypes from './tab_settings/teams/tab_employee_types.vue'
import TabHolidayList from './tab_settings/holiday_list/tab_holiday_list.vue'
import TabHolidayListAssignment from './tab_settings/holiday_list/tab_holiday_list_assignment.vue'

const route = useRoute()
const teamStore = useTeamStore()
const leaveStore = useLeaveStore()

const activeTab = ref(route.query.tab || '')

watch(
	() => route.query.tab,
	(newTab) => {
		if (newTab) {
			activeTab.value = newTab
		}
	}
)

watchEffect(() => {
	if (!activeTab.value) {
		if (teamStore.readEmployeePermissionResource.data) {
			activeTab.value = 'employees'
		} else if (teamStore.readUsersPermissionResource.data) {
			activeTab.value = 'users'
		} else if (teamStore.readRolePermissionResource?.data) {
			activeTab.value = 'roles'
		} else if (teamStore.readDepartmentPermissionResource?.data) {
			activeTab.value = 'departments'
		} else if (teamStore.readDesignationPermissionResource?.data) {
			activeTab.value = 'designations'
		} else if (teamStore.readBranchPermissionResource?.data) {
			activeTab.value = 'branches'
		} else if (teamStore.readEmployeeGradePermissionResource?.data) {
			activeTab.value = 'employee_grades'
		} else if (teamStore.readSalutationPermissionResource?.data) {
			activeTab.value = 'salutations'
		} else if (teamStore.readGenderPermissionResource?.data) {
			activeTab.value = 'genders'
		} else if (teamStore.readEmployeeTypePermissionResource?.data) {
			activeTab.value = 'employee_types'
		} else if (leaveStore.canReadHolidayListAssignment) {
			activeTab.value = 'holiday_list_assignment'
		} else if (leaveStore.canReadHolidayList) {
			activeTab.value = 'holiday_list'
		}
	}
})

onMounted(() => {
	teamStore.fetchLists()
})
</script>
