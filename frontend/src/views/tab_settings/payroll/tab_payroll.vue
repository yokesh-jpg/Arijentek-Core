<template>
	<div class="space-y-5 tab-fill">
		<!-- ===== Header ===== -->
		<div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
			<div>
				<h2 class="section-title">Payroll</h2>
				<p class="section-subtitle">Each run produces one salary slip per employee.</p>
			</div>
			<div class="flex items-center gap-2">
				<button v-if="canCreatePayrollEntry" @click="editId = ''; showCreateModal = true" class="btn-primary shrink-0">
					<span class="material-symbols-outlined !text-[18px]">add</span>
					New run
				</button>
			</div>
		</div>

		<div class="glass-card !p-3 flex flex-wrap items-center gap-2">
			<div class="relative flex-1 min-w-[220px]">
				<span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/55 pointer-events-none">search</span>
				<input v-model="searchQuery" type="text" placeholder="Search by run ID" class="field-input !pl-9" aria-label="Search by run ID" />
			</div>
		</div>

		<!-- ===== Table ===== -->
		<DataTable
			:columns="listColumns"
			:rows="pager.state.rows"
			:actions="actionsForPayroll"
			:row-key="'name'"
			:loading="pager.state.loading"
			:empty-text="searchQuery ? 'Nothing matches that search.' : 'No payroll runs yet.'"
			:show-pager="true"
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			:on-row-click="(entry) => openViewPayroll(entry.name)"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
		>
			<template #cell-name="{ row }">
				<div class="flex items-center gap-2 sm:gap-3 min-w-0">
					<span class="avatar-chip !w-7 !h-7 sm:!w-9 sm:!h-9">
						<span class="material-symbols-outlined !text-[16px]">receipt_long</span>
					</span>
					<span class="min-w-0">
						<span class="block break-words leading-snug sm:truncate font-medium">{{ row.name }}</span>
						<span class="block sm:hidden text-xs font-normal text-[#5C6169] dark:text-white/60 leading-snug">
							{{ formatDate(row.start_date) }} – {{ formatDate(row.end_date) }}
						</span>
					</span>
				</div>
			</template>
			<template #cell-period="{ row }">
				<span class="whitespace-nowrap tabular-nums">{{ formatDate(row.start_date) }} – {{ formatDate(row.end_date) }}</span>
			</template>
			<template #cell-basis="{ row }">
				<span class="premium-tag" :class="row.salary_slip_based_on_timesheet ? 'tag-accent' : 'tag-neutral'">
					{{ row.salary_slip_based_on_timesheet ? 'Timesheet' : 'Salary' }}
				</span>
			</template>
			<template #cell-total_net_pay="{ row }">
				<span class="tabular-nums whitespace-nowrap">
					{{ 'USD' }} {{ Number(row.total_net_pay || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
				</span>
			</template>
			<template #cell-status="{ row }">
				<span class="premium-tag" :class="payrollStatusClass(row.status)">{{ row.status }}</span>
			</template>
		</DataTable>

		<!-- Create Modal -->
		<CreatePayroll 
			v-model="showCreateModal"
			:edit-id="editId"
			@save="pager.fetchPage"
		/>

		<!-- View Modal -->
		<ViewPayroll 
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
import { notify, ask } from '@/utils/feedback.js'
import { ref, watch, onMounted } from 'vue';
import { call } from 'frappe-ui';
import { storeToRefs } from 'pinia';
import { usePayrollStore } from '../../../stores/payroll';
import CreatePayroll from '@/views/forms/payroll/create_payroll.vue';
import ViewPayroll from '@/views/page_views/payroll/view_payroll.vue';
import { getErrorMessage } from '@/utils';

const payrollStore = usePayrollStore();
const { canCreatePayrollEntry, canEditPayrollEntry, canDeletePayrollEntry } = storeToRefs(payrollStore);
const editId = ref('');
/* A submitted or cancelled run is final, the same as in ERPNext. */
const isLocked = (e) => e.status === 'Submitted' || e.status === 'Cancelled';

const searchQuery = ref('');
const showCreateModal = ref(false);
const showViewModal = ref(false);
const selectedViewName = ref('');
const deleting = ref(null);

// Filter states
const postingDateStart = ref('');
const postingDateEnd = ref('');
const postingDatePreset = ref('All Time');
const hourlyPaidFilter = ref(false);

const listColumns = [
	{ key: 'name', label: 'Run', className: 'table-td-strong max-w-[170px] sm:max-w-none' },
	{ key: 'period', label: 'Period', className: 'table-td hidden sm:table-cell whitespace-nowrap tabular-nums' },
	{ key: 'basis', label: 'Basis', className: 'table-td hidden lg:table-cell whitespace-nowrap' },
	{ key: 'total_net_pay', label: 'Net pay', align: 'right', className: 'table-td text-right tabular-nums hidden md:table-cell whitespace-nowrap' },
	{ key: 'status', label: 'Status', className: 'table-td w-[92px] sm:w-auto' },
];

function actionsForPayroll(entry) {
	return [
		{
			label: isLocked(entry) ? entry.status + ' runs cannot be edited' : 'Edit',
			icon: 'edit',
			show: canEditPayrollEntry.value,
			disabled: isLocked(entry),
			onClick: () => openEdit(entry.name),
		},
		{ divider: true },
		{
			label: 'Delete',
			icon: 'delete',
			danger: true,
			show: canDeletePayrollEntry.value,
			disabled: deleting.value === entry.name,
			onClick: () => handleDeletePayroll(entry.name),
		},
	];
}

function openViewPayroll(name) {
	selectedViewName.value = name;
	showViewModal.value = true;
}

function openEdit(name) {
	editId.value = name;
	showCreateModal.value = true;
}
function handleEditFromView(data) {
	showViewModal.value = false;
	openEdit(data?.name || selectedViewName.value);
}

async function handleDeletePayroll(name) {
	if (!await ask('Are you sure you want to delete this payroll entry? This action cannot be undone.')) return;
	
	deleting.value = name;
	try {
		await call('arijentek_core.api.payroll.delete_payroll', { name });
		await pager.fetchPage();
	} catch (err) {
		notify(getErrorMessage(err, 'Failed to delete payroll entry.'));
	} finally {
		deleting.value = null;
	}
}

async function fetchPayrollEntries(page, size) {
	try {
		const params = {
			page: page || 1,
			page_size: size || pager.state.size || 10,
		};
		if (searchQuery.value) {
			params.id = searchQuery.value;
		}
		if (postingDateStart.value) {
			params.posting_date_start = postingDateStart.value;
		}
		if (postingDateEnd.value) {
			params.posting_date_end = postingDateEnd.value;
		}
		if (hourlyPaidFilter.value) {
			params.salary_slip_based_on_timesheet = 'true';
		}

		const res = await call('arijentek_core.api.payroll.get_payroll_entries', params);
		const rows = Array.isArray(res) ? res : (res?.data || []);
		const total = Array.isArray(res) ? res.length : Number(res?.total || 0);
		return { rows, total };
	} catch (e) {
		console.error('Failed to fetch payroll entries:', e);
		return { rows: [], total: 0 };
	}
}

const pager = useServerPager((page, size) => fetchPayrollEntries(page, size), { size: 10 });

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

watch([postingDateStart, postingDateEnd, postingDatePreset, hourlyPaidFilter], () => {
	triggerFilterRefresh();
});

onMounted(() => {
	pager.fetchPage();
});

function payrollStatusClass(status) {
	const s = String(status || '').toLowerCase();
	if (s === 'submitted' || s === 'approved' || s === 'paid') return 'tag-emerald';
	if (s === 'draft' || s === 'pending') return 'tag-amber';
	if (s === 'cancelled' || s === 'rejected' || s === 'failed') return 'tag-red';
	return 'tag-neutral';
}
</script>
