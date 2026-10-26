<template>
  <div class="space-y-4 sm:space-y-5 tab-fill">
    <!-- Header & Actions -->
    <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
      <div>
        <h2 class="section-title">Issue types</h2>
        <p class="section-subtitle">The categories staff choose from when raising an issue.</p>
      </div>

      <div class="flex flex-col sm:flex-row items-center gap-3">
        <button 
          v-if="permissions.can_create"
          @click="handleCreate" 
          class="btn-primary shrink-0"
        >
          <span class="material-symbols-outlined !text-[18px]">add</span>
          New issue type
        </button>
      </div>
    </div>

    <!-- Filters Row -->
    <div class="glass-card !p-3 flex flex-wrap items-center gap-2">
      <!-- Search By Name -->
      <div class="flex-1 min-w-[220px]">
        <label class="sr-only">Search</label>
        <div class="relative w-full">
          <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <span class="material-symbols-outlined text-[#656A72] dark:text-white/60 text-lg">search</span>
          </div>
          <input 
            type="text"
            v-model="searchQuery"
            placeholder="Search by name..."
            class="field-input !pl-10"
          />
        </div>
      </div>
    </div>

    <!-- Table -->
    <DataTable
      :columns="listColumns"
      :rows="pg.rows"
      :actions="actionsForType"
      :row-key="'name'"
      :loading="loading"
      empty-text="No issue types found. Try a different search, or add one."
      :show-pager="pg.total > 0"
      :total="pg.total"
      :page="pg.page"
      :page-size="pg.size"
      :on-row-click="editType"
      @update:page="pg.page = $event"
      @update:page-size="(s) => { pg.size = s; pg.page = 1; }"
    >
      <template #cell-name="{ row }">
        <span class="line-clamp-1 font-medium">{{ row.name }}</span>
      </template>
      <template #cell-description="{ row }">
        <span class="line-clamp-1">{{ row.description || '—' }}</span>
      </template>
    </DataTable>

    <!-- Edit/Create Modal -->
    <CreateIssueTypes
      v-model="showEditModal"
      :editData="selectedEditData"
      @save="fetchIssueTypes"
    />
  </div>
</template>

<script setup>
import DataTable from '@/components/DataTable.vue'
import { usePager } from '@/composables/usePager.js'
import { notify, ask } from '@/utils/feedback.js'
import { ref, computed, onMounted } from 'vue';
import { call } from 'frappe-ui';
import CreateIssueTypes from '../../forms/issues/create_issue_types.vue';
import { getErrorMessage } from '@/utils';

const issueTypes = ref([]);
const searchQuery = ref('');
const loading = ref(true);

const permissions = ref({
  can_edit: false,
  can_delete: false,
  can_create: false
});

const showEditModal = ref(false);
const selectedEditData = ref(null);

const listColumns = [
  { key: 'name', label: 'Name', className: 'table-td-strong' },
  { key: 'description', label: 'Description', className: 'table-td' },
];

function actionsForType(type) {
  return [
    {
      label: 'Edit',
      icon: 'edit',
      show: permissions.value.can_edit,
      onClick: () => editType(type),
    },
    { divider: true },
    {
      label: 'Delete',
      icon: 'delete',
      danger: true,
      show: permissions.value.can_delete,
      onClick: () => deleteType(type),
    },
  ];
}

const fetchPermissions = async () => {
  try {
    const editPerm = await call('arijentek_core.api.issues.can_edit_grievance_type');
    permissions.value.can_edit = !!editPerm;
    
    const deletePerm = await call('arijentek_core.api.issues.can_delete_grievance_type');
    permissions.value.can_delete = !!deletePerm;

    const createPerm = await call('arijentek_core.api.issues.can_create_grievance_type');
    permissions.value.can_create = !!createPerm;
  } catch (error) {
    console.error("Failed to fetch permissions:", error);
  }
};

const fetchIssueTypes = async () => {
  loading.value = true;
  try {
    const res = await call('arijentek_core.api.issues.get_issues_types');
    issueTypes.value = res || [];
  } catch (error) {
    console.error("Failed to fetch issue types:", error);
  } finally {
    loading.value = false;
  }
};

const filteredTypes = computed(() => {
  if (!searchQuery.value) return issueTypes.value;
  const q = searchQuery.value.toLowerCase();
  return issueTypes.value.filter(t => 
    (t.name && t.name.toLowerCase().includes(q)) || 
    (t.description && t.description.toLowerCase().includes(q))
  );
});

const handleCreate = () => {
  selectedEditData.value = null;
  showEditModal.value = true;
};

const editType = (type) => {
  selectedEditData.value = type;
  showEditModal.value = true;
};

const deleteType = async (type) => {
  if (!await ask(`Are you sure you want to delete the issue type: ${type.name}?`)) return;
  
  try {
    await call('arijentek_core.api.issues.delete_issue_type', { name: type.name });
    await fetchIssueTypes();
  } catch (err) {
    console.error(err);
    notify(getErrorMessage(err, 'Failed to delete issue type'));
  }
};

onMounted(() => {
  fetchPermissions();
  fetchIssueTypes();
});

/* Client-side paging for the list above (TablePager inside DataTable). */
const pg = usePager(() => filteredTypes)
</script>

<style scoped>
</style>
