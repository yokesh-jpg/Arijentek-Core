<template>
  <Dialog :options="{ size: 'xl' }" v-model="show">
    <template #body>
      <div class="modal-panel">
        <!-- Custom Header -->
        <header class="modal-header">
          <div>
            <h3 class="modal-title truncate">Assignment details</h3>
            <p class="text-[12px] text-[#656A72] dark:text-white/60 truncate tabular-nums">{{ name }}</p>
          </div>
          <div class="flex items-center gap-1 shrink-0">
            <button class="btn-icon-ghost" aria-label="Edit" title="Edit" 
              v-if="details && canEditSalaryStructureAssignment" 
              @click="emit('edit', details); show = false" 
             
            ><span class="material-symbols-outlined !text-[18px]">edit</span></button>
            <button class="btn-danger-ghost disabled:opacity-40" aria-label="Delete" title="Delete" 
              v-if="details && canDeleteSalaryStructureAssignment" 
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
          <div v-else-if="details" class="glass-card">
            <div class="flex justify-between items-center mb-4 pb-4 border-b border-gray-100 dark:border-gray-800">
              <div class="flex items-center gap-3">
                <div class="w-12 h-12 rounded-[12px] bg-accent/[0.10] dark:bg-accent/20 border border-accent/30 dark:border-accent/30/50 flex items-center justify-center text-accent dark:text-accent-light shrink-0 shadow-sm">
                  <span class="material-symbols-outlined text-xl">account_tree</span>
                </div>
                <div>
                  <h3 class="text-[14px] font-semibold text-[#17181B] dark:text-white">
                    Salary Structure Assignment
                  </h3>
                  <p class="text-[12px] text-[#656A72] dark:text-white/55">Assigned Salary Configuration</p>
                </div>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <!-- Employee ID -->
              <div class="space-y-1">
                <p class="status-label">Employee</p>
                <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">
                  {{ details.employee_name ? `${details.employee_name} (${details.employee})` : details.employee }}
                </div>
              </div>

              <!-- Salary Structure -->
              <div class="space-y-1">
                <p class="status-label">Salary structure</p>
                <div class="text-[14px] font-semibold text-accent dark:text-accent-light mt-1 tabular-nums">
                  {{ details.salary_structure }}
                </div>
              </div>

              <!-- From Date -->
              <div class="space-y-1">
                <p class="status-label">From date</p>
                <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">
                  {{ formatDate(details.from_date) }}
                </div>
              </div>

              <!-- Base Salary -->
              <div class="space-y-1">
                <p class="status-label">Base salary</p>
                <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">
                  {{ formatAmount(details.base_salary || details.base) }}
                </div>
              </div>

              <!-- Company -->
              <div class="space-y-1">
                <p class="status-label">Company</p>
                <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">
                  {{ details.company || '-' }}
                </div>
              </div>

              <!-- Department -->
              <div class="space-y-1">
                <p class="status-label">Department</p>
                <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">
                  {{ details.department || '-' }}
                </div>
              </div>

              <!-- Designation -->
              <div class="space-y-1">
                <p class="status-label">Designation</p>
                <div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">
                  {{ details.designation || '-' }}
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
import { ref, watch, computed } from 'vue';
import { Dialog, call } from 'frappe-ui';
import { storeToRefs } from 'pinia';
import { usePayrollStore } from '@/stores/payroll';

const payrollStore = usePayrollStore();
const { canEditSalaryStructureAssignment, canDeleteSalaryStructureAssignment } = storeToRefs(payrollStore);

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

function formatDate(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

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
    const res = await call('arijentek_core.api.payroll.get_salary_structure_assignment', {
      id: props.name
    });
    details.value = res;
  } catch (err) {
    console.error('Failed to load salary structure assignment details:', err);
    error.value = err.message || 'An error occurred while fetching details';
  } finally {
    loading.value = false;
  }
}
</script>
