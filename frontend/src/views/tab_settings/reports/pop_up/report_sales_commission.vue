<template>
	<ReportDialog
		:show="show"
		title="Sales commission"
		subtitle="Invoice contributions per salesperson and the commission they earn."
		:loading="loading"
		:empty="!reportData.length"
		empty-icon="percent"
		empty-title="No commission to show."
		empty-text="No invoices in this range were credited to a salesperson."
		:count="reportData.length"
		unit="salesperson"
		unit-plural="salespeople"
		wide
		@close="emitClose"
		@export-excel="exportExcel"
		@export-pdf="exportPDF"
	>
		<template #filters>
			<div class="flex flex-wrap items-end gap-3">
				<div class="min-w-[200px] flex-1">
					<label class="field-label">Sales date range</label>
					<DateRangePicker
						v-model:fromDate="filters.fromDate"
						v-model:toDate="filters.toDate"
						v-model:preset="filters.preset"
						@change="handleDateRangeChange"
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
				<div class="basis-full flex flex-wrap items-center gap-x-5 gap-y-2 pt-0.5">
					<label class="flex items-center gap-2 text-[13px] text-[#17181B] dark:text-white cursor-pointer select-none shrink-0">
					<input type="checkbox" v-model="filters.eligibleOnly" @change="fetchReportData" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40" />
					Eligible only (over 30,000)
				</label>
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
import { exportReportPdf } from '@/utils/reportExport.js';

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
	employees: [],
	departments: [],
	designations: [],
});

const getDefaultDates = () => {
	const now = new Date();
	const yyyy = now.getFullYear();
	const mm = String(now.getMonth() + 1).padStart(2, '0');
	const firstDay = `${yyyy}-${mm}-01`;
	const lastDay = new Date(yyyy, now.getMonth() + 1, 0).toISOString().split('T')[0];
	return { fromDate: firstDay, toDate: lastDay };
};

const defaultDates = getDefaultDates();

const filters = reactive({
	fromDate: defaultDates.fromDate,
	toDate: defaultDates.toDate,
	preset: 'This Month',
	employee: '',
	department: '',
	designation: '',
	eligibleOnly: false,
});

const handleDateRangeChange = (range) => {
	if (range) {
		filters.fromDate = range.fromDate || '';
		filters.toDate = range.toDate || '';
		filters.preset = range.preset || 'All Time';
	}
	fetchReportData();
};

/* This report names its own columns rather than taking them from the server.
   Fieldtype is declared so the money and count columns right-align. */
const REPORT_COLUMNS = [
	{ fieldname: 'employee_name', label: 'Employee', fieldtype: 'Data' },
	{ fieldname: 'department', label: 'Department', fieldtype: 'Data' },
	{ fieldname: 'designation', label: 'Designation', fieldtype: 'Data' },
	{ fieldname: 'invoice_count', label: 'Invoices', fieldtype: 'Int' },
	{ fieldname: 'total_invoice_value', label: 'Invoice value', fieldtype: 'Currency' },
	{ fieldname: 'contributed_amount', label: 'Contributed', fieldtype: 'Currency' },
	{ fieldname: 'commission_rate', label: 'Rate', fieldtype: 'Data' },
	{ fieldname: 'commission_amount', label: 'Commission', fieldtype: 'Currency' },
	{ fieldname: 'status', label: 'Status', fieldtype: 'Data' },
];

const reportData = ref([]);
const summary = reactive({
	total_employees: 0,
	total_contributed_sales: 0,
	total_commission: 0,
	total_transactions: 0,
	eligible_count: 0,
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
		const res = await fetch('/api/method/arijentek_core.api.sales_history.get_salesperson_filter_meta', {
			method: 'GET',
			headers: { 'Content-Type': 'application/json' },
		});
		if (res.ok) {
			const data = await res.json();
			const msg = data.message || {};
			filterOptions.employees = (msg.employees || []).map((e) => ({
				id: e.name,
				name: e.employee_name ? `${e.employee_name} (${e.name})` : e.name,
			}));
			filterOptions.departments = (msg.departments || []).map((d) => ({
				id: typeof d === 'object' ? d.name || d.id : d,
				name: typeof d === 'object' ? d.name || d.id : d,
			}));
			filterOptions.designations = (msg.designations || []).map((d) => ({
				id: typeof d === 'object' ? d.name || d.id : d,
				name: typeof d === 'object' ? d.name || d.id : d,
			}));
		}
	} catch (e) {
		console.warn('Failed to load commission filter options', e);
	}
};

async function fetchReportData() {
	loading.value = true;
	try {
		const params = new URLSearchParams();
		if (filters.fromDate) params.set('from_date', filters.fromDate);
		if (filters.toDate) params.set('to_date', filters.toDate);
		if (filters.employee) params.set('employee', filters.employee);
		if (filters.department) params.set('department', filters.department);
		if (filters.designation) params.set('designation', filters.designation);
		if (filters.eligibleOnly) params.set('eligible_only', '1');

		const res = await fetch(`/api/method/arijentek_core.api.sales_history.get_employee_sales_commission_summary?${params.toString()}`, {
			method: 'GET',
			headers: { 'Content-Type': 'application/json' },
		});

		if (res.ok) {
			const json = await res.json();
			const payload = json.message || {};
			reportData.value = payload.data || [];
			if (payload.summary) {
				Object.assign(summary, payload.summary);
			}
		} else {
			reportData.value = [];
		}
	} catch (e) {
		console.error('Error fetching sales commission report data', e);
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
	filters.department = '';
	filters.designation = '';
	filters.eligibleOnly = false;
	fetchReportData();
};

const exportExcel = () => {
	const params = new URLSearchParams();
	if (filters.fromDate) params.set('from_date', filters.fromDate);
	if (filters.toDate) params.set('to_date', filters.toDate);
	if (filters.employee) params.set('employee', filters.employee);
	if (filters.department) params.set('department', filters.department);
	if (filters.designation) params.set('designation', filters.designation);
	if (filters.eligibleOnly) params.set('eligible_only', '1');
	params.set('export', '1');

	const url = `/api/method/arijentek_core.api.sales_history.get_employee_sales_commission_summary?${params.toString()}`;
	window.open(url, '_blank');
};

const exportPDF = () => {
	const params = new URLSearchParams();
	if (filters.fromDate) params.set('from_date', filters.fromDate);
	if (filters.toDate) params.set('to_date', filters.toDate);
	if (filters.employee) params.set('employee', filters.employee);
	if (filters.department) params.set('department', filters.department);
	if (filters.designation) params.set('designation', filters.designation);
	if (filters.eligibleOnly) params.set('eligible_only', '1');
	params.set('pdf', '1');

	const url = `/api/method/arijentek_core.api.sales_history.get_employee_sales_commission_summary?${params.toString()}`;
	exportReportPdf({ title: 'Sales Commission Report', url });
};

const formatCurrency = (val) => {
	const num = parseFloat(val) || 0;
	return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
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

