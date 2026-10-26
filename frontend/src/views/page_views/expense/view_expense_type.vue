<template>
  <Teleport to="body">
    <div v-if="modelValue" class="modal-scrim" @click.self="$emit('update:modelValue', false)">
      <div class="modal-panel max-w-lg" role="dialog" aria-modal="true" aria-labelledby="et-view-title">
        <header class="modal-header !items-start">
          <div class="min-w-0">
            <h2 id="et-view-title" class="modal-title truncate">Expense type</h2>
            <p class="text-[13px] text-[#5C6169] dark:text-white/65 truncate">{{ expenseTypeData?.name || id }}</p>
          </div>
          <div class="flex items-center gap-1 shrink-0">
            <button v-if="canEdit && expenseTypeData" @click="handleEdit" class="btn-icon-ghost" aria-label="Edit" title="Edit">
              <span class="material-symbols-outlined !text-[18px]">edit</span>
            </button>
            <button v-if="canDelete && expenseTypeData" @click="handleDelete" class="btn-danger-ghost" aria-label="Delete" title="Delete">
              <span class="material-symbols-outlined !text-[18px]">delete</span>
            </button>
            <button @click="$emit('update:modelValue', false)" class="btn-icon-ghost" aria-label="Close">
              <span class="material-symbols-outlined !text-[18px]">close</span>
            </button>
          </div>
        </header>

        <div v-if="loading" class="empty-state">
          <span class="w-6 h-6 rounded-full border-2 border-accent/25 border-t-accent animate-spin"></span>
          <p class="empty-state-text">Loading…</p>
        </div>

        <div v-else-if="!expenseTypeData" class="empty-state">
          <span class="material-symbols-outlined">error</span>
          <p class="empty-state-title">Could not load this expense type</p>
          <p class="empty-state-text">Close and try again.</p>
        </div>

        <div v-else class="modal-body !space-y-0">
          <div class="modal-section">
            <p class="status-label">Expense type name</p>
            <p class="text-[14px] font-semibold text-[#17181B] dark:text-white">{{ expenseTypeData.name }}</p>
          </div>
          <div class="modal-section">
            <p class="status-label">Default account</p>
            <p class="text-[14px] font-semibold text-[#17181B] dark:text-white">{{ expenseTypeData.default_account || '—' }}</p>
          </div>
          <div class="modal-section">
            <p class="status-label">Description</p>
            <p class="text-[13px] leading-relaxed text-[#17181B] dark:text-white/85">{{ expenseTypeData.description || '—' }}</p>
          </div>
        </div>

        <footer class="modal-footer">
          <button class="btn-secondary w-full" @click="$emit('update:modelValue', false)">Close</button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { notify } from '@/utils/feedback.js'
import { ref, watch, onMounted, onUnmounted } from 'vue';
import { call } from 'frappe-ui';
import { getErrorMessage } from '@/utils';

const props = defineProps({
  modelValue: Boolean,
  id: {
    type: String,
    default: null
  },
  canEdit: Boolean,
  canDelete: Boolean
});

const emit = defineEmits(['update:modelValue', 'edit', 'delete']);

const expenseTypeData = ref(null);
const loading = ref(false);
const activeActionMenu = ref(false);

function toggleActionMenu() {
  activeActionMenu.value = !activeActionMenu.value;
}

function closeActionMenu() {
  activeActionMenu.value = false;
}

const handleWindowClick = (e) => {
  if (!e.target.closest(".more_vert") && !e.target.closest(".dropdown-menu")) {
    closeActionMenu();
  }
};

onMounted(() => {
  window.addEventListener("click", handleWindowClick);
});

onUnmounted(() => {
  window.removeEventListener("click", handleWindowClick);
});

function handleEdit() {
  closeActionMenu();
  emit('edit', expenseTypeData.value);
}

function handleDelete() {
  closeActionMenu();
  emit('delete', expenseTypeData.value);
}

watch(() => props.modelValue, (newVal) => {
  if (newVal && props.id) {
    fetchData();
  } else {
    expenseTypeData.value = null;
  }
});

async function fetchData() {
  loading.value = true;
  try {
    const res = await call('arijentek_core.api.expense.get_expense_types', { name: props.id });
    if (res && res.length > 0) {
      expenseTypeData.value = res[0];
    } else {
      expenseTypeData.value = null;
    }
  } catch (e) {
    console.error('Failed to fetch expense type details:', e);
    notify(getErrorMessage(e, 'Failed to fetch details'));
    emit('update:modelValue', false);
  } finally {
    loading.value = false;
  }
}
</script>
