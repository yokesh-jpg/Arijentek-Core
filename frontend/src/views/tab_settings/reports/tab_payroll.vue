<template>
	<div class="space-y-6">
		<!-- Reports Catalog List -->
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
			<div
				v-for="report in payrollReports"
				:key="report.id"
				@click="openReportModal(report)"
				class="group bg-white dark:bg-gray-800/80 rounded-[12px] p-5 border border-gray-200 dark:border-gray-700/60 shadow-sm hover:shadow-md hover:border-emerald-500/50 dark:hover:border-emerald-500/50 transition-all duration-200 cursor-pointer flex flex-col justify-between"
			>
				<div>
					<div class="flex items-center justify-between mb-3">
						<div
							class="w-10 h-10 rounded-[12px] flex items-center justify-center"
							:class="report.colorClass || 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'"
						>
							<span class="material-symbols-outlined text-2xl">{{ report.icon }}</span>
						</div>
						<span class="text-xs font-semibold px-2.5 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
							{{ report.badge || 'Report' }}
						</span>
					</div>
					<h3 class="text-base font-semibold text-gray-900 dark:text-white group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
						{{ report.title }}
					</h3>
					<p class="text-xs text-gray-600 dark:text-gray-400 mt-1 line-clamp-2 leading-relaxed">
						{{ report.description }}
					</p>
				</div>
				<div class="mt-4 pt-3 border-t border-gray-100 dark:border-gray-700/40 flex items-center justify-between text-xs font-semibold text-emerald-600 dark:text-emerald-400">
					<span>View & Export PDF</span>
					<span class="material-symbols-outlined text-[16px] group-hover:translate-x-1 transition-transform">arrow_forward</span>
				</div>
			</div>
		</div>

		<!-- Salary Slips & Payslip Pop-up Modal -->
		<ReportSalarySlip
			:show="activeModal === 'salary_slip_report'"
			@close="activeModal = null"
		/>

		<!-- Payroll Entry Pop-up Modal -->
		<ReportPayrollEntry
			:show="activeModal === 'payroll_entry_report'"
			@close="activeModal = null"
		/>

		<!-- Salary Structure Assignment Pop-up Modal -->
		<ReportSalaryStructureAssignment
			:show="activeModal === 'salary_structure_assignment_report'"
			@close="activeModal = null"
		/>
	</div>
</template>

<script setup>
import { ref } from 'vue';
import ReportSalarySlip from './pop_up/report_salary_slip.vue';
import ReportPayrollEntry from './pop_up/report_payroll_entry.vue';
import ReportSalaryStructureAssignment from './pop_up/report_salary_structure_assignment.vue';

const activeModal = ref(null);

const payrollReports = [
	{
		id: 'salary_slip_report',
		title: 'Salary Slips & Payslips',
		description: 'Comprehensive payroll history, earnings, deductions, net pay breakdown, and individual employee payslip PDF downloads.',
		icon: 'account_balance_wallet',
		badge: 'Payslips & PDF',
		colorClass: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
	},
	{
		id: 'payroll_entry_report',
		title: 'Payroll Entry Report',
		description: 'View and export payroll entries filtered by posting date range and employee with comma-separated employee lists.',
		icon: 'payments',
		badge: 'Core Report',
		colorClass: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
	},
	{
		id: 'salary_structure_assignment_report',
		title: 'Salary Structure Assignment Report',
		description: 'View and export salary structure assignments filtered by employee, department, designation, and salary structure.',
		icon: 'badge',
		badge: 'Core Report',
		colorClass: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
	},
];

const openReportModal = (report) => {
	activeModal.value = report.id;
};
</script>
