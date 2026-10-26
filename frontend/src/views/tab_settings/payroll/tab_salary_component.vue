<template>
	<div class="space-y-5 tab-fill">
		<!-- ===== Header ===== -->
		<div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
			<div>
				<h2 class="section-title">Salary components</h2>
				<p class="section-subtitle">The earnings and deductions a structure is built from.</p>
			</div>
			<div class="flex items-center gap-2">
				<button v-if="canCreateSalaryComponent" @click="openCreateModal()" class="btn-primary shrink-0">
					<span class="material-symbols-outlined !text-[18px]">add</span>
					Add component
				</button>
			</div>
		</div>

		<!-- ===== Filters ===== -->
		<div class="glass-card !p-3 flex flex-wrap items-center gap-2">
			<div class="relative flex-[2] min-w-[220px]">
				<span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/55 pointer-events-none">search</span>
				<input v-model="searchQuery" type="text" placeholder="Search components" class="field-input !pl-9" aria-label="Search components" />
			</div>
			<div class="flex-1 min-w-[180px]">
				<SearchableDropdown
					v-model="statusFilter"
					:options="statusOptions"
					placeholder="All types"
					:showAllOption="true"
					allOptionLabel="All types"
				/>
			</div>
		</div>

		<!-- ===== Table ===== -->
		<DataTable
			:columns="listColumns"
			:rows="pager.state.rows"
			:actions="actionsForSalaryComponent"
			:row-key="'name'"
			:loading="pager.state.loading"
			:empty-text="searchQuery ? 'Nothing matches that search.' : 'No salary components yet.'"
			:show-pager="true"
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			:on-row-click="handleRowClick"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
		>
			<template #cell-name="{ row }">
				<div class="flex items-center gap-2 sm:gap-3 min-w-0">
					<span
						class="avatar-chip !w-7 !h-7 sm:!w-9 sm:!h-9 !text-[12px]"
						:class="row.type === 'Deduction' ? '!bg-red-500/[0.12] !text-red-600 dark:text-red-400 dark:!text-red-300' : ''"
					>{{ row.salary_component_abbr || '—' }}</span>
					<div class="min-w-0">
						<span class="block break-words leading-snug sm:truncate font-medium">{{ row.name }}</span>
						<span class="block sm:hidden text-xs font-normal text-[#5C6169] dark:text-white/60 leading-snug">{{ row.type }}</span>
					</div>
				</div>
			</template>
			<template #cell-salary_component_abbr="{ row }">
				<span>{{ row.salary_component_abbr || '—' }}</span>
			</template>
			<template #cell-type="{ row }">
				<span class="premium-tag" :class="row.type === 'Deduction' ? 'tag-red' : 'tag-emerald'">{{ row.type }}</span>
			</template>
		</DataTable>

		<!-- Edit/Create Modal -->
		<CreateSalaryComponent 
			v-model="showModal"
			:editData="selectedEditData"
			@save="pager.fetchPage"
		/>

		<!-- View Pop-up Modal -->
		<div 
			v-if="showViewModal" 
			class="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 bg-[#0B0B0E]/70 backdrop-blur-sm" 
			@click="showViewModal = false"
		>
			<div class="relative w-full max-w-5xl max-h-[90vh] flex flex-col" @click.stop>
				<ViewSalaryComponent 
					v-if="selectedViewId" 
					:id="selectedViewId" 
					@close="showViewModal = false" 
					@refresh="pager.fetchPage" 
					@edit="openEditFromView" 
				/>
			</div>
		</div>
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
import SearchableDropdown from '../../../components/SearchableDropdown.vue';
import CreateSalaryComponent from '../../forms/payroll/create_salary_component.vue';
import ViewSalaryComponent from '../../page_views/payroll/view_salary_component.vue';
import { getErrorMessage } from '@/utils';

const payrollStore = usePayrollStore();
const { canCreateSalaryComponent, canEditSalaryComponent, canDeleteSalaryComponent } = storeToRefs(payrollStore);

const searchQuery = ref('');
const statusFilter = ref('');
const statusOptions = ref([]);
const deleting = ref(null);

const showModal = ref(false);
const selectedEditData = ref(null);

const showViewModal = ref(false);
const selectedViewId = ref(null);

const listColumns = [
	{ key: 'name', label: 'Component', className: 'table-td-strong max-w-[180px] sm:max-w-none' },
	{ key: 'salary_component_abbr', label: 'Abbreviation', className: 'table-td hidden lg:table-cell' },
	{ key: 'type', label: 'Type', className: 'table-td hidden sm:table-cell' },
];

function actionsForSalaryComponent(comp) {
	return [
		{ label: 'Edit', icon: 'edit', show: canEditSalaryComponent.value, onClick: () => handleEdit(comp) },
		{ label: 'Delete', icon: 'delete', danger: true, show: canDeleteSalaryComponent.value, disabled: deleting.value === comp.name, onClick: () => handleDelete(comp) },
	];
}

function handleRowClick(comp) {
	selectedViewId.value = comp.name;
	showViewModal.value = true;
}

function openEditFromView(comp) {
	showViewModal.value = false;
	selectedEditData.value = comp;
	showModal.value = true;
}

function openCreateModal() {
	selectedEditData.value = null;
	showModal.value = true;
}

function handleEdit(comp) {
	selectedEditData.value = comp;
	showModal.value = true;
}

async function handleDelete(comp) {
	if (await ask(`Are you sure you want to delete the salary component "${comp.name}"?`)) {
		deleting.value = comp.name;
		try {
			await call('arijentek_core.api.payroll.delete_salary_component', { name: comp.name });
			await pager.fetchPage();
		} catch (e) {
			console.error('Failed to delete salary component:', e);
			notify(getErrorMessage(e, 'Failed to delete salary component'));
			await pager.fetchPage();
		} finally {
			deleting.value = null;
		}
	}
}

async function fetchStatusOptions() {
	try {
		const res = await call('arijentek_core.api.payroll.get_salary_compent_status');
		statusOptions.value = res || [];
	} catch (e) {
		console.error('Failed to fetch status options:', e);
	}
}

async function fetchSalaryComponents(page, size) {
	try {
		const params = {
			page: page || 1,
			page_size: size || pager.state.size || 10,
		};
		if (searchQuery.value) {
			params.name = searchQuery.value; 
		}
		if (statusFilter.value) {
			params.status = statusFilter.value;
		}
		
		const res = await call('arijentek_core.api.payroll.get_salary_components', params);
		const rows = Array.isArray(res) ? res : (res?.data || []);
		const total = Array.isArray(res) ? res.length : Number(res?.total || 0);
		return { rows, total };
	} catch (e) {
		console.error('Failed to fetch salary components:', e);
		return { rows: [], total: 0 };
	}
}

const pager = useServerPager((page, size) => fetchSalaryComponents(page, size), { size: 10 });

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

watch(statusFilter, () => {
	triggerFilterRefresh();
});

onMounted(() => {
	fetchStatusOptions();
	pager.fetchPage();
});
</script>
