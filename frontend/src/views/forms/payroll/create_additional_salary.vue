<template>
  <Teleport to="body">
    <Dialog :options="{ size: 'lg' }" v-model="show">
      <template #body>
        <div class="modal-panel relative w-full overflow-hidden flex flex-col max-h-[90vh]">
          <!-- Custom Header -->
          <header class="modal-header shrink-0 flex justify-between items-center">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-[12px] bg-accent/[0.10] dark:bg-accent/20 border border-accent/30 dark:border-accent/30 flex items-center justify-center text-accent dark:text-accent-light shrink-0 shadow-sm">
                <span class="material-symbols-outlined text-xl">payments</span>
              </div>
              <div>
                <h3 class="modal-title">
                  {{ editId ? 'Edit additional salary' : 'New additional salary' }}
                </h3>
                <p class="text-xs font-medium text-[#5C6169] dark:text-white/65">
                  {{ editId ? 'Update employee additional salary details' : 'Create additional salary entry for employee' }}
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
              <p class="text-xs font-medium text-[#5C6169] dark:text-white/65">Loading additional salary details...</p>
            </div>

            <template v-else>
              <!-- Submit Error message -->
              <div v-if="errorMessage" class="p-4 bg-red-50 border border-red-100 rounded-[12px] flex items-start gap-3">
                <span class="material-symbols-outlined text-red-500 dark:text-red-400 text-lg shrink-0">error</span>
                <div class="text-xs font-medium text-red-700 dark:text-red-400 leading-relaxed">{{ errorMessage }}</div>
              </div>

              <!-- Field 1: Employee -->
              <div class="flex flex-col gap-2">
                <label class="field-label">
                  Employee <span class="text-red-500 dark:text-red-400">*</span>
                </label>
                <SearchableDropdown
                  v-model="formData.employee"
                  :options="employeeOptions"
                  placeholder="Select employee"
                />
              </div>

              <!-- Field 2: Salary Component -->
              <div class="flex flex-col gap-2">
                <label class="field-label">
                  Salary Component <span class="text-red-500 dark:text-red-400">*</span>
                </label>
                <SearchableDropdown
                  v-model="formData.salary_component"
                  :options="salaryComponentOptions"
                  placeholder="Select salary component"
                />
              </div>

              <!-- Grid Fields: Amount & Payroll Date -->
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <!-- Field 3: Amount -->
                <div class="flex flex-col gap-2">
                  <label class="field-label">
                    Amount ($) <span class="text-red-500 dark:text-red-400">*</span>
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    v-model.number="formData.amount"
                    placeholder="0.00"
                    required
                    class="field-input w-full"
                  />
                </div>

                <!-- Field 4: Payroll Date -->
                <div class="flex flex-col gap-2">
                  <label class="field-label">
                    Payroll Date <span class="text-red-500 dark:text-red-400">*</span>
                  </label>
                  <DateField v-model="formData.payroll_date" />
                </div>
              </div>

              <!-- Field 5: Overwrite Salary Structure Amount -->
              <div class="flex items-center gap-3 pt-2">
                <input
                  type="checkbox"
                  id="overwrite_amount"
                  v-model="formData.overwrite_salary_structure_amount"
                  class="w-4 h-4 text-accent dark:text-accent-light rounded focus:ring-accent/20 border-black/[0.09] dark:border-white/10"
                />
                <label for="overwrite_amount" class="text-xs font-medium text-[#17181B] dark:text-white/80 cursor-pointer">
                  Overwrite Salary Structure Amount
                </label>
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
import DateField from '../../../components/DateField.vue'

const props = defineProps({
  modelValue: Boolean,
  editId: String,
});

const emit = defineEmits(['update:modelValue', 'save']);

const loading = ref(false);
const saving = ref(false);
const errorMessage = ref('');

const employeeOptions = ref([]);
const salaryComponentOptions = ref([]);

const todayDate = new Date().toISOString().split('T')[0];

const formData = ref({
  name: '',
  employee: '',
  salary_component: '',
  amount: 0,
  payroll_date: todayDate,
  overwrite_salary_structure_amount: false,
});

const defaultSalaryComponent = ref(null);

const show = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
});

async function fetchDropdownOptions() {
  try {
    const [empRes, compRes] = await Promise.all([
      call('arijentek_core.api.payroll.get_employee_list'),
      call('arijentek_core.api.payroll.get_salary_components'),
    ]);

    employeeOptions.value = (empRes || []).map((emp) => ({
      value: emp.name,
      label: emp.employee_name ? `${emp.employee_name} (${emp.name})` : emp.name,
    }));

    const components = (compRes || []).map((comp) => ({
      value: comp.name,
      label: comp.salary_component ? `${comp.salary_component} (${comp.name})` : comp.name,
    }));

    salaryComponentOptions.value = components;

    // Find the "Basic" salary component to use as default
    const basicComponent = components.find(c => 
      c.label.toLowerCase().includes('basic') || 
      c.value.toLowerCase().includes('basic')
    );
    if (basicComponent) {
      defaultSalaryComponent.value = basicComponent.value;
    }
  } catch (e) {
    console.error('Failed to fetch dropdown options:', e);
  }
}

async function loadData() {
  errorMessage.value = '';
  if (props.editId) {
    loading.value = true;
    try {
      const res = await call('arijentek_core.api.payroll.get_additional_salary_details', { name: props.editId });
      if (res) {
        formData.value = {
          name: res.name || '',
          employee: res.employee || '',
          salary_component: res.salary_component || '',
          amount: res.amount || 0,
          payroll_date: res.payroll_date || todayDate,
          overwrite_salary_structure_amount: !!res.overwrite_salary_structure_amount,
        };
      }
    } catch (e) {
      console.error('Failed to load additional salary details:', e);
      errorMessage.value = getErrorMessage(e, 'Failed to load additional salary details.');
    } finally {
      loading.value = false;
    }
  } else {
    formData.value = {
      name: '',
      employee: '',
      salary_component: defaultSalaryComponent.value || '',
      amount: 0,
      payroll_date: todayDate,
      overwrite_salary_structure_amount: false,
    };
  }
}

async function submitForm() {
  errorMessage.value = '';
  if (!formData.value.employee) {
    errorMessage.value = 'Employee is required.';
    return;
  }
  if (!formData.value.salary_component) {
    errorMessage.value = 'Salary Component is required.';
    return;
  }
  if (!formData.value.amount || formData.value.amount <= 0) {
    errorMessage.value = 'Valid amount is required.';
    return;
  }
  if (!formData.value.payroll_date) {
    errorMessage.value = 'Payroll Date is required.';
    return;
  }

  saving.value = true;
  try {
    await call('arijentek_core.api.payroll.save_additional_salary', { doc: formData.value });
    emit('save');
    show.value = false;
  } catch (e) {
    console.error('Failed to save additional salary:', e);
    errorMessage.value = getErrorMessage(e, 'Failed to save Additional Salary.');
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
