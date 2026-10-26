<template>
  <div class="modal-panel max-w-2xl mx-auto">
    <!-- Header -->
    <header class="flex items-start justify-between gap-3 px-5 py-4 border-b border-black/[0.07] dark:border-white/10 shrink-0">
      <div>
        <h3 class="modal-title">Additional salary details</h3>
        <p class="text-xs text-[#5C6169] dark:text-white/65">{{ id }}</p>
      </div>
      <div class="flex items-center gap-1 shrink-0">
          <button v-if="details && canEdit" class="btn-icon-ghost" aria-label="Edit" title="Edit" @click="$emit('edit', details)"><span class="material-symbols-outlined !text-[18px]">edit</span></button>
          <button v-if="details && canDelete" class="btn-danger-ghost" aria-label="Delete" title="Delete" @click="$emit('delete', details)"><span class="material-symbols-outlined !text-[18px]">delete</span></button>
          <button @click="$emit('close')" class="btn-icon-ghost shrink-0" aria-label="Close">
        <span class="material-symbols-outlined !text-[18px]">close</span>
      </button>
        </div>
    </header>

    <!-- Content -->
    <div v-if="loading" class="flex-1 py-12 flex justify-center">
      <div class="w-6 h-6 border-2 border-black/[0.07] border-t-[#17181B] dark:border-white/10 dark:border-t-white rounded-full animate-spin"></div>
    </div>

    <div v-else-if="details" class="flex-1 overflow-y-auto px-6 py-5 space-y-5">
      <div class="grid grid-cols-2 gap-x-6 gap-y-5">
        <div>
          <span class="status-label block">Salary ID</span>
          <span class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 block">{{ details.name }}</span>
        </div>
        <div>
          <span class="status-label block">Employee</span>
          <span class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 block">{{ details.employee_name || details.employee }}</span>
        </div>
        <div>
          <span class="status-label block">Salary Component</span>
          <span class="text-[14px] font-semibold text-accent dark:text-accent-light mt-1 block">{{ details.salary_component || '-' }}</span>
        </div>
        <div>
          <span class="status-label block">Amount</span>
          <span class="text-[14px] font-semibold text-[#17181B] dark:text-white tabular-nums mt-1 block">${{ (details.amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
        </div>
        <div>
          <span class="status-label block">Payroll Date</span>
          <span class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 block">{{ details.payroll_date || '-' }}</span>
        </div>
        <div>
          <span class="status-label block mb-1">Status</span>
          <span
            class="premium-tag"
            :class="getStatusBadgeClasses(details.status || (details.docstatus === 1 ? 'Submitted' : details.docstatus === 2 ? 'Cancelled' : 'Draft'))"
          >
            {{ details.status || (details.docstatus === 1 ? 'Submitted' : details.docstatus === 2 ? 'Cancelled' : 'Draft') }}
          </span>
        </div>
      </div>

      <div v-if="details.ref_doctype" class="inset-panel flex items-center justify-between">
        <div>
          <span class="status-label block">Reference Document</span>
          <span class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 block">{{ details.ref_doctype }}: {{ details.ref_docname }}</span>
        </div>
      </div>
    </div>
    <footer class="px-5 py-4 border-t border-black/[0.07] dark:border-white/10 shrink-0">
      <button class="btn-secondary w-full" @click="$emit('close')">Close</button>
    </footer>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue';
import { call } from 'frappe-ui';

const props = defineProps({
  /* Passed down by the list so the dialog offers the same actions as its row. */
  canEdit: { type: Boolean, default: false },
  canDelete: { type: Boolean, default: false },
  id: String,
});

const emit = defineEmits(['close', 'refresh', 'edit', 'delete']);

const loading = ref(false);
const details = ref(null);

function getStatusBadgeClasses(status) {
  const s = (status || '').toLowerCase();
  if (s === 'submitted' || s === 'approved') return 'tag-emerald';
  if (s === 'cancelled' || s === 'rejected') return 'tag-red';
  return 'tag-amber';
}

async function fetchDetails() {
  if (!props.id) return;
  loading.value = true;
  try {
    const res = await call('arijentek_core.api.payroll.get_additional_salary_details', { name: props.id });
    details.value = res || null;
  } catch (e) {
    console.error('Failed to fetch additional salary details:', e);
  } finally {
    loading.value = false;
  }
}

watch(() => props.id, () => {
  fetchDetails();
});

onMounted(() => {
  fetchDetails();
});
</script>
