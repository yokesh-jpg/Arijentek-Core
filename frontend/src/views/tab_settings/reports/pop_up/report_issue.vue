<template>
	<ReportDialog
		:show="show"
		title="Issues"
		subtitle="Workplace issues raised by staff, and where each one stands."
		:loading="loading"
		:empty="!reportData.length"
		empty-icon="inbox"
		empty-title="No issues match these filters."
		empty-text="Try widening the date range or clearing the status filter."
		:count="reportData.length"
		unit="issue"
		unit-plural="issues"
		@close="emitClose"
		@export-excel="exportExcel"
		@export-pdf="exportPDF"
	>
		<template #filters>
			<div class="flex flex-wrap items-end gap-3">
				<div class="min-w-[200px] flex-1">
					<label class="field-label">Date range</label>
					<DateRangePicker @change="fetchReportData" />
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
				<div class="min-w-[170px] flex-1">
					<label class="field-label">Issue type</label>
					<SearchableDropdown
						v-model="filters.issue_type"
						:options="filterOptions.issue_types"
						placeholder="All issue types"
						@change="fetchReportData"
					/>
				</div>
				<div class="min-w-[170px] flex-1">
					<label class="field-label">Raised by</label>
					<SearchableDropdown
						v-model="filters.employee"
						:options="filterOptions.employees"
						placeholder="All employees"
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
	{ fieldname: 'name', label: 'Issue' },
	{ fieldname: 'subject', label: 'Subject' },
	{ fieldname: 'date', label: 'Date' },
	{ fieldname: 'raised_by_str', label: 'Raised by' },
	{ fieldname: 'issue_type', label: 'Type' },
	{ fieldname: 'status', label: 'Status' },
];

const emitClose = () => {
	emit('close');
};

const loading = ref(false);

const filterOptions = reactive({
	employees: [],
	statuses: [],
	issue_types: [],
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
	status: '',
	issue_type: '',
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
		const res = await fetch('/api/method/arijentek_core.api.issues.get_issue_report_filter_options', {
			method: 'GET',
			headers: { 'Content-Type': 'application/json' },
		});
		if (res.ok) {
			const data = await res.json();
			const msg = data.message || {};
			filterOptions.employees = msg.employees || [];
			filterOptions.statuses = msg.statuses || [];
			filterOptions.issue_types = msg.issue_types || [];
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
		if (filters.status) params.set('status', filters.status);
		if (filters.issue_type) params.set('issue_type', filters.issue_type);

		const res = await fetch(`/api/method/arijentek_core.api.issues.report_issue_list?${params.toString()}`, {
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
	filters.status = '';
	filters.issue_type = '';
	fetchReportData();
};

const exportExcel = () => {
	const params = new URLSearchParams();
	if (filters.fromDate) params.set('from_date', filters.fromDate);
	if (filters.toDate) params.set('to_date', filters.toDate);
	if (filters.employee) params.set('employee', filters.employee);
	if (filters.status) params.set('status', filters.status);
	if (filters.issue_type) params.set('issue_type', filters.issue_type);
	params.set('export', '1');

	const url = `/api/method/arijentek_core.api.issues.report_issue_list?${params.toString()}`;
	window.open(url, '_blank');
};

const exportPDF = () => {
	const params = new URLSearchParams();
	if (filters.fromDate) params.set('from_date', filters.fromDate);
	if (filters.toDate) params.set('to_date', filters.toDate);
	if (filters.employee) params.set('employee', filters.employee);
	if (filters.status) params.set('status', filters.status);
	if (filters.issue_type) params.set('issue_type', filters.issue_type);
	params.set('pdf', '1');

	const url = `/api/method/arijentek_core.api.issues.report_issue_list?${params.toString()}`;
	window.open(url, '_blank');
};

;
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
