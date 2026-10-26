<template>
	<ReportDialog
		:show="show"
		title="Leave balances"
		subtitle="Leave allocated against leave taken, and what remains."
		:loading="loading"
		:empty="!reportData.length"
		empty-icon="beach_access"
		empty-title="No leave allocations."
		empty-text="Nobody has leave allocated for this period."
		:count="reportData.length"
		unit="allocation"
		unit-plural="allocations"
		@close="emitClose"
		@export-excel="exportExcel"
		@export-pdf="exportPDF"
	>
		<template #filters>
			<div class="flex flex-wrap items-end gap-3">
				<div class="min-w-[200px] flex-1">
					<label class="field-label">Leave period / date range</label>
					<DateRangePicker @change="fetchReportData" />
				</div>
				<div class="min-w-[170px] flex-1">
					<label class="field-label">Employee</label>
					<SearchableDropdown
						v-model="filters.employee"
						:options="filterOptions.employees"
						placeholder="All employees"
						@change="fetchReportData"
					/>
				</div>
				<div class="min-w-[170px] flex-1">
					<label class="field-label">Leave type</label>
					<SearchableDropdown
						v-model="filters.leave_type"
						:options="filterOptions.leave_types"
						placeholder="All leave types"
						@change="fetchReportData"
					/>
				</div>
			</div>
		</template>
		<div class="overflow-x-auto table-scroll">
			<ReportTable :columns="REPORT_COLUMNS" :rows="reportData" />
		</div>
	</ReportDialog>
</template>

<script setup>
import { ref, reactive, watch } from 'vue';
import SearchableDropdown from '../../../../components/SearchableDropdown.vue';
import DateRangePicker from '../../../../components/DateRangePicker.vue';
import ReportDialog from '@/components/ReportDialog.vue';
import ReportTable from '@/components/ReportTable.vue';

const props = defineProps({
	show: {
		type: Boolean,
		default: false,
	},
});

const emit = defineEmits(['close']);

/* This report names its own columns rather than taking them from the
   server, so they live here instead of in the markup. */
const REPORT_COLUMNS = [
	{ fieldname: 'name', label: 'Allocation' },
	{ fieldname: 'employee', label: 'Employee ID' },
	{ fieldname: 'employee_name', label: 'Employee' },
	{ fieldname: 'leave_type', label: 'Leave type' },
	{ fieldname: 'from_date', label: 'From' },
	{ fieldname: 'to_date', label: 'To' },
	{ fieldname: 'total_leaves_allocated', label: 'Allocated' },
	{ fieldname: 'leaves_taken', label: 'Taken' },
	{ fieldname: 'leave_balance', label: 'Remaining' },
];

const emitClose = () => {
	emit('close');
};

const loading = ref(false);

const filterOptions = reactive({
	employees: [],
	leave_types: [],
});

const getDefaultDates = () => {
	const now = new Date();
	const yyyy = now.getFullYear();
	const firstDay = `${yyyy}-01-01`;
	const lastDay = `${yyyy}-12-31`;
	return { fromDate: firstDay, toDate: lastDay };
};

const defaultDates = getDefaultDates();

const filters = reactive({
	fromDate: defaultDates.fromDate,
	toDate: defaultDates.toDate,
	preset: 'This Year',
	employee: '',
	leave_type: '',
});

const reportData = ref([]);

watch(
	() => props.show,
	async (newVal) => {
		if (newVal) {
			await fetchFilterOptions();
			await fetchReportData();
		}
	},
	{ immediate: true }
);

async function fetchFilterOptions() {
	try {
		const res = await fetch('/api/method/arijentek_core.api.leave.get_leave_allocation_report_filter_options', {
			method: 'GET',
			headers: { 'Content-Type': 'application/json' },
		});
		if (res.ok) {
			const data = await res.json();
			const msg = data.message || {};
			filterOptions.employees = msg.employees || [];
			filterOptions.leave_types = msg.leave_types || [];
		}
	} catch (e) {
		console.warn('Failed to load filter options', e);
	}
};

async function fetchReportData() {
	loading.value = true;
	try {
		const params = new URLSearchParams();
		if (filters.fromDate) params.set('from_date', filters.fromDate);
		if (filters.toDate) params.set('to_date', filters.toDate);
		if (filters.employee) params.set('employee', filters.employee);
		if (filters.leave_type) params.set('leave_type', filters.leave_type);

		const res = await fetch(`/api/method/arijentek_core.api.leave.report_leave_allocation_balance_list?${params.toString()}`, {
			method: 'GET',
			headers: { 'Content-Type': 'application/json' },
		});

		if (res.ok) {
			const json = await res.json();
			reportData.value = json.message || [];
		} else {
			reportData.value = [];
		}
	} catch (e) {
		console.error('Error fetching report data', e);
		reportData.value = [];
	} finally {
		loading.value = false;
	}
};

const resetFilters = () => {
	const d = getDefaultDates();
	filters.fromDate = d.fromDate;
	filters.toDate = d.toDate;
	filters.preset = 'This Year';
	filters.employee = '';
	filters.leave_type = '';
	fetchReportData();
};

const exportExcel = () => {
	const params = new URLSearchParams();
	if (filters.fromDate) params.set('from_date', filters.fromDate);
	if (filters.toDate) params.set('to_date', filters.toDate);
	if (filters.employee) params.set('employee', filters.employee);
	if (filters.leave_type) params.set('leave_type', filters.leave_type);
	params.set('export', '1');

	const url = `/api/method/arijentek_core.api.leave.report_leave_allocation_balance_list?${params.toString()}`;
	window.open(url, '_blank');
};

const exportPDF = () => {
	const params = new URLSearchParams();
	if (filters.fromDate) params.set('from_date', filters.fromDate);
	if (filters.toDate) params.set('to_date', filters.toDate);
	if (filters.employee) params.set('employee', filters.employee);
	if (filters.leave_type) params.set('leave_type', filters.leave_type);
	params.set('pdf', '1');

	const url = `/api/method/arijentek_core.api.leave.report_leave_allocation_balance_list?${params.toString()}`;
	window.open(url, '_blank');
};

const getBalanceBadgeClass = (balance) => {
	if (balance > 0) {
		return 'text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800';
	} else if (balance === 0) {
		return 'text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/60 border border-amber-200 dark:border-amber-800';
	} else {
		return 'text-rose-700 dark:text-rose-300 bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800';
	}
};
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
	transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
	opacity: 0;
}
</style>
