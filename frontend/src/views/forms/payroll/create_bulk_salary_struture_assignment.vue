<template>
  <Dialog :options="{ size: '6xl' }" v-model="show">
    <template #body>
      <div class="modal-panel relative w-full overflow-hidden flex flex-col max-h-[90vh]">
        <!-- Header -->
        <header class="modal-header shrink-0 flex justify-between items-center">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-[12px] bg-accent/[0.10] dark:bg-accent/20 border border-accent/30 dark:border-accent/30 flex items-center justify-center text-accent dark:text-accent-light shrink-0 shadow-sm">
              <span class="material-symbols-outlined text-xl">group_add</span>
            </div>
            <div>
              <h3 class="modal-title">
                Bulk assign salary structure
              </h3>
              <p class="text-xs font-medium text-[#5C6169] dark:text-white/65">
                Filter employees and assign structures in bulk
              </p>
            </div>
          </div>
          <button @click="show = false" class="p-2 text-[#656A72] dark:text-white/60 hover:text-[#17181B] dark:hover:text-white hover:bg-black/[0.04] dark:hover:bg-white/[0.06] rounded-[12px] transition-all">
            <span class="material-symbols-outlined text-sm">close</span>
          </button>
        </header>

        <!-- Body -->
        <div class="modal-body overflow-y-auto space-y-6 flex-1">
          <div class="inset-panel grid grid-cols-1 md:grid-cols-2 gap-6">
            <!-- Salary Structure Dropdown -->
            <div class="flex flex-col gap-2">
              <label class="field-label">
                Salary Structure <span class="text-red-500 dark:text-red-400">*</span>
              </label>
              <div class="flex items-center gap-2">
                <div class="flex-1 min-w-0">
                  <SearchableDropdown
                    v-model="bulkData.salary_structure"
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
              <DateField v-model="bulkData.from_date" :invalid="!!errors.from_date" />
              <p v-if="errors.from_date" class="field-error">{{ errors.from_date }}</p>
            </div>
          </div>

          <!-- Filters Section -->
          <div class="space-y-3">
            <h4 class="field-label">Filters</h4>
            <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-4">
              <!-- Branch -->
              <div class="flex flex-col gap-1.5">
                <label class="field-label">Branch</label>
                <SearchableDropdown
                  v-model="filters.branch"
                  :options="branchOptions"
                  placeholder="All Branches"
                  :showAllOption="true"
                  allOptionLabel="All Branches"
                />
              </div>

              <!-- Department -->
              <div class="flex flex-col gap-1.5">
                <label class="field-label">Department</label>
                <SearchableDropdown
                  v-model="filters.department"
                  :options="departmentOptions"
                  placeholder="All departments"
                  :showAllOption="true"
                  allOptionLabel="All departments"
                />
              </div>

              <!-- Designation -->
              <div class="flex flex-col gap-1.5">
                <label class="field-label">Designation</label>
                <SearchableDropdown
                  v-model="filters.designation"
                  :options="designationOptions"
                  placeholder="All designations"
                  :showAllOption="true"
                  allOptionLabel="All designations"
                />
              </div>

              <!-- Employee Type -->
              <div class="flex flex-col gap-1.5">
                <label class="field-label">Employee type</label>
                <SearchableDropdown
                  v-model="filters.employee_type"
                  :options="employeeTypeOptions"
                  placeholder="All types"
                  :showAllOption="true"
                  allOptionLabel="All types"
                />
              </div>

              <!-- Employee Grade -->
              <div class="flex flex-col gap-1.5">
                <label class="field-label">Grade</label>
                <SearchableDropdown
                  v-model="filters.grade"
                  :options="gradeOptions"
                  placeholder="All Grades"
                  :showAllOption="true"
                  allOptionLabel="All Grades"
                />
              </div>
            </div>
          </div>

          <!-- Quick Fill Tools -->
          <div class="inset-panel flex flex-col sm:flex-row items-end gap-4">
            <div class="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-4 w-full">
              <div class="flex flex-col gap-1.5">
                <label class="field-label">Base amount for all</label>
                <input 
                  v-model.number="bulkBase" 
                  type="number" 
                  placeholder="Set base for all selected..."
                  class="field-input w-full"
                />
              </div>
              <div class="flex flex-col gap-1.5">
                <label class="field-label">Variable amount for all</label>
                <input 
                  v-model.number="bulkVariable" 
                  type="number" 
                  placeholder="Set variable for all selected..."
                  class="field-input w-full"
                />
              </div>
            </div>
            <button 
              @click="applyBulkAmounts"
              class="btn-secondary self-end sm:mb-0.5"
            >
              Apply to Selected
            </button>
          </div>

          <!-- Employees Table -->
          <div class="border border-black/[0.07] dark:border-white/10 rounded-[12px] overflow-hidden shadow-sm">
            <div v-if="loadingEmployees" class="p-12 flex justify-center bg-white dark:bg-surface-1">
              <div class="w-6 h-6 border-2 border-black/[0.07] border-t-accent rounded-full animate-spin"></div>
            </div>

            <table v-else class="w-full text-left border-collapse bg-white dark:bg-surface-1">
              <thead>
                <tr class="border-b border-black/[0.07] dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.05]">
                  <th class="px-6 py-4 w-12 text-center">
                    <input 
                      type="checkbox" 
                      :checked="allSelected" 
                      @change="toggleSelectAll"
                      class="rounded text-accent dark:text-accent-light focus:ring-accent/20 border-black/[0.09]"
                    />
                  </th>
                  <th class="table-th">Employee ID and name</th>
                  <th class="table-th w-48">Base amount</th>
                  <th class="table-th w-48">Variable amount</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-black/[0.05] dark:divide-white/[0.06]">
                <tr v-for="emp in employeesList" :key="emp.name" class="hover:bg-black/[0.03] dark:hover:bg-white/[0.06] transition-colors">
                  <td class="px-6 py-4 text-center">
                    <input 
                      type="checkbox" 
                      v-model="emp.selected"
                      class="rounded text-accent dark:text-accent-light focus:ring-accent/20 border-black/[0.09]"
                    />
                  </td>
                  <td class="px-6 py-4">
                    <div class="flex flex-col">
                      <span class="text-sm font-semibold text-[#17181B] dark:text-white">{{ emp.employee_name }}</span>
                      <span class="text-xs text-[#656A72] dark:text-white/60">{{ emp.name }}</span>
                    </div>
                  </td>
                  <td class="px-6 py-4">
                    <input 
                      v-model.number="emp.base_salary" 
                      type="number" 
                      min="0"
                      step="0.01"
                      class="field-input w-full"
                      :disabled="!emp.selected"
                    />
                  </td>
                  <td class="px-6 py-4">
                    <input 
                      v-model.number="emp.variable" 
                      type="number" 
                      min="0"
                      step="0.01"
                      class="field-input w-full"
                      :disabled="!emp.selected"
                    />
                  </td>
                </tr>
                <tr v-if="employeesList.length === 0">
                  <td colspan="4" class="px-6 py-12 text-center text-[#5C6169] dark:text-white/65">
                    No active employees found matching the filters
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Submit/Validation Errors -->
          <div v-if="submitError || errors.general" class="p-4 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-[12px] flex items-start gap-3 mt-4">
            <span class="material-symbols-outlined text-red-500 dark:text-red-400 text-lg shrink-0">error</span>
            <div class="text-xs font-medium text-red-700 dark:text-red-300 leading-relaxed">{{ submitError || errors.general }}</div>
          </div>
        </div>

        <!-- Footer -->
        <footer class="p-6 border-t border-black/[0.07] dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.05] flex justify-between items-center shrink-0">
          <div class="text-xs font-semibold text-[#5C6169] dark:text-white/65">
            Selected: {{ selectedCount }} of {{ employeesList.length }}
          </div>
          <div class="flex gap-3">
            <button @click="show = false" class="btn-secondary">Cancel</button>
            <button 
              @click="submitBulk" 
              :disabled="submitting" 
              class="btn-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <div v-if="submitting" class="w-4 h-4 border-2 border-white/30 dark:border-white/20 border-t-white dark:border-t-white rounded-full animate-spin"></div>
              <span>Assign structure</span>
            </button>
          </div>
        </footer>
      </div>
    </template>
  </Dialog>

  <CreateSalaryStructure v-model="showCreateStructureModal" @save="onStructureCreated" />
</template>

<script setup>
import { notify } from '@/utils/feedback.js'
import { ref, computed, watch } from 'vue';
import { Dialog, call } from 'frappe-ui';
import SearchableDropdown from '../../../components/SearchableDropdown.vue';
import { getErrorMessage } from '../../../utils';
import { usePayrollStore } from '../../../stores/payroll';
import { storeToRefs } from 'pinia';
import CreateSalaryStructure from './create_salary_structure.vue';
import DateField from '../../../components/DateField.vue'

const show = defineModel();
const emit = defineEmits(['save']);

const submitting = ref(false);
const loadingEmployees = ref(false);
const submitError = ref('');

const payrollStore = usePayrollStore();
const { canCreateSalaryStructure, canCreateSalaryStructureAssignment } = storeToRefs(payrollStore);
const showCreateStructureModal = ref(false);

async function onStructureCreated(savedDoc) {
  await loadFilterOptions();
  if (savedDoc && savedDoc.name) {
    bulkData.value.salary_structure = savedDoc.name;
  }
}

const bulkData = ref({
  salary_structure: '',
  from_date: '',
  payroll_payable_account: ''
});

const filters = ref({
  branch: '',
  department: '',
  designation: '',
  employee_type: '',
  grade: ''
});

const bulkBase = ref(0);
const bulkVariable = ref(0);

const salaryStructureOptions = ref([]);
const branchOptions = ref([]);
const departmentOptions = ref([]);
const designationOptions = ref([]);
const employeeTypeOptions = ref([]);
const gradeOptions = ref([]);

const employeesList = ref([]);

const selectedCount = computed(() => {
  return employeesList.value.filter(emp => emp.selected).length;
});

const allSelected = computed(() => {
  return employeesList.value.length > 0 && employeesList.value.every(emp => emp.selected);
});

function toggleSelectAll() {
  const target = !allSelected.value;
  employeesList.value.forEach(emp => {
    emp.selected = target;
  });
}

function applyBulkAmounts() {
  if (selectedCount.value === 0) {
    notify('Select at least one employee first to apply amounts', 'info');
    return;
  }
  employeesList.value.forEach(emp => {
    if (emp.selected) {
      if (bulkBase.value !== null && bulkBase.value !== undefined) {
        emp.base_salary = bulkBase.value;
      }
      if (bulkVariable.value !== null && bulkVariable.value !== undefined) {
        emp.variable = bulkVariable.value;
      }
    }
  });
}

async function loadFilterOptions() {
  try {
    const res = await call('arijentek_core.api.payroll.get_salary_structure_assignment_options');
    if (res) {
      salaryStructureOptions.value = (res.salary_structures || []).map(s => ({ label: s, value: s }));
      branchOptions.value = (res.branches || []).map(b => ({ label: b, value: b }));
      departmentOptions.value = (res.departments || []).map(d => ({ label: d, value: d }));
      designationOptions.value = (res.designations || []).map(d => ({ label: d, value: d }));
      employeeTypeOptions.value = (res.employee_types || []).map(t => ({ label: t, value: t }));
      gradeOptions.value = (res.grades || []).map(g => ({ label: g, value: g }));
    }
  } catch (e) {
    console.error('Failed to load filter options:', e);
  }
}

async function fetchEmployees() {
  loadingEmployees.value = true;
  try {
    const params = {};
    if (filters.value.branch) params.branch = filters.value.branch;
    if (filters.value.department) params.department = filters.value.department;
    if (filters.value.designation) params.designation = filters.value.designation;
    if (filters.value.employee_type) params.employee_type = filters.value.employee_type;
    if (filters.value.grade) params.grade = filters.value.grade;

    const res = await call('arijentek_core.api.payroll.get_employees_for_bulk_assignment', params);
    employeesList.value = (res || []).map(emp => ({
      name: emp.name,
      employee_name: emp.employee_name,
      selected: false,
      base_salary: 0,
      variable: 0
    }));
  } catch (e) {
    console.error('Failed to fetch employees:', e);
  } finally {
    loadingEmployees.value = false;
  }
}

// Watch filters to automatically refresh employee list
let debounceTimer;
watch(filters, () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    fetchEmployees();
  }, 350);
}, { deep: true });

const errors = ref({});

watch(show, async (newVal) => {
  if (newVal) {
    bulkData.value = {
      salary_structure: '',
      from_date: '',
      payroll_payable_account: ''
    };
    filters.value = {
      branch: '',
      department: '',
      designation: '',
      employee_type: '',
      grade: ''
    };
    bulkBase.value = 0;
    bulkVariable.value = 0;
    errors.value = {};
    submitError.value = '';
    
    await loadFilterOptions();
    await fetchEmployees();
  }
});

function validate() {
  errors.value = {};
  submitError.value = '';
  let isValid = true;

  if (!canCreateSalaryStructureAssignment.value) {
    submitError.value = 'You do not have permission to assign salary structures';
    return false;
  }

  if (!bulkData.value.salary_structure) {
    errors.value.salary_structure = 'Salary Structure is required';
    isValid = false;
  }

  if (!bulkData.value.from_date) {
    errors.value.from_date = 'From Date is required';
    isValid = false;
  }

  if (selectedCount.value === 0) {
    errors.value.general = 'Please select at least one employee';
    isValid = false;
  }

  return isValid;
}

async function submitBulk() {
  submitError.value = '';
  if (!validate()) return;

  submitting.value = true;
  const selectedEmployees = employeesList.value.filter(emp => emp.selected);

  try {
    const payload = {
      assignments: JSON.stringify(selectedEmployees.map(emp => ({
        employee: emp.name,
        base_salary: emp.base_salary,
        variable: emp.variable
      }))),
      salary_structure: bulkData.value.salary_structure,
      from_date: bulkData.value.from_date
    };
    if (bulkData.value.payroll_payable_account) {
      payload.payroll_payable_account = bulkData.value.payroll_payable_account;
    }

    await call('arijentek_core.api.payroll.save_bulk_salary_structure_assignments', payload);
    notify('Successfully completed salary structure assignments!');
    emit('save');
    show.value = false;
  } catch (e) {
    console.error(e);
    submitError.value = getErrorMessage(e, 'Failed to assign salary structure.');
  } finally {
    submitting.value = false;
  }
}
</script>
