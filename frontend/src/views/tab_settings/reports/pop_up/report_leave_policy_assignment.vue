<template>
	<ReportDialog
		:show="show"
		title="Leave policy assignments"
		subtitle="Which leave policy applies to each person, and for how long."
		:loading="loading"
		:empty="!reportData.length"
		empty-icon="policy"
		empty-title="No leave policies assigned."
		empty-text="A policy sets how much leave of each type a person accrues."
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
					<label class="field-label">Leave policy</label>
					<SearchableDropdown
						v-model="filters.leave_policy"
						:options="filterOptions.leave_policies"
						placeholder="All leave policies"
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
	{ fieldname: 'employee', label: 'Employee ID' },
	{ fieldname: 'employee_name', label: 'Employee' },
	{ fieldname: 'leave_policy', label: 'Policy' },
	{ fieldname: 'effective_from', label: 'From' },
	{ fieldname: 'effective_to', label: 'To' },
];

const emitClose = () => {
	emit('close');
};

const loading = ref(false);

const filterOptions = reactive({
	employees: [],
	leave_policies: [],
});

const filters = reactive({
	employee: '',
	leave_policy: '',
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
		const res = await fetch('/api/method/arijentek_core.api.leave.get_leave_policy_assignment_report_filter_options', {
			method: 'GET',
			headers: { 'Content-Type': 'application/json' },
		});
		if (res.ok) {
			const data = await res.json();
			const msg = data.message || {};
			filterOptions.employees = msg.employees || [];
			filterOptions.leave_policies = msg.leave_policies || [];
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
		if (filters.leave_policy) params.set('leave_policy', filters.leave_policy);

		const res = await fetch(`/api/method/arijentek_core.api.leave.report_leave_policy_assignment_list?${params.toString()}`, {
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
	filters.leave_policy = '';
	fetchReportData();
};

const exportExcel = () => {
	const params = new URLSearchParams();
	if (filters.employee) params.set('employee', filters.employee);
	if (filters.leave_policy) params.set('leave_policy', filters.leave_policy);
	params.set('export', '1');

	const url = `/api/method/arijentek_core.api.leave.report_leave_policy_assignment_list?${params.toString()}`;
	window.open(url, '_blank');
};

const exportPDF = () => {
	const params = new URLSearchParams();
	if (filters.employee) params.set('employee', filters.employee);
	if (filters.leave_policy) params.set('leave_policy', filters.leave_policy);
	params.set('pdf', '1');

	const url = `/api/method/arijentek_core.api.leave.report_leave_policy_assignment_list?${params.toString()}`;
	window.open(url, '_blank');
};

const formatDate = (dateStr) => {
	if (!dateStr) return '';
	// Expected format: YYYY-MM-DD
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
