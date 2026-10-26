<template>
	<ReportDialog
		:show="show"
		title="Leave applications"
		subtitle="Leave requested by staff, the days covered and the decision."
		:loading="loading"
		:empty="!reportData.length"
		empty-icon="beach_access"
		empty-title="No leave applications."
		empty-text="Nobody applied for leave in this range."
		:count="reportData.length"
		unit="application"
		unit-plural="applications"
		@close="emitClose"
		@export-excel="exportExcel"
		@export-pdf="exportPDF"
	>
		<template #filters>
			<div class="flex flex-wrap items-end gap-3">
				<div class="min-w-[200px] flex-1">
					<label class="field-label">Leave period</label>
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
						v-model="filters.leaveType"
						:options="filterOptions.leaveTypes"
						placeholder="All leave types"
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
	{ fieldname: 'name', label: 'Application' },
	{ fieldname: 'employee_name', label: 'Employee' },
	{ fieldname: 'leave_type', label: 'Leave type' },
	{ fieldname: 'from_date', label: 'From' },
	{ fieldname: 'to_date', label: 'To' },
	{ fieldname: 'total_leave_days', label: 'Days' },
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
	leaveType: '',
	status: '',
});

const filterOptions = reactive({
	employees: [],
	leaveTypes: [],
	statuses: [],
});

// --- Initialization ---
async function fetchFilterOptions() {
	try {
		const res = await fetch('/api/method/arijentek_core.api.leave.get_leave_application_report_filter_options');
		const data = await res.json();
		if (data.message) {
			filterOptions.employees = data.message.employees;
			// Adapt strings into objects for SearchableDropdown if needed, 
			// SearchableDropdown handles array of strings well too if value-key and label-key are unset.
			filterOptions.leaveTypes = data.message.leave_types;
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
		if (filters.leaveType) params.append('leave_type', filters.leaveType);
		if (filters.status) params.append('status', filters.status);

		const res = await fetch(`/api/method/arijentek_core.api.leave.report_leave_application_list?${params.toString()}`);
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
	// Resetting preset might not trigger date update immediately, 
	// typically DateRangePicker handles preset->dates sync, 
	// but it's safe to clear them just in case.
	// filters.fromDate = '';
	// filters.toDate = '';
	filters.employee = '';
	filters.leaveType = '';
	filters.status = '';
	fetchReportData();
};

const exportExcel = () => {
	const params = new URLSearchParams();
	if (filters.fromDate) params.append('from_date', filters.fromDate);
	if (filters.toDate) params.append('to_date', filters.toDate);
	if (filters.employee) params.append('employee', filters.employee);
	if (filters.leaveType) params.append('leave_type', filters.leaveType);
	if (filters.status) params.append('status', filters.status);
	params.append('export', '1');

	window.open(`/api/method/arijentek_core.api.leave.report_leave_application_list?${params.toString()}`, '_blank');
};

const exportPDF = () => {
	const params = new URLSearchParams();
	if (filters.fromDate) params.append('from_date', filters.fromDate);
	if (filters.toDate) params.append('to_date', filters.toDate);
	if (filters.employee) params.append('employee', filters.employee);
	if (filters.leaveType) params.append('leave_type', filters.leaveType);
	if (filters.status) params.append('status', filters.status);
	params.append('pdf', '1');

	window.open(`/api/method/arijentek_core.api.leave.report_leave_application_list?${params.toString()}`, '_blank');
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
