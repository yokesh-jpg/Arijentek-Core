<template>
	<div class="space-y-6">
		<!-- Reports Catalog List -->
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
			<div
				v-for="report in expenseReports"
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
					<span>View and export</span>
					<span class="material-symbols-outlined text-[16px] group-hover:translate-x-1 transition-transform">arrow_forward</span>
				</div>
			</div>
		</div>

		<!-- Expense Claim Pop-up Modal -->
		<ReportExpenseClaim
			:show="activeModal === 'expense_claim_report'"
			@close="activeModal = null"
		/>

		<!-- Expense Type Pop-up Modal -->
		<ReportExpenseType
			:show="activeModal === 'expense_type_report'"
			@close="activeModal = null"
		/>
	</div>
</template>

<script setup>
import { ref } from 'vue';
import ReportExpenseClaim from './pop_up/report_expense_claim.vue';
import ReportExpenseType from './pop_up/report_expense_type.vue';

const activeModal = ref(null);

const expenseReports = [
	{
		id: 'expense_claim_report',
		title: 'Expense Claim Report',
		description: 'View and export expense claims filtered by date range, employee, and status with Excel and PDF export capabilities.',
		icon: 'receipt_long',
		badge: 'Core Report',
		colorClass: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
	},
	{
		id: 'expense_type_report',
		title: 'Expense Type Report',
		description: 'View and export expense claim types filtered by default account with Excel and PDF export capabilities.',
		icon: 'category',
		badge: 'Core Report',
		colorClass: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
	},
];

const openReportModal = (report) => {
	activeModal.value = report.id;
};
</script>
