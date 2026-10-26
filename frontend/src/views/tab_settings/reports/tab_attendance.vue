<template>
	<div class="space-y-6">
		<!-- Reports Catalog List -->
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
			<div
				v-for="report in attendanceReports"
				:key="report.id"
				@click="openReportModal(report)"
				class="group bg-white dark:bg-gray-800/80 rounded-[12px] p-5 border border-gray-200 dark:border-gray-700/60 shadow-sm hover:shadow-md hover:border-primary-500/50 dark:hover:border-primary-500/50 transition-all duration-200 cursor-pointer flex flex-col justify-between"
			>
				<div>
					<div class="flex items-center justify-between mb-3">
						<div class="w-10 h-10 rounded-[12px] bg-emerald-500/10 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
							<span class="material-symbols-outlined text-2xl">{{ report.icon }}</span>
						</div>
						<span class="text-xs font-semibold px-2.5 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
							{{ report.badge || 'Report' }}
						</span>
					</div>
					<h3 class="text-base font-semibold text-gray-900 dark:text-white group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
						{{ report.title }}
					</h3>
					<p class="text-xs text-gray-600 dark:text-gray-400 mt-1 line-clamp-2 leading-relaxed">
						{{ report.description }}
					</p>
				</div>
				<div class="mt-4 pt-3 border-t border-gray-100 dark:border-gray-700/40 flex items-center justify-between text-xs font-semibold text-primary-600 dark:text-primary-400">
					<span>View and export</span>
					<span class="material-symbols-outlined text-[16px] group-hover:translate-x-1 transition-transform">arrow_forward</span>
				</div>
			</div>
		</div>

		<!-- Monthly Attendance Sheet Pop-up Modal -->
		<ReportMonthlyAttendance
			:show="activeModal === 'monthly_attendance_sheet'"
			@close="activeModal = null"
		/>

		<!-- Daily Timesheet Pop-up Modal -->
		<ReportDailyTimesheet
			:show="activeModal === 'daily_timesheet'"
			@close="activeModal = null"
		/>

		<!-- Attendance Request Pop-up Modal -->
		<ReportAttendanceRequest
			:show="activeModal === 'attendance_request'"
			@close="activeModal = null"
		/>

		<!-- Attendance without Clock In/Out Modal -->
		<ReportAttendanceNoClock
			:show="activeModal === 'attendance_no_clock'"
			@close="activeModal = null"
		/>
	</div>
</template>

<script setup>
import { ref } from 'vue';
import ReportMonthlyAttendance from './pop_up/report_monthly_attendance.vue';
import ReportDailyTimesheet from './pop_up/report_daily_timesheet.vue';
import ReportAttendanceRequest from './pop_up/report_attendance_request.vue';
import ReportAttendanceNoClock from './pop_up/report_attendance_no_clock.vue';

const activeModal = ref(null);

const attendanceReports = [
	{
		id: 'monthly_attendance_sheet',
		title: 'Monthly Attendance Sheet',
		description: 'Frappe HR style matrix breakdown of employee attendance by days with status codes (P, A, HD, L, H, WO) and Excel export.',
		icon: 'calendar_month',
		badge: 'Monthly Matrix Export',
	},
	{
		id: 'daily_timesheet',
		title: 'Daily Timesheet',
		description: 'Daily employee hours, shift logs, project allocations, and activity timesheet summary.',
		icon: 'schedule',
		badge: 'Daily Log',
	},
	{
		id: 'attendance_request',
		title: 'Attendance Request',
		description: 'View and export attendance requests filtered by date range, employee, and status.',
		icon: 'rule',
		badge: 'Request Export',
	},
	{
		id: 'attendance_no_clock',
		title: 'Attendance Without Clock',
		description: 'View attendance entries that do not have clock-in and clock-out times for timesheet-based payroll.',
		icon: 'timer_off',
		badge: 'Payroll Prep',
	},
];

const openReportModal = (report) => {
	activeModal.value = report.id;
};
</script>
