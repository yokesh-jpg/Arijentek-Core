<template>
	<div class="tab-page">
		<!-- Tabs -->
		<TabBar>
			<button
				@click="activeTab = 'leave_management'"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'leave_management' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">event_busy</span>
				<span class="tab-label">Leave management</span>
			</button>
			<button
				v-if="leaveStore.canReadCompLeave || leaveStore.canCreateCompLeave"
				@click="activeTab = 'compensatory_leave'"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'compensatory_leave' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">event_repeat</span>
				<span class="tab-label">Compensatory leave</span>
			</button>
			<button
				v-if="leaveStore.canReadLeavePolicyAssignment"
				@click="activeTab = 'leave_policy_assignment'"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'leave_policy_assignment' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">assignment_ind</span>
				<span class="tab-label">Leave policy assignment</span>
			</button>
			<button
				v-if="leaveStore.canReadLeavePolicy"
				@click="activeTab = 'leave_policy'"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'leave_policy' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">policy</span>
				<span class="tab-label">Leave policy</span>
			</button>
			<button
				v-if="leaveStore.canReadLeaveAllocation"
				@click="activeTab = 'leave_allocation'"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'leave_allocation' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">event_available</span>
				<span class="tab-label">Leave allocation</span>
			</button>
			<button
				v-if="leaveStore.canReadLeaveTypes"
				@click="activeTab = 'leave_types'"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'leave_types' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">category</span>
				<span class="tab-label">Leave types</span>
			</button>
			<button
				v-if="leaveStore.canReadLeavePeriod"
				@click="activeTab = 'leave_period'"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'leave_period' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">date_range</span>
				<span class="tab-label">Leave period</span>
			</button>
			<button
				v-if="leaveStore.canReadHolidayListAssignment"
				@click="activeTab = 'holiday_list_assignment'"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'holiday_list_assignment' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">assignment_ind</span>
				<span class="tab-label">Holiday list assignment</span>
			</button>
			<button
				v-if="leaveStore.canReadHolidayList"
				@click="activeTab = 'holiday_list'"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'holiday_list' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">beach_access</span>
				<span class="tab-label">Holiday list</span>
			</button>
		</TabBar>

		<!-- Tab Content -->
		<div class="pb-20 lg:pb-0 tab-fill">
			<TabLeaveManagement 
				v-if="visitedTabs.leave_management" 
				v-show="activeTab === 'leave_management'" 
				:is-active="activeTab === 'leave_management'" 
			/>
			<TabCompensatoryLeave 
				v-if="visitedTabs.compensatory_leave && (leaveStore.canReadCompLeave || leaveStore.canCreateCompLeave)" 
				v-show="activeTab === 'compensatory_leave'" 
			/>
			<TabLeavePolicyAssignment 
				v-if="visitedTabs.leave_policy_assignment && leaveStore.canReadLeavePolicyAssignment" 
				v-show="activeTab === 'leave_policy_assignment'" 
			/>
			<TabLeavePolicy 
				v-if="visitedTabs.leave_policy && leaveStore.canReadLeavePolicy" 
				v-show="activeTab === 'leave_policy'" 
			/>
			<TabLeaveAllocation 
				v-if="visitedTabs.leave_allocation && leaveStore.canReadLeaveAllocation" 
				v-show="activeTab === 'leave_allocation'" 
			/>
			<TabLeaveTypes 
				v-if="visitedTabs.leave_types && leaveStore.canReadLeaveTypes" 
				v-show="activeTab === 'leave_types'" 
			/>
			<TabLeavePeriod 
				v-if="visitedTabs.leave_period && leaveStore.canReadLeavePeriod" 
				v-show="activeTab === 'leave_period'" 
			/>
			<TabHolidayListAssignment 
				v-if="visitedTabs.holiday_list_assignment && leaveStore.canReadHolidayListAssignment" 
				v-show="activeTab === 'holiday_list_assignment'" 
			/>
			<TabHolidayList 
				v-if="visitedTabs.holiday_list && leaveStore.canReadHolidayList" 
				v-show="activeTab === 'holiday_list'" 
			/>
		</div>
	</div>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useLeaveStore } from '@/stores/leave'
import { useEmployeeStore } from '@/stores/employee'
import TabBar from '@/components/TabBar.vue'

defineOptions({ name: 'LeaveView' })

import TabLeaveManagement from './tab_settings/leave/tab_leave_management.vue'
import TabCompensatoryLeave from './tab_settings/leave/tab_compensatory_leave.vue'
import TabLeavePolicyAssignment from './tab_settings/leave/tab_leave_policy_assignment.vue'
import TabLeavePolicy from './tab_settings/leave/tab_leave_policy.vue'
import TabLeaveAllocation from './tab_settings/leave/tab_leave_allocation.vue'
import TabLeaveTypes from './tab_settings/leave/tab_leave_types.vue'
import TabLeavePeriod from './tab_settings/leave/tab_leave_period.vue'
import TabHolidayListAssignment from './tab_settings/holiday_list/tab_holiday_list_assignment.vue'
import TabHolidayList from './tab_settings/holiday_list/tab_holiday_list.vue'

const route = useRoute()
const leaveStore = useLeaveStore()
const employeeStore = useEmployeeStore()

const activeTab = ref(route.query.tab || 'leave_management')

const visitedTabs = reactive({
	leave_management: activeTab.value === 'leave_management',
	compensatory_leave: activeTab.value === 'compensatory_leave',
	leave_policy_assignment: activeTab.value === 'leave_policy_assignment',
	leave_policy: activeTab.value === 'leave_policy',
	leave_allocation: activeTab.value === 'leave_allocation',
	leave_types: activeTab.value === 'leave_types',
	leave_period: activeTab.value === 'leave_period',
	holiday_list_assignment: activeTab.value === 'holiday_list_assignment',
	holiday_list: activeTab.value === 'holiday_list',
})

watch(
	() => route.query.tab,
	(newTab) => {
		if (newTab) {
			activeTab.value = newTab
		}
	}
)

watch(activeTab, (newTab) => {
	if (newTab && visitedTabs[newTab] !== undefined) {
		visitedTabs[newTab] = true
	}
})

onMounted(async () => {
	await employeeStore.init()
	const employeeId = employeeStore.employee?.name
	if (employeeId) {
		leaveStore.init(employeeId)
	}
	await leaveStore.checkApproverStatus()
})
</script>
