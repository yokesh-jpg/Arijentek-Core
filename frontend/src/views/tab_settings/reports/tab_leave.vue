<template>
	<div class="space-y-6">
		<!-- Reports Catalog List -->
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
			<div
				v-for="report in leaveReports"
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

		<!-- Leave Application Pop-up Modal -->
		<ReportLeaveApplication
			:show="activeModal === 'leave_application'"
			@close="activeModal = null"
		/>

		<!-- Compensatory Leave Pop-up Modal -->
		<ReportCompensatoryLeave
			:show="activeModal === 'compensatory_leave'"
			@close="activeModal = null"
		/>

		<!-- Leave Policy Assignment Pop-up Modal -->
		<ReportLeavePolicyAssignment
			:show="activeModal === 'leave_policy_assignment'"
			@close="activeModal = null"
		/>

		<!-- Leave Allocations & Balances Pop-up Modal -->
		<ReportLeaveAllocationBalance
			:show="activeModal === 'leave_allocation_balance'"
			@close="activeModal = null"
		/>

		<!-- Holiday List Assignment Pop-up Modal -->
		<ReportHolidayListAssignment
			:show="activeModal === 'holiday_list_assignment'"
			@close="activeModal = null"
		/>
	</div>
</template>

<script setup>
import { ref } from 'vue';
import ReportLeaveApplication from './pop_up/report_leave_application.vue';
import ReportCompensatoryLeave from './pop_up/report_compensatory_leave.vue';
import ReportLeavePolicyAssignment from './pop_up/report_leave_policy_assignment.vue';
import ReportLeaveAllocationBalance from './pop_up/report_leave_allocation_balance.vue';
import ReportHolidayListAssignment from './pop_up/report_holiday_list_assignment.vue';

const activeModal = ref(null);

const leaveReports = [
	{
		id: 'leave_application',
		title: 'Leave Application Report',
		description: 'View and export leave applications filtered by employee, date range, type, and status.',
		icon: 'beach_access',
		badge: 'Core Report',
	},
	{
		id: 'compensatory_leave',
		title: 'Compensatory Leave Report',
		description: 'View and export compensatory leave requests filtered by work date range, employee, and status.',
		icon: 'more_time',
		badge: 'Core Report',
	},
	{
		id: 'leave_policy_assignment',
		title: 'Leave Policy Assignment Report',
		description: 'View and export leave policy assignments filtered by employee and leave policy.',
		icon: 'assignment_ind',
		badge: 'Core Report',
	},
	{
		id: 'leave_allocation_balance',
		title: 'Leave Allocations & Balances Report',
		description: 'View and export allocated leaves, leaves taken, and remaining balances per employee and leave period.',
		icon: 'account_balance_wallet',
		badge: 'Core Report',
	},
	{
		id: 'holiday_list_assignment',
		title: 'Holiday List Assignment Report',
		description: 'View and export holiday list assignments filtered by employee, holiday list, and date range.',
		icon: 'event_available',
		badge: 'Core Report',
	}
];

const openReportModal = (report) => {
	activeModal.value = report.id;
};
</script>
