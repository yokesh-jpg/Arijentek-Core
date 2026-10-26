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
		<TabDashboardAttendance v-if="activeTab === 'dashboard'" />
		
		<TabAttendance 
			v-if="activeTab === 'attendance'" 
			@request-attendance="activeTab = 'requests'; openRequestDialogOnTabChange = true" 
		/>
		
		<TabCheckins v-if="activeTab === 'checkins'" />
		
		<TabAttendanceRequests 
			v-if="activeTab === 'requests'" 
			:open-dialog-on-mount="openRequestDialogOnTabChange" 
			@close-dialog="openRequestDialogOnTabChange = false" 
		/>

		<TabTimesheet v-if="activeTab === 'timesheet'" />
	</div>
</template>

<script setup>
import { ref, watch } from "vue";
import { useRoute } from "vue-router";
import { useAttendanceStore } from "@/stores/attendance";
import TabDashboardAttendance from "./tab_settings/attendance/tab_dashboard_attendance.vue";
import TabAttendance from "./tab_settings/attendance/tab_attendance.vue";
import TabCheckins from "./tab_settings/attendance/tab_checkins.vue";
import TabAttendanceRequests from "./tab_settings/attendance/tab_attendance_requests.vue";
import TabTimesheet from "./tab_settings/attendance/tab_timesheet.vue";
import TabBar from "@/components/TabBar.vue";

const route = useRoute();
const attendanceStore = useAttendanceStore();
const activeTab = ref(route.query.tab || "dashboard");
const openRequestDialogOnTabChange = ref(false);

watch(
  () => route.query.tab,
  (newTab) => {
    if (newTab) {
      activeTab.value = newTab;
    }
  }
);
</script>
