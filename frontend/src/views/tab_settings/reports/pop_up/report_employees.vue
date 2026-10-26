<template>
	<ReportDialog
		:show="show"
		title="Employee directory"
		subtitle="Every employee with their department, designation and branch."
		:loading="loading"
		:empty="!reportData.length"
		empty-icon="group"
		empty-title="No employees match these filters."
		empty-text="Try widening the department or designation filter."
		:count="reportData.length"
		unit="employee"
		unit-plural="employees"
		@close="emitClose"
		@export-excel="exportExcel"
		@export-pdf="exportPDF"
	>
		<template #filters>
			<div class="flex flex-wrap items-end gap-3">
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
					<label class="field-label">Branch</label>
					<SearchableDropdown
						v-model="filters.branch"
						:options="filterOptions.branches"
						placeholder="All branches"
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

const filterOptions = reactive({
	departments: [],
	branches: [],
	designations: [],
	employees: [],
});

const filters = reactive({
	department: '',
	branch: '',
	designation: '',
	status: 'Active',
	employee: '',
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
		const res = await fetch('/api/method/arijentek_core.api.reports.get_attendance_report_filter_options', {
			method: 'GET',
			headers: { 'Content-Type': 'application/json' },
		});
		if (res.ok) {
			const data = await res.json();
			const msg = data.message || {};
			filterOptions.departments = msg.departments || [];
			filterOptions.branches = msg.branches || [];
			filterOptions.designations = msg.designations || [];
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
		if (filters.department) params.set('department', filters.department);
		if (filters.branch) params.set('branch', filters.branch);
		if (filters.designation) params.set('designation', filters.designation);
		if (filters.status) params.set('status', filters.status);
		if (filters.employee) params.set('employee', filters.employee);

		const res = await fetch(`/api/method/arijentek_core.api.teams_permissons.report_employee_list?${params.toString()}`, {
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
	filters.department = '';
	filters.branch = '';
	filters.designation = '';
	filters.status = 'Active';
	filters.employee = '';
	fetchReportData();
};

const downloadRowProfilePDF = (employeeId) => {
	const url = `/api/method/arijentek_core.api.teams_permissons.generate_employee_profile_pdf?employee=${encodeURIComponent(employeeId)}`;
	window.open(url, '_blank');
};

const exportExcel = () => {
	const params = new URLSearchParams();
	if (filters.department) params.set('department', filters.department);
	if (filters.branch) params.set('branch', filters.branch);
	if (filters.designation) params.set('designation', filters.designation);
	if (filters.status) params.set('status', filters.status);
	if (filters.employee) params.set('employee', filters.employee);
	params.set('export', '1');

	const url = `/api/method/arijentek_core.api.teams_permissons.report_employee_list?${params.toString()}`;
	window.open(url, '_blank');
};

const exportPDF = () => {
	const params = new URLSearchParams();
	if (filters.department) params.set('department', filters.department);
	if (filters.branch) params.set('branch', filters.branch);
	if (filters.designation) params.set('designation', filters.designation);
	if (filters.status) params.set('status', filters.status);
	if (filters.employee) params.set('employee', filters.employee);
	params.set('pdf', '1');

	const url = `/api/method/arijentek_core.api.teams_permissons.report_employee_list?${params.toString()}`;
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
