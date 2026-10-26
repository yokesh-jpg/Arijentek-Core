<template>
	<div class="space-y-5 tab-fill">
		<!-- ===== Header ===== -->
		<div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
			<div>
				<h2 class="section-title">Salary structures</h2>
				<p class="section-subtitle">The template a person is paid against.</p>
			</div>
			<div class="flex items-center gap-2">
				<button v-if="canCreateSalaryStructure" @click="openCreateModal()" class="btn-primary shrink-0">
					<span class="material-symbols-outlined !text-[18px]">add</span>
					Add structure
				</button>
			</div>
		</div>

		<div class="glass-card !p-3 flex flex-wrap items-center gap-2">
			<div class="relative flex-1 min-w-[220px]">
				<span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/55 pointer-events-none">search</span>
				<input v-model="searchQuery" type="text" placeholder="Search structures" class="field-input !pl-9" aria-label="Search structures" />
			</div>
		</div>

		<!-- ===== Table ===== -->
		<DataTable
			:columns="listColumns"
			:rows="pager.state.rows"
			:actions="actionsForStructure"
			:row-key="'name'"
			:loading="pager.state.loading"
			:empty-text="searchQuery ? 'Nothing matches that search.' : 'No salary structures yet.'"
			:show-pager="true"
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			:on-row-click="openViewModal"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
		>
			<template #cell-name="{ row }">
				<div class="flex items-center gap-2 sm:gap-3 min-w-0">
					<span class="avatar-chip !w-7 !h-7 sm:!w-9 sm:!h-9">
						<span class="material-symbols-outlined !text-[16px]">account_tree</span>
					</span>
					<div class="min-w-0">
						<span class="block break-words leading-snug sm:truncate font-medium">{{ row.name }}</span>
						<span class="block sm:hidden text-xs font-normal text-[#5C6169] dark:text-white/60 leading-snug">{{ row.payroll_frequency }}</span>
					</div>
				</div>
			</template>
			<template #cell-company="{ row }">
				<span>{{ row.company || '—' }}</span>
			</template>
			<template #cell-payroll_frequency="{ row }">
				<span class="whitespace-nowrap">{{ row.payroll_frequency || '—' }}</span>
			</template>
			<template #cell-is_active="{ row }">
				<span class="premium-tag" :class="String(row.is_active) === 'Yes' ? 'tag-emerald' : 'tag-neutral'">
					{{ String(row.is_active) === 'Yes' ? 'Active' : 'Inactive' }}
				</span>
			</template>
		</DataTable>

		<!-- Edit/Create Modal -->
		<CreateSalaryStructure 
			v-model="showModal"
			:editData="selectedEditData"
			@save="pager.fetchPage"
		/>

		<!-- View Modal -->
		<ViewSalaryStructure 
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
import CreateSalaryStructure from '../../forms/payroll/create_salary_structure.vue';
import ViewSalaryStructure from '../../page_views/view_salary_structure.vue';
import { getErrorMessage } from '@/utils';

const payrollStore = usePayrollStore();
const { canCreateSalaryStructure, canEditSalaryStructure, canDeleteSalaryStructure } = storeToRefs(payrollStore);

const searchQuery = ref('');
const deleting = ref(null);

const showModal = ref(false);
const selectedEditData = ref(null);

const showViewModal = ref(false);
const selectedViewName = ref('');

const listColumns = [
	{ key: 'name', label: 'Structure', className: 'table-td-strong max-w-[180px] sm:max-w-none' },
	{ key: 'company', label: 'Company', className: 'table-td hidden lg:table-cell' },
	{ key: 'payroll_frequency', label: 'Frequency', className: 'table-td hidden sm:table-cell whitespace-nowrap' },
	{ key: 'is_active', label: 'Active', className: 'table-td w-[86px] sm:w-auto' },
];

function actionsForStructure(struct) {
	return [
		{ label: 'Edit', icon: 'edit', show: canEditSalaryStructure.value, onClick: () => handleEdit(struct) },
		{ label: 'Delete', icon: 'delete', danger: true, show: canDeleteSalaryStructure.value, disabled: deleting.value === struct.name, onClick: () => handleDelete(struct) },
	];
}

function openViewModal(struct) {
	selectedViewName.value = struct.name;
	showViewModal.value = true;
}

function handleViewEdit(struct) {
	selectedEditData.value = { ...struct };
	showModal.value = true;
}

function handleViewDelete(struct) {
	handleDelete(struct);
}

function openCreateModal() {
	selectedEditData.value = null;
	showModal.value = true;
}

function handleEdit(struct) {
	selectedEditData.value = { ...struct };
	showModal.value = true;
}

async function handleDelete(struct) {
	if (await ask(`Are you sure you want to delete the salary structure "${struct.name}"?`)) {
		deleting.value = struct.name;
		try {
			await call('arijentek_core.api.payroll.delete_salary_structure', { name: struct.name });
			await pager.fetchPage();
		} catch (e) {
			console.error('Failed to delete salary structure:', e);
			notify(getErrorMessage(e, 'Failed to delete salary structure'));
			await pager.fetchPage();
		} finally {
			deleting.value = null;
		}
	}
}

async function fetchSalaryStructures(page, size) {
	try {
		const params = {
			page: page || 1,
			page_size: size || pager.state.size || 10,
		};
		if (searchQuery.value) {
			params.id = searchQuery.value; 
		}
		
		const res = await call('arijentek_core.api.payroll.get_salary_structures', params);
		const rows = Array.isArray(res) ? res : (res?.data || []);
		const total = Array.isArray(res) ? res.length : Number(res?.total || 0);
		return { rows, total };
	} catch (e) {
		console.error('Failed to fetch salary structures:', e);
		return { rows: [], total: 0 };
	}
}

const pager = useServerPager((page, size) => fetchSalaryStructures(page, size), { size: 10 });

function triggerFilterRefresh() {
	if (pager.state.page !== 1) {
		pager.state.page = 1;
	} else {
		pager.fetchPage();
	}
}

// Watch filters to trigger refetch
let debounceTimer;
watch(searchQuery, () => {
	clearTimeout(debounceTimer);
	debounceTimer = setTimeout(() => {
		triggerFilterRefresh();
	}, 300);
});

onMounted(() => {
	pager.fetchPage();
});
</script>
