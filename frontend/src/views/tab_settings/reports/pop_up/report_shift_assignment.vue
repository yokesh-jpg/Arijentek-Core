<template>
	<ReportDialog
		:show="show"
		title="Shift assignments"
		subtitle="Who is assigned to which shift, and for what dates."
		:loading="loading"
		:empty="!reportData.length"
		empty-icon="event_repeat"
		empty-title="No shift assignments."
		empty-text="Nobody is assigned a shift in this range."
		:count="reportData.length"
		unit="assignment"
		unit-plural="assignments"
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
					<label class="field-label">Department</label>
					<SearchableDropdown
						v-model="filters.department"
						:options="filterOptions.departments"
						placeholder="All departments"
						@change="fetchReportData"
					/>
				</div>
				<div class="min-w-[170px] flex-1">
					<label class="field-label">Designation</label>
					<SearchableDropdown
						v-model="filters.designation"
						:options="filterOptions.designations"
						placeholder="All designations"
						@change="fetchReportData"
					/>
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
					<label class="field-label">Shift type</label>
					<SearchableDropdown
						v-model="filters.shift_type"
						:options="filterOptions.shift_types"
						placeholder="All shift types"
						@change="fetchReportData"
					/>
				</div>
			</div>
		</template>
		<div class="overflow-x-auto table-scroll">
			<ReportTable :columns="columns" :rows="reportData" />
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

const emitClose = () => {
	emit('close');
};

const loading = ref(false);

const filterOptions = reactive({
	departments: [],
	designations: [],
	employees: [],
	shift_types: [],
});

const getDefaultDates = () => {
	const now = new Date();
	const yyyy = now.getFullYear();
	const mm = String(now.getMonth() + 1).padStart(2, '0');
	const firstDay = `${yyyy}-${mm}-01`;
	const lastDayObj = new Date(yyyy, now.getMonth() + 1, 0);
	const lastDay = `${yyyy}-${mm}-${String(lastDayObj.getDate()).padStart(2, '0')}`;
	return { fromDate: firstDay, toDate: lastDay };
};

const defaultDates = getDefaultDates();

const filters = reactive({
	fromDate: defaultDates.fromDate,
	toDate: defaultDates.toDate,
	preset: 'This Month',
	department: '',
	designation: '',
	employee: '',
	shift_type: '',
});

const columns = ref([]);
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
		const res = await fetch('/api/method/arijentek_core.api.roster.get_shift_assignment_report_filter_options', {
			method: 'GET',
			headers: { 'Content-Type': 'application/json' },
		});
		if (res.ok) {
			const data = await res.json();
			const msg = data.message || {};
			filterOptions.departments = msg.departments || [];
			filterOptions.designations = msg.designations || [];
			filterOptions.employees = msg.employees || [];
			filterOptions.shift_types = msg.shift_types || [];
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
		if (filters.department) params.set('department', filters.department);
		if (filters.designation) params.set('designation', filters.designation);
		if (filters.employee) params.set('employee', filters.employee);
		if (filters.shift_type) params.set('shift_type', filters.shift_type);

		const res = await fetch(`/api/method/arijentek_core.api.roster.report_shift_assignment_list?${params.toString()}`, {
			method: 'GET',
			headers: { 'Content-Type': 'application/json' },
		});

		if (res.ok) {
			const json = await res.json();
			const result = json.message || {};
			if (result.columns) columns.value = result.columns;
			reportData.value = result.data || [];
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
	filters.preset = 'This Month';
	filters.department = '';
	filters.designation = '';
	filters.employee = '';
	filters.shift_type = '';
	fetchReportData();
};

const exportExcel = () => {
	const params = new URLSearchParams();
	if (filters.fromDate) params.set('from_date', filters.fromDate);
	if (filters.toDate) params.set('to_date', filters.toDate);
	if (filters.department) params.set('department', filters.department);
	if (filters.designation) params.set('designation', filters.designation);
	if (filters.employee) params.set('employee', filters.employee);
	if (filters.shift_type) params.set('shift_type', filters.shift_type);
	params.set('export', '1');

	const url = `/api/method/arijentek_core.api.roster.report_shift_assignment_list?${params.toString()}`;
	window.open(url, '_blank');
};

const exportPDF = () => {
	const params = new URLSearchParams();
	if (filters.fromDate) params.set('from_date', filters.fromDate);
	if (filters.toDate) params.set('to_date', filters.toDate);
	if (filters.department) params.set('department', filters.department);
	if (filters.designation) params.set('designation', filters.designation);
	if (filters.employee) params.set('employee', filters.employee);
	if (filters.shift_type) params.set('shift_type', filters.shift_type);
	params.set('pdf', '1');

	const url = `/api/method/arijentek_core.api.roster.report_shift_assignment_list?${params.toString()}`;
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
