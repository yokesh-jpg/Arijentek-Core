<template>
	<ReportDialog
		:show="show"
		title="Attendance without clock"
		subtitle="Attendance entries with no clock-in or clock-out time, which timesheet-based payroll cannot price."
		:loading="loading"
		:empty="!reportData.length"
		empty-icon="timer_off"
		empty-title="Every entry has clock times."
		empty-text="Nothing in this range is missing a clock-in or clock-out."
		:count="reportData.length"
		unit="entry"
		unit-plural="entries"
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
					<label class="field-label">Employee</label>
					<SearchableDropdown
						v-model="filters.employee"
						:options="filterOptions.employees"
						placeholder="All employees"
						@change="fetchReportData"
					/>
				</div>
				<div class="basis-full flex flex-wrap items-center gap-x-5 gap-y-2 pt-0.5">
					<label class="flex items-center gap-2 text-[13px] text-[#17181B] dark:text-white cursor-pointer select-none shrink-0">
					<input type="checkbox" v-model="filters.forgotClockOut" @change="fetchReportData" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40" />
					Forgot clock out (clocked in but no clock out)
				</label>
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
import AttendancePageView from '../../../page_views/AttendancePageView.vue';
import CreateAttendance from '../../../../views/forms/attendance/create_attendance.vue';
import ReportDialog from '@/components/ReportDialog.vue';
import ReportTable from '@/components/ReportTable.vue';

const props = defineProps({
	show: {
		type: Boolean,
		default: false,
	},
});

const emit = defineEmits(['close', 'edit']);

const emitClose = () => {
	emit('close');
};

const showAttendanceModal = ref(false);
const selectedAttendanceId = ref('');
const showAddAttendanceDialog = ref(false);
const selectedRecordToEdit = ref(null);

function openAttendance(id) {
	selectedAttendanceId.value = id;
	showAttendanceModal.value = true;
}

function openEditDialog(record) {
	showAttendanceModal.value = false;
	selectedRecordToEdit.value = record;
	showAddAttendanceDialog.value = true;
}

const loading = ref(false);

const filterOptions = reactive({
	employees: [],
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
	employee: '',
	forgotClockOut: true,
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
		const res = await fetch('/api/method/arijentek_core.api.attendance.get_attendance_request_filter_options', {
			method: 'GET',
			headers: { 'Content-Type': 'application/json' },
		});
		if (res.ok) {
			const data = await res.json();
			const msg = data.message || {};
			filterOptions.employees = msg.employees || [];
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
		if (filters.forgotClockOut) params.set('forgot_clock_out', '1');

		const res = await fetch(`/api/method/arijentek_core.api.attendance.report_attendance_no_clock_list?${params.toString()}`, {
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
	filters.employee = '';
	filters.forgotClockOut = true;
	fetchReportData();
};

const exportExcel = () => {
	const params = new URLSearchParams();
	if (filters.fromDate) params.set('from_date', filters.fromDate);
	if (filters.toDate) params.set('to_date', filters.toDate);
	if (filters.employee) params.set('employee', filters.employee);
	if (filters.forgotClockOut) params.set('forgot_clock_out', '1');
	params.set('export', '1');

	const url = `/api/method/arijentek_core.api.attendance.report_attendance_no_clock_list?${params.toString()}`;
	window.open(url, '_blank');
};

const exportPDF = () => {
	const params = new URLSearchParams();
	if (filters.fromDate) params.set('from_date', filters.fromDate);
	if (filters.toDate) params.set('to_date', filters.toDate);
	if (filters.employee) params.set('employee', filters.employee);
	if (filters.forgotClockOut) params.set('forgot_clock_out', '1');
	params.set('pdf', '1');

	const url = `/api/method/arijentek_core.api.attendance.report_attendance_no_clock_list?${params.toString()}`;
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
