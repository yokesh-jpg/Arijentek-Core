<template>
	<ReportDialog
		:show="show"
		title="Salary slips"
		subtitle="Gross pay, deductions and net pay per payslip."
		:loading="loading"
		:empty="!reportData.length"
		empty-icon="receipt"
		empty-title="No salary slips."
		empty-text="No payslips exist for this period."
		:count="reportData.length"
		unit="slip"
		unit-plural="slips"
		@close="emitClose"
		@export-excel="exportExcel"
		@export-pdf="exportPDF"
	>
		<template #filters>
			<div class="flex flex-wrap items-end gap-3">
				<div class="min-w-[170px] flex-1">
					<label class="field-label">Employee</label>
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
			<ReportTable :columns="columns" :rows="reportData" />
		</div>
	</ReportDialog>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue';
import SearchableDropdown from '../../../../components/SearchableDropdown.vue';
import SelectField from '../../../../components/SelectField.vue'
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
const currentYear = new Date().getFullYear();

const monthOptions = [
	{ label: 'January', value: 1 },
	{ label: 'February', value: 2 },
	{ label: 'March', value: 3 },
	{ label: 'April', value: 4 },
	{ label: 'May', value: 5 },
	{ label: 'June', value: 6 },
	{ label: 'July', value: 7 },
	{ label: 'August', value: 8 },
	{ label: 'September', value: 9 },
	{ label: 'October', value: 10 },
	{ label: 'November', value: 11 },
	{ label: 'December', value: 12 },
];

const yearOptions = computed(() => {
	const years = [];
	for (let y = currentYear; y >= currentYear - 5; y--) {
		years.push(y);
	}
	return years;
});

const filterOptions = reactive({
	employees: [],
});

const filters = reactive({
	employee: '',
	month: '',
	year: currentYear,
	status: 'Submitted',
});

const columns = ref([]);
const reportData = ref([]);

const totalNetPay = computed(() => {
	return reportData.value.reduce((acc, row) => acc + (parseFloat(row.net_pay) || 0), 0);
});

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
		const res = await fetch('/api/method/arijentek_core.api.reports.get_attendance_report_filter_options', {
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
		if (filters.employee) params.set('employee', filters.employee);
		if (filters.month) params.set('month', filters.month);
		if (filters.year) params.set('year', filters.year);
		if (filters.status) params.set('status', filters.status);

		const res = await fetch(`/api/method/arijentek_core.api.payroll.report_salary_slip_list?${params.toString()}`, {
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
		console.error('Error fetching salary slip report data', e);
		reportData.value = [];
	} finally {
		loading.value = false;
	}
};

const resetFilters = () => {
	filters.employee = '';
	filters.month = '';
	filters.year = currentYear;
	filters.status = 'Submitted';
	fetchReportData();
};

const downloadRowPayslip = (slipName) => {
	const url = `/api/method/arijentek_core.api.payroll.report_salary_slip_list?slip_name=${encodeURIComponent(slipName)}&pdf=1`;
	window.open(url, '_blank');
};

const exportPDF = () => {
	const params = new URLSearchParams();
	if (filters.employee) params.set('employee', filters.employee);
	if (filters.month) params.set('month', filters.month);
	if (filters.year) params.set('year', filters.year);
	if (filters.status) params.set('status', filters.status);
	params.set('pdf', '1');

	const url = `/api/method/arijentek_core.api.payroll.report_salary_slip_list?${params.toString()}`;
	window.open(url, '_blank');
};

const formatCurrency = (val) => {
	const num = parseFloat(val) || 0;
	return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
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
