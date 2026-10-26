<template>
	<div class="space-y-5 tab-fill">
		<div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
			<div>
				<h2 class="section-title">Shift types</h2>
				<p class="section-subtitle">The shift patterns available when rostering.</p>
			</div>
			<button v-if="canCreate" @click="createNew" class="btn-primary">
				<span class="material-symbols-outlined !text-[18px]">add</span>
				Add shift type
			</button>
		</div>

		<div v-if="loading" class="table-card">
			<div class="empty-state">
				<span class="material-symbols-outlined !text-[28px] text-accent dark:text-accent-light animate-spin">progress_activity</span>
				<p class="empty-state-text">Loading shift types…</p>
			</div>
		</div>

		<div v-else-if="!canView" class="table-card">
			<div class="empty-state">
				<span class="material-symbols-outlined !text-[28px] text-[#C4C7CC] dark:text-white/25">lock</span>
				<p class="empty-state-text">You don't have permission to view shift types.</p>
			</div>
		</div>

		<!-- Table (rows or loading) -->
		<DataTable
			v-else-if="pager.state.rows.length || pager.state.loading"
			:columns="listColumns"
			:rows="pager.state.rows"
			:actions="actionsForRow"
			:row-key="'name'"
			:loading="pager.state.loading"
			empty-text="No shift types yet."
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
		>
			<template #cell-name="{ row }">
				<div class="flex items-center gap-3">
					<span class="w-9 h-9 shrink-0 rounded-[10px] grid place-items-center bg-accent/[0.10] text-accent dark:text-accent-light">
						<span class="material-symbols-outlined !text-[18px]">schedule</span>
					</span>
					<span class="min-w-0">
						<span class="block truncate">{{ row.name }}</span>
						<!-- Same times as the Hours column, which is hidden at this
						     width so the row's actions stay on screen. -->
						<span class="sm:hidden block text-xs font-normal tabular-nums text-[#5C6169] dark:text-white/60 whitespace-nowrap">
							<template v-if="row.start_time && row.end_time">{{ formatTime(row.start_time) }} – {{ formatTime(row.end_time) }}</template>
							<template v-else>Not set</template>
						</span>
					</span>
				</div>
			</template>
			<template #cell-hours="{ row }">
				<span v-if="row.start_time && row.end_time" class="tabular-nums">{{ formatTime(row.start_time) }} – {{ formatTime(row.end_time) }}</span>
				<span v-else class="text-[#656A72] dark:text-white/30">Not set</span>
			</template>
			<!-- Derived, not stored. A rota is easier to read when the
			     length is on the page than when you subtract it yourself. -->
			<template #cell-length="{ row }">
				<span v-if="shiftLength(row)" class="premium-tag tag-neutral tabular-nums">{{ shiftLength(row) }}</span>
				<span v-else class="text-[#656A72] dark:text-white/30">—</span>
			</template>
		</DataTable>

		<!-- Empty state with Add button -->
		<div v-else class="table-card">
			<div class="empty-state">
				<span class="material-symbols-outlined !text-[28px] text-[#C4C7CC] dark:text-white/25">schedule</span>
				<p class="empty-state-text">No shift types yet.</p>
				<button v-if="canCreate" @click="createNew" class="btn-secondary !h-9 mt-1">Add the first one</button>
			</div>
		</div>

		<ShiftTypeForm
			v-if="showAddModal"
			:editing-shift="editingShiftData"
			@close="closeModal"
			@saved="onShiftTypeSaved"
		/>
	</div>
</template>

<script setup>
import { notify, ask } from '@/utils/feedback.js'
import DataTable from '@/components/DataTable.vue'
import { useServerPager } from '@/composables/useServerPager'
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { call, createResource } from 'frappe-ui';
import ShiftTypeForm from '../forms/roster/shift_type.vue';
import { getErrorMessage } from '@/utils';
import SelectField from '../../components/SelectField.vue'

const router = useRouter();

const loading = ref(true);
const canView = ref(false);
const canCreate = ref(false);
const canEdit = ref(false);
const canDelete = ref(false);
const deletingId = ref(null);

/* "8h 30m" from the two times. Robustly parses "H:M:S" or "HH:MM:SS". */
function shiftLength(shift) {
	if (!shift?.start_time || !shift?.end_time) return '';
	const parseMinutes = (t) => {
		if (!t || typeof t !== 'string') return NaN;
		const parts = t.split(':').map((p) => parseInt(p, 10));
		if (parts.length < 2 || isNaN(parts[0]) || isNaN(parts[1])) return NaN;
		return parts[0] * 60 + parts[1];
	};
	const startMins = parseMinutes(shift.start_time);
	const endMins = parseMinutes(shift.end_time);
	if (isNaN(startMins) || isNaN(endMins)) return '';
	let d = endMins - startMins;
	if (d <= 0) d += 24 * 60; // a shift that runs past midnight
	const h = Math.floor(d / 60);
	const m = d % 60;
	if (h && m) return `${h}h ${m}m`;
	if (h) return `${h}h`;
	return `${m}m`;
}

/* Server-side fetch: one page at a time (limit_start/limit_page_length) +
   total via get_count. Returns { rows, total } for useServerPager. */
async function fetchShiftTypes(page, pageSize) {
	const offset = (page - 1) * pageSize;
	const [data, total] = await Promise.all([
		call('frappe.client.get_list', {
			doctype: 'Shift Type',
			fields: ['name', 'start_time', 'end_time'],
			order_by: 'name asc',
			limit_start: offset,
			limit_page_length: pageSize,
		}),
		call('frappe.client.get_count', {
			doctype: 'Shift Type',
		}),
	]);
	return { rows: data || [], total: Number(total) || 0 };
}

const pager = useServerPager((page, size) => fetchShiftTypes(page, size), { size: 10 });

/* Column declarations for the list view (order = render order; `className`
   carries the responsive hiding). */
const listColumns = [
	{ key: 'name', label: 'Shift', className: 'table-td-strong' },
	{ key: 'hours', label: 'Hours', className: 'hidden sm:table-cell' },
	{ key: 'length', label: 'Length', className: 'hidden sm:table-cell' },
];

/* Per-row actions, gated by permission. 2+ actions fold into the More dropdown
   (RowActions maxInline=1), so a row never shows delete one mis-click from edit. */
function actionsForRow(row) {
	return [
		{ label: 'Edit', icon: 'edit', show: canEdit.value, onClick: () => editShiftType(row) },
		{ divider: true },
		{ label: deletingId.value === row.name ? 'Deleting…' : 'Delete', icon: 'delete', danger: true, show: canDelete.value, disabled: deletingId.value === row.name, onClick: () => deleteShiftType(row.name) },
	];
}

const canViewRes = createResource({
	url: 'arijentek_core.api.roster.can_view_shift_type',
	auto: false,
});

const canCreateRes = createResource({
	url: 'arijentek_core.api.roster.can_user_create_shift_types',
	auto: false,
});

const canEditRes = createResource({
	url: 'arijentek_core.api.roster.can_edit_shift_types',
	auto: false,
});

const canDeleteRes = createResource({
	url: 'arijentek_core.api.roster.can_delete_shift_types',
	auto: false,
});

async function checkPermissions() {
	loading.value = true;
	try {
		const [viewRes, createRes, editRes, delRes] = await Promise.all([
			canViewRes.fetch(),
			canCreateRes.fetch(),
			canEditRes.fetch(),
			canDeleteRes.fetch()
		]);
		canView.value = !!viewRes;
		canCreate.value = !!createRes;
		canEdit.value = !!editRes;
		canDelete.value = !!delRes;

		if (canView.value) {
			pager.fetchPage();
		}
	} catch (err) {
		console.error("Error fetching permissions", err);
	} finally {
		loading.value = false;
	}
}

const showAddModal = ref(false);
const editingShiftData = ref(null);

function createNew() {
    editingShiftData.value = null;
    showAddModal.value = true;
}

function editShiftType(shift) {
    editingShiftData.value = shift;
    showAddModal.value = true;
}

function closeModal() {
    showAddModal.value = false;
    editingShiftData.value = null;
}

function onShiftTypeSaved() {
    closeModal();
    pager.fetchPage();
}

const deleteResource = createResource({
    url: 'arijentek_core.api.roster.delete_shift_type',
    auto: false
});

async function deleteShiftType(name) {
    if (!await ask(`Are you sure you want to delete Shift Type '${name}'?`)) return;
    deletingId.value = name;
    try {
        await deleteResource.submit({ shift_name: name });
        await pager.fetchPage();
    } catch (err) {
        const errMsg = getErrorMessage(err, "Failed to delete shift type.");
        notify(errMsg);
    } finally {
        deletingId.value = null;
    }
}

function formatTime(timeStr) {
    if (!timeStr) return '';
    // timeStr is usually "HH:MM:SS"
    const parts = timeStr.split(':');
    if (parts.length >= 2) {
        let h = parseInt(parts[0], 10);
        let m = parts[1];
        let ampm = h >= 12 ? 'PM' : 'AM';
        h = h % 12;
        h = h ? h : 12;
        return `${h}:${m} ${ampm}`;
    }
    return timeStr;
}

onMounted(() => {
	checkPermissions();
});
</script>
