<template>
	<div class="space-y-5 tab-fill">
		<!-- ===== Header ===== -->
		<div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
			<div>
				<h2 class="section-title">Salary slips</h2>
				<p class="section-subtitle">One slip per employee per payroll run.</p>
			</div>
			<div class="flex items-center gap-2">
				<button v-if="canCreateSalarySlip" @click="handleCreate()" class="btn-primary shrink-0">
					<span class="material-symbols-outlined !text-[18px]">add</span>
					New slip
				</button>
			</div>
		</div>

		<!-- ===== Filters ===== -->
		<div class="glass-card !p-3 flex flex-wrap items-center gap-2">
			<div class="relative flex-[2] min-w-[220px]">
				<span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/55 pointer-events-none">search</span>
				<input v-model="searchQuery" type="text" placeholder="Search by slip ID or name" class="field-input !pl-9" aria-label="Search by slip ID or name" />
			</div>
			<div class="flex-1 min-w-[160px]">
				<SearchableDropdown
					v-model="employeeFilter"
					:options="employeeList"
					labelKey="employee_name"
					valueKey="name"
					placeholder="All employees"
					:showAllOption="true"
					allOptionLabel="All employees"
				/>
			</div>
			<div class="flex-1 min-w-[160px]">
				<SearchableDropdown
					v-model="departmentFilter"
					:options="departments"
					placeholder="All departments"
					:showAllOption="true"
					allOptionLabel="All departments"
				/>
			</div>
			<div class="flex-1 min-w-[160px]">
				<SearchableDropdown
					v-model="designationFilter"
					:options="designations"
					placeholder="All designations"
					:showAllOption="true"
					allOptionLabel="All designations"
				/>
			</div>
			<div class="flex-1 min-w-[160px]">
				<SearchableDropdown
					v-model="statusFilter"
					:options="statusOptions"
					placeholder="All statuses"
					:showAllOption="true"
					allOptionLabel="All statuses"
				/>
			</div>
		</div>

		<!-- ===== Table ===== -->
		<DataTable
			:columns="listColumns"
			:rows="pager.state.rows"
			:actions="actionsForSlip"
			:row-key="'name'"
			:loading="pager.state.loading"
			:empty-text="searchQuery ? 'Nothing matches that search.' : 'No salary slips yet.'"
			:show-pager="true"
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			:on-row-click="(slip) => openViewSalarySlip(slip.name)"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
		>
			<template #cell-name="{ row }">
				<div class="max-w-[180px] sm:max-w-none">
					<span class="block tabular-nums break-words leading-snug sm:truncate font-medium">{{ row.name }}</span>
					<span class="block sm:hidden text-xs font-normal text-[#5C6169] dark:text-white/60 leading-snug">
						{{ row.employee_name || row.employee }} · {{ formatDate(row.start_date) }} – {{ formatDate(row.end_date) }}
					</span>
				</div>
			</template>
			<template #cell-employee="{ row }">
				<span class="truncate">{{ row.employee_name || row.employee }}</span>
			</template>
			<template #cell-period="{ row }">
				<span class="whitespace-nowrap tabular-nums">{{ formatDate(row.start_date) }} – {{ formatDate(row.end_date) }}</span>
			</template>
			<template #cell-gross_pay="{ row }">
				<span class="tabular-nums whitespace-nowrap">
					{{ row.currency || 'USD' }} {{ Number(row.gross_pay || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
				</span>
			</template>
			<template #cell-net_pay="{ row }">
				<span class="tabular-nums whitespace-nowrap font-medium text-[#17181B] dark:text-white">
					{{ row.currency || 'USD' }} {{ Number(row.net_pay || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
				</span>
			</template>
			<template #cell-status="{ row }">
				<span class="premium-tag" :class="payrollStatusClass(row.status)">{{ row.status }}</span>
			</template>
		</DataTable>

		<!-- Edit/Create Modal -->
		<CreateSalarySlip
			v-model="showEditModal"
			:editData="selectedEditData"
			@save="pager.fetchPage"
		/>

		<!-- View Modal -->
		<ViewSalarySlip
			v-model="showViewModal"
			:name="selectedViewName"
			@edit="handleEditFromView"
			@refresh="pager.fetchPage"
		/>
	</div>
</template>

<script setup>
import DataTable from '@/components/DataTable.vue'
import { useServerPager } from '@/composables/useServerPager.js'
import { ref, watch, onMounted } from 'vue';
import { call } from 'frappe-ui';
import { storeToRefs } from 'pinia';
import { usePayrollStore } from '../../../stores/payroll';
import { useEmployeeStore } from '../../../stores/employee';
import SearchableDropdown from '@/components/SearchableDropdown.vue';
import CreateSalarySlip from '@/views/forms/payroll/create_salary_slip.vue';
import ViewSalarySlip from '@/views/page_views/payroll/view_salary_slip.vue';
import { notify, ask } from '@/utils/feedback.js';
import { getErrorMessage } from '@/utils';

const payrollStore = usePayrollStore();
const { canCreateSalarySlip, canEditSalarySlip, canDeleteSalarySlip, employeeList } = storeToRefs(payrollStore);
/* Submitted and cancelled slips are final, as in ERPNext and on the payroll runs list. */
const isLocked = (s) => s.status === 'Submitted' || s.status === 'Cancelled';
const deleting = ref(null);

const employeeStore = useEmployeeStore();

// Filter States
const searchQuery = ref('');
const employeeFilter = ref('');
const departmentFilter = ref('');
const designationFilter = ref('');
const branchFilter = ref('');
const statusFilter = ref('');

// Options Lists
const departments = ref([]);
const designations = ref([]);
const branches = ref([]);

const statusOptions = [
	{ label: 'Draft', value: 'Draft' },
	{ label: 'Submitted', value: 'Submitted' },
	{ label: 'Cancelled', value: 'Cancelled' }
];

// Edit modal states
const showEditModal = ref(false);
const selectedEditData = ref(null);

// View modal states
const showViewModal = ref(false);
const selectedViewName = ref('');

const listColumns = [
	{ key: 'name', label: 'Slip', className: 'table-td-strong max-w-[180px] sm:max-w-none' },
	{ key: 'employee', label: 'Employee', className: 'table-td hidden sm:table-cell' },
	{ key: 'period', label: 'Period', className: 'table-td hidden sm:table-cell whitespace-nowrap tabular-nums' },
	{ key: 'gross_pay', label: 'Gross', align: 'right', className: 'table-td text-right tabular-nums hidden lg:table-cell whitespace-nowrap' },
	{ key: 'net_pay', label: 'Net pay', align: 'right', className: 'table-td text-right tabular-nums hidden md:table-cell whitespace-nowrap font-medium text-[#17181B] dark:text-white' },
	{ key: 'status', label: 'Status', className: 'table-td w-[92px] sm:w-auto' },
];

function actionsForSlip(slip) {
	return [
		{
			label: isLocked(slip) ? slip.status + ' slips cannot be edited' : 'Edit',
			icon: 'edit',
			show: canEditSalarySlip.value,
			disabled: isLocked(slip),
			onClick: () => handleEdit(slip),
		},
		{ divider: true },
		{
			label: 'Delete',
			icon: 'delete',
			danger: true,
			show: canDeleteSalarySlip.value,
			disabled: deleting.value === slip.name,
			onClick: () => handleDelete(slip.name),
		},
	];
}

async function handleDelete(name) {
	if (!await ask('Delete this salary slip? This cannot be undone.')) return;
	deleting.value = name;
	try {
		await call('arijentek_core.api.payroll.delete_salary_slip', { name });
		await pager.fetchPage();
	} catch (err) {
		notify(getErrorMessage(err, 'Failed to delete salary slip.'));
	} finally {
		deleting.value = null;
	}
}

async function fetchSalarySlips(page, size) {
	try {
		const params = {
			page: page || 1,
			page_size: size || pager.state.size || 10,
		};
		if (canCreateSalarySlip.value) {
			if (searchQuery.value) params.id = searchQuery.value;
			if (employeeFilter.value) params.employee = employeeFilter.value;
			if (departmentFilter.value) params.department = departmentFilter.value;
			if (designationFilter.value) params.designation = designationFilter.value;
			if (branchFilter.value) params.branch = branchFilter.value;
			if (statusFilter.value) params.status = statusFilter.value;
		} else {
			if (searchQuery.value) params.id = searchQuery.value;
			if (statusFilter.value) params.status = statusFilter.value;
			const empId = employeeStore.employee?.name;
			if (empId) {
				params.employee = empId;
			}
		}

		const res = await call('arijentek_core.api.payroll.get_salary_Slip', params);
		const rows = Array.isArray(res) ? res : (res?.data || []);
		const total = Array.isArray(res) ? res.length : Number(res?.total || 0);
		return { rows, total };
	} catch (e) {
		console.error('Failed to fetch salary slips:', e);
		return { rows: [], total: 0 };
	}
}

const pager = useServerPager((page, size) => fetchSalarySlips(page, size), { size: 10 });

function triggerFilterRefresh() {
	if (pager.state.page !== 1) {
		pager.state.page = 1;
	} else {
		pager.fetchPage();
	}
}

async function fetchFilterOptions() {
	try {
		const res = await call('arijentek_core.api.payroll.get_payroll_entry_options');
		if (res) {
			branches.value = (res.branches || []).map(b => ({ label: b, value: b }));
			designations.value = (res.designations || []).map(d => ({ label: d, value: d }));
			departments.value = (res.departments || []).map(d => ({ label: d, value: d }));
		}
	} catch (e) {
		console.error('Failed to load filter options:', e);
	}
}

function formatDate(dateStr) {
	if (!dateStr) return '-';
	const d = new Date(dateStr);
	return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

function handleCreate() {
	selectedEditData.value = null;
	showEditModal.value = true;
}

function handleEdit(slip) {
	selectedEditData.value = slip;
	showEditModal.value = true;
}

function openViewSalarySlip(name) {
	selectedViewName.value = name;
	showViewModal.value = true;
}

function handleEditFromView(data) {
	selectedEditData.value = data;
	showEditModal.value = true;
}

let debounceTimer;
watch(searchQuery, () => {
	clearTimeout(debounceTimer);
	debounceTimer = setTimeout(() => {
		triggerFilterRefresh();
	}, 300);
});

watch([employeeFilter, departmentFilter, designationFilter, branchFilter, statusFilter], () => {
	triggerFilterRefresh();
});

onMounted(async () => {
	await employeeStore.init();
	if (canCreateSalarySlip.value) {
		await fetchFilterOptions();
		await payrollStore.fetchEmployeeList();
	}
	await pager.fetchPage();
});

function payrollStatusClass(status) {
	const s = String(status || '').toLowerCase();
	if (s === 'submitted' || s === 'approved' || s === 'paid') return 'tag-emerald';
	if (s === 'draft' || s === 'pending') return 'tag-amber';
	if (s === 'cancelled' || s === 'rejected' || s === 'failed') return 'tag-red';
	return 'tag-neutral';
}
</script>
