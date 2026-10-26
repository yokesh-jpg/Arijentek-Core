<template>
	<div class="space-y-5 tab-fill">
		<!-- ===== Header ===== -->
		<div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
			<div>
				<h2 class="section-title">Overtime slips</h2>
				<p class="section-subtitle">Extra hours claimed against an overtime type.</p>
			</div>
			<div class="flex items-center gap-2">
				<button v-if="canCreateOvertimeSlip" @click="handleCreate()" class="btn-primary shrink-0">
					<span class="material-symbols-outlined !text-[18px]">add</span>
					New slip
				</button>
			</div>
		</div>

		<div class="glass-card !p-3 flex flex-wrap items-center gap-2">
			<div class="relative flex-1 min-w-[220px]">
				<span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/55 pointer-events-none">search</span>
				<input v-model="searchQuery" type="text" placeholder="Search by ID or name" class="field-input !pl-9" aria-label="Search by ID or name" />
			</div>
		</div>

		<!-- ===== Table ===== -->
		<DataTable
			:columns="listColumns"
			:rows="pager.state.rows"
			:actions="actionsForOvertimeSlip"
			:row-key="'name'"
			:loading="pager.state.loading"
			:empty-text="searchQuery ? 'Nothing matches that search.' : 'No overtime claimed yet.'"
			:show-pager="true"
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			:on-row-click="handleRowClick"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
		>
			<template #cell-employee="{ row }">
				<div class="max-w-[180px] sm:max-w-none">
					<span class="block break-words leading-snug sm:truncate font-medium">{{ row.employee_name }}</span>
					<span class="block sm:hidden text-xs font-normal text-[#5C6169] dark:text-white/60 leading-snug">
						{{ formatDate(row.start_date) }} – {{ formatDate(row.end_date) }}
					</span>
				</div>
			</template>
			<template #cell-period="{ row }">
				<span class="whitespace-nowrap tabular-nums">{{ formatDate(row.start_date) }} – {{ formatDate(row.end_date) }}</span>
			</template>
			<template #cell-overtime_type="{ row }">
				<span class="whitespace-nowrap">{{ row.overtime_type || '—' }}</span>
			</template>
			<template #cell-total_overtime_duration="{ row }">
				<span class="tabular-nums whitespace-nowrap font-medium text-[#17181B] dark:text-white">{{ row.total_overtime_duration || '—' }}</span>
			</template>
			<template #cell-status="{ row }">
				<span class="premium-tag" :class="payrollStatusClass(row.status)">{{ row.status }}</span>
			</template>
		</DataTable>

		<!-- Edit/Create Modal -->
		<CreateOvertimeSlip
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
				<ViewOvertimeSlip
					:can-edit="canEditOvertimeSlip"
					:can-delete="canDeleteOvertimeSlip"
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
import CreateOvertimeSlip from '../../forms/payroll/create_overtime_slip.vue';
import ViewOvertimeSlip from '../../page_views/payroll/view_overtime_slip.vue';
import { getErrorMessage } from '@/utils';

const payrollStore = usePayrollStore();
const { canCreateOvertimeSlip, canEditOvertimeSlip, canDeleteOvertimeSlip } = storeToRefs(payrollStore);

const searchQuery = ref('');
const deleting = ref(null);

const showModal = ref(false);
const selectedEditId = ref(null);

const showViewModal = ref(false);
const selectedViewId = ref(null);

const listColumns = [
	{ key: 'employee', label: 'Employee', className: 'table-td-strong max-w-[180px] sm:max-w-none' },
	{ key: 'period', label: 'Period', className: 'table-td hidden sm:table-cell whitespace-nowrap tabular-nums' },
	{ key: 'overtime_type', label: 'Type', className: 'table-td hidden lg:table-cell whitespace-nowrap' },
	{ key: 'total_overtime_duration', label: 'Hours', align: 'right', className: 'table-td text-right tabular-nums whitespace-nowrap font-medium text-[#17181B] dark:text-white' },
	{ key: 'status', label: 'Status', className: 'table-td hidden md:table-cell' },
];

function actionsForOvertimeSlip(item) {
	return [
		{ label: 'Edit', icon: 'edit', show: canEditOvertimeSlip.value, onClick: () => handleEdit(item) },
		{ label: 'Delete', icon: 'delete', danger: true, show: canDeleteOvertimeSlip.value, disabled: deleting.value === item.name, onClick: () => handleDelete(item) },
	];
}

function handleRowClick(item) {
	selectedViewId.value = item.name;
	showViewModal.value = true;
}

async function fetchOvertimeSlips(page, size) {
	try {
		const params = {
			page: page || 1,
			page_size: size || pager.state.size || 10,
		};
		if (searchQuery.value) {
			params.name = searchQuery.value;
		}
		const res = await call('arijentek_core.api.payroll.get_overtime_slips_list', params);
		const rows = Array.isArray(res) ? res : (res?.data || []);
		const total = Array.isArray(res) ? res.length : Number(res?.total || 0);
		return { rows, total };
	} catch (e) {
		console.error('Failed to fetch overtime slips:', e);
		return { rows: [], total: 0 };
	}
}

const pager = useServerPager((page, size) => fetchOvertimeSlips(page, size), { size: 10 });

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
	if (await ask(`Are you sure you want to cancel and delete Overtime Slip "${item.name}"?`)) {
		deleting.value = item.name;
		try {
			await call('arijentek_core.api.payroll.delete_overtime_slip', { name: item.name });
			await pager.fetchPage();
		} catch (e) {
			console.error('Failed to delete overtime slip:', e);
			notify(getErrorMessage(e, 'Failed to cancel and delete overtime slip.'));
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

/* Submitted is done, Draft is not yet real, Cancelled is neither. */
function payrollStatusClass(status) {
	const s = String(status || '').toLowerCase();
	if (s === 'submitted' || s === 'approved' || s === 'paid') return 'tag-emerald';
	if (s === 'draft' || s === 'pending') return 'tag-amber';
	if (s === 'cancelled' || s === 'rejected' || s === 'failed') return 'tag-red';
	return 'tag-neutral';
}

function formatDate(d) {
	if (!d) return '—';
	return new Date(d + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}
</script>
