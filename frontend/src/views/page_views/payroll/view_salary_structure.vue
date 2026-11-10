<template>
  <Dialog :options="{ size: '3xl' }" v-model="show">
    <template #body>
      <div class="modal-panel">
        <!-- Custom Header -->
        <header class="modal-header">
          <div>
            <h3 class="modal-title truncate">Salary structure details</h3>
            <p class="text-[12px] text-[#656A72] dark:text-white/60 truncate tabular-nums">{{ name }}</p>
          </div>
          <div class="flex items-center gap-1 shrink-0">
            <button class="btn-icon-ghost" aria-label="Edit" title="Edit" 
              v-if="details && canEditSalaryStructure" 
              @click="emit('edit', details); show = false" 
             
            ><span class="material-symbols-outlined !text-[18px]">edit</span></button>
            <button class="btn-danger-ghost disabled:opacity-40" aria-label="Delete" title="Delete" 
              v-if="details && canDeleteSalaryStructure" 
              @click="emit('delete', details); show = false" 
             
            ><span class="material-symbols-outlined !text-[18px]">delete</span></button>
            <button 
              @click="show = false" 
              class="btn-icon-ghost shrink-0"
             aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span></button>
          </div>
        </header>

        <!-- Main Content -->
        <div class="flex-1 overflow-y-auto px-6 py-5">
          <!-- Loading State -->
          <div v-if="loading" class="flex flex-col items-center justify-center py-16 gap-3">
						<span class="w-5 h-5 rounded-full border-2 border-black/10 dark:border-white/15 border-t-accent animate-spin"></span>
						<span class="text-[13px] text-[#5C6169] dark:text-white/65">Loading details…</span>
					</div>

          <!-- Error State -->
          <div v-else-if="error" class="empty-state">
						<span class="material-symbols-outlined !text-[28px] text-red-600 dark:text-red-400">error</span>
						<p class="empty-state-text">Could not load this record</p>
						<p class="text-[12px] text-[#656A72] dark:text-white/55">{{ error }}</p>
						<button @click="fetchDetails" class="btn-secondary !h-9 mt-1">Try again</button>
					</div>

          <!-- Details Content -->
          <div v-else-if="details" class="flex flex-col gap-6">
            <!-- General Info Card -->
            <div class="glass-card">
              <div class="flex justify-between items-center mb-6 pb-4 border-b border-gray-100 dark:border-gray-800">
                <p class="status-label">General details</p>
                <span 
                  class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold"
                  :class="details.is_active === 'Yes' ? 'bg-accent/[0.10] border-accent/30 text-accent dark:bg-accent/20 dark:border-accent/30 dark:text-accent-light' : 'bg-red-50 border-red-100 text-red-600 dark:bg-red-900/20 dark:border-red-800 dark:text-red-400'"
                >
                  {{ details.is_active === 'Yes' ? 'Active' : 'Inactive' }}
                </span>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <!-- Company -->
                <div class="space-y-1">
                  <p class="status-label">Company</p>
                  <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.company || '-' }}</div>
                </div>

                <!-- Currency -->
                <div class="space-y-1">
                  <p class="status-label">Currency</p>
                  <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.currency || 'USD' }}</div>
                </div>

                <!-- Payroll Frequency -->
                <div class="space-y-1">
                  <p class="status-label">Payroll frequency</p>
                  <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.payroll_frequency || '-' }}</div>
                </div>

                <!-- Salary Slip Based on Timesheet -->
                <div class="space-y-1">
                  <p class="status-label">Based on timesheet</p>
                  <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">
                    {{ details.salary_slip_based_on_timesheet ? 'Yes' : 'No' }}
                  </div>
                </div>

                <!-- Salary Component (only if based on timesheet) -->
                <div v-if="details.salary_slip_based_on_timesheet" class="space-y-1">
                  <p class="status-label">Timesheet component</p>
                  <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.salary_component || '-' }}</div>
                </div>

                <!-- Hour Rate (only if based on timesheet) -->
                <div v-if="details.salary_slip_based_on_timesheet" class="space-y-1">
                  <p class="status-label">Hour rate</p>
                  <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ formatAmount(details.hour_rate) }}</div>
                </div>
              </div>
            </div>

            <!-- Earnings List -->
            <div class="glass-card">
              <div class="flex justify-between items-center mb-4 pb-3 border-b border-gray-100 dark:border-gray-800">
                <p class="status-label">Earnings components</p>
                <span class="text-xs text-[#656A72] dark:text-white/55 tabular-nums">
                  {{ details.earnings?.length || 0 }} Components
                </span>
              </div>

              <!-- Earnings Table -->
              <div class="overflow-x-auto" v-if="details.earnings && details.earnings.length > 0">
                <table class="w-full text-left border-collapse">
                  <thead>
                    <tr class="border-b border-black/[0.07] dark:border-white/10">
                      <th class="table-th">Component</th>
                      <th class="table-th">Abbr</th>
                      <th class="table-th">Formula / condition</th>
                      <th class="!text-right table-th">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="item in details.earnings" :key="item.salary_component" class="border-b last:border-0 border-black/[0.05] dark:border-white/[0.06]">
                      <td class="table-td">
                        {{ item.salary_component }}
                      </td>
                      <td class="table-td">
                        {{ item.abbr || '-' }}
                      </td>
                      <td class="table-td">
                        <div v-if="item.formula" class="flex flex-col">
                          <p class="status-label">Formula</p>
                          <code class="btn-secondary text-accent dark:text-accent-light font-mono w-fit max-w-xs truncate block" :title="item.formula">
                            {{ item.formula }}
                          </code>
                        </div>
                        <div v-if="item.condition" class="flex flex-col">
                          <p class="status-label">Condition</p>
                          <code class="btn-secondary text-amber-600 font-mono w-fit max-w-xs truncate block" :title="item.condition">
                            {{ item.condition }}
                          </code>
                        </div>
                        <span v-if="!item.formula && !item.condition" class="text-xs text-[#656A72] dark:text-white/60">Fixed Amount</span>
                      </td>
                      <td class="!text-right table-td">
                        {{ formatAmount(item.amount) }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-else class="text-center py-6 text-[13px] text-[#656A72] dark:text-white/55">
                No earning components configured
              </div>
            </div>

            <!-- Deductions List -->
            <div class="glass-card">
              <div class="flex justify-between items-center mb-4 pb-3 border-b border-gray-100 dark:border-gray-800">
                <p class="status-label">Deductions components</p>
                <span class="text-xs text-[#656A72] dark:text-white/55 tabular-nums">
                  {{ details.deductions?.length || 0 }} Components
                </span>
              </div>

              <!-- Deductions Table -->
              <div class="overflow-x-auto" v-if="details.deductions && details.deductions.length > 0">
                <table class="w-full text-left border-collapse">
                  <thead>
                    <tr class="border-b border-black/[0.07] dark:border-white/10">
                      <th class="table-th">Component</th>
                      <th class="table-th">Abbr</th>
                      <th class="table-th">Formula / condition</th>
                      <th class="!text-right table-th">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="item in details.deductions" :key="item.salary_component" class="border-b last:border-0 border-black/[0.05] dark:border-white/[0.06]">
                      <td class="table-td">
                        {{ item.salary_component }}
                      </td>
                      <td class="table-td">
                        {{ item.abbr || '-' }}
                      </td>
                      <td class="table-td">
                        <div v-if="item.formula" class="flex flex-col">
                          <p class="status-label">Formula</p>
                          <code class="btn-secondary text-accent dark:text-accent-light font-mono w-fit max-w-xs truncate block" :title="item.formula">
                            {{ item.formula }}
                          </code>
                        </div>
                        <div v-if="item.condition" class="flex flex-col">
                          <p class="status-label">Condition</p>
                          <code class="btn-secondary text-amber-600 font-mono w-fit max-w-xs truncate block" :title="item.condition">
                            {{ item.condition }}
                          </code>
                        </div>
                        <span v-if="!item.formula && !item.condition" class="text-xs text-[#656A72] dark:text-white/60">Fixed Amount</span>
                      </td>
                      <td class="!text-right table-td">
                        {{ formatAmount(item.amount) }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-else class="text-center py-6 text-[13px] text-[#656A72] dark:text-white/55">
                No deduction components configured
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
import { ref, watch, computed } from 'vue';
import { Dialog, call } from 'frappe-ui';
import { storeToRefs } from 'pinia';
import { usePayrollStore } from '@/stores/payroll';

const payrollStore = usePayrollStore();
const { canEditSalaryStructure, canDeleteSalaryStructure } = storeToRefs(payrollStore);

const props = defineProps({
  modelValue: Boolean,
  name: String
});

const emit = defineEmits(['update:modelValue', 'edit', 'delete']);

const show = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
});

const loading = ref(true);
const error = ref('');
const details = ref(null);

watch(() => show.value, (newVal) => {
  if (newVal && props.name) {
    fetchDetails();
  } else {
    details.value = null;
  }
});

function formatAmount(val) {
  if (val === undefined || val === null) return '0.00';
  const num = parseFloat(val);
  const formatted = num.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
  return `${details.value?.currency || 'USD'} ${formatted}`;
}

async function fetchDetails() {
  if (!props.name) return;
  
  loading.value = true;
  error.value = '';
  
  try {
    const res = await call('arijentek_core.api.payroll.get_salary_structure_details', {
      name: props.name
    });
    details.value = res;
  } catch (err) {
    console.error('Failed to load salary structure details:', err);
    error.value = err.message || 'An error occurred while fetching details';
  } finally {
    loading.value = false;
  }
}
</script>
