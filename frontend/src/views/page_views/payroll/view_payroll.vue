<template>
  <Dialog :options="{ size: '4xl' }" v-model="show">
    <template #body>
      <div class="modal-panel">
        <!-- Custom Header -->
        <header class="modal-header">
          <div class="flex items-center gap-3">
            <div>
              <h3 class="modal-title truncate">Payroll entry details</h3>
              <p class="text-[12px] text-[#656A72] dark:text-white/60 truncate tabular-nums">{{ name }}</p>
            </div>
          </div>
          <div class="flex items-center gap-1 shrink-0">
            <button class="btn-icon-ghost disabled:opacity-40 disabled:cursor-not-allowed" aria-label="Edit"
              v-if="details && canEditPayrollEntry"
              :disabled="editLocked"
              :title="editLocked ? statusText + ' runs cannot be edited' : 'Edit'"
              @click="handleEdit"
             
            ><span class="material-symbols-outlined !text-[18px]">edit</span></button>
            <button class="btn-danger-ghost disabled:opacity-40" aria-label="Delete" title="Delete" 
              v-if="details && canDeletePayrollEntry"
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
            <span class="w-5 h-5 rounded-full border-2 border-black/10 dark:border-white/15 border-t-accent animate-spin"></span>
            <span class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">Loading payroll entry details...</span>
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
                  <p class="status-label">Company</p>
                  <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.company || '-' }}</div>
                </div>
                <div class="space-y-1">
                  <p class="status-label">Currency</p>
                  <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.currency || '-' }}</div>
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
                  <p class="status-label">Payroll frequency</p>
                  <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.payroll_frequency || '-' }}</div>
                </div>
                <div class="space-y-1">
                  <p class="status-label">Based on timesheet</p>
                  <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.salary_slip_based_on_timesheet ? 'Yes' : 'No' }}</div>
                </div>
                <div v-if="details.salary_structure" class="space-y-1">
                  <p class="status-label">Salary structure</p>
                  <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.salary_structure }}</div>
                </div>
                <div v-if="details.payroll_payable_account" class="space-y-1">
                  <p class="status-label">Payable account</p>
                  <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.payroll_payable_account }}</div>
                </div>
              </div>
            </div>

            <!-- Section 2: Filter Info -->
            <div v-if="details.department || details.designation || details.branch" class="modal-section">
              <p class="status-label flex items-center gap-1.5">Filter criteria</p>
              <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
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

            <!-- Section 3: Employees Table -->
            <div v-if="employees.length > 0" class="modal-section">
              <div class="flex items-center justify-between mb-4 pb-3 border-b border-black/[0.07] dark:border-white/10">
                <p class="status-label flex items-center gap-1.5">Employees</p>
                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold tag-neutral">
                  {{ employees.length }} {{ employees.length === 1 ? 'employee' : 'employees' }}
                </span>
              </div>

              <div class="overflow-x-auto -mx-5 px-5">
                <table class="w-full text-left border-collapse">
                  <thead>
                    <tr class="border-b border-black/[0.07] dark:border-white/10">
                      <th class="table-th">#</th>
                      <th class="table-th">Employee</th>
                      <th class="table-th">Employee name</th>
                      <th class="table-th">Department</th>
                      <th class="table-th">Designation</th>
                      <th class="table-th !text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(emp, idx) in employees" :key="emp.name || idx" class="border-b last:border-0 border-black/[0.05] dark:border-white/[0.06]">
                      <td class="table-td">{{ idx + 1 }}</td>
                      <td class="table-td">{{ emp.employee }}</td>
                      <td class="table-td">{{ emp.employee_name }}</td>
                      <td class="table-td">{{ emp.department || '-' }}</td>
                      <td class="table-td">{{ emp.designation || '-' }}</td>
                      <td class="!text-right table-td">
                        <button 
                          v-if="!hasActiveSlip(emp.employee)"
                          @click.stop="handleRecreateSlip"
                          class="btn-secondary !h-8 !px-3"
                          :disabled="creatingSlip"
                        >
                          <span v-if="creatingSlip" class="material-symbols-outlined text-[14px] animate-spin">progress_activity</span>
                          <span v-else class="material-symbols-outlined text-[14px]">add_circle</span>
                          Create Slip
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Section: Salary Slips Table -->
            <div class="modal-section">
              <div class="flex items-center justify-between mb-4 pb-3 border-b border-black/[0.07] dark:border-white/10">
                <p class="status-label flex items-center gap-1.5">Salary slips</p>
                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold tag-neutral">
                  {{ salarySlips.length }} {{ salarySlips.length === 1 ? 'slip' : 'slips' }}
                </span>
              </div>

              <div v-if="loadingSlips" class="py-6 flex justify-center">
                <span class="w-5 h-5 rounded-full border-2 border-black/10 dark:border-white/15 border-t-accent animate-spin"></span>
              </div>
              <div v-else-if="salarySlips.length > 0" class="overflow-x-auto -mx-5 px-5">
                <table class="w-full text-left border-collapse">
                  <thead>
                    <tr class="border-b border-black/[0.07] dark:border-white/10">
                      <th class="table-th">ID</th>
                      <th class="table-th">Employee</th>
                      <th class="table-th !text-right">Net pay</th>
                      <th class="table-th !text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr 
                      v-for="slip in salarySlips" 
                      :key="slip.name" 
                      class="hover:bg-black/[0.03] dark:hover:bg-white/[0.05] transition-colors cursor-pointer group"
                      @click="openViewSalarySlip(slip.name)"
                    >
                      <td class="table-td">{{ slip.name }}</td>
                      <td class="table-td">
                        <div class="font-semibold text-[#17181B] dark:text-white">{{ slip.employee_name }}</div>
                        <div class="text-xs text-[#656A72] dark:text-white/60 font-mono">{{ slip.employee }}</div>
                      </td>
                      <td class="!text-right table-td">{{ formatCurrency(slip.net_pay, slip.currency) }}</td>
                      <td class="!text-right table-td">
                        <span 
                          class="premium-tag"
                          :class="getSlipStatusBadgeClass(slip.status)"
                        >
                          {{ slip.status }}
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-else class="p-6 text-center border border-dashed border-black/[0.07] dark:border-white/10 rounded-[12px] text-xs text-[#656A72] dark:text-white/60">
                No salary slips found for this payroll entry.
              </div>
            </div>

            <!-- Section 4: Timestamps -->
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

  <!-- View Salary Slip Modal (popup above view payroll) -->
  <ViewSalarySlip 
    v-model="showSalarySlipViewModal"
    :name="selectedSalarySlipName"
    @refresh="fetchSalarySlips"
  />
</template>

<script setup>
import { notify, ask } from '@/utils/feedback.js'
import { ref, computed, watch } from 'vue';
import { Dialog, call } from 'frappe-ui';
import { storeToRefs } from 'pinia';
import { usePayrollStore } from '@/stores/payroll';
import { getErrorMessage } from '@/utils';
import ViewSalarySlip from '@/views/page_views/payroll/view_salary_slip.vue';

const payrollStore = usePayrollStore();
const { canEditPayrollEntry, canDeletePayrollEntry } = storeToRefs(payrollStore);
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
const loadingSlips = ref(false);
const error = ref('');
const details = ref(null);
const salarySlips = ref([]);
const deleting = ref(false);
const creatingSlip = ref(false);

const showSalarySlipViewModal = ref(false);
const selectedSalarySlipName = ref('');

const employees = computed(() => {
  if (!details.value) return [];
  return details.value.employees || [];
});

const statusLabel = computed(() => {
  if (!details.value) return 'Unknown';
  if (details.value.status) return details.value.status;
  if (details.value.docstatus === 1) return 'Submitted';
  if (details.value.docstatus === 2) return 'Cancelled';
  return 'Draft';
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
    const res = await call('arijentek_core.api.payroll.get_payroll_details', { payroll_name: props.name });
    if (res && !Array.isArray(res)) {
      details.value = res;
      // Fetch Salary Slips associated with this payroll entry
      await fetchSalarySlips();
    } else {
      error.value = 'Payroll Entry not found.';
    }
  } catch (err) {
    error.value = getErrorMessage(err, 'Failed to load payroll entry details.');
  } finally {
    loading.value = false;
  }
}

async function fetchSalarySlips() {
  if (!props.name) return;
  loadingSlips.value = true;
  try {
    const res = await call('arijentek_core.api.payroll.get_salary_Slip', { payroll_entry: props.name });
    salarySlips.value = res || [];
  } catch (err) {
    console.error('Failed to fetch salary slips for payroll entry:', err);
  } finally {
    loadingSlips.value = false;
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

watch(() => props.modelValue, (val) => {
  if (val && props.name) {
    fetchDetails();
  }
});

function openViewSalarySlip(slipName) {
  selectedSalarySlipName.value = slipName;
  showSalarySlipViewModal.value = true;
}

function getSlipStatusBadgeClass(status) {
  if (status === 'Submitted') {
    return 'tag-emerald';
  } else if (status === 'Cancelled') {
    return 'tag-red';
  }
  return 'tag-accent';
}

function formatCurrency(amount, currency = 'USD') {
  const num = parseFloat(amount || 0);
  try {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(num);
  } catch (e) {
    return `${currency} ${num.toFixed(2)}`;
  }
}

function handleEdit() {
  emit('edit', details.value);
  show.value = false;
}

async function handleDelete() {
  if (!await ask('Are you sure you want to delete this payroll entry? This action cannot be undone.')) return;
  deleting.value = true;
  try {
    await call('arijentek_core.api.payroll.delete_payroll', { name: props.name });
    show.value = false;
    emit('delete');
    emit('refresh');
  } catch (err) {
    notify(getErrorMessage(err, 'Failed to delete payroll entry.'));
  } finally {
    deleting.value = false;
  }
}

function hasActiveSlip(employeeId) {
  return salarySlips.value.some(slip => slip.employee === employeeId && slip.status !== 'Cancelled');
}

async function handleRecreateSlip() {
  creatingSlip.value = true;
  try {
    await call('arijentek_core.api.payroll.recreate_missing_salary_slips', { payroll_entry: props.name });
    await fetchSalarySlips(); // Refresh the list so the new slip shows up
  } catch (err) {
    notify(getErrorMessage(err, 'Failed to recreate salary slip.'));
  } finally {
    creatingSlip.value = false;
  }
}
</script>
