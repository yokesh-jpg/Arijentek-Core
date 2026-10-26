<template>
	<div class="space-y-5 tab-fill">
		<!-- ===== Header ===== -->
		<div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
			<div>
				<h2 class="section-title">Structure assignments</h2>
				<p class="section-subtitle">Which structure each person is paid against, and their base.</p>
			</div>
			<div class="flex items-center gap-2">
				<button v-if="canCreateSalaryStructureAssignment" @click="openBulkCreateModal()" class="btn-secondary shrink-0">
					<span class="material-symbols-outlined !text-[18px]">group_add</span>
					Bulk assign
				</button>
				<button v-if="canCreateSalaryStructureAssignment" @click="openCreateModal()" class="btn-primary shrink-0">
					<span class="material-symbols-outlined !text-[18px]">add</span>
					Assign
				</button>
			</div>
		</div>

		<!-- ===== Filters ===== -->
		<div class="glass-card !p-3 flex flex-wrap items-center gap-2">
			<div class="relative flex-[2] min-w-[220px]">
				<span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/55 pointer-events-none">search</span>
				<input v-model="searchQuery" type="text" placeholder="Search by ID or name" class="field-input !pl-9" aria-label="Search by ID or name" />
			</div>
			<div class="flex-1 min-w-[160px]">
				<SearchableDropdown
					v-model="employeeFilter"
					:options="employeeOptions"
					placeholder="All employees"
					:showAllOption="true"
					allOptionLabel="All employees"
				/>
			</div>
			<div class="flex-1 min-w-[160px]">
				<SearchableDropdown
					v-model="departmentFilter"
					:options="departmentOptions"
					placeholder="All departments"
					:showAllOption="true"
					allOptionLabel="All departments"
				/>
			</div>
			<div class="flex-1 min-w-[160px]">
				<SearchableDropdown
					v-model="designationFilter"
					:options="designationOptions"
					placeholder="All designations"
					:showAllOption="true"
					allOptionLabel="All designations"
				/>
			</div>
			<div class="flex-1 min-w-[160px]">
				<SearchableDropdown
					v-model="salaryStructureFilter"
					:options="salaryStructureOptions"
					placeholder="All structures"
					:showAllOption="true"
					allOptionLabel="All structures"
				/>
			</div>
		</div>

		<!-- ===== Table ===== -->
		<DataTable
			:columns="listColumns"
			:rows="pager.state.rows"
			:actions="actionsForAssignment"
			:row-key="'name'"
			:loading="pager.state.loading"
			:empty-text="searchQuery ? 'Nothing matches that search.' : 'Nothing assigned yet.'"
			:show-pager="true"
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			:on-row-click="openViewModal"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
		>
			<template #cell-employee="{ row }">
				<div class="max-w-[180px] sm:max-w-none">
					<span class="block break-words leading-snug sm:truncate font-medium">{{ row.employee_name || row.employee }}</span>
					<span class="block sm:hidden text-xs font-normal text-[#5C6169] dark:text-white/60 break-words leading-snug">{{ row.salary_structure }}</span>
				</div>
			</template>
			<template #cell-salary_structure="{ row }">
				<span>{{ row.salary_structure }}</span>
			</template>
			<template #cell-department="{ row }">
				<span>{{ row.department || '—' }}</span>
			</template>
			<template #cell-from_date="{ row }">
				<span class="whitespace-nowrap tabular-nums">{{ formatDate(row.from_date) }}</span>
			</template>
			<template #cell-base="{ row }">
				<span class="tabular-nums whitespace-nowrap font-medium text-[#17181B] dark:text-white">
					{{ row.currency || 'USD' }} {{ Number(row.base || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
				</span>
			</template>
		</DataTable>

		<!-- Edit/Create Modal -->
		<CreateSalaryStructureAssignment 
			v-model="showModal"
			:editData="selectedEditData"
			@save="pager.fetchPage"
		/>

		<!-- Bulk Create Modal -->
		<CreateBulkSalaryStrutureAssignment 
			v-if="canCreateSalaryStructureAssignment"
			v-model="showBulkModal"
			@save="pager.fetchPage"
		/>

		<!-- View Modal -->
		<ViewSalaryStructureAssignment 
			v-model="showViewModal"
			:name="selectedViewName"
			@edit="handleViewEdit"
			@delete="handleViewDelete"
		/>
	</div>
</template>

<script setup>
import DataTable from '@/components/DataTable.vue'
import { useServerPager } from '@/composables/useServerPager.js'
import { notify, ask } from '@/utils/feedback.js'
import { ref, watch, onMounted } from 'vue';
import { call } from 'frappe-ui';
import { storeToRefs } from 'pinia';
import { usePayrollStore } from '../../../stores/payroll';
import { useEmployeeStore } from '../../../stores/employee';
import SearchableDropdown from '../../../components/SearchableDropdown.vue';
import CreateSalaryStructureAssignment from '../../forms/payroll/create_salary_structure_assignment.vue';
import CreateBulkSalaryStrutureAssignment from '../../forms/payroll/create_bulk_salary_struture_assignment.vue';
import ViewSalaryStructureAssignment from '../../page_views/view_salary_structure_assignment.vue';
import { getErrorMessage } from '@/utils';

const payrollStore = usePayrollStore();
const { canCreateSalaryStructureAssignment, canEditSalaryStructureAssignment, canDeleteSalaryStructureAssignment } = storeToRefs(payrollStore);
const employeeStore = useEmployeeStore();

const searchQuery = ref('');

// Filter states
const employeeFilter = ref('');
const departmentFilter = ref('');
const designationFilter = ref('');
const salaryStructureFilter = ref('');

// Filter options lists
const employeeOptions = ref([]);
const departmentOptions = ref([]);
const designationOptions = ref([]);
const salaryStructureOptions = ref([]);

const showModal = ref(false);
const selectedEditData = ref(null);

const showBulkModal = ref(false);

const showViewModal = ref(false);
const selectedViewName = ref('');

const listColumns = [
	{ key: 'employee', label: 'Employee', className: 'table-td-strong max-w-[180px] sm:max-w-none' },
	{ key: 'salary_structure', label: 'Structure', className: 'table-td hidden sm:table-cell' },
	{ key: 'department', label: 'Department', className: 'table-td hidden xl:table-cell' },
	{ key: 'from_date', label: 'From', className: 'table-td hidden lg:table-cell whitespace-nowrap tabular-nums' },
	{ key: 'base', label: 'Base', align: 'right', className: 'table-td text-right tabular-nums whitespace-nowrap font-medium text-[#17181B] dark:text-white' },
];

function actionsForAssignment(assign) {
	return [
		{
			label: 'Edit',
			icon: 'edit',
			show: canEditSalaryStructureAssignment.value,
			onClick: () => handleEdit(assign),
		},
		{ divider: true },
		{
			label: 'Delete',
			icon: 'delete',
			danger: true,
			show: canDeleteSalaryStructureAssignment.value,
			onClick: () => handleDelete(assign),
		},
	];
}

function openViewModal(assign) {
	selectedViewName.value = assign.name;
	showViewModal.value = true;
}

function handleViewEdit(assign) {
	selectedEditData.value = { ...assign };
	showModal.value = true;
}

function handleViewDelete(assign) {
	handleDelete(assign);
}

function openCreateModal() {
	selectedEditData.value = null;
	showModal.value = true;
}

function openBulkCreateModal() {
	showBulkModal.value = true;
}

function handleEdit(assign) {
	selectedEditData.value = { ...assign };
	showModal.value = true;
}

async function handleDelete(assign) {
	if (await ask(`Are you sure you want to delete the assignment for "${assign.employee_name || assign.employee}"?`)) {
		try {
			await call('arijentek_core.api.payroll.delete_salary_structure_assignment', { name: assign.name });
			await pager.fetchPage();
		} catch (e) {
			console.error('Failed to delete assignment:', e);
			notify(getErrorMessage(e, 'Failed to delete assignment'));
		}
	}
}

async function fetchFilterOptions() {
	try {
		const res = await call('arijentek_core.api.payroll.get_salary_structure_assignment_options');
		if (res) {
			employeeOptions.value = (res.employees || []).map(emp => ({
				label: emp.employee_name ? `${emp.employee_name} (${emp.name})` : emp.name,
				value: emp.name
			}));
			departmentOptions.value = (res.departments || []).map(d => ({ label: d, value: d }));
			designationOptions.value = (res.designations || []).map(d => ({ label: d, value: d }));
			salaryStructureOptions.value = (res.salary_structures || []).map(s => ({ label: s, value: s }));
		}
	} catch (e) {
		console.error('Failed to fetch filter options:', e);
	}
}

async function fetchAssignments(page, size) {
	try {
		const params = {
			page: page || 1,
			page_size: size || pager.state.size || 10,
		};
		if (canCreateSalaryStructureAssignment.value) {
			if (searchQuery.value) {
				params.id = searchQuery.value;
			}
			if (employeeFilter.value) {
				params.employee = employeeFilter.value;
			}
			if (departmentFilter.value) {
				params.department = departmentFilter.value;
			}
			if (designationFilter.value) {
				params.designation = designationFilter.value;
			}
			if (salaryStructureFilter.value) {
				params.salary_structure = salaryStructureFilter.value;
			}
		} else {
			const empId = employeeStore.employee?.name;
			if (empId) {
				params.employee = empId;
			}
		}

		const res = await call('arijentek_core.api.payroll.get_salary_structure_assignment', params);
		const rows = Array.isArray(res) ? res : (res?.data || []);
		const total = Array.isArray(res) ? res.length : Number(res?.total || 0);
		return { rows, total };
	} catch (e) {
		console.error('Failed to fetch assignments:', e);
		return { rows: [], total: 0 };
	}
}

const pager = useServerPager((page, size) => fetchAssignments(page, size), { size: 10 });

function triggerFilterRefresh() {
	if (pager.state.page !== 1) {
		pager.state.page = 1;
	} else {
		pager.fetchPage();
	}
}

function formatDate(dateStr) {
	if (!dateStr) return '-';
	const d = new Date(dateStr);
	return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

let debounceTimer;
watch(searchQuery, () => {
	clearTimeout(debounceTimer);
	debounceTimer = setTimeout(() => {
		triggerFilterRefresh();
	}, 300);
});

watch([employeeFilter, departmentFilter, designationFilter, salaryStructureFilter], () => {
	triggerFilterRefresh();
});

onMounted(async () => {
	await employeeStore.init();
	if (canCreateSalaryStructureAssignment.value) {
		await fetchFilterOptions();
	}
	await pager.fetchPage();
});
</script>
