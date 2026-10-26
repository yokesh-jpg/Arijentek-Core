<template>
  <Teleport to="body">
    <Dialog :options="{ size: 'lg' }" v-model="show">
      <template #body>
        <div class="modal-panel relative w-full overflow-hidden flex flex-col max-h-[90vh]">
          <!-- Custom Header -->
          <header class="modal-header shrink-0 flex justify-between items-center">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-[12px] bg-accent/[0.10] dark:bg-accent/20 border border-accent/30 dark:border-accent/30 flex items-center justify-center text-accent dark:text-accent-light shrink-0 shadow-sm">
                <span class="material-symbols-outlined text-xl">more_time</span>
              </div>
              <div>
                <h3 class="modal-title">
                  {{ editId ? 'Edit overtime type' : 'New overtime type' }}
                </h3>
                <p class="text-xs font-medium text-[#5C6169] dark:text-white/65">
                  {{ editId ? `Editing details for ${editId}` : 'Configure overtime calculation rules and multipliers' }}
                </p>
              </div>
            </div>
            <button @click="show = false" class="p-2 text-[#656A72] dark:text-white/60 hover:text-[#17181B] dark:hover:text-white hover:bg-black/[0.04] dark:hover:bg-white/[0.06] rounded-[12px] transition-all">
              <span class="material-symbols-outlined text-sm">close</span>
            </button>
          </header>

          <!-- Form Body -->
          <div class="modal-body overflow-y-auto space-y-6 flex-1">
            <!-- Loading Spinner -->
            <div v-if="loading" class="py-12 flex flex-col items-center justify-center gap-3">
              <div class="w-8 h-8 border-2 border-accent/30 border-t-transparent rounded-full animate-spin"></div>
              <p class="text-xs font-medium text-[#5C6169] dark:text-white/65">Loading overtime type details...</p>
            </div>

            <template v-else>
              <!-- Submit Error message -->
              <div v-if="errorMessage" class="p-4 bg-red-50 border border-red-100 rounded-[12px] flex items-start gap-3">
                <span class="material-symbols-outlined text-red-500 dark:text-red-400 text-lg shrink-0">error</span>
                <div class="text-xs font-medium text-red-700 dark:text-red-400 leading-relaxed">{{ errorMessage }}</div>
              </div>

              <!-- Field 1: Name -->
              <div class="flex flex-col gap-2">
                <label class="field-label">
                  Overtime Type Name <span class="text-red-500 dark:text-red-400">*</span>
                </label>
                <input
                  type="text"
                  v-model="formData.name"
                  :disabled="!!editId"
                  placeholder="e.g. Standard Overtime, Weekend OT"
                  required
                  class="field-input w-full disabled:opacity-60 disabled:cursor-not-allowed"
                />
              </div>

              <!-- Field 2: Overtime Salary Component -->
              <div class="flex flex-col gap-2">
                <label class="field-label">
                  Overtime Salary Component <span class="text-red-500 dark:text-red-400">*</span>
                </label>
                <SearchableDropdown
                  v-model="formData.overtime_salary_component"
                  :options="salaryComponentOptions"
                  placeholder="Select salary component"
                />
              </div>

              <!-- Field 3: Overtime Amount Calculation -->
              <div class="flex flex-col gap-2">
                <label class="field-label">
                  Overtime Amount Calculation <span class="text-red-500 dark:text-red-400">*</span>
                </label>
                <SearchableDropdown
                  v-model="formData.overtime_calculation_method"
                  :options="calculationMethodOptions"
                  placeholder="Select calculation method"
                />
                <p class="text-xs font-medium text-[#5C6169] dark:text-white/65">
                  <span v-if="formData.overtime_calculation_method === 'Salary Component Based'">
                    Calculated based on employee's component salary from salary slip.
                  </span>
                  <span v-else-if="formData.overtime_calculation_method === 'Fixed Hourly Rate'">
                    Uses a fixed hourly rate defined manually below.
                  </span>
                </p>
              </div>

              <!-- Field 4: Fixed Hourly Rate (Conditional) -->
              <div v-if="formData.overtime_calculation_method === 'Fixed Hourly Rate'" class="flex flex-col gap-2">
                <label class="field-label">
                  Hourly Rate ($) <span class="text-red-500 dark:text-red-400">*</span>
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  v-model="formData.hourly_rate"
                  placeholder="0.00"
                  required
                  class="field-input w-full"
                />
              </div>

              <!-- Field 5: Standard Multiplier -->
              <div class="flex flex-col gap-2">
                <label class="field-label">
                  Standard Multiplier <span class="text-red-500 dark:text-red-400">*</span>
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  v-model="formData.standard_multiplier"
                  placeholder="1.0"
                  required
                  class="field-input w-full"
                />
                <p class="text-xs font-medium text-[#5C6169] dark:text-white/65">
                  Multipliers that adjust the hourly overtime amount for standard hours (e.g. 1.5 for 1.5x pay).
                </p>
              </div>
            </template>
          </div>

          <!-- Footer Actions -->
          <footer class="p-6 border-t border-black/[0.07] dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.05] flex justify-end gap-3 shrink-0">
            <button @click="show = false" class="btn-secondary">Cancel</button>
            <button 
              @click="submitForm" 
              :disabled="saving || loading" 
              class="btn-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <div v-if="saving" class="w-4 h-4 border-2 border-white/30 dark:border-white/20 border-t-white dark:border-t-white rounded-full animate-spin"></div>
              <span>{{ editId ? 'Update' : 'Create' }}</span>
            </button>
          </footer>
        </div>
      </template>
    </Dialog>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { Dialog, call } from 'frappe-ui';
import SearchableDropdown from '@/components/SearchableDropdown.vue';
import { getErrorMessage } from '@/utils';

const props = defineProps({
  modelValue: Boolean,
  editId: String,
});

const emit = defineEmits(['update:modelValue', 'save']);

const loading = ref(false);
const saving = ref(false);
const errorMessage = ref('');
const overtimeTypeOptions = ref([]);
const salaryComponentOptions = ref([]);
const calculationMethodOptions = ref([
  { value: 'Salary Component Based', label: 'Salary Component Based' },
  { value: 'Fixed Hourly Rate', label: 'Fixed Hourly Rate' },
]);

const formData = ref({
  name: '',
  overtime_salary_component: '',
  overtime_calculation_method: 'Salary Component Based',
  hourly_rate: 0,
  standard_multiplier: 1.0,
});

const show = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
});

async function fetchDropdownOptions() {
  try {
    const [compRes, otRes] = await Promise.all([
      call('arijentek_core.api.payroll.get_salary_components'),
      call('arijentek_core.api.payroll.get_overtime_type_list'),
    ]);

    salaryComponentOptions.value = (compRes || []).map((comp) => ({
      value: comp.name,
      label: comp.salary_component ? `${comp.salary_component} (${comp.name})` : comp.name,
    }));

    overtimeTypeOptions.value = (otRes || []).map((ot) => ({
      value: ot.value || ot.name,
      label: ot.label || ot.name,
    }));
  } catch (e) {
    console.error('Failed to fetch dropdown options:', e);
  }
}

async function loadData() {
  errorMessage.value = '';
  if (props.editId) {
    loading.value = true;
    try {
      const res = await call('arijentek_core.api.payroll.get_overtime_type_details', { name: props.editId });
      if (res) {
        formData.value = {
          name: res.name || '',
          overtime_salary_component: res.overtime_salary_component || '',
          overtime_calculation_method: res.overtime_calculation_method || 'Salary Component Based',
          hourly_rate: res.hourly_rate || 0,
          standard_multiplier: res.standard_multiplier || 1.0,
        };
      }
    } catch (e) {
      console.error('Failed to load overtime type details:', e);
      errorMessage.value = getErrorMessage(e, 'Failed to load overtime type details.');
    } finally {
      loading.value = false;
    }
  } else {
    formData.value = {
      name: '',
      overtime_salary_component: '',
      overtime_calculation_method: 'Salary Component Based',
      hourly_rate: 0,
      standard_multiplier: 1.0,
    };
  }
}

async function submitForm() {
  errorMessage.value = '';
  if (!formData.value.name) {
    errorMessage.value = 'Overtime Type Name is required.';
    return;
  }
  if (!formData.value.overtime_salary_component) {
    errorMessage.value = 'Overtime Salary Component is required.';
    return;
  }
  if (formData.value.overtime_calculation_method === 'Fixed Hourly Rate' && !formData.value.hourly_rate) {
    errorMessage.value = 'Hourly Rate is required for Fixed Hourly Rate calculation.';
    return;
  }

  saving.value = true;
  try {
    const res = await call('arijentek_core.api.payroll.save_overtime_type', { doc: formData.value });
    emit('save', res?.name || formData.value.name);
    show.value = false;
  } catch (e) {
    console.error('Failed to save overtime type:', e);
    errorMessage.value = getErrorMessage(e, 'Failed to save Overtime Type.');
  } finally {
    saving.value = false;
  }
}

watch(
  () => [props.modelValue, props.editId],
  async ([isOpen]) => {
    if (isOpen) {
      await fetchDropdownOptions();
      await loadData();
    }
  },
  { immediate: true }
);

onMounted(async () => {
  await fetchDropdownOptions();
});
</script>
