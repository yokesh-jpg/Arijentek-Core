<template>
	<div class="tab-page">
		<!-- Nav Tabs -->
		<TabBar>
			<button
				@click="activeTab = 'dashboard'"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'dashboard' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">space_dashboard</span>
				<span class="tab-label">Dashboard</span>
			</button>
			<button
				v-if="attendanceStore.readAttendancePermissionResource?.data"
				@click="activeTab = 'attendance'"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'attendance' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">how_to_reg</span>
				<span class="tab-label">Attendance</span>
			</button>
			<button
				v-if="attendanceStore.readEmployeeCheckinPermissionResource?.data"
				@click="activeTab = 'checkins'"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'checkins' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">login</span>
				<span class="tab-label">Checkins</span>
			</button>
			<button
				v-if="attendanceStore.readAttendanceRequestPermissionResource?.data"
				@click="activeTab = 'requests'"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'requests' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">inbox</span>
				<span class="tab-label">Requests</span>
			</button>
			<button
				v-if="attendanceStore.readTimesheetPermissionResource?.data"
				@click="activeTab = 'timesheet'"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'timesheet' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">schedule</span>
				<span class="tab-label">Timesheet</span>
			</button>
		</TabBar>

		<!-- Tab Content -->
		<TabDashboardAttendance 
			v-if="visitedTabs.dashboard" 
			v-show="activeTab === 'dashboard'" 
		/>
		
		<TabAttendance 
			v-if="visitedTabs.attendance"
			v-show="activeTab === 'attendance'" 
			@request-attendance="activeTab = 'requests'; openRequestDialogOnTabChange = true" 
		/>
		
		<TabCheckins 
			v-if="visitedTabs.checkins" 
			v-show="activeTab === 'checkins'" 
		/>
		
		<TabAttendanceRequests 
			v-if="visitedTabs.requests" 
			v-show="activeTab === 'requests'" 
			:open-dialog-on-mount="openRequestDialogOnTabChange" 
			@close-dialog="openRequestDialogOnTabChange = false" 
		/>

		<TabTimesheet 
			v-if="visitedTabs.timesheet" 
			v-show="activeTab === 'timesheet'" 
		/>
	</div>
</template>

<script setup>
import { ref, reactive, watch } from "vue";
import { useRoute } from "vue-router";
import { useAttendanceStore } from "@/stores/attendance";
import TabDashboardAttendance from "./tab_settings/attendance/tab_dashboard_attendance.vue";
import TabAttendance from "./tab_settings/attendance/tab_attendance.vue";
import TabCheckins from "./tab_settings/attendance/tab_checkins.vue";
import TabAttendanceRequests from "./tab_settings/attendance/tab_attendance_requests.vue";
import TabTimesheet from "./tab_settings/attendance/tab_timesheet.vue";
import TabBar from "@/components/TabBar.vue";

defineOptions({ name: "AttendanceView" });

const route = useRoute();
const attendanceStore = useAttendanceStore();
const activeTab = ref(route.query.tab || "dashboard");
const visitedTabs = reactive({
	dashboard: activeTab.value === "dashboard",
	attendance: activeTab.value === "attendance",
	checkins: activeTab.value === "checkins",
	requests: activeTab.value === "requests",
	timesheet: activeTab.value === "timesheet",
});
const openRequestDialogOnTabChange = ref(false);

watch(activeTab, (newTab) => {
	if (newTab && visitedTabs[newTab] !== undefined) {
		visitedTabs[newTab] = true;
	}
});

watch(
  () => route.query.tab,
  (newTab) => {
    if (newTab) {
      activeTab.value = newTab;
    }
  }
);
</script>
