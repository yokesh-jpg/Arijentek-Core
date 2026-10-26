<template>
	<ReportDialog
		:show="show"
		title="Holiday list assignments"
		subtitle="Which holiday list each person or group is measured against."
		:loading="loading"
		:empty="!reportData.length"
		empty-icon="event"
		empty-title="No holiday lists assigned."
		empty-text="Until a list is assigned, nobody has non-working days set."
		:count="reportData.length"
		unit="assignment"
		unit-plural="assignments"
		@close="emitClose"
		@export-excel="exportExcel"
		@export-pdf="exportPDF"
	>
		<template #filters>
			<div class="flex flex-wrap items-end gap-3">
				<div class="min-w-[170px] flex-1">
					<label class="field-label">Applicable for</label>
					<SearchableDropdown
						v-model="filters.applicable_for"
						:options="filterOptions.applicable_fors"
						placeholder="Anyone"
						@change="fetchReportData"
					/>
				</div>
				<div class="min-w-[200px] flex-1">
					<label class="field-label">Effective date range</label>
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
					<label class="field-label">Holiday list</label>
					<SearchableDropdown
						v-model="filters.holiday_list"
						:options="filterOptions.holiday_lists"
						placeholder="All holiday lists"
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
	{ fieldname: 'name', label: 'Assignment' },
	{ fieldname: 'applicable_for', label: 'Applies to' },
	{ fieldname: 'assigned_to', label: 'Employee ID' },
	{ fieldname: 'employee_name', label: 'Employee' },
	{ fieldname: 'holiday_list', label: 'Holiday list' },
	{ fieldname: 'from_date', label: 'Effective from' },
];

const emitClose = () => {
	emit('close');
};

const loading = ref(false);

const filterOptions = reactive({
	applicable_fors: [],
	employees: [],
	holiday_lists: [],
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
	applicable_for: '',
	fromDate: defaultDates.fromDate,
	toDate: defaultDates.toDate,
	preset: 'This Year',
	employee: '',
	holiday_list: '',
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
		const res = await fetch('/api/method/arijentek_core.api.leave.get_holiday_list_assignment_report_filter_options', {
			method: 'GET',
			headers: { 'Content-Type': 'application/json' },
		});
		if (res.ok) {
			const data = await res.json();
			const msg = data.message || {};
			filterOptions.applicable_fors = msg.applicable_fors || [];
			filterOptions.employees = msg.employees || [];
			filterOptions.holiday_lists = msg.holiday_lists || [];
		}
	} catch (e) {
		console.warn('Failed to load filter options', e);
	}
};

async function fetchReportData() {
	loading.value = true;
	try {
		const params = new URLSearchParams();
		if (filters.applicable_for) params.set('applicable_for', filters.applicable_for);
		if (filters.fromDate) params.set('from_date', filters.fromDate);
		if (filters.toDate) params.set('to_date', filters.toDate);
		if (filters.employee) params.set('employee', filters.employee);
		if (filters.holiday_list) params.set('holiday_list', filters.holiday_list);

		const res = await fetch(`/api/method/arijentek_core.api.leave.report_holiday_list_assignment_list?${params.toString()}`, {
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
	filters.applicable_for = '';
	filters.fromDate = d.fromDate;
	filters.toDate = d.toDate;
	filters.preset = 'This Year';
	filters.employee = '';
	filters.holiday_list = '';
	fetchReportData();
};

const exportExcel = () => {
	const params = new URLSearchParams();
	if (filters.applicable_for) params.set('applicable_for', filters.applicable_for);
	if (filters.fromDate) params.set('from_date', filters.fromDate);
	if (filters.toDate) params.set('to_date', filters.toDate);
	if (filters.employee) params.set('employee', filters.employee);
	if (filters.holiday_list) params.set('holiday_list', filters.holiday_list);
	params.set('export', '1');

	const url = `/api/method/arijentek_core.api.leave.report_holiday_list_assignment_list?${params.toString()}`;
	window.open(url, '_blank');
};

const exportPDF = () => {
	const params = new URLSearchParams();
	if (filters.applicable_for) params.set('applicable_for', filters.applicable_for);
	if (filters.fromDate) params.set('from_date', filters.fromDate);
	if (filters.toDate) params.set('to_date', filters.toDate);
	if (filters.employee) params.set('employee', filters.employee);
	if (filters.holiday_list) params.set('holiday_list', filters.holiday_list);
	params.set('pdf', '1');

	const url = `/api/method/arijentek_core.api.leave.report_holiday_list_assignment_list?${params.toString()}`;
	window.open(url, '_blank');
};

const formatDate = (dateStr) => {
	if (!dateStr) return '';
	return dateStr;
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
