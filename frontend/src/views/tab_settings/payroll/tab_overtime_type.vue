<template>
	<div class="space-y-5 tab-fill">
		<!-- ===== Header ===== -->
		<div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
			<div>
				<h2 class="section-title">Overtime types</h2>
				<p class="section-subtitle">What each extra hour is worth.</p>
			</div>
			<div class="flex items-center gap-2">
				<button v-if="canCreateOvertimeType" @click="handleCreate()" class="btn-primary shrink-0">
					<span class="material-symbols-outlined !text-[18px]">add</span>
					Add type
				</button>
			</div>
		</div>

		<div class="glass-card !p-3 flex flex-wrap items-center gap-2">
			<div class="relative flex-1 min-w-[220px]">
				<span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/55 pointer-events-none">search</span>
				<input v-model="searchQuery" type="text" placeholder="Search overtime types" class="field-input !pl-9" aria-label="Search overtime types" />
			</div>
		</div>

		<!-- ===== Table ===== -->
		<DataTable
			:columns="listColumns"
			:rows="pager.state.rows"
			:actions="actionsForOvertimeType"
			:row-key="'name'"
			:loading="pager.state.loading"
			:empty-text="searchQuery ? 'Nothing matches that search.' : 'No overtime types yet.'"
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
					<span class="avatar-chip !w-7 !h-7 sm:!w-9 sm:!h-9">
						<span class="material-symbols-outlined !text-[16px]">timer</span>
					</span>
					<div class="min-w-0">
						<span class="block break-words leading-snug sm:truncate font-medium">{{ row.name }}</span>
						<span class="block sm:hidden text-xs font-normal text-[#5C6169] dark:text-white/60 leading-snug">{{ row.overtime_calculation_method }}</span>
					</div>
				</div>
			</template>
			<template #cell-overtime_calculation_method="{ row }">
				<span class="whitespace-nowrap">{{ row.overtime_calculation_method || '—' }}</span>
			</template>
			<template #cell-overtime_salary_component="{ row }">
				<span class="whitespace-nowrap">{{ row.overtime_salary_component || '—' }}</span>
			</template>
			<template #cell-standard_multiplier="{ row }">
				<span class="tabular-nums whitespace-nowrap">×{{ row.standard_multiplier }}</span>
			</template>
			<template #cell-weekend_multiplier="{ row }">
				<span class="tabular-nums whitespace-nowrap">×{{ row.weekend_multiplier }}</span>
			</template>
			<template #cell-public_holiday_multiplier="{ row }">
				<span class="tabular-nums whitespace-nowrap">×{{ row.public_holiday_multiplier }}</span>
			</template>
		</DataTable>

		<!-- Edit/Create Modal -->
		<CreateOvertimeType
			v-model="showModal"
			:editId="selectedEditId"
			@save="pager.fetchPage"
		/>

		<!-- View Pop-up Modal -->
		<div 
			v-if="showViewModal" 
			class="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 bg-[#0B0B0E]/70 backdrop-blur-sm" 
			@click="showViewModal = false"
		>
			<div class="relative w-full max-w-4xl max-h-[90vh] flex flex-col" @click.stop>
				<ViewOvertimeType
					:can-edit="canEditOvertimeType"
					:can-delete="canDeleteOvertimeType"
					@edit="(d) => { showViewModal = false; handleEdit(d) }"
					@delete="(d) => { showViewModal = false; handleDelete(d) }" 
					v-if="selectedViewId" 
					:id="selectedViewId" 
					@close="showViewModal = false" 
					@refresh="pager.fetchPage" 
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
import CreateOvertimeType from '../../forms/payroll/create_overtime_type.vue';
import ViewOvertimeType from '../../page_views/payroll/view_overtime_type.vue';
import { getErrorMessage } from '@/utils';

const payrollStore = usePayrollStore();
const { canCreateOvertimeType, canEditOvertimeType, canDeleteOvertimeType } = storeToRefs(payrollStore);

const searchQuery = ref('');
const deleting = ref(null);

const showModal = ref(false);
const selectedEditId = ref(null);

const showViewModal = ref(false);
const selectedViewId = ref(null);

const listColumns = [
	{ key: 'name', label: 'Type', className: 'table-td-strong max-w-[160px] sm:max-w-none' },
	{ key: 'overtime_calculation_method', label: 'Method', className: 'table-td hidden sm:table-cell whitespace-nowrap' },
	{ key: 'overtime_salary_component', label: 'Component', className: 'table-td hidden xl:table-cell whitespace-nowrap' },
	{ key: 'standard_multiplier', label: 'Standard', align: 'right', className: 'table-td text-right tabular-nums whitespace-nowrap' },
	{ key: 'weekend_multiplier', label: 'Weekend', align: 'right', className: 'table-td text-right tabular-nums hidden md:table-cell whitespace-nowrap' },
	{ key: 'public_holiday_multiplier', label: 'Holiday', align: 'right', className: 'table-td text-right tabular-nums hidden md:table-cell whitespace-nowrap' },
];

function actionsForOvertimeType(item) {
	return [
		{ label: 'Edit', icon: 'edit', show: canEditOvertimeType.value, onClick: () => handleEdit(item) },
		{ label: 'Delete', icon: 'delete', danger: true, show: canDeleteOvertimeType.value, disabled: deleting.value === item.name, onClick: () => handleDelete(item) },
	];
}

function handleRowClick(item) {
	selectedViewId.value = item.name;
	showViewModal.value = true;
}

async function fetchOvertimeTypes(page, size) {
	try {
		const params = {
			page: page || 1,
			page_size: size || pager.state.size || 10,
		};
		if (searchQuery.value) {
			params.name = searchQuery.value;
		}
		const res = await call('arijentek_core.api.payroll.get_overtime_types', params);
		const rows = Array.isArray(res) ? res : (res?.data || []);
		const total = Array.isArray(res) ? res.length : Number(res?.total || 0);
		return { rows, total };
	} catch (e) {
		console.error('Failed to fetch overtime types:', e);
		return { rows: [], total: 0 };
	}
}

const pager = useServerPager((page, size) => fetchOvertimeTypes(page, size), { size: 10 });

function triggerFilterRefresh() {
	if (pager.state.page !== 1) {
		pager.state.page = 1;
	} else {
		pager.fetchPage();
	}
}

function handleCreate() {
	selectedEditId.value = null;
	showModal.value = true;
}

function handleEdit(item) {
	selectedEditId.value = item.name;
	showModal.value = true;
}

async function handleDelete(item) {
	if (await ask(`Are you sure you want to delete Overtime Type "${item.name}"?`)) {
		deleting.value = item.name;
		try {
			await call('arijentek_core.api.payroll.delete_overtime_type', { name: item.name });
			await pager.fetchPage();
		} catch (e) {
			console.error('Failed to delete overtime type:', e);
			notify(getErrorMessage(e, 'Failed to delete overtime type'));
			await pager.fetchPage();
		} finally {
			deleting.value = null;
		}
	}
}

// Watch search query for debounced filtering
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
