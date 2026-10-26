<template>
  <div class="space-y-4 sm:space-y-5 tab-fill">
    <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
      <div>
        <h2 class="section-title">Expense types</h2>
        <p class="section-subtitle">The categories a claim line is filed under, and their defaults.</p>
      </div>
      <button v-if="canCreate" @click="openCreateModal" class="btn-primary shrink-0">
        <span class="material-symbols-outlined !text-[18px]">add</span>
        New expense type
      </button>
    </div>

    <div class="glass-card !p-3 flex flex-wrap items-center gap-2">
      <div class="relative flex-1 min-w-[220px]">
        <span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/55 pointer-events-none">search</span>
        <input v-model="searchQuery" type="text" placeholder="Search by name" aria-label="Search expense types" class="field-input !pl-9" />
      </div>
    </div>

    <!-- Table (server-side pagination) -->
    <DataTable
      :columns="listColumns"
      :rows="pager.state.rows"
      :actions="actionsForType"
      :row-key="'name'"
      :loading="pager.state.loading"
      empty-text="No expense types found. Try a different search, or add one."
      :show-pager="true"
      :total="pager.state.total"
      :page="pager.state.page"
      :page-size="pager.state.size"
      :on-row-click="(type) => handleRowClick(type)"
      @update:page="pager.state.page = $event"
      @update:page-size="pager.setPageSize($event)"
    >
      <template #cell-name="{ row }">
        <span class="line-clamp-1">{{ row.name }}</span>
      </template>
      <template #cell-default_account="{ row }">
        <span class="line-clamp-1">{{ row.default_account || '—' }}</span>
      </template>
    </DataTable>

    <!-- Modals -->
    <CreateExpenseType
      v-model="showModal"
      :editData="selectedEditData"
      @save="onSaveType"
    />

    <ViewExpenseType
      v-model="showViewModal"
      :id="selectedViewId"
      :canEdit="canEdit"
      :canDelete="canDelete"
      @edit="handleViewEdit"
      @delete="handleViewDelete"
    />
  </div>
</template>

<script setup>
import DataTable from '@/components/DataTable.vue'
import { useServerPager } from '@/composables/useServerPager.js'
import { notify, ask } from '@/utils/feedback.js'
import { ref, computed, onMounted, watch } from 'vue';
import { call } from 'frappe-ui';
import CreateExpenseType from '../../forms/expense/create_expense_type.vue';
import ViewExpenseType from '../../page_views/expense/view_expense_type.vue';
import { getErrorMessage } from '@/utils';

const canCreate = ref(false);
const canEdit = ref(false);
const canDelete = ref(false);

const searchQuery = ref('');

const showModal = ref(false);
const selectedEditData = ref(null);

const showViewModal = ref(false);
const selectedViewId = ref(null);

function handleRowClick(type) {
  selectedViewId.value = type.name;
  showViewModal.value = true;
}

function handleViewEdit(type) {
  showViewModal.value = false;
  handleEdit(type);
}

function handleViewDelete(type) {
  showViewModal.value = false;
  handleDelete(type);
}

function openCreateModal() {
  selectedEditData.value = null;
  showModal.value = true;
}

function handleEdit(type) {
  selectedEditData.value = type;
  showModal.value = true;
}

async function handleDelete(type) {
  if (await ask(`Are you sure you want to delete the expense type "${type.name}"?`)) {
    try {
      await call('arijentek_core.api.expense.delete_expense_type', { name: type.name });
      await pager.fetchPage();
    } catch (e) {
      console.error('Failed to delete expense type:', e);
      notify(getErrorMessage(e, 'Failed to delete expense type'));
    }
  }
}

async function checkPermissions() {
  try {
    const [createRes, editRes, deleteRes] = await Promise.all([
      call('arijentek_core.api.expense.can_create_expense_types'),
      call('arijentek_core.api.expense.can_edit_expense_types'),
      call('arijentek_core.api.expense.can_delete_expense_types')
    ]);
    canCreate.value = !!createRes;
    canEdit.value = !!editRes;
    canDelete.value = !!deleteRes;
  } catch (e) {
    console.error("Failed to check expense type permissions", e);
  }
}

/* Server-side fetch: `page`/`page_size` are passed to the API (LIMIT/OFFSET),
   and the response holds the current page + total. Returns { rows, total }
   for useServerPager. Handles both the paginated dict (page_size > 0) and
   the legacy list (page_size = 0) responses. */
async function fetchExpenseTypes(page, size) {
  const params = {
    page: page,
    page_size: size,
    name: searchQuery.value || "",
  };
  try {
    const res = await call('arijentek_core.api.expense.get_expense_types', params);
    const rows = Array.isArray(res) ? res : (res?.data || []);
    const total = Array.isArray(res) ? res.length : Number(res?.total || 0);
    return { rows, total };
  } catch (e) {
    console.error('Failed to fetch expense types:', e);
    return { rows: [], total: 0 };
  }
}

/* Server-side pager: one page at a time (LIMIT/OFFSET). Stale-while-revalidate
   keeps the previous page visible while the next loads; a stale fetch is dropped. */
const pager = useServerPager((page, size) => fetchExpenseTypes(page, size), { size: 10 });

/* Column declarations for the list (order = render order; `className`
   carries the responsive hiding). */
const listColumns = [
  { key: "name", label: "Name", className: "table-td-strong" },
  { key: "default_account", label: "Default Account" },
];

/* Per-row actions, gated by permission. */
function actionsForType(type) {
  return [
    { label: 'Edit', icon: 'edit', show: canEdit.value, onClick: () => handleEdit(type) },
    { label: 'Delete', icon: 'delete', danger: true, show: canDelete.value, onClick: () => handleDelete(type) },
  ];
}

function onSaveType() {
  pager.fetchPage();
}

// Filter changes reset to page 1. The pager's own [page, size] watch re-fetches
// when the page actually changes; if it is already 1, fetch directly so a filter
// change on page 1 still refreshes.
watch(searchQuery, () => {
  if (pager.state.page !== 1) {
    pager.state.page = 1;
  } else {
    pager.fetchPage();
  }
});

onMounted(async () => {
  await checkPermissions();
  await pager.fetchPage();
});
</script>
