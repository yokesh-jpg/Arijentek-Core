<template>
  <Teleport to="body">
    <Dialog :options="{ size: '5xl' }" v-model="show">
      <template #body>
        <div class="modal-panel flex flex-col overflow-hidden max-h-[90vh]">
          <!-- Custom Header -->
          <header class="bg-white dark:bg-white/[0.06] border-b border-black/[0.07] dark:border-white/10 shrink-0 sticky top-0 z-20 px-6 py-5 flex justify-between items-center">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-[12px] bg-accent/[0.10] dark:bg-accent/20 border border-accent/30 dark:border-accent/30 flex items-center justify-center text-accent dark:text-accent-light shrink-0 shadow-sm">
                <span class="material-symbols-outlined text-xl">account_tree</span>
              </div>
              <div>
                <h1 class="modal-title">
                  {{ isEdit ? 'Edit salary structure' : 'New salary structure' }}
                </h1>
                <p class="text-xs font-medium text-[#5C6169] dark:text-white/65">
                  {{ isEdit ? 'Update salary structure details and components' : 'Configure primary structure details, earnings, and deductions' }}
                </p>
              </div>
            </div>
            <button 
              @click="show = false" 
              class="p-2 -mr-2 rounded-[12px] text-[#656A72] dark:text-white/60 hover:text-[#17181B] dark:hover:text-white hover:bg-black/[0.04] dark:hover:bg-white/[0.08] transition-colors"
            >
              <span class="material-symbols-outlined text-xl">close</span>
            </button>
          </header>

          <!-- Main Content Area -->
          <div class="p-6 overflow-y-auto flex flex-col gap-6">
            <!-- Loading Indicator -->
            <div v-if="loadingOptions" class="py-12 flex flex-col items-center justify-center gap-3">
              <div class="w-8 h-8 border-2 border-accent/30 border-t-transparent rounded-full animate-spin"></div>
              <p class="text-xs font-medium text-[#5C6169] dark:text-white/65">Loading default settings and components...</p>
            </div>

            <template v-else>
              <!-- SECTION 1: Primary Information Card -->
              <div class="bg-white dark:bg-white/[0.06] border border-black/[0.07] dark:border-white/10 rounded-[16px] p-6 shadow-sm space-y-6">
                <h3 class="field-label">
                  1. General Details
                </h3>

                <!-- Salary Structure Name -->
                <div class="flex flex-col gap-2">
                  <label class="field-label flex items-center justify-between">
                    <span class="flex items-center gap-2">
                      Salary Structure Name <span class="text-red-500 dark:text-red-400">*</span>
                      <span v-if="isEdit" class="text-xs font-semibold text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40 px-2 py-0.5 rounded border border-amber-200/60 dark:border-amber-900/50">
                        (Read-Only on Edit)
                      </span>
                    </span>
                    <span class="text-xs font-normal text-[#656A72] dark:text-white/55">Unique name for this structure</span>
                  </label>
                  <input 
                    v-model="formData.name" 
                    type="text" 
                    :disabled="isEdit"
                    placeholder="e.g. Executive Salary Structure 2026" 
                    class="field-input w-full disabled:opacity-75 disabled:bg-black/[0.04] dark:disabled:bg-white/[0.06] disabled:cursor-not-allowed"
                    :class="{ 'border-red-400 focus:border-red-500 focus:ring-red-500/20': errors.name }"
                  />
                  <p v-if="errors.name" class="field-error text-red-500 dark:text-red-400 flex items-center gap-1 mt-0.5">
                    <span class="material-symbols-outlined text-sm">error</span>
                    {{ errors.name }}
                  </p>
                </div>

                <!-- Company & Currency Information Labels -->
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
                  <!-- Company Name Label -->
                  <div class="inset-panel flex flex-col gap-1.5">
                    <div class="flex items-center gap-2 text-[#5C6169] dark:text-white/65">
                      <span class="material-symbols-outlined text-base text-accent dark:text-accent-light">domain</span>
                      <span class="text-xs font-semibold ">Company</span>
                    </div>
                    <div class="flex items-center justify-between">
                      <span class="text-sm font-semibold text-[#17181B] dark:text-white truncate">
                        {{ companyName || formData.company || 'Default Company' }}
                      </span>
                      <span class="premium-tag tag-accent">
                        Default
                      </span>
                    </div>
                  </div>

                  <!-- Currency Label -->
                  <div class="inset-panel flex flex-col gap-1.5">
                    <div class="flex items-center gap-2 text-[#5C6169] dark:text-white/65">
                      <span class="material-symbols-outlined text-base text-accent dark:text-accent-light">payments</span>
                      <span class="text-xs font-semibold ">Currency</span>
                    </div>
                    <div class="flex items-center justify-between">
                      <span class="text-sm font-semibold text-[#17181B] dark:text-white truncate">
                        {{ companyCurrency || formData.currency || 'USD' }}
                      </span>
                      <span class="premium-tag tag-accent">
                        Base
                      </span>
                    </div>
                  </div>
                </div>

                <!-- Payroll Frequency & Active Status Row -->
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-1">
                  <!-- Payroll Frequency Dropdown -->
                  <div class="flex flex-col gap-2">
                    <label class="field-label flex items-center justify-between">
                      <span>Payroll Frequency <span class="text-red-500 dark:text-red-400">*</span></span>
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

                  <!-- Active Status Toggle -->
                  <div class="flex flex-col gap-2">
                    <label class="field-label">
                      Status
                    </label>
                    <div class="field-static !py-0 flex items-center justify-between h-11">
                      <div class="flex items-center gap-2">
                        <span 
                          class="w-2.5 h-2.5 rounded-full" 
                          :class="formData.is_active === 'Yes' ? 'bg-accent shadow-sm shadow-accent/50' : 'bg-black/[0.12]'"
                        ></span>
                        <span class="text-sm font-semibold text-[#17181B] dark:text-white/80">
                          {{ formData.is_active === 'Yes' ? 'Active' : 'Inactive' }}
                        </span>
                      </div>

                      <button 
                        type="button"
                        @click="toggleStatus"
                        class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none"
                        :class="formData.is_active === 'Yes' ? 'bg-accent' : 'bg-black/[0.12] dark:bg-white/[0.08]'"
                      >
                        <span 
                          class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
                          :class="formData.is_active === 'Yes' ? 'translate-x-5' : 'translate-x-0'"
                        />
                      </button>
                    </div>
                  </div>
                </div>

                <!-- Salary based on Hours (Timesheet-based) Row -->
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-1">
                  <!-- Toggle Switch for Salary based on Hours -->
                  <div class="flex flex-col gap-2">
                    <label class="field-label flex items-center justify-between">
                      <span>Salary based on Hours</span>
                      <span class="text-xs font-normal text-[#656A72] dark:text-white/55">Based on Timesheet</span>
                    </label>
                    <div class="field-static !py-0 flex items-center justify-between h-11">
                      <div class="flex items-center gap-2">
                        <span 
                          class="w-2.5 h-2.5 rounded-full" 
                          :class="formData.salary_slip_based_on_timesheet ? 'bg-accent shadow-sm shadow-accent/50' : 'bg-black/[0.12]'"
                        ></span>
                        <span class="text-sm font-semibold text-[#17181B] dark:text-white/80">
                          {{ formData.salary_slip_based_on_timesheet ? 'Yes' : 'No' }}
                        </span>
                      </div>
                      <button 
                        type="button"
                        @click="formData.salary_slip_based_on_timesheet = formData.salary_slip_based_on_timesheet ? 0 : 1"
                        class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none"
                        :class="formData.salary_slip_based_on_timesheet ? 'bg-accent' : 'bg-black/[0.12] dark:bg-white/[0.08]'"
                      >
                        <span 
                          class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
                          :class="formData.salary_slip_based_on_timesheet ? 'translate-x-5' : 'translate-x-0'"
                        />
                      </button>
                    </div>
                  </div>
                </div>

                <!-- Conditional Hourly Configuration Fields -->
                <div v-if="formData.salary_slip_based_on_timesheet" class="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-1 border-t border-dashed border-black/[0.07] dark:border-white/10 pt-4">
                  <!-- Salary Component Selection (Earnings List) -->
                  <div class="flex flex-col gap-2">
                    <label class="field-label">
                      Salary Component <span class="text-red-500 dark:text-red-400">*</span>
                    </label>
                    <SearchableDropdown
                      v-model="formData.salary_component"
                      :options="earningComponentOptions"
                      placeholder="Select earning component"
                    />
                    <p v-if="errors.salary_component" class="field-error text-red-500 dark:text-red-400 flex items-center gap-1 mt-0.5">
                      <span class="material-symbols-outlined text-sm">error</span>
                      {{ errors.salary_component }}
                    </p>
                  </div>

                  <!-- Hour Rate Field with Currency Label -->
                  <div class="flex flex-col gap-2">
                    <label class="field-label">
                      Hour Rate <span class="text-red-500 dark:text-red-400">*</span>
                    </label>
                    <div class="relative">
                      <span class="absolute left-4 top-1/2 -translate-y-1/2 text-sm font-semibold text-[#656A72] dark:text-white/55 select-none">
                        {{ companyCurrency || 'USD' }}
                      </span>
                      <input 
                        v-model.number="formData.hour_rate" 
                        type="number" 
                        placeholder="0.00" 
                        step="0.01"
                        min="0"
                        class="w-full pl-16 pr-4 py-2.5 bg-white dark:bg-surface-1/60 border border-black/[0.07] dark:border-white/10 rounded-[12px] text-sm font-semibold text-[#17181B] dark:text-white placeholder-[#656A72] focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent/30 transition-all font-mono"
                        :class="{ 'border-red-400 focus:border-red-500 focus:ring-red-500/20': errors.hour_rate }"
                      />
                    </div>
                    <p v-if="errors.hour_rate" class="field-error text-red-500 dark:text-red-400 flex items-center gap-1 mt-0.5">
                      <span class="material-symbols-outlined text-sm">error</span>
                      {{ errors.hour_rate }}
                    </p>
                  </div>
                </div>
              </div>

              <!-- SECTION 2: Salary Line Items (Earnings & Deductions) -->
              <div class="bg-white dark:bg-white/[0.06] border border-black/[0.07] dark:border-white/10 rounded-[16px] p-6 shadow-sm space-y-6">
                <div class="flex items-center justify-between">
                  <h3 class="field-label">
                    2. Earnings & Deductions Components
                  </h3>
                  <div class="flex items-center gap-4 text-xs font-semibold">
                    <span class="text-accent dark:text-accent-light flex items-center gap-1">
                      <span class="material-symbols-outlined text-sm">add_circle</span>
                      Earnings: {{ formData.earnings.length }}
                    </span>
                    <span class="text-rose-600 dark:text-rose-400 flex items-center gap-1">
                      <span class="material-symbols-outlined text-sm">remove_circle</span>
                      Deductions: {{ formData.deductions.length }}
                    </span>
                  </div>
                </div>

                <!-- EARNINGS TABLE -->
                <div class="space-y-3">
                  <div class="flex items-center justify-between">
                    <h4 class="text-sm font-semibold text-[#17181B] dark:text-white flex items-center gap-2">
                      <span class="w-2 h-2 rounded-full bg-accent"></span>
                      Earnings
                    </h4>
                  </div>

                  <!-- Table Header -->
                  <div class="px-1 pb-2 mb-1 border-b border-black/[0.07] dark:border-white/10 hidden md:grid grid-cols-12 gap-3">
                    <span class="field-label col-span-6">Salary Component</span>
                    <span class="field-label col-span-5">Amount / Formula</span>
                    <span class="field-label col-span-1 text-center">Action</span>
                  </div>

                  <!-- Rows -->
                  <div v-if="formData.earnings.length > 0" class="space-y-2.5">
                    <div 
                      v-for="(line, index) in formData.earnings" 
                      :key="'earning-' + index"
                      class="grid grid-cols-12 gap-3 items-center p-2.5 sm:p-2 bg-white dark:bg-surface-1/40 border border-black/[0.07] dark:border-white/10 rounded-[12px]"
                    >
                      <!-- Component Select -->
                      <div class="col-span-12 md:col-span-6 flex gap-2">
                        <div class="flex-1 min-w-0">
                          <SearchableDropdown
                            v-model="line.salary_component"
                            :options="earningComponentOptions"
                            placeholder="Select earning component"
                            @change="(val) => onEarningComponentChange(index, val)"
                          />
                        </div>
                        <button 
                          type="button" 
                          @click="openCreateSalaryComponent('earning', index)" 
                          class="w-[38px] h-[38px] shrink-0 rounded-[12px] bg-black/[0.02] hover:bg-accent/[0.10] dark:bg-surface-1/80 dark:hover:bg-accent-hover/40 border border-black/[0.07] hover:border-accent/30 dark:border-white/10 dark:hover:border-accent/30 text-[#5C6169] dark:text-white/65 hover:text-accent dark:hover:text-accent flex items-center justify-center transition-all shadow-sm self-center"
                          title="Create Earning Component"
                        >
                          <span class="material-symbols-outlined text-lg">add</span>
                        </button>
                      </div>

                      <!-- Value / Formula / Input -->
                      <div class="col-span-12 md:col-span-5">
                        <!-- Case 1: Formula Enabled (Read-only Formula Badge) -->
                        <div 
                          v-if="line.amount_based_on_formula || line.formula" 
                          class="px-3 py-2 bg-black/[0.04] dark:bg-white/[0.06] text-[#17181B] dark:text-white font-mono text-xs rounded-[12px] flex items-center justify-between"
                          title="Formula configured on component (read-only)"
                        >
                          <div class="flex items-center gap-1.5 truncate">
                            <span class="material-symbols-outlined text-sm shrink-0">functions</span>
                            <span class="truncate font-semibold">{{ line.formula || 'Formula Based' }}</span>
                          </div>
                          <span class="text-[13px] font-semibold bg-blue-200/60 dark:bg-blue-900/60 px-1.5 py-0.5 rounded text-blue-800 dark:text-blue-200 shrink-0">
                            Formula
                          </span>
                        </div>

                        <!-- Case 2: Amount-Based -> Editable Amount Input (Fetches default amount, editable if needed) -->
                        <div v-else class="relative">
                          <input 
                            type="number" 
                            v-model.number="line.amount" 
                            placeholder="0.00" 
                            step="any"
                            class="field-input w-full font-mono"
                          />
                        </div>
                      </div>

                      <!-- Action (Delete) -->
                      <div class="col-span-12 md:col-span-1 flex justify-center">
                        <button 
                          type="button" 
                          @click="removeEarningLine(index)" 
                          class="w-8 h-8 rounded-[12px] hover:bg-rose-50 dark:hover:bg-rose-950/40 text-rose-500 dark:text-rose-400 transition-all flex items-center justify-center"
                          title="Remove Line"
                        >
                          <span class="material-symbols-outlined text-base">delete</span>
                        </button>
                      </div>
                    </div>
                  </div>

                  <div v-else class="p-4 text-center border border-dashed border-black/[0.07] dark:border-white/10 rounded-[12px] text-xs text-[#656A72] dark:text-white/60">
                    No earning components added yet.
                  </div>

                  <!-- Add Earnings Line Button under Earnings Table -->
                  <div class="flex justify-start pt-1">
                    <button 
                      type="button" 
                      @click="addEarningLine" 
                      class="btn-secondary"
                    >
                      <span class="material-symbols-outlined text-base">add</span>
                      Add Earnings Line
                    </button>
                  </div>
                </div>

                <!-- DEDUCTIONS TABLE -->
                <div class="space-y-3 pt-4 border-t border-black/[0.07] dark:border-white/10">
                  <div class="flex items-center justify-between">
                    <h4 class="text-sm font-semibold text-[#17181B] dark:text-white flex items-center gap-2">
                      <span class="w-2 h-2 rounded-full bg-rose-500"></span>
                      Deductions
                    </h4>
                  </div>

                  <!-- Table Header -->
                  <div class="px-1 pb-2 mb-1 border-b border-black/[0.07] dark:border-white/10 hidden md:grid grid-cols-12 gap-3">
                    <span class="field-label col-span-6">Salary Component</span>
                    <span class="field-label col-span-5">Amount / Formula</span>
                    <span class="field-label col-span-1 text-center">Action</span>
                  </div>

                  <!-- Rows -->
                  <div v-if="formData.deductions.length > 0" class="space-y-2.5">
                    <div 
                      v-for="(line, index) in formData.deductions" 
                      :key="'deduction-' + index"
                      class="grid grid-cols-12 gap-3 items-center p-2.5 sm:p-2 bg-white dark:bg-surface-1/40 border border-black/[0.07] dark:border-white/10 rounded-[12px]"
                    >
                      <!-- Component Select -->
                      <div class="col-span-12 md:col-span-6 flex gap-2">
                        <div class="flex-1 min-w-0">
                          <SearchableDropdown
                            v-model="line.salary_component"
                            :options="deductionComponentOptions"
                            placeholder="Select deduction component"
                            @change="(val) => onDeductionComponentChange(index, val)"
                          />
                        </div>
                        <button 
                          type="button" 
                          @click="openCreateSalaryComponent('deduction', index)" 
                          class="w-[38px] h-[38px] shrink-0 rounded-[12px] bg-black/[0.02] hover:bg-rose-50 dark:bg-surface-1/80 dark:hover:bg-rose-900/40 border border-black/[0.07] hover:border-rose-200 dark:border-white/10 dark:hover:border-rose-800/50 text-[#5C6169] dark:text-white/65 hover:text-rose-600 dark:hover:text-rose-400 flex items-center justify-center transition-all shadow-sm self-center"
                          title="Create Deduction Component"
                        >
                          <span class="material-symbols-outlined text-lg">add</span>
                        </button>
                      </div>

                      <!-- Value / Formula / Input -->
                      <div class="col-span-12 md:col-span-5">
                        <!-- Case 1: Formula Enabled (Read-only Formula Badge) -->
                        <div 
                          v-if="line.amount_based_on_formula || line.formula" 
                          class="px-3 py-2 bg-black/[0.04] dark:bg-white/[0.06] text-[#17181B] dark:text-white font-mono text-xs rounded-[12px] flex items-center justify-between"
                          title="Formula configured on component (read-only)"
                        >
                          <div class="flex items-center gap-1.5 truncate">
                            <span class="material-symbols-outlined text-sm shrink-0">functions</span>
                            <span class="truncate font-semibold">{{ line.formula || 'Formula Based' }}</span>
                          </div>
                          <span class="text-[13px] font-semibold bg-blue-200/60 dark:bg-blue-900/60 px-1.5 py-0.5 rounded text-blue-800 dark:text-blue-200 shrink-0">
                            Formula
                          </span>
                        </div>

                        <!-- Case 2: Amount-Based -> Editable Amount Input (Fetches default amount, editable if needed) -->
                        <div v-else class="relative">
                          <input 
                            type="number" 
                            v-model.number="line.amount" 
                            placeholder="0.00" 
                            step="any"
                            class="field-input w-full font-mono"
                          />
                        </div>
                      </div>

                      <!-- Action (Delete) -->
                      <div class="col-span-12 md:col-span-1 flex justify-center">
                        <button 
                          type="button" 
                          @click="removeDeductionLine(index)" 
                          class="w-8 h-8 rounded-[12px] hover:bg-rose-50 dark:hover:bg-rose-950/40 text-rose-500 dark:text-rose-400 transition-all flex items-center justify-center"
                          title="Remove Line"
                        >
                          <span class="material-symbols-outlined text-base">delete</span>
                        </button>
                      </div>
                    </div>
                  </div>

                  <div v-else class="p-4 text-center border border-dashed border-black/[0.07] dark:border-white/10 rounded-[12px] text-xs text-[#656A72] dark:text-white/60">
                    No deduction components added yet.
                  </div>

                  <!-- Add Deduction Line Button under Deductions Table -->
                  <div class="flex justify-start pt-1">
                    <button 
                      type="button" 
                      @click="addDeductionLine" 
                      class="btn-secondary"
                    >
                      <span class="material-symbols-outlined text-base">add</span>
                      Add Deduction Line
                    </button>
                  </div>
                </div>
              </div>
            </template>
          </div>

          <!-- Actions Footer -->
          <footer class="modal-footer flex flex-col mt-auto shrink-0">
            <p v-if="submitError" class="field-error text-red-500 dark:text-red-400 text-center mb-3 flex items-center justify-center gap-1">
              <span class="material-symbols-outlined text-sm">warning</span>
              {{ submitError }}
            </p>
            <div class="flex justify-end items-center gap-3">
              <button 
                type="button"
                class="btn-secondary" 
                @click="show = false"
                :disabled="submitting"
              >
                Cancel
              </button>
              <button 
                type="button"
                class="btn-primary active:bg-accent flex items-center gap-2 disabled:opacity-70" 
                @click="handleSave"
                :disabled="submitting || loadingOptions"
              >
                <span v-if="submitting" class="material-symbols-outlined text-base animate-spin">progress_activity</span>
                <span v-else class="material-symbols-outlined text-base">check_circle</span>
                {{ submitting ? 'Saving…' : (isEdit ? 'Update structure' : 'Save structure') }}
              </button>
            </div>
          </footer>
        </div>
      </template>
    </Dialog>
    <CreateSalaryComponent 
      v-model="showCreateComponent" 
      @save="handleComponentSaved" 
    />
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { Dialog, call } from 'frappe-ui';
import SearchableDropdown from '../../../components/SearchableDropdown.vue';
import { getErrorMessage } from '@/utils';
import CreateSalaryComponent from './create_salary_component.vue';

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  editData: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['update:modelValue', 'save']);

const show = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
});

const isEdit = computed(() => !!props.editData && !!props.editData.name);

const frequencyOptions = [
  'Monthly',
  'Fortnightly',
  'Bimonthly',
  'Weekly',
  'Daily'
];

const companyName = ref('');
const companyCurrency = ref('');
const loadingOptions = ref(false);
const submitting = ref(false);
const submitError = ref('');
const errors = ref({});

const earningComponents = ref([]);
const deductionComponents = ref([]);

const showCreateComponent = ref(false);
const currentComponentType = ref('');
const currentComponentIndex = ref(-1);

const openCreateSalaryComponent = (type, index) => {
  currentComponentType.value = type;
  currentComponentIndex.value = index;
  showCreateComponent.value = true;
};

const handleComponentSaved = (newComponent) => {
  if (newComponent.type === 'Earning') {
    const exists = earningComponents.value.find(c => c.name === newComponent.name);
    if (!exists) earningComponents.value.push(newComponent);
    
    if (currentComponentType.value === 'earning' && currentComponentIndex.value > -1) {
      const line = formData.value.earnings[currentComponentIndex.value];
      if (line) {
        line.salary_component = newComponent.name;
        onEarningComponentChange(currentComponentIndex.value, newComponent.name);
      }
    }
  } else if (newComponent.type === 'Deduction') {
    const exists = deductionComponents.value.find(c => c.name === newComponent.name);
    if (!exists) deductionComponents.value.push(newComponent);
    
    if (currentComponentType.value === 'deduction' && currentComponentIndex.value > -1) {
      const line = formData.value.deductions[currentComponentIndex.value];
      if (line) {
        line.salary_component = newComponent.name;
        onDeductionComponentChange(currentComponentIndex.value, newComponent.name);
      }
    }
  }
  
  currentComponentType.value = '';
  currentComponentIndex.value = -1;
};

const getInitialFormData = () => ({
  name: '',
  company: '',
  currency: '',
  payroll_frequency: 'Monthly',
  is_active: 'Yes',
  salary_slip_based_on_timesheet: 0,
  hour_rate: 0,
  salary_component: '',
  earnings: [],
  deductions: []
});

const formData = ref(getInitialFormData());

const toggleStatus = () => {
  formData.value.is_active = formData.value.is_active === 'Yes' ? 'No' : 'Yes';
};

// Computed dropdown options for SearchableDropdown
const earningComponentOptions = computed(() => {
  return earningComponents.value.map(c => ({
    label: `${c.salary_component || c.name}${c.salary_component_abbr ? ' (' + c.salary_component_abbr + ')' : ''}`,
    value: c.name,
    raw: c
  }));
});

const deductionComponentOptions = computed(() => {
  return deductionComponents.value.map(c => ({
    label: `${c.salary_component || c.name}${c.salary_component_abbr ? ' (' + c.salary_component_abbr + ')' : ''}`,
    value: c.name,
    raw: c
  }));
});

const formatCurrency = (val) => {
  const num = parseFloat(val || 0);
  const curr = companyCurrency.value || 'USD';
  try {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: curr }).format(num);
  } catch (e) {
    return `${curr} ${num.toFixed(2)}`;
  }
};

// Line Item Actions for Earnings
const addEarningLine = () => {
  formData.value.earnings.push({
    salary_component: '',
    salary_component_abbr: '',
    amount_based_on_formula: false,
    amount: 0,
    formula: '',
    condition: ''
  });
};

const removeEarningLine = (idx) => {
  formData.value.earnings.splice(idx, 1);
};

const onEarningComponentChange = (index, componentName) => {
  const line = formData.value.earnings[index];
  if (!line) return;

  const comp = earningComponents.value.find(c => c.name === componentName);
  if (comp) {
    line.salary_component = comp.name;
    line.salary_component_abbr = comp.salary_component_abbr || '';
    line.amount_based_on_formula = !!comp.amount_based_on_formula;
    line.formula = comp.formula || '';
    line.condition = comp.condition || '';

    if (comp.amount_based_on_formula) {
      line.amount = 0;
    } else {
      // Fetch default component amount into input box (can be changed if needed)
      line.amount = comp.amount != null ? parseFloat(comp.amount) : 0;
    }
  }
};

// Line Item Actions for Deductions
const addDeductionLine = () => {
  formData.value.deductions.push({
    salary_component: '',
    salary_component_abbr: '',
    amount_based_on_formula: false,
    amount: 0,
    formula: '',
    condition: ''
  });
};

const removeDeductionLine = (idx) => {
  formData.value.deductions.splice(idx, 1);
};

const onDeductionComponentChange = (index, componentName) => {
  const line = formData.value.deductions[index];
  if (!line) return;

  const comp = deductionComponents.value.find(c => c.name === componentName);
  if (comp) {
    line.salary_component = comp.name;
    line.salary_component_abbr = comp.salary_component_abbr || '';
    line.amount_based_on_formula = !!comp.amount_based_on_formula;
    line.formula = comp.formula || '';
    line.condition = comp.condition || '';

    if (comp.amount_based_on_formula) {
      line.amount = 0;
    } else {
      // Fetch default component amount into input box (can be changed if needed)
      line.amount = comp.amount != null ? parseFloat(comp.amount) : 0;
    }
  }
};

// Load defaults and components
const loadOptionsAndDefaults = async () => {
  loadingOptions.value = true;
  try {
    const res = await call('arijentek_core.api.payroll.get_salary_structure_options');
    if (res) {
      if (res.default_company) {
        formData.value.company = res.default_company;
      }
      if (res.default_company_name) {
        companyName.value = res.default_company_name;
      } else if (res.default_company) {
        companyName.value = res.default_company;
      }
      if (res.default_currency) {
        formData.value.currency = res.default_currency;
        companyCurrency.value = res.default_currency;
      }
      if (res.earning_components) {
        earningComponents.value = res.earning_components;
      }
      if (res.deduction_components) {
        deductionComponents.value = res.deduction_components;
      }
    }
  } catch (err) {
    console.error('Failed to load salary structure options:', err);
  } finally {
    loadingOptions.value = false;
  }
};

watch(show, async (newVal) => {
  if (newVal) {
    formData.value = getInitialFormData();
    errors.value = {};
    submitError.value = '';
    
    await loadOptionsAndDefaults();

    if (props.editData && props.editData.name) {
      try {
        const fullDoc = await call('arijentek_core.api.payroll.get_salary_structure_details', {
          name: props.editData.name
        });

        if (fullDoc) {
          formData.value.name = fullDoc.name || props.editData.name;
          formData.value.company = fullDoc.company || formData.value.company;
          formData.value.currency = fullDoc.currency || formData.value.currency;
          formData.value.payroll_frequency = fullDoc.payroll_frequency || 'Monthly';
          formData.value.is_active = fullDoc.is_active || 'Yes';
          formData.value.salary_slip_based_on_timesheet = 
            fullDoc.salary_slip_based_on_timesheet === 1 || 
            fullDoc.salary_slip_based_on_timesheet === true || 
            fullDoc.salary_slip_based_on_timesheet === '1' ||
            fullDoc.salary_slip_based_on_timesheet === 'Yes' 
              ? 1 : 0;
          formData.value.hour_rate = fullDoc.hour_rate ? parseFloat(fullDoc.hour_rate) : 0;
          formData.value.salary_component = fullDoc.salary_component || '';

          if (fullDoc.company) companyName.value = fullDoc.company;
          if (fullDoc.currency) companyCurrency.value = fullDoc.currency;

          // Map earnings
          if (fullDoc.earnings && fullDoc.earnings.length > 0) {
            formData.value.earnings = fullDoc.earnings.map(row => {
              const comp = earningComponents.value.find(c => c.name === row.salary_component);
              const isFormula = !!row.amount_based_on_formula || !!row.formula || (comp && !!comp.amount_based_on_formula);
              return {
                salary_component: row.salary_component,
                salary_component_abbr: row.abbr || row.salary_component_abbr || (comp ? comp.salary_component_abbr : ''),
                amount_based_on_formula: isFormula,
                amount: row.amount != null ? parseFloat(row.amount) : (comp && comp.amount != null ? parseFloat(comp.amount) : 0),
                formula: row.formula || (comp ? comp.formula : ''),
                condition: row.condition || (comp ? comp.condition : '')
              };
            });
          }

          // Map deductions
          if (fullDoc.deductions && fullDoc.deductions.length > 0) {
            formData.value.deductions = fullDoc.deductions.map(row => {
              const comp = deductionComponents.value.find(c => c.name === row.salary_component);
              const isFormula = !!row.amount_based_on_formula || !!row.formula || (comp && !!comp.amount_based_on_formula);
              return {
                salary_component: row.salary_component,
                salary_component_abbr: row.abbr || row.salary_component_abbr || (comp ? comp.salary_component_abbr : ''),
                amount_based_on_formula: isFormula,
                amount: row.amount != null ? parseFloat(row.amount) : (comp && comp.amount != null ? parseFloat(comp.amount) : 0),
                formula: row.formula || (comp ? comp.formula : ''),
                condition: row.condition || (comp ? comp.condition : '')
              };
            });
          }
        }
      } catch (err) {
        console.error('Failed to load salary structure details:', err);
      }
    }
  }
});

const validate = () => {
  errors.value = {};
  let isValid = true;

  if (!formData.value.name || !formData.value.name.trim()) {
    errors.value.name = 'Salary Structure Name is required';
    isValid = false;
  }

  if (!formData.value.payroll_frequency) {
    errors.value.payroll_frequency = 'Payroll Frequency is required';
    isValid = false;
  }

  if (formData.value.salary_slip_based_on_timesheet) {
    if (!formData.value.salary_component) {
      errors.value.salary_component = 'Salary Component is required';
      isValid = false;
    }
    if (formData.value.hour_rate === undefined || formData.value.hour_rate === null || formData.value.hour_rate <= 0) {
      errors.value.hour_rate = 'Hour Rate must be greater than 0';
      isValid = false;
    }
  }

  return isValid;
};

const handleSave = async () => {
  submitError.value = '';
  if (!validate()) return;

  submitting.value = true;
  try {
    await call('arijentek_core.api.payroll.save_salary_structure', {
      doc: formData.value
    });
    emit('save', formData.value);
    show.value = false;
  } catch (err) {
    submitError.value = getErrorMessage(err, 'Failed to save salary structure');
  } finally {
    submitting.value = false;
  }
};
</script>
