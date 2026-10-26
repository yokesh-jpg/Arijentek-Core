<template>
	<ReportDialog
		:show="show"
		title="Compensatory leave"
		subtitle="Leave earned by working a day off, and whether it has been granted."
		:loading="loading"
		:empty="!reportData.length"
		empty-icon="more_time"
		empty-title="No compensatory leave requests."
		empty-text="Nobody has claimed time back for working a day off in this range."
		:count="reportData.length"
		unit="request"
		unit-plural="requests"
		@close="emitClose"
		@export-excel="exportExcel"
		@export-pdf="exportPDF"
	>
		<template #filters>
			<div class="flex flex-wrap items-end gap-3">
				<div class="min-w-[200px] flex-1">
					<label class="field-label">Work period</label>
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
					<label class="field-label">Status</label>
					<SearchableDropdown
						v-model="filters.status"
						:options="filterOptions.statuses"
						placeholder="Any status"
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
import { ref, reactive, watch, onMounted } from 'vue';
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
	{ fieldname: 'name', label: 'Request' },
	{ fieldname: 'employee_name', label: 'Employee' },
	{ fieldname: 'work_from_date', label: 'Worked from' },
	{ fieldname: 'work_end_date', label: 'Worked to' },
	{ fieldname: 'leave_type', label: 'Leave type' },
	{ fieldname: 'status', label: 'Status' },
];

// --- State ---
const loading = ref(false);
const reportData = ref([]);

const filters = reactive({
	preset: 'This Month',
	fromDate: '',
	toDate: '',
	employee: '',
	status: '',
});

const filterOptions = reactive({
	employees: [],
	statuses: [],
});

// --- Initialization ---
async function fetchFilterOptions() {
	try {
		const res = await fetch('/api/method/arijentek_core.api.leave.get_compensatory_leave_report_filter_options');
		const data = await res.json();
		if (data.message) {
			filterOptions.employees = data.message.employees;
			filterOptions.statuses = data.message.statuses;
		}
	} catch (error) {
		console.error("Error fetching filter options:", error);
	}
};

async function fetchReportData() {
	if (!props.show) return;
	
	loading.value = true;
	try {
		const params = new URLSearchParams();
		if (filters.fromDate) params.append('from_date', filters.fromDate);
		if (filters.toDate) params.append('to_date', filters.toDate);
		if (filters.employee) params.append('employee', filters.employee);
		if (filters.status) params.append('status', filters.status);

		const res = await fetch(`/api/method/arijentek_core.api.leave.report_compensatory_leave_list?${params.toString()}`);
		const data = await res.json();
		
		if (data.message) {
			reportData.value = data.message;
		} else {
			reportData.value = [];
		}
	} catch (error) {
		console.error("Error fetching report data:", error);
		reportData.value = [];
	} finally {
		loading.value = false;
	}
};

// --- Actions ---
const resetFilters = () => {
	filters.preset = 'This Month';
	filters.employee = '';
	filters.status = '';
	fetchReportData();
};

const exportExcel = () => {
	const params = new URLSearchParams();
	if (filters.fromDate) params.append('from_date', filters.fromDate);
	if (filters.toDate) params.append('to_date', filters.toDate);
	if (filters.employee) params.append('employee', filters.employee);
	if (filters.status) params.append('status', filters.status);
	params.append('export', '1');

	window.open(`/api/method/arijentek_core.api.leave.report_compensatory_leave_list?${params.toString()}`, '_blank');
};

const exportPDF = () => {
	const params = new URLSearchParams();
	if (filters.fromDate) params.append('from_date', filters.fromDate);
	if (filters.toDate) params.append('to_date', filters.toDate);
	if (filters.employee) params.append('employee', filters.employee);
	if (filters.status) params.append('status', filters.status);
	params.append('pdf', '1');

	window.open(`/api/method/arijentek_core.api.leave.report_compensatory_leave_list?${params.toString()}`, '_blank');
};

const emitClose = () => {
	emit('close');
};

// --- Utilities ---
const formatDate = (dateString) => {
	if (!dateString) return '';
	const options = { year: 'numeric', month: 'short', day: 'numeric' };
	return new Date(dateString).toLocaleDateString(undefined, options);
};

;

// --- Watchers & Lifecycle ---
watch(() => props.show, (newVal) => {
	if (newVal) {
		if (filterOptions.employees.length === 0) {
			fetchFilterOptions();
		}
		fetchReportData();
	}
});

onMounted(() => {
	// Pre-fetch filter options if needed, but watch(show) will handle it when opened
});
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
