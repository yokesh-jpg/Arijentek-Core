<template>
	<div class="space-y-5 tab-fill">
		<div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
			<div>
				<h2 class="section-title">Shift locations</h2>
				<p class="section-subtitle">Where shifts can be rostered.</p>
			</div>
			<button v-if="canCreate" @click="showAddModal = true" class="btn-primary">
				<span class="material-symbols-outlined !text-[18px]">add_location_alt</span>
				Add location
			</button>
		</div>

		<!-- Table (rows or loading) -->
		<DataTable
			v-if="pager.state.rows.length || pager.state.loading"
			:columns="listColumns"
			:rows="pager.state.rows"
			:actions="actionsForRow"
			:row-key="'name'"
			:loading="pager.state.loading"
			empty-text="No shift locations yet."
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
		>
			<template #cell-name="{ row }">
				<div class="flex items-center gap-3">
					<span class="w-9 h-9 shrink-0 rounded-[10px] grid place-items-center bg-accent/[0.10] text-accent dark:text-accent-light">
						<span class="material-symbols-outlined !text-[18px]">location_on</span>
					</span>
					<span class="truncate">{{ row.location_name || row.name }}</span>
				</div>
			</template>
		</DataTable>

		<!-- Empty state with Add button -->
		<div v-else class="table-card">
			<div class="empty-state">
				<span class="material-symbols-outlined !text-[28px] text-[#C4C7CC] dark:text-white/25">location_off</span>
				<p class="empty-state-text">No shift locations yet.</p>
				<button v-if="canCreate" @click="showAddModal = true" class="btn-secondary !h-9 mt-1">Add the first one</button>
			</div>
		</div>

		<Teleport to="body">
			<ShiftLocationForm
				v-if="showAddModal"
				:editing-location="editingLocationData"
				@close="closeModal"
				@saved="onLocationSaved"
			/>
		</Teleport>
	</div>
</template>

<script setup>
import { notify, ask } from '@/utils/feedback.js'
import DataTable from '@/components/DataTable.vue'
import { useServerPager } from '@/composables/useServerPager'
import { ref, computed, onMounted } from 'vue';
import { createResource, call } from 'frappe-ui';
import { useRosterStore } from '@/stores/roster';
import ShiftLocationForm from '@/views/forms/roster/shift_location.vue';
import { getErrorMessage } from '@/utils';
import SelectField from '../../components/SelectField.vue'
import RowActions from '@/components/RowActions.vue';

const rosterStore = useRosterStore();

const showAddModal = ref(false);
const editingLocationData = ref(null);
const canCreate = ref(false);
const canEdit = ref(false);
const canDelete = ref(false);
const deletingId = ref(null);

/* Server-side fetch: one page at a time (page/page_size) via get_shift_locations.
   Returns { rows, total } for useServerPager. */
async function fetchLocations(page, pageSize) {
	const res = await call('arijentek_core.api.roster.get_shift_locations', {
		page: page,
		page_size: pageSize,
	});
	return { rows: res.data || [], total: Number(res.total) || 0 };
}

const pager = useServerPager((page, size) => fetchLocations(page, size), { size: 10 });

/* Column declarations for the list view (order = render order; `className`
   carries the responsive hiding). */
const listColumns = [
	{ key: 'name', label: 'Location', className: 'table-td-strong' },
];

/* Per-row actions, gated by permission. 2+ actions fold into the More dropdown
   (RowActions maxInline=1), so a row never shows delete one mis-click from edit. */
function actionsForRow(row) {
	return [
		{ label: 'Edit', icon: 'edit', show: canEdit.value, onClick: () => editLocation(row) },
		{ divider: true },
		{ label: deletingId.value === row.name ? 'Deleting…' : 'Delete', icon: 'delete', danger: true, show: canDelete.value, disabled: deletingId.value === row.name, onClick: () => deleteLocation(row.name) },
	];
}

const canCreateResource = createResource({
  url: "arijentek_core.api.roster.can_create_shift_location",
  auto: false,
  onSuccess(data) {
    canCreate.value = data;
  }
});

const canEditResource = createResource({
  url: "arijentek_core.api.roster.can_edit_shift_location",
  auto: false,
  onSuccess(data) {
    canEdit.value = data;
  }
});

const canDeleteResource = createResource({
  url: "arijentek_core.api.roster.can_delete_shift_location",
  auto: false,
  onSuccess(data) {
    canDelete.value = data;
  }
});

onMounted(() => {
  // Fetch initial list of shift locations
  pager.fetchPage();
  // Check permissions
  canCreateResource.fetch();
  canEditResource.fetch();
  canDeleteResource.fetch();
});

const closeModal = () => {
  showAddModal.value = false;
  editingLocationData.value = null;
};

const editLocation = (loc) => {
  editingLocationData.value = loc;
  showAddModal.value = true;
};

const onLocationSaved = async () => {
  await pager.fetchPage();
  closeModal();
};

const deleteLocationResource = createResource({
  url: "arijentek_core.api.roster.delete_shift_location",
  auto: false,
});

const deleteLocation = async (name) => {
  if (!await ask("Are you sure you want to delete this shift location?")) return;

  deletingId.value = name;
  try {
    await deleteLocationResource.submit({
      location_name: name
    });
    // Refresh the list immediately after deleting
    await pager.fetchPage();
  } catch (err) {
    const errMsg = getErrorMessage(err, "Failed to delete location.");
    notify(errMsg);
  } finally {
    deletingId.value = null;
  }
};
</script>
