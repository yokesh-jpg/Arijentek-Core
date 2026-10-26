<template>
  <Dialog :options="{ size: '4xl' }" v-model="show">
    <template #body>
      <div class="modal-panel">
        <!-- Custom Header -->
        <header class="modal-header">
          <div class="flex items-center gap-3">
            <div>
              <h3 class="modal-title truncate">Salary slip details</h3>
              <p class="text-[12px] text-[#656A72] dark:text-white/60 truncate tabular-nums">{{ name }}</p>
            </div>
          </div>
          <div class="flex items-center gap-1 shrink-0">
            <button class="btn-icon-ghost disabled:opacity-40 disabled:cursor-not-allowed" aria-label="Edit"
              v-if="details && canEditSalarySlip"
              :disabled="editLocked"
              :title="editLocked ? statusText + ' slips cannot be edited' : 'Edit'"
              @click="handleEdit"
             
            ><span class="material-symbols-outlined !text-[18px]">edit</span></button>
            <button class="btn-danger-ghost disabled:opacity-40" aria-label="Delete" title="Delete" 
              v-if="details && canDeleteSalarySlip"
              @click="handleDelete"
             
              :disabled="deleting"
            ><span v-if="deleting" class="w-4 h-4 rounded-full border-2 border-current/30 border-t-current animate-spin"></span><span v-else class="material-symbols-outlined !text-[18px]">delete</span></button>
            <button 
              @click="show = false" 
              class="btn-icon-ghost shrink-0"
             aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span></button>
          </div>
        </header>

        <!-- Main Content -->
        <div class="flex-1 overflow-y-auto px-6 py-5">
          <!-- Loading State -->
          <div v-if="loading" class="flex flex-col items-center justify-center py-20 gap-3">
            <div class="w-8 h-8 border-2 border-accent/30 border-t-transparent rounded-full animate-spin"></div>
            <span class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">Loading salary slip details...</span>
          </div>

          <!-- Error State -->
          <div v-else-if="error" class="empty-state">
						<span class="material-symbols-outlined !text-[28px] text-red-600 dark:text-red-400">error</span>
						<p class="empty-state-text">Could not load this record</p>
						<p class="text-[12px] text-[#656A72] dark:text-white/55">{{ error }}</p>
						<button @click="fetchDetails" class="btn-secondary !h-9 mt-1">Try again</button>
					</div>

          <!-- Details Content -->
          <div v-else-if="details" class="flex flex-col">

            <!-- Section 1: General Info -->
            <div class="modal-section">
              <div class="flex justify-between items-center mb-6 pb-4 border-b border-black/[0.07] dark:border-white/10">
                <p class="status-label flex items-center gap-1.5">General details</p>
                <span 
                  class="premium-tag"
                  :class="statusBadgeClass"
                >
                  {{ statusLabel }}
                </span>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <div class="space-y-1">
                  <p class="status-label">ID</p>
                  <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.name || '-' }}</div>
                </div>
                <div class="space-y-1">
                  <p class="status-label">Employee</p>
                  <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.employee_name || '-' }}</div>
                  <div class="text-xs text-[#656A72] dark:text-white/60 font-mono">{{ details.employee || '' }}</div>
                </div>
                <div class="space-y-1">
                  <p class="status-label">Company</p>
                  <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.company || '-' }}</div>
                </div>
                <div class="space-y-1">
                  <p class="status-label">Posting date</p>
                  <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ formatDate(details.posting_date) }}</div>
                </div>
                <div class="space-y-1">
                  <p class="status-label">Pay period</p>
                  <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">
                    {{ formatDate(details.start_date) }} — {{ formatDate(details.end_date) }}
                  </div>
                </div>
                <div class="space-y-1">
                  <p class="status-label">Currency</p>
                  <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.currency || '-' }}</div>
                </div>
                <div v-if="details.department" class="space-y-1">
                  <p class="status-label">Department</p>
                  <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.department }}</div>
                </div>
                <div v-if="details.designation" class="space-y-1">
                  <p class="status-label">Designation</p>
                  <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.designation }}</div>
                </div>
                <div v-if="details.branch" class="space-y-1">
                  <p class="status-label">Branch</p>
                  <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.branch }}</div>
                </div>
              </div>
            </div>

            <!-- Section 2: Attendance Summary -->
            <div class="modal-section">
              <p class="status-label flex items-center gap-1.5">Attendance summary</p>
              <div class="grid grid-cols-2 sm:grid-cols-5 gap-4">
                <div>
                  <p class="status-label">Working days</p>
                  <p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 tabular-nums">{{ details.total_working_days || details.working_days || 0 }}</p>
                </div>
                <div>
                  <p class="status-label">Payment days</p>
                  <p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 tabular-nums">{{ details.payment_days || 0 }}</p>
                </div>
                <div>
                  <p class="status-label">Present days</p>
                  <p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 tabular-nums">{{ details.present_days || 0 }}</p>
                </div>
                <div>
                  <p class="status-label">Absent days</p>
                  <p class="text-[14px] font-semibold text-red-700 dark:text-red-400 mt-1 tabular-nums">{{ details.absent_days || 0 }}</p>
                </div>
                <div class="col-span-2 sm:col-span-1">
                  <p class="status-label">Leave without pay</p>
                  <p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 tabular-nums">{{ details.leave_without_pay || details.lop_days || 0 }}</p>
                </div>
              </div>
            </div>

            <!-- Section 3: Timesheet Details (if applicable) -->
            <div v-if="details.salary_slip_based_on_timesheet" class="modal-section">
              <p class="status-label flex items-center gap-1.5">Timesheet details</p>
              <div class="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-4">
                <div class="space-y-1">
                  <p class="status-label">Total working hours</p>
                  <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ parseFloat(details.total_working_hours || 0).toFixed(3) }} hrs</div>
                </div>
                <div class="space-y-1">
                  <p class="status-label">Hour rate</p>
                  <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ formatCurrency(details.hour_rate) }}</div>
                </div>
              </div>

              <div v-if="timesheets.length > 0" class="overflow-x-auto -mx-5 px-5">
                <table class="w-full text-left border-collapse">
                  <thead>
                    <tr class="border-b border-black/[0.07] dark:border-white/10">
                      <th class="table-th">Timesheet</th>
                      <th class="table-th !text-right">Working hours</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(ts, idx) in timesheets" :key="idx">
                      <td class="table-td">{{ ts.time_sheet || ts.timesheet || '-' }}</td>
                      <td class="!text-right table-td">{{ parseFloat(ts.working_hours || ts.total_hours || 0).toFixed(3) }} hrs</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-else class="p-4 text-center border border-dashed border-black/[0.07] dark:border-white/10 rounded-[12px] text-xs text-[#656A72] dark:text-white/60">
                No timesheets linked.
              </div>
            </div>

            <!-- Section 4: Earnings Table -->
            <div class="modal-section">
              <div class="flex items-center justify-between mb-4 pb-3 border-b border-black/[0.07] dark:border-white/10">
                <p class="status-label flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-accent"></span>Earnings</p>
                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold tag-neutral">
                  {{ earnings.length }} {{ earnings.length === 1 ? 'component' : 'components' }}
                </span>
              </div>

              <div v-if="earnings.length > 0" class="overflow-x-auto -mx-5 px-5">
                <table class="w-full text-left border-collapse">
                  <thead>
                    <tr class="border-b border-black/[0.07] dark:border-white/10">
                      <th class="table-th">Component</th>
                      <th class="table-th">Abbr</th>
                      <th class="table-th !text-right">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(e, idx) in earnings" :key="idx">
                      <td class="table-td">{{ e.salary_component }}</td>
                      <td class="table-td">{{ e.abbr || '-' }}</td>
                      <td class="!text-right table-td">{{ formatCurrency(e.amount) }}</td>
                    </tr>
                  </tbody>
                  <tfoot>
                    <tr class="border-t-2 border-black/[0.07] dark:border-white/10">
                      <td colspan="2" class="py-3 text-[13px] font-semibold text-[#17181B] dark:text-white">Total Earnings</td>
                      <td class="!text-right table-td">{{ formatCurrency(details.gross_pay) }}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
              <div v-else class="p-4 text-center border border-dashed border-black/[0.07] dark:border-white/10 rounded-[12px] text-xs text-[#656A72] dark:text-white/60">
                No earnings found.
              </div>
            </div>

            <!-- Section 5: Deductions Table -->
            <div class="modal-section">
              <div class="flex items-center justify-between mb-4 pb-3 border-b border-black/[0.07] dark:border-white/10">
                <p class="status-label flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-red-500"></span>Deductions</p>
                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold tag-neutral">
                  {{ deductions.length }} {{ deductions.length === 1 ? 'component' : 'components' }}
                </span>
              </div>

              <div v-if="deductions.length > 0" class="overflow-x-auto -mx-5 px-5">
                <table class="w-full text-left border-collapse">
                  <thead>
                    <tr class="border-b border-black/[0.07] dark:border-white/10">
                      <th class="table-th">Component</th>
                      <th class="table-th">Abbr</th>
                      <th class="table-th !text-right">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(d, idx) in deductions" :key="idx">
                      <td class="table-td">{{ d.salary_component }}</td>
                      <td class="table-td">{{ d.abbr || '-' }}</td>
                      <td class="!text-right table-td">{{ formatCurrency(d.amount) }}</td>
                    </tr>
                  </tbody>
                  <tfoot>
                    <tr class="border-t-2 border-black/[0.07] dark:border-white/10">
                      <td colspan="2" class="py-3 text-[13px] font-semibold text-[#17181B] dark:text-white">Total Deductions</td>
                      <td class="!text-right table-td">{{ formatCurrency(details.total_deduction) }}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
              <div v-else class="p-4 text-center border border-dashed border-black/[0.07] dark:border-white/10 rounded-[12px] text-xs text-[#656A72] dark:text-white/60">
                No deductions found.
              </div>
            </div>

            <!-- Section 6: Net Pay Summary -->
            <div class="modal-section">
              <p class="status-label mb-3">Pay summary</p>
              <div class="grid grid-cols-1 sm:grid-cols-3 gap-6">
                <div class="flex flex-col border-b sm:border-b-0 sm:border-r border-black/[0.07] dark:border-white/10 pb-4 sm:pb-0 sm:pr-6">
                  <span class="status-label">Gross pay</span>
                  <span class="text-[20px] font-semibold tabular-nums mt-1 text-[#17181B] dark:text-white">{{ formatCurrency(details.gross_pay) }}</span>
                </div>
                <div class="flex flex-col border-b sm:border-b-0 sm:border-r border-black/[0.07] dark:border-white/10 pb-4 sm:pb-0 sm:pr-6">
                  <span class="status-label">Total deduction</span>
                  <span class="text-[20px] font-semibold tabular-nums mt-1 text-red-600 dark:text-red-400">{{ formatCurrency(details.total_deduction) }}</span>
                </div>
                <div class="flex flex-col">
                  <span class="status-label">Net pay</span>
                  <!-- The one figure the slip exists to state, so it carries the accent. -->
                  <span class="text-[20px] font-semibold tabular-nums mt-1 text-accent dark:text-accent-light">{{ formatCurrency(details.net_pay) }}</span>
                </div>
              </div>

              <div v-if="details.gross_year_to_date" class="pt-4 mt-4 border-t border-black/[0.07] dark:border-white/10 flex items-center justify-between">
                <span class="status-label">Gross year to date</span>
                <span class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ formatCurrency(details.gross_year_to_date) }}</span>
              </div>
            </div>

            <!-- Section 7: Audit Trail -->
            <div class="modal-section">
              <p class="status-label flex items-center gap-1.5">Audit trail</p>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div class="space-y-1">
                  <p class="status-label">Created by</p>
                  <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.owner || '-' }}</div>
                </div>
                <div class="space-y-1">
                  <p class="status-label">Created on</p>
                  <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ formatDateTime(details.creation) }}</div>
                </div>
                <div class="space-y-1">
                  <p class="status-label">Modified by</p>
                  <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.modified_by || '-' }}</div>
                </div>
                <div class="space-y-1">
                  <p class="status-label">Last modified</p>
                  <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ formatDateTime(details.modified) }}</div>
                </div>
              </div>
            </div>

          </div>
        </div>
      	<footer class="px-5 py-4 border-t border-black/[0.07] dark:border-white/10 shrink-0">
					<button class="btn-secondary w-full" @click="show = false">Close</button>
				</footer>
			</div>
    </template>
  </Dialog>
</template>

<script setup>
import { notify, ask } from '@/utils/feedback.js'
import { ref, computed, watch } from 'vue';
import { Dialog, call } from 'frappe-ui';
import { storeToRefs } from 'pinia';
import { usePayrollStore } from '@/stores/payroll';
import { getErrorMessage } from '@/utils';

const payrollStore = usePayrollStore();
const { canEditSalarySlip, canDeleteSalarySlip } = storeToRefs(payrollStore);
/* Submitted and cancelled documents are final; Edit stays visible but disabled. */
const statusText = computed(() => details.value?.status || (details.value?.docstatus === 1 ? 'Submitted' : details.value?.docstatus === 2 ? 'Cancelled' : 'Draft'));
const editLocked = computed(() => statusText.value !== 'Draft');

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  name: { type: String, default: '' }
});

const emit = defineEmits(['update:modelValue', 'edit', 'delete', 'refresh']);

const show = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
});

const loading = ref(false);
const error = ref('');
const details = ref(null);
const deleting = ref(false);

const earnings = computed(() => {
  if (!details.value) return [];
  return details.value.earnings || [];
});

const deductions = computed(() => {
  if (!details.value) return [];
  return details.value.deductions || [];
});

const timesheets = computed(() => {
  if (!details.value) return [];
  return details.value.timesheets || [];
});

const statusLabel = computed(() => {
  if (!details.value) return 'Unknown';
  if (details.value.docstatus === 1) return 'Submitted';
  if (details.value.docstatus === 2) return 'Cancelled';
  return details.value.status || 'Draft';
});

const statusBadgeClass = computed(() => {
  const s = statusLabel.value;
  if (s === 'Submitted') return 'tag-emerald';
  if (s === 'Cancelled') return 'tag-red';
  return 'tag-accent';
});

async function fetchDetails() {
  if (!props.name) return;
  loading.value = true;
  error.value = '';
  details.value = null;
  try {
    const res = await call('arijentek_core.api.payroll.get_salary_slip_details', { slip_name: props.name });
    if (res) {
      details.value = res;
    } else {
      error.value = 'Salary Slip not found.';
    }
  } catch (err) {
    error.value = getErrorMessage(err, 'Failed to load salary slip details.');
  } finally {
    loading.value = false;
  }
}

function formatDate(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

function formatDateTime(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) + ', ' +
    d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

function formatCurrency(amount) {
  const num = parseFloat(amount || 0);
  const curr = details.value?.currency || 'USD';
  try {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: curr }).format(num);
  } catch (e) {
    return `${curr} ${num.toFixed(2)}`;
  }
}

watch(() => props.modelValue, (val) => {
  if (val && props.name) {
    fetchDetails();
  }
});

function handleEdit() {
  emit('edit', details.value);
  show.value = false;
}

async function handleDelete() {
  if (!await ask('Are you sure you want to delete this salary slip? This action cannot be undone.')) return;
  deleting.value = true;
  try {
    await call('arijentek_core.api.payroll.delete_salary_slip', { name: props.name });
    show.value = false;
    emit('delete');
    emit('refresh');
  } catch (err) {
    notify(getErrorMessage(err, 'Failed to delete salary slip.'));
  } finally {
    deleting.value = false;
  }
}
</script>
