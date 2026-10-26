<template>
  <Dialog :options="{ size: '4xl' }" v-model="show">
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
                {{ editId ? 'Edit payroll entry' : 'Create payroll entry' }}
              </h3>
              <p class="text-xs font-medium text-[#5C6169] dark:text-white/65">
                {{ editId ? editId : 'Setup new payroll parameters and select employees.' }}
              </p>
            </div>
          </div>
          <button @click="show = false" class="p-2 text-[#656A72] dark:text-white/60 hover:text-[#17181B] dark:hover:text-white hover:bg-black/[0.04] dark:hover:bg-white/[0.06] rounded-[12px] transition-all">
            <span class="material-symbols-outlined text-sm">close</span>
          </button>
        </header>

        <!-- Form Body -->
        <div class="modal-body overflow-y-auto space-y-6 flex-1">
          <!-- Submit Error message -->
          <div v-if="submitError" class="p-4 bg-red-50 border border-red-100 rounded-[12px] flex items-start gap-3">
            <span class="material-symbols-outlined text-red-500 dark:text-red-400 text-lg shrink-0">error</span>
            <div class="text-xs font-medium text-red-700 dark:text-red-400 leading-relaxed">{{ submitError }}</div>
          </div>

          <div v-if="loadingOptions" class="py-12 flex flex-col items-center justify-center gap-3">
            <div class="w-8 h-8 border-2 border-accent/30 border-t-transparent rounded-full animate-spin"></div>
            <p class="text-xs font-medium text-[#5C6169] dark:text-white/65">Loading form settings...</p>
          </div>

          <template v-else>
            <!-- Core Form Section -->
            <div class="inset-panel grid grid-cols-1 sm:grid-cols-2 gap-6">
              <!-- Company Selection -->
              <div class="flex flex-col gap-2">
                <label class="field-label">
                  Company <span class="text-red-500 dark:text-red-400">*</span>
                </label>
                <SearchableDropdown
                  v-model="formData.company"
                  :options="companyOptions"
                  placeholder="Select company"
                />
                <p v-if="errors.company" class="field-error text-red-500 dark:text-red-400 flex items-center gap-1 mt-0.5">
                  <span class="material-symbols-outlined text-sm">error</span>
                  {{ errors.company }}
                </p>
              </div>

              <!-- Currency Display -->
              <div class="flex flex-col gap-2">
                <label class="field-label">
                  Currency
                </label>
                <div class="relative w-full">
                  <input
                    type="text"
                    :value="formData.currency || '—'"
                    readonly
                    class="field-input !pr-9 cursor-default font-medium text-gray-900 dark:text-white bg-black/[0.02] dark:bg-white/[0.03]"
                    placeholder="Currency"
                  />
                  <span class="material-symbols-outlined !text-[18px] absolute right-2.5 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/60 pointer-events-none">
                    payments
                  </span>
                </div>
              </div>

              <!-- Posting Date -->
              <div class="flex flex-col gap-2">
                <label class="field-label">
                  Posting Date <span class="text-red-500 dark:text-red-400">*</span>
                </label>
                <DateField v-model="formData.posting_date" :invalid="!!errors.posting_date" />
                <p v-if="errors.posting_date" class="field-error text-red-500 dark:text-red-400 flex items-center gap-1 mt-0.5">
                  <span class="material-symbols-outlined text-sm">error</span>
                  {{ errors.posting_date }}
                </p>
              </div>

              <!-- Payroll Frequency -->
              <div class="flex flex-col gap-2">
                <label class="field-label">
                  Payroll Frequency <span class="text-red-500 dark:text-red-400">*</span>
                </label>
                <SearchableDropdown
                  v-model="formData.payroll_frequency"
                  :options="frequencyOptions"
                  placeholder="Select frequency"
                />
                <p v-if="errors.payroll_frequency" class="field-error text-red-500 dark:text-red-400 flex items-center gap-1 mt-0.5">
                  <span class="material-symbols-outlined text-sm">error</span>
                  {{ errors.payroll_frequency }}
                </p>
              </div>

              <!-- Start Date -->
              <div class="flex flex-col gap-2">
                <label class="field-label">
                  Start Date <span class="text-red-500 dark:text-red-400">*</span>
                </label>
                <DateField v-model="formData.start_date" :invalid="!!errors.start_date" />
                <p v-if="errors.start_date" class="field-error text-red-500 dark:text-red-400 flex items-center gap-1 mt-0.5">
                  <span class="material-symbols-outlined text-sm">error</span>
                  {{ errors.start_date }}
                </p>
              </div>

              <!-- End Date -->
              <div class="flex flex-col gap-2">
                <label class="field-label">
                  End Date <span class="text-red-500 dark:text-red-400">*</span>
                </label>
                <DateField v-model="formData.end_date" :min="formData.start_date" :invalid="!!errors.end_date" />
                <p v-if="errors.end_date" class="field-error text-red-500 dark:text-red-400 flex items-center gap-1 mt-0.5">
                  <span class="material-symbols-outlined text-sm">error</span>
                  {{ errors.end_date }}
                </p>
              </div>
            </div>

            <!-- Get Employee Filters Block -->
            <div class="space-y-4">
              <h4 class="text-sm font-semibold text-[#17181B] dark:text-white">
                Get Employees Filters
              </h4>
              
              <div class="inset-panel grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-4">
                <!-- Branch -->
                <div class="flex flex-col gap-1.5">
                  <label class="field-label">Branch</label>
                  <SearchableDropdown
                    v-model="employeeFilters.branch"
                    :options="branchOptions"
                    placeholder="All Branches"
                    showAllOption
                    allOptionLabel="All Branches"
                  />
                </div>

                <!-- Designation -->
                <div class="flex flex-col gap-1.5">
                  <label class="field-label">Designation</label>
                  <SearchableDropdown
                    v-model="employeeFilters.designation"
                    :options="designationOptions"
                    placeholder="All designations"
                    showAllOption
                    allOptionLabel="All designations"
                  />
                </div>

                <!-- Department -->
                <div class="flex flex-col gap-1.5">
                  <label class="field-label">Department</label>
                  <SearchableDropdown
                    v-model="employeeFilters.department"
                    :options="departmentOptions"
                    placeholder="All departments"
                    showAllOption
                    allOptionLabel="All departments"
                  />
                </div>

                <!-- Grade -->
                <div class="flex flex-col gap-1.5">
                  <label class="field-label">Grade</label>
                  <SearchableDropdown
                    v-model="employeeFilters.grade"
                    :options="gradeOptions"
                    placeholder="All Grades"
                    showAllOption
                    allOptionLabel="All Grades"
                  />
                </div>

                <!-- Salary Structure -->
                <div class="flex flex-col gap-1.5">
                  <label class="field-label">Salary structure</label>
                  <SearchableDropdown
                    v-model="employeeFilters.salary_structure"
                    :options="salaryStructureOptions"
                    placeholder="All Structures"
                    showAllOption
                    allOptionLabel="All Structures"
                  />
                </div>

                <!-- Hourly Paid (Based on Timesheet) -->
                <div class="flex items-center col-span-1 sm:col-span-2 md:col-span-5 mt-2">
                  <label class="flex items-center gap-3 cursor-pointer group">
                    <input 
                      type="checkbox"
                      v-model="employeeFilters.salary_slip_based_on_timesheet"
                      class="w-5 h-5 rounded border-black/[0.09] dark:border-white/10 dark:bg-white/[0.06] text-accent dark:text-accent-light focus:ring-accent/20"
                    />
                    <span class="field-label group-hover:text-[#17181B] dark:text-white dark:group-hover:text-white">
                      Salary Slip Based on Timesheet (Hourly Based)
                    </span>
                  </label>
                </div>
              </div>

              <!-- Fetch Action Button -->
              <div class="flex justify-end">
                <button
                  type="button"
                  @click="fetchEmployees"
                  :disabled="fetchingEmployees || !formData.company"
                  class="btn-primary disabled:bg-black/[0.08] dark:disabled:bg-white/[0.06] disabled:cursor-not-allowed flex items-center gap-2"
                >
                  <div v-if="fetchingEmployees" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  <span>Get employees</span>
                </button>
              </div>
            </div>            <!-- Employees List Container -->
            <div v-if="hasFetchedEmployees" class="space-y-4">
              <div class="flex items-center justify-between">
                <h4 class="text-sm font-semibold text-[#17181B] dark:text-white">
                  Eligible Employees ({{ filteredEmployees.length }})
                </h4>
              </div>

              <!-- Scrollable Employees List (Table Layout) -->
              <div class="relative border border-black/[0.07] dark:border-white/10 rounded-[16px] overflow-hidden max-h-64 overflow-y-auto bg-white dark:bg-surface-1 shadow-sm custom-scrollbar">
                <div v-if="filteredEmployees.length === 0" class="py-12 flex flex-col items-center justify-center gap-2 text-[#656A72] dark:text-white/60">
                  <span class="material-symbols-outlined text-4xl">group_off</span>
                  <p class="text-xs font-semibold">No active employees found matching the filters.</p>
                </div>
                
                <table v-else class="w-full text-left border-separate border-spacing-0 bg-white dark:bg-surface-1">
                  <thead class="sticky top-0 z-20">
                    <tr>
                      <th class="sticky top-0 z-20 px-6 py-3.5 w-12 text-center bg-[#F5F5F8] dark:bg-surface-2 border-b border-black/[0.08] dark:border-white/10">
                        <input 
                          type="checkbox" 
                          :checked="isAllSelected" 
                          @change="toggleSelectAll"
                          class="rounded text-accent dark:text-accent-light focus:ring-accent/20 border-black/[0.09]"
                        />
                      </th>
                      <th class="sticky top-0 z-20 px-6 py-3.5 text-[12px] leading-[14px] font-semibold text-[#17181B] dark:text-white text-left whitespace-nowrap bg-[#F5F5F8] dark:bg-surface-2 border-b border-black/[0.08] dark:border-white/10">
                        Employee ID and name
                      </th>
                      <th class="sticky top-0 z-20 px-6 py-3.5 text-[12px] leading-[14px] font-semibold text-[#17181B] dark:text-white text-left whitespace-nowrap bg-[#F5F5F8] dark:bg-surface-2 border-b border-black/[0.08] dark:border-white/10 hidden sm:table-cell">
                        Designation and department
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr 
                      v-for="emp in filteredEmployees" 
                      :key="emp.name" 
                      @click="toggleEmployee(emp.name)"
                      class="hover:bg-black/[0.03] dark:hover:bg-white/[0.06] transition-colors cursor-pointer"
                    >
                      <td class="px-6 py-4 text-center border-b border-black/[0.05] dark:border-white/[0.06]" @click.stop>
                        <input 
                          type="checkbox" 
                          :value="emp.name" 
                          v-model="selectedEmployeeIds"
                          class="rounded text-accent dark:text-accent-light focus:ring-accent/20 border-black/[0.09]"
                        />
                      </td>
                      <td class="px-6 py-4 border-b border-black/[0.05] dark:border-white/[0.06]">
                        <div class="flex flex-col">
                          <span class="text-sm font-semibold text-[#17181B] dark:text-white">{{ emp.employee_name || emp.name }}</span>
                          <span class="text-xs text-[#656A72] dark:text-white/60">{{ emp.name }}</span>
                        </div>
                      </td>
                      <td class="px-6 py-4 border-b border-black/[0.05] dark:border-white/[0.06] hidden sm:table-cell">
                        <div class="flex flex-col text-xs text-[#5C6169] dark:text-white/65">
                          <span>{{ emp.designation || 'No Designation' }}</span>
                          <span>{{ emp.department || 'No Department' }}</span>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              
              <p v-if="errors.employees" class="field-error text-red-500 dark:text-red-400 flex items-center gap-1 mt-0.5">
                <span class="material-symbols-outlined text-sm">error</span>
                {{ errors.employees }}
              </p>
            </div>
          </template>
        </div>

        <!-- Footer Actions -->
        <footer class="p-6 border-t border-black/[0.07] dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.05] flex justify-end gap-3 shrink-0">
          <button @click="show = false" class="btn-secondary">Cancel</button>
          <button 
            @click="submitForm" 
            :disabled="submitting || loadingOptions || !hasFetchedEmployees || selectedEmployeeIds.length === 0" 
            class="btn-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <div v-if="submitting" class="w-4 h-4 border-2 border-white/30 dark:border-white/20 border-t-white dark:border-t-white rounded-full animate-spin"></div>
            <span>{{ editId ? 'Save changes' : 'Create payroll' }}</span>
          </button>
        </footer>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { notify } from '@/utils/feedback.js'
import { ref, computed, watch } from 'vue';
import { Dialog, call } from 'frappe-ui';
import SearchableDropdown from '../../../components/SearchableDropdown.vue';
import { getErrorMessage } from '@/utils';
import DateField from '../../../components/DateField.vue'

const show = defineModel();
const emit = defineEmits(['save']);
/* Set to an entry's name to open the form on that entry instead of a blank one. */
const props = defineProps({ editId: { type: String, default: '' } });

const submitting = ref(false);
const loadingOptions = ref(false);
const submitError = ref('');

const formData = ref(getInitialFormData());
const errors = ref({});

// Dropdown Options
const rawCompanies = ref([]);
const companyOptions = ref([]);
const frequencyOptions = ref([]);
const branchOptions = ref([]);
const designationOptions = ref([]);
const departmentOptions = ref([]);
const gradeOptions = ref([]);
const salaryStructureOptions = ref([]);

// Get Employees state
const fetchingEmployees = ref(false);
const hasFetchedEmployees = ref(false);
const filteredEmployees = ref([]);
const selectedEmployeeIds = ref([]);

const employeeFilters = ref({
  branch: '',
  designation: '',
  department: '',
  grade: '',
  salary_structure: '',
  salary_slip_based_on_timesheet: false
});

const isAllSelected = computed(() => {
  if (filteredEmployees.value.length === 0) return false;
  return selectedEmployeeIds.value.length === filteredEmployees.value.length;
});

function toggleSelectAll() {
  if (isAllSelected.value) {
    selectedEmployeeIds.value = [];
  } else {
    selectedEmployeeIds.value = filteredEmployees.value.map(emp => emp.name);
  }
}

function getInitialFormData() {
  const todayStr = new Date().toISOString().substring(0, 10);
  
  // Start/End of current month
  const now = new Date();
  const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
  const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  
  const formatDate = (date) => {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  };

  return {
    posting_date: todayStr,
    company: '',
    currency: '',
    payroll_frequency: 'Monthly',
    start_date: formatDate(firstDay),
    end_date: formatDate(lastDay),
    payroll_payable_account: ''
  };
}

let editEmployees = [];
async function loadEntry(name) {
  try {
    const d = await call('arijentek_core.api.payroll.get_payroll_details', { payroll_name: name });
    if (!d) return;
    formData.value = {
      posting_date: d.posting_date || formData.value.posting_date,
      company: d.company || formData.value.company,
      currency: d.currency || formData.value.currency,
      payroll_frequency: d.payroll_frequency || 'Monthly',
      start_date: d.start_date || formData.value.start_date,
      end_date: d.end_date || formData.value.end_date,
      payroll_payable_account: d.payroll_payable_account || formData.value.payroll_payable_account,
    };
    employeeFilters.value.salary_slip_based_on_timesheet = !!d.salary_slip_based_on_timesheet;
    editEmployees = (d.employees || []).map(e => e.employee);
  } catch (e) {
    console.error('Failed to load payroll entry:', e);
  }
}

async function loadOptions() {
  loadingOptions.value = true;
  try {
    const res = await call('arijentek_core.api.payroll.get_payroll_entry_options');
    if (res) {
      rawCompanies.value = res.companies || [];
      companyOptions.value = rawCompanies.value.map(c => ({
        label: c.company_name || c.name,
        value: c.name
      }));
      frequencyOptions.value = (res.payroll_frequencies || []).map(f => ({ label: f, value: f }));
      branchOptions.value = (res.branches || []).map(b => ({ label: b, value: b }));
      designationOptions.value = (res.designations || []).map(d => ({ label: d, value: d }));
      departmentOptions.value = (res.departments || []).map(d => ({ label: d, value: d }));
      gradeOptions.value = (res.grades || []).map(g => ({ label: g, value: g }));
      salaryStructureOptions.value = (res.salary_structures || []).map(s => ({ label: s, value: s }));
      
      // Default company
      if (companyOptions.value.length > 0) {
        // Try getting user default
        const defaultCompany = await call('frappe.client.get_value', {
          doctype: 'Global Defaults',
          fieldname: 'default_company'
        });
        const matched = companyOptions.value.find(o => o.value === defaultCompany?.message?.default_company) 
          || companyOptions.value[0];
        if (matched) {
          formData.value.company = matched.value;
        }
      }
    }
  } catch (e) {
    console.error('Failed to load payroll options:', e);
  } finally {
    loadingOptions.value = false;
  }
}

watch(show, async (newVal) => {
  if (newVal) {
    formData.value = getInitialFormData();
    errors.value = {};
    submitError.value = '';
    hasFetchedEmployees.value = false;
    filteredEmployees.value = [];
    employeeFilters.value = {
      branch: '',
      designation: '',
      department: '',
      grade: '',
      salary_structure: '',
      salary_slip_based_on_timesheet: false
    };

    await loadOptions();
    if (props.editId) await loadEntry(props.editId);
    if (formData.value.company) {
      await fetchEmployees();
    }
    if (props.editId && editEmployees.length) {
      selectedEmployeeIds.value = filteredEmployees.value.map(e => e.name).filter(n => editEmployees.includes(n));
    }
  }
});

watch(() => formData.value.company, (newCompany) => {
  if (newCompany) {
    const matched = rawCompanies.value.find(c => c.name === newCompany);
    if (matched) {
      formData.value.currency = matched.default_currency || 'USD';
      formData.value.payroll_payable_account = matched.default_payroll_payable_account || '';
    }
  } else {
    formData.value.currency = '';
    formData.value.payroll_payable_account = '';
  }
});

watch(
  [() => formData.value.start_date, () => formData.value.payroll_frequency],
  ([newStartDate, newFreq]) => {
    if (!newStartDate) return;
    
    const start = new Date(newStartDate);
    if (isNaN(start.getTime())) return;
    
    let end = new Date(start);
    
    if (newFreq === 'Monthly') {
      if (start.getDate() === 1) {
        end = new Date(start.getFullYear(), start.getMonth() + 1, 0);
      } else {
        end = new Date(start.getFullYear(), start.getMonth() + 1, start.getDate() - 1);
      }
    } else if (newFreq === 'Fortnightly') {
      end.setDate(start.getDate() + 13);
    } else if (newFreq === 'Weekly') {
      end.setDate(start.getDate() + 6);
    } else if (newFreq === 'Daily') {
      // same day, no offset
    }
    
    const y = end.getFullYear();
    const m = String(end.getMonth() + 1).padStart(2, '0');
    const d = String(end.getDate()).padStart(2, '0');
    formData.value.end_date = `${y}-${m}-${d}`;
  }
);

let fetchDebounceTimer;
watch(
  [
    () => formData.value.company,
    () => formData.value.payroll_frequency,
    () => formData.value.start_date,
    () => formData.value.end_date,
    () => employeeFilters.value.branch,
    () => employeeFilters.value.designation,
    () => employeeFilters.value.department,
    () => employeeFilters.value.grade,
    () => employeeFilters.value.salary_structure,
    () => employeeFilters.value.salary_slip_based_on_timesheet
  ],
  () => {
    clearTimeout(fetchDebounceTimer);
    fetchDebounceTimer = setTimeout(() => {
      if (formData.value.company) {
        fetchEmployees();
      } else {
        filteredEmployees.value = [];
        selectedEmployeeIds.value = [];
        hasFetchedEmployees.value = false;
      }
    }, 300);
  }
);

async function fetchEmployees() {
  if (!formData.value.company) {
    errors.value.company = 'Company is required to fetch employees';
    return;
  }
  
  fetchingEmployees.value = true;
  hasFetchedEmployees.value = false;
  errors.value = {};
  
  try {
    const params = {
      company: formData.value.company,
      payroll_frequency: formData.value.payroll_frequency,
      salary_slip_based_on_timesheet: employeeFilters.value.salary_slip_based_on_timesheet ? 1 : 0,
      branch: employeeFilters.value.branch || null,
      designation: employeeFilters.value.designation || null,
      department: employeeFilters.value.department || null,
      grade: employeeFilters.value.grade || null,
      salary_structure: employeeFilters.value.salary_structure || null,
      start_date: formData.value.start_date || null,
      end_date: formData.value.end_date || null
    };
    
    const res = await call('arijentek_core.api.payroll.get_payroll_eligible_employees', params);
    filteredEmployees.value = res || [];
    selectedEmployeeIds.value = []; // Default unchecked initially
    hasFetchedEmployees.value = true;
  } catch (err) {
    console.error(err);
    notify(getErrorMessage(err, 'Failed to fetch eligible employees'));
  } finally {
    fetchingEmployees.value = false;
  }
}

function toggleEmployee(empId) {
  const index = selectedEmployeeIds.value.indexOf(empId);
  if (index > -1) {
    selectedEmployeeIds.value.splice(index, 1);
  } else {
    selectedEmployeeIds.value.push(empId);
  }
}

watch(
  () => formData.value.start_date,
  (newStart) => {
    if (!newStart) return;
    if (!formData.value.end_date || formData.value.end_date < newStart) {
      formData.value.end_date = newStart;
    }
  }
);

function validate() {
  errors.value = {};
  let isValid = true;

  if (!formData.value.company) {
    errors.value.company = 'Company is required';
    isValid = false;
  }
  if (!formData.value.posting_date) {
    errors.value.posting_date = 'Posting Date is required';
    isValid = false;
  }
  if (!formData.value.payroll_frequency) {
    errors.value.payroll_frequency = 'Payroll Frequency is required';
    isValid = false;
  }
  if (!formData.value.start_date) {
    errors.value.start_date = 'Start Date is required';
    isValid = false;
  }
  if (!formData.value.end_date) {
    errors.value.end_date = 'End Date is required';
    isValid = false;
  } else if (formData.value.start_date && formData.value.end_date < formData.value.start_date) {
    errors.value.end_date = 'End Date cannot be earlier than Start Date';
    isValid = false;
  }
  if (selectedEmployeeIds.value.length === 0) {
    errors.value.employees = 'At least one employee must be selected';
    isValid = false;
  }

  return isValid;
}

async function submitForm() {
  submitError.value = '';
  if (!validate()) return;

  submitting.value = true;
  try {
    const payload = {
      ...formData.value,
      salary_slip_based_on_timesheet: employeeFilters.value.salary_slip_based_on_timesheet ? 1 : 0,
      employees: selectedEmployeeIds.value,
      ...(props.editId ? { name: props.editId } : {}),
      submit: true
    };
    
    await call('arijentek_core.api.payroll.save_payroll_entry', {
      doc: payload
    });
    emit('save');
    show.value = false;
  } catch (err) {
    console.error(err);
    submitError.value = getErrorMessage(err, 'Failed to save payroll entry');
  } finally {
    submitting.value = false;
  }
}
</script>
