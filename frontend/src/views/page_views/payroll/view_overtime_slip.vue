<template>
  <div class="modal-panel max-w-2xl mx-auto">
    <!-- Header -->
    <header class="flex items-start justify-between gap-3 px-5 py-4 border-b border-black/[0.07] dark:border-white/10 shrink-0">
      <div>
        <h3 class="modal-title">Overtime slip details</h3>
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
          <span class="status-label block">Overtime Slip ID</span>
          <span class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 block">{{ details.name }}</span>
        </div>
        <div>
          <span class="status-label block">Employee</span>
          <span class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 block">{{ details.employee_name || details.employee }}</span>
        </div>
        <div>
          <span class="status-label block">Start Date</span>
          <span class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 block">{{ details.start_date || '-' }}</span>
        </div>
        <div>
          <span class="status-label block">End Date</span>
          <span class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 block">{{ details.end_date || '-' }}</span>
        </div>
        <div>
          <span class="status-label block">Total Overtime Hours</span>
          <span class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 block">{{ details.total_overtime_duration ?? ((details.total_overtime_hours ?? 0) + ' hrs') }}</span>
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

      <!-- Overtime Details Line Items -->
      <div class="space-y-3">
        <h4 class="text-[13px] font-semiboldr text-[#17181B] dark:text-white flex items-center gap-2">
          <span class="material-symbols-outlined text-base text-accent dark:text-accent-light">list_alt</span>
          Overtime Line Items
        </h4>

        <div class="border border-black/[0.07] dark:border-white/10 rounded-[12px] overflow-hidden shadow-sm">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-black/[0.02] dark:bg-white/[0.06] border-b border-black/[0.07] dark:border-white/10">
                <th class="table-th">Date</th>
                <th class="table-th">Overtime Type</th>
                <th class="table-th !text-right">Overtime Duration</th>
                <th class="table-th !text-right">Std Working Hours</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-black/[0.05] dark:divide-white/[0.06]">
              <tr
                v-for="(item, idx) in (details.overtime_details || [])"
                :key="idx"
                class="hover:bg-black/[0.03] dark:hover:bg-white/[0.06] transition-colors"
              >
                <td class="table-td-strong">
                  {{ formatDate(item.date) }}
                </td>
                <td class="px-4 py-3 text-xs font-semibold text-accent dark:text-accent-light">
                  {{ item.overtime_type || '-' }}
                </td>
                <td class="table-td-strong !text-right tabular-nums">
                  {{ item.overtime_duration || 0 }} hrs
                </td>
                <td class="px-4 py-3 text-xs font-medium text-[#5C6169] dark:text-white/65 text-right tabular-nums">
                  {{ item.standard_working_hours || 0 }} hrs
                </td>
              </tr>
              <tr v-if="!details.overtime_details || details.overtime_details.length === 0">
                <td colspan="4" class="px-4 py-8 text-center text-xs text-[#656A72] dark:text-white/60">
                  No overtime line items found for this slip.
                </td>
              </tr>
            </tbody>
          </table>
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

function formatDate(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

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
    const res = await call('arijentek_core.api.payroll.get_overtime_slip_details', { name: props.id });
    details.value = res || null;
  } catch (e) {
    console.error('Failed to fetch overtime slip details:', e);
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
