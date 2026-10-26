<template>
	<ReportDialog
		:show="show"
		title="Salary structure assignments"
		subtitle="Which salary structure each employee is on, and their base."
		:loading="loading"
		:empty="!reportData.length"
		empty-icon="payments"
		empty-title="No structure assignments."
		empty-text="Until a structure is assigned, payroll cannot price a payslip."
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
				<div class="min-w-[170px] flex-1">
					<label class="field-label">Salary structure</label>
					<SearchableDropdown
						v-model="filters.salary_structure"
						:options="filterOptions.salary_structures"
						placeholder="All salary structures"
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
	{ fieldname: 'employee_str', label: 'Employee' },
	{ fieldname: 'department', label: 'Department' },
	{ fieldname: 'designation', label: 'Designation' },
	{ fieldname: 'salary_structure', label: 'Structure' },
	{ fieldname: 'base', label: 'Base salary' },
];

const emitClose = () => {
	emit('close');
};

const loading = ref(false);

const filterOptions = reactive({
	employees: [],
	departments: [],
	designations: [],
	salary_structures: [],
});

const filters = reactive({
	employee: '',
	department: '',
	designation: '',
	salary_structure: '',
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
		const res = await fetch('/api/method/arijentek_core.api.payroll.get_salary_structure_assignment_report_filter_options', {
			method: 'GET',
			headers: { 'Content-Type': 'application/json' },
		});
		if (res.ok) {
			const data = await res.json();
			const msg = data.message || {};
			filterOptions.employees = msg.employees || [];
			filterOptions.departments = msg.departments || [];
			filterOptions.designations = msg.designations || [];
			filterOptions.salary_structures = msg.salary_structures || [];
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
		if (filters.department) params.set('department', filters.department);
		if (filters.designation) params.set('designation', filters.designation);
		if (filters.salary_structure) params.set('salary_structure', filters.salary_structure);

		const res = await fetch(`/api/method/arijentek_core.api.payroll.report_salary_structure_assignment_list?${params.toString()}`, {
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
	filters.employee = '';
	filters.department = '';
	filters.designation = '';
	filters.salary_structure = '';
	fetchReportData();
};

const exportExcel = () => {
	const params = new URLSearchParams();
	if (filters.employee) params.set('employee', filters.employee);
	if (filters.department) params.set('department', filters.department);
	if (filters.designation) params.set('designation', filters.designation);
	if (filters.salary_structure) params.set('salary_structure', filters.salary_structure);
	params.set('export', '1');

	const url = `/api/method/arijentek_core.api.payroll.report_salary_structure_assignment_list?${params.toString()}`;
	window.open(url, '_blank');
};

const exportPDF = () => {
	const params = new URLSearchParams();
	if (filters.employee) params.set('employee', filters.employee);
	if (filters.department) params.set('department', filters.department);
	if (filters.designation) params.set('designation', filters.designation);
	if (filters.salary_structure) params.set('salary_structure', filters.salary_structure);
	params.set('pdf', '1');

	const url = `/api/method/arijentek_core.api.payroll.report_salary_structure_assignment_list?${params.toString()}`;
	window.open(url, '_blank');
};

const formatCurrency = (val) => {
	if (val === undefined || val === null) return '0.00';
	return Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
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
