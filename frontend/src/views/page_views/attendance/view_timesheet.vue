<template>
  <div class="modal-panel max-w-4xl mx-auto" :class="{ 'h-full': !isModal }">
    
    <div v-if="loading" class="p-12 flex justify-center items-center">
      <span class="material-symbols-outlined animate-spin text-3xl text-accent dark:text-accent-light">progress_activity</span>
    </div>

    <div v-else-if="!record" class="p-12 flex justify-center items-center">
      <p class="text-[#5C6169] dark:text-white/65 font-semibold">Could not load timesheet details.</p>
    </div>

    <template v-else>
      <!-- One header row for the panel, not a card of its own. -->
      <header class="flex items-start justify-between gap-3 px-5 py-4 border-b border-black/[0.07] dark:border-white/10 shrink-0">
        <div class="min-w-0">
          <h2 class="modal-title truncate">Timesheet</h2>
          <p class="text-[12px] text-[#656A72] dark:text-white/55 truncate tabular-nums">{{ record.name }}</p>
        </div>
        <div class="flex items-center gap-2 relative shrink-0">
          <span class="premium-tag" :class="getStatusClasses(record.status)">
            {{ record.status }}
          </span>
          <RowActions :actions="[
          		{ label: 'Edit', icon: 'edit', show: !!(canEdit && record.status !== 'Cancelled'), onClick: () => { handleEdit() } },
          		{ label: 'Submit', icon: 'send', show: !!(record.status === 'Draft'), onClick: () => { handleSubmit() } },
          		{ divider: true },
          		{ label: 'Delete', icon: 'delete', danger: true, show: !!(canDelete), onClick: () => { handleDelete() } },
          	]" />
        </div>
      </header>

      <div class="flex-1 overflow-y-auto px-6 py-5">
        <!-- Facts read as plain fields on the panel; a card here would be a
             second surface inside the dialog. -->
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-5">
          <div>
            <p class="status-label">Employee</p>
            <p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ record.employee_name || record.employee }}</p>
          </div>
          <div>
            <p class="status-label">Start date</p>
            <p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ formatDate(record.start_date) }}</p>
          </div>
          <div>
            <p class="status-label">Total hours</p>
            <p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 tabular-nums">{{ formatHours(record.total_hours) }}</p>
          </div>
        </div>

        <!-- Time Logs Details Table -->
        <div class="mt-6 pt-5 border-t border-black/[0.07] dark:border-white/10">
          <p class="status-label mb-2.5">Time logs</p>

          <div class="table-card !rounded-[12px]">
            <table class="w-full">
              <thead>
                <tr class="border-b border-black/[0.07] dark:border-white/10">
                  <th class="table-th">Activity</th>
                  <th class="table-th">From</th>
                  <th class="table-th">To</th>
                  <th class="table-th">Description</th>
                  <th class="table-th !text-right">Hours</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!record.time_logs || record.time_logs.length === 0">
                  <td colspan="5" class="px-4 py-8 text-center text-[13px] text-[#656A72] dark:text-white/55">No time logs found.</td>
                </tr>
                <tr v-for="(line, idx) in record.time_logs" :key="idx" class="border-b border-black/[0.05] dark:border-white/[0.06]">
                  <td class="table-td-strong">{{ line.activity_type }}</td>
                  <td class="table-td">{{ formatDateTimeDisplay(line.from_time) }}</td>
                  <td class="table-td">{{ formatDateTimeDisplay(line.to_time) }}</td>
                  <td class="table-td">{{ line.description || '—' }}</td>
                  <td class="table-td-strong !text-right tabular-nums">{{ formatHours(line.hours) }}</td>
                </tr>
              </tbody>
              <tfoot v-if="record.time_logs && record.time_logs.length">
                <tr>
                  <td colspan="4" class="table-td !text-right">Total</td>
                  <td class="table-td-strong !text-right tabular-nums">{{ formatHours(record.total_hours) }}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      </div>

      <footer class="px-5 py-4 border-t border-black/[0.07] dark:border-white/10 shrink-0">
        <button class="btn-secondary w-full" @click="$emit('close')">Close</button>
      </footer>
    </template>
  </div>
</template>

<script setup>
import { notify, ask } from '@/utils/feedback.js'
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { call } from 'frappe-ui';
import { getErrorMessage } from '@/utils';
import { useAttendanceStore } from '@/stores/attendance';
import RowActions from '@/components/RowActions.vue';

const props = defineProps({
  id: {
    type: String,
    required: true
  },
  isModal: {
    type: Boolean,
    default: true
  }
});

const emit = defineEmits(['close', 'refresh', 'edit']);

const attendanceStore = useAttendanceStore();
const loading = ref(true);
const record = ref(null);
const activeActionMenu = ref(false);
const floatPrecision = ref(2);

const canEdit = computed(() => attendanceStore.editTimesheetPermissionResource.data ?? true);
const canDelete = computed(() => attendanceStore.deleteTimesheetPermissionResource.data ?? true);

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

async function handleSubmit() {
  closeActionMenu();
  try {
    const res = await call('arijentek_core.api.attendance.submit_timesheet', {
      name: record.value.name
    });
    if (res && res.success === false) {
      notify(res.error || 'Failed to submit timesheet');
      return;
    }
    await fetchRecord();
    emit('refresh');
  } catch (e) {
    console.error('Failed to submit timesheet:', e);
    notify(getErrorMessage(e, 'Failed to submit timesheet'));
  }
}

function handleEdit() {
  closeActionMenu();
  emit('edit', record.value);
  emit('close');
}

async function handleDelete() {
  closeActionMenu();
  if (!await ask("Are you sure you want to delete this timesheet?")) return;
  try {
    const res = await call('arijentek_core.api.attendance.delete_timesheet', {
      name: record.value?.name
    });
    if (res && res.success === false) {
      notify(res.error || 'Failed to delete timesheet');
      return;
    }
    emit('refresh');
    emit('close');
  } catch (e) {
    console.error('Failed to delete timesheet:', e);
    notify(getErrorMessage(e, 'Failed to delete timesheet'));
  }
}

const getStatusClasses = (status) => {
  const s = status?.toLowerCase();
  if (s === "submitted" || s === "approved") return "tag-emerald";
  if (s === "rejected" || s === "cancelled") return "tag-red";
  return "tag-neutral";
};

const formatDate = (dateStr) => {
  if (!dateStr) return "-";
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
};

const formatDateTimeDisplay = (dtStr) => {
  if (!dtStr) return "-";
  const date = new Date(dtStr);
  return date.toLocaleDateString("en-US", { 
    month: "short", 
    day: "numeric", 
    year: "numeric", 
    hour: "numeric", 
    minute: "2-digit" 
  });
};

function formatHours(hours) {
	if (hours === undefined || hours === null) return `0.${'0'.repeat(floatPrecision.value)}h`;
	
	let hrsNum = 0;
	if (typeof hours === "string") {
		hrsNum = parseFloat(hours.replace("h", "").trim()) || 0;
	} else {
		hrsNum = hours;
	}
	return `${hrsNum.toFixed(floatPrecision.value)}h`;
}

async function fetchRecord() {
  loading.value = true;
  try {
    const res = await call('arijentek_core.api.attendance.get_timesheet_list_details', { name: props.id });
    record.value = res || null;
  } catch (e) {
    console.error("Failed to fetch timesheet details", e);
    record.value = null;
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  window.addEventListener("click", handleWindowClick);
  
  try {
    const precision = await call("arijentek_core.api.attendance.get_float_precision");
    floatPrecision.value = parseInt(precision) || 2;
  } catch (e) {
    console.error("Failed to fetch float precision:", e);
  }

  if (props.id) {
    fetchRecord();
  }
});

onUnmounted(() => {
  window.removeEventListener("click", handleWindowClick);
});
</script>
