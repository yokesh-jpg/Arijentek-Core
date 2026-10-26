<template>
  <Dialog :options="{ size: 'lg' }" v-model="show">
    <template #body>
      <div class="modal-panel relative w-full overflow-hidden flex flex-col max-h-[90vh]">
        <!-- Custom Header -->
        <header class="modal-header shrink-0 flex justify-between items-center">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-[12px] bg-accent/[0.10] dark:bg-accent/20 border border-accent/30 dark:border-accent/30 flex items-center justify-center text-accent dark:text-accent-light shrink-0 shadow-sm">
              <span class="material-symbols-outlined text-xl">assignment_ind</span>
            </div>
            <div>
              <h3 class="modal-title">
                {{ isEdit ? 'Edit salary structure assignment' : 'Assign Salary Structure' }}
              </h3>
              <p class="text-xs font-medium text-[#5C6169] dark:text-white/65">
                {{ isEdit ? 'Update employee salary structure details' : 'Create new salary assignment configurations' }}
              </p>
            </div>
          </div>
          <button @click="show = false" class="p-2 text-[#656A72] dark:text-white/60 hover:text-[#17181B] dark:hover:text-white hover:bg-black/[0.04] dark:hover:bg-white/[0.06] rounded-[12px] transition-all">
            <span class="material-symbols-outlined text-sm">close</span>
          </button>
        </header>

        <!-- Form Body -->
        <div class="modal-body overflow-y-auto space-y-6 flex-1">
          <!-- Loading Options -->
          <div v-if="loadingOptions" class="py-12 flex flex-col items-center justify-center gap-3">
            <div class="w-8 h-8 border-2 border-accent/30 border-t-transparent rounded-full animate-spin"></div>
            <p class="text-xs font-medium text-[#5C6169] dark:text-white/65">Loading form settings...</p>
          </div>

          <template v-else>
            <!-- Submit Error message -->
            <div v-if="submitError" class="p-4 bg-red-50 border border-red-100 rounded-[12px] flex items-start gap-3">
              <span class="material-symbols-outlined text-red-500 dark:text-red-400 text-lg shrink-0">error</span>
              <div class="text-xs font-medium text-red-700 dark:text-red-400 leading-relaxed">{{ submitError }}</div>
            </div>

            <!-- Employee Dropdown -->
            <div class="flex flex-col gap-2">
              <label class="field-label">
                Employee <span class="text-red-500 dark:text-red-400">*</span>
              </label>
              <SearchableDropdown
                v-model="formData.employee"
                :options="employeeOptions"
                placeholder="Select employee"
                :disabled="isEdit"
              />
              <p v-if="errors.employee" class="field-error">{{ errors.employee }}</p>
            </div>

            <!-- Salary Structure Dropdown -->
            <div class="flex flex-col gap-2">
              <label class="field-label">
                Salary Structure <span class="text-red-500 dark:text-red-400">*</span>
              </label>
              <div class="flex items-center gap-2">
                <div class="flex-1 min-w-0">
                  <SearchableDropdown
                    v-model="formData.salary_structure"
                    :options="salaryStructureOptions"
                    placeholder="Select salary structure"
                  />
                </div>
                <button
                  v-if="canCreateSalaryStructure"
                  @click="showCreateStructureModal = true" type="button" class="btn-add-option" title="Add a new salary structure" aria-label="Add a new salary structure"><span class="material-symbols-outlined !text-[18px]">add</span></button>
              </div>
              <p v-if="errors.salary_structure" class="field-error">{{ errors.salary_structure }}</p>
            </div>

            <!-- From Date Input -->
            <div class="flex flex-col gap-2">
              <label class="field-label">
                From Date <span class="text-red-500 dark:text-red-400">*</span>
              </label>
              <DateField v-model="formData.from_date" :invalid="!!errors.from_date" />
              <p v-if="errors.from_date" class="field-error">{{ errors.from_date }}</p>
            </div>

            <!-- Base and Variable Amount Grid -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <!-- Base Salary -->
              <div class="flex flex-col gap-2">
                <label class="field-label">
                  Base Amount <span class="text-red-500 dark:text-red-400">*</span>
                </label>
                <input 
                  v-model.number="formData.base_salary" 
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="e.g. 5000"
                  class="field-input w-full"
                  :class="{ 'border-red-400 focus:border-red-500 focus:ring-red-500/20': errors.base_salary }"
                />
                <p v-if="errors.base_salary" class="field-error">{{ errors.base_salary }}</p>
              </div>

              <!-- Variable Amount -->
              <div class="flex flex-col gap-2">
                <label class="field-label">
                  Variable Amount
                </label>
                <input 
                  v-model.number="formData.variable" 
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="e.g. 1000"
                  class="field-input w-full"
                />
              </div>
            </div>
          </template>
        </div>

        <!-- Footer Actions -->
        <footer class="p-6 border-t border-black/[0.07] dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.05] flex justify-end gap-3 shrink-0">
          <button @click="show = false" class="btn-secondary">Cancel</button>
          <button 
            @click="submitForm" 
            :disabled="submitting || loadingOptions" 
            class="btn-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <div v-if="submitting" class="w-4 h-4 border-2 border-white/30 dark:border-white/20 border-t-white dark:border-t-white rounded-full animate-spin"></div>
            <span>{{ isEdit ? 'Update' : 'Create' }}</span>
          </button>
        </footer>
      </div>
    </template>
  </Dialog>

  <CreateSalaryStructure v-model="showCreateStructureModal" @save="onStructureCreated" />
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { Dialog, call } from 'frappe-ui';
import SearchableDropdown from '../../../components/SearchableDropdown.vue';
import { getErrorMessage } from '@/utils';
import { usePayrollStore } from '../../../stores/payroll';
import { storeToRefs } from 'pinia';
import CreateSalaryStructure from './create_salary_structure.vue';
import DateField from '../../../components/DateField.vue'

const show = defineModel();
const props = defineProps({ editData: { type: Object, default: null } });
const emit = defineEmits(['save']);

const isEdit = computed(() => !!props.editData);
const submitting = ref(false);
const loadingOptions = ref(false);
const submitError = ref('');

const payrollStore = usePayrollStore();
const { canCreateSalaryStructure } = storeToRefs(payrollStore);
const showCreateStructureModal = ref(false);

const formData = ref(getInitialFormData());
const errors = ref({});

const employeeOptions = ref([]);
const salaryStructureOptions = ref([]);

async function onStructureCreated(savedDoc) {
  await loadOptions();
  if (savedDoc && savedDoc.name) {
    formData.value.salary_structure = savedDoc.name;
  }
}

function getInitialFormData() {
  return {
    name: '',
    employee: '',
    company: '',
    salary_structure: '',
    from_date: '',
    base_salary: 0,
    variable: 0
  };
}

async function loadOptions() {
  loadingOptions.value = true;
  try {
    const empRes = await call('arijentek_core.api.payroll.get_active_employees');
    employeeOptions.value = (empRes || []).map(emp => ({
      label: emp.employee_name ? `${emp.employee_name} (${emp.name})` : emp.name,
      value: emp.name,
      company: emp.company || ''
    }));

    const structRes = await call('arijentek_core.api.payroll.get_salary_structures_list');
    salaryStructureOptions.value = (structRes || []).map(s => ({
      label: s,
      value: s
    }));

    // Options loaded
  } catch (e) {
    console.error('Failed to load form options:', e);
  } finally {
    loadingOptions.value = false;
  }
}

watch(show, async (newVal) => {
  if (newVal) {
    formData.value = getInitialFormData();
    errors.value = {};
    submitError.value = '';
    
    await loadOptions();

    if (props.editData && props.editData.name) {
      loadingOptions.value = true;
      try {
        const fullDoc = await call('arijentek_core.api.payroll.get_salary_structure_assignment', {
          id: props.editData.name
        });
        if (fullDoc) {
          formData.value.name = fullDoc.name || '';
          formData.value.employee = fullDoc.employee || '';
          formData.value.company = fullDoc.company || '';
          formData.value.salary_structure = fullDoc.salary_structure || '';
          formData.value.from_date = fullDoc.from_date || '';
          formData.value.base_salary = fullDoc.base_salary || fullDoc.base || 0;
          formData.value.variable = fullDoc.variable || 0;
        }
      } catch (err) {
        console.error('Failed to fetch assignment details for edit:', err);
      } finally {
        loadingOptions.value = false;
      }
    }
  }
});

watch(() => formData.value.employee, (newEmp) => {
  if (newEmp && !isEdit.value) {
    const empOpt = employeeOptions.value.find(e => e.value === newEmp);
    formData.value.company = empOpt?.company || '';
  }
});

function validate() {
  errors.value = {};
  let isValid = true;

  if (!formData.value.employee) {
    errors.value.employee = 'Employee is required';
    isValid = false;
  }

  if (!formData.value.salary_structure) {
    errors.value.salary_structure = 'Salary Structure is required';
    isValid = false;
  }

  if (!formData.value.from_date) {
    errors.value.from_date = 'From Date is required';
    isValid = false;
  }

  if (formData.value.base_salary === undefined || formData.value.base_salary === null || formData.value.base_salary < 0) {
    errors.value.base_salary = 'Base Amount must be a positive number';
    isValid = false;
  }

  return isValid;
}

async function submitForm() {
  submitError.value = '';
  if (!validate()) return;

  submitting.value = true;
  try {
    await call('arijentek_core.api.payroll.save_salary_structure_assignment', {
      doc: formData.value
    });
    emit('save', formData.value);
    show.value = false;
  } catch (err) {
    console.error(err);
    submitError.value = getErrorMessage(err, 'Failed to save salary structure assignment');
  } finally {
    submitting.value = false;
  }
}
</script>
