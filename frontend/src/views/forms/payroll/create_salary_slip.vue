<template>
  <Teleport to="body">
    <Dialog :options="{ size: '5xl' }" v-model="show">
      <template #body>
        <div class="modal-panel flex flex-col overflow-hidden max-h-[90vh]">
          <!-- Custom Header -->
          <header class="modal-header">
            <div class="flex items-center gap-3">
              <div>
                <h3 class="modal-title">{{ isEdit ? 'Edit salary slip' : 'New salary slip' }}</h3>
                <p class="text-[12px] text-[#656A72] dark:text-white/60">
                  {{ isEdit ? 'Update existing salary slip details' : 'Generate and customize employee salary slip' }}
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
            <!-- Loading Options -->
            <div v-if="loadingOptions" class="py-12 flex flex-col items-center justify-center gap-3">
              <div class="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin"></div>
              <p class="text-xs font-medium text-[#5C6169] dark:text-white/65">Loading defaults and employee data...</p>
            </div>

            <template v-else>
              <!-- SECTION 1: General Details -->
              <div class="bg-white dark:bg-white/[0.06] border border-black/[0.07] dark:border-white/10 rounded-[16px] p-6 shadow-sm space-y-6">
                <h3 class="field-label">
                  1. General details
                </h3>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  <!-- Employee Select -->
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
                    <p v-if="errors.employee" class="field-error text-red-500 dark:text-red-400 flex items-center gap-1 mt-0.5">
                      <span class="material-symbols-outlined text-sm">error</span>
                      {{ errors.employee }}
                    </p>
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
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-1">
                  <!-- Company Select -->
                  <div class="flex flex-col gap-2">
                    <label class="field-label">
                      Company <span class="text-red-500 dark:text-red-400">*</span>
                    </label>
                    <SearchableDropdown
                      v-model="formData.company"
                      :options="companyOptions"
                      placeholder="Select company"
                      :disabled="isEdit"
                    />
                    <p v-if="errors.company" class="field-error text-red-500 dark:text-red-400 flex items-center gap-1 mt-0.5">
                      <span class="material-symbols-outlined text-sm">error</span>
                      {{ errors.company }}
                    </p>
                  </div>

                  <!-- Payroll Frequency Dropdown -->
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
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-1">
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

                <!-- Salary Slip Based on Timesheet -->
                <div class="flex flex-col gap-2 pt-1">
                  <label class="field-label flex items-center justify-between">
                    <span>Salary Slip Based on Timesheet</span>
                    <span class="text-xs font-normal text-[#656A72] dark:text-white/55">Hourly Based calculation</span>
                  </label>
                  <div class="field-static !py-0 flex items-center justify-between h-11">
                    <div class="flex items-center gap-2">
                      <span 
                        class="w-2.5 h-2.5 rounded-full" 
                        :class="formData.salary_slip_based_on_timesheet ? 'bg-accent' : 'bg-black/[0.12]'"
                      ></span>
                      <span class="text-sm font-semibold text-[#17181B] dark:text-white/80">
                        {{ formData.salary_slip_based_on_timesheet ? 'Yes (Hourly Based)' : 'No' }}
                      </span>
                    </div>
                    <!-- Static Toggle (disabled state for display only) -->
                    <button 
                      type="button"
                      class="relative inline-flex h-6 w-11 shrink-0 cursor-not-allowed opacity-60 rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none"
                      :class="formData.salary_slip_based_on_timesheet ? 'bg-accent' : 'bg-black/[0.08] dark:bg-white/[0.08]'"
                    >
                      <span class="sr-only">Use timesheet</span>
                      <span 
                        aria-hidden="true" 
                        class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
                        :class="formData.salary_slip_based_on_timesheet ? 'translate-x-5' : 'translate-x-0'"
                      ></span>
                    </button>
                  </div>
                </div>
              </div>

              <!-- SECTION 2: Dynamic Days and Summary Labels (based on holiday list, attendance) -->
              <div v-if="formData.employee && formData.start_date && formData.end_date" class="bg-white dark:bg-white/[0.06] border border-black/[0.07] dark:border-white/10 rounded-[16px] p-6 shadow-sm space-y-6">
                <h3 class="field-label">
                  2. Calculations and attendance
                </h3>

                <div v-if="loadingDetails" class="py-4 flex items-center justify-center gap-2">
                  <div class="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin"></div>
                  <span class="text-xs text-[#5C6169] dark:text-white/65">Recalculating attendance days...</span>
                </div>

                <div v-else class="grid grid-cols-2 sm:grid-cols-5 gap-4">
                  <!-- Working Days -->
                  <div class="inset-panel flex flex-col gap-1">
                    <span class="field-label">Working days</span>
                    <span class="modal-title">{{ formData.working_days || 0 }}</span>
                  </div>

                  <!-- Payment Days -->
                  <div class="inset-panel flex flex-col gap-1">
                    <span class="field-label">Payment days</span>
                    <span class="modal-title">{{ formData.payment_days || 0 }}</span>
                  </div>

                  <!-- Present Days -->
                  <div class="inset-panel flex flex-col gap-1">
                    <span class="field-label">Present days</span>
                    <span class="modal-title">{{ formData.present_days || 0 }}</span>
                  </div>

                  <!-- Absent Days -->
                  <div class="inset-panel flex flex-col gap-1">
                    <span class="field-label">Absent days</span>
                    <span class="text-lg font-semibold text-rose-600 dark:text-rose-400">{{ formData.absent_days || 0 }}</span>
                  </div>

                  <!-- Holiday Days -->
                  <div class="inset-panel flex flex-col gap-1 col-span-2 sm:col-span-1">
                    <span class="field-label">Holidays</span>
                    <span class="text-lg font-semibold text-accent dark:text-accent-light">{{ formData.holiday_days || 0 }}</span>
                  </div>
                </div>
              </div>

              <!-- SECTION 3: Timesheet Details Section -->
              <div v-if="formData.salary_slip_based_on_timesheet" class="bg-white dark:bg-white/[0.06] border border-black/[0.07] dark:border-white/10 rounded-[16px] p-6 shadow-sm space-y-6">
                <h3 class="field-label">
                  Timesheet Details
                </h3>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <!-- Timesheet table column (2/3 width) -->
                  <div class="md:col-span-2 space-y-3">
                    <h4 class="field-label">
                      Salary Slip Timesheet
                    </h4>

                    <!-- Header -->
                    <div class="px-1 pb-2 mb-1 border-b border-black/[0.07] dark:border-white/10 grid grid-cols-12 gap-3">
                      <span class="field-label col-span-8">Time Sheet</span>
                      <span class="field-label col-span-4 text-right">Working Hours</span>
                    </div>

                    <!-- Rows -->
                    <div v-if="formData.timesheets.length > 0" class="space-y-2.5">
                      <div 
                        v-for="(line, index) in formData.timesheets" 
                        :key="'timesheet-' + index"
                        class="grid grid-cols-12 gap-3 items-center py-1.5"
                      >
                        <!-- Timesheet Label -->
                        <span class="col-span-8 text-xs font-mono text-[#17181B] dark:text-white/80">
                          {{ line.time_sheet }}
                        </span>

                        <!-- Working Hours Label -->
                        <span class="col-span-4 text-xs font-semibold font-mono text-[#17181B] dark:text-white text-right">
                          {{ parseFloat(line.working_hours || 0).toFixed(3) }} hrs
                        </span>
                      </div>
                    </div>

                    <div v-else class="p-4 text-center border border-dashed border-black/[0.07] dark:border-white/10 rounded-[12px] text-xs text-[#656A72] dark:text-white/60">
                      No timesheets added to this salary slip.
                    </div>
                  </div>

                  <!-- Calculations column (1/3 width) -->
                  <div class="space-y-4 md:border-l md:border-dashed border-black/[0.07] dark:border-white/10 md:pl-6">
                    <!-- Total Working Hours -->
                    <div class="flex flex-col gap-1.5">
                      <label class="field-label">
                        Total Working Hours
                      </label>
                      <input 
                        type="number"
                        v-model.number="formData.total_working_hours"
                        step="any"
                        class="field-input w-full font-mono"
                      />
                    </div>

                    <!-- Hour Rate -->
                    <div class="flex flex-col gap-1.5">
                      <label class="field-label">
                        Hour Rate (USD)
                      </label>
                      <div class="relative">
                        <span class="absolute left-4 top-1/2 -translate-y-1/2 text-sm font-semibold text-[#656A72] dark:text-white/60 font-mono">
                          $
                        </span>
                        <input 
                          type="number"
                          v-model.number="formData.hour_rate"
                          step="any"
                          class="field-input !pl-8 tabular-nums font-semibold"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- SECTION 4: Earnings & Deductions Tables -->
              <div class="bg-white dark:bg-white/[0.06] border border-black/[0.07] dark:border-white/10 rounded-[16px] p-6 shadow-sm space-y-6">
                <div class="flex items-center justify-between">
                  <h3 class="field-label">
                    3. Salary components
                  </h3>
                  <div class="flex items-center gap-4 text-xs font-semibold">
                    <span class="text-accent dark:text-accent-light flex items-center gap-1">
                      Earnings: {{ formData.earnings.length }}
                    </span>
                    <span class="text-rose-600 dark:text-rose-400 flex items-center gap-1">
                      Deductions: {{ formData.deductions.length }}
                    </span>
                  </div>
                </div>


                <!-- EARNINGS TABLE -->
                <div class="space-y-3">
                  <h4 class="text-sm font-semibold text-[#17181B] dark:text-white flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-accent"></span>
                    Earnings
                  </h4>

                  <!-- Table Header -->
                  <div class="px-1 pb-2 mb-1 border-b border-black/[0.07] dark:border-white/10 hidden md:grid grid-cols-12 gap-3">
                    <span class="field-label col-span-6">Salary Component</span>
                    <span class="field-label col-span-5">Amount</span>
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
                      <div class="col-span-12 md:col-span-6">
                        <SearchableDropdown
                          v-model="line.salary_component"
                          :options="earningComponentOptions"
                          placeholder="Select earning component"
                          @change="(val) => onEarningComponentChange(index, val)"
                        />
                      </div>

                      <!-- Amount -->
                      <div class="col-span-12 md:col-span-5 relative">
                        <span class="absolute left-3 top-1/2 -translate-y-1/2 text-xs font-semibold text-[#656A72] dark:text-white/60 font-mono">
                          $
                        </span>
                        <input 
                          type="number" 
                          v-model.number="line.amount" 
                          placeholder="0.00" 
                          step="any"
                          class="field-input !pl-8 !h-9 tabular-nums"
                        />
                      </div>

                      <!-- Delete Action -->
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

                  <!-- Add Earnings Line Button -->
                  <div class="flex justify-start pt-1">
                    <button 
                      type="button" 
                      @click="addEarningLine" 
                      class="btn-secondary"
                    >
                      <span class="material-symbols-outlined text-base">add</span>
                      Add Row
                    </button>
                  </div>
                </div>

                <!-- DEDUCTIONS TABLE -->
                <div class="space-y-3 pt-4 border-t border-black/[0.07] dark:border-white/10">
                  <h4 class="text-sm font-semibold text-[#17181B] dark:text-white flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-rose-500"></span>
                    Deductions
                  </h4>

                  <!-- Table Header -->
                  <div class="px-1 pb-2 mb-1 border-b border-black/[0.07] dark:border-white/10 hidden md:grid grid-cols-12 gap-3">
                    <span class="field-label col-span-6">Salary Component</span>
                    <span class="field-label col-span-5">Amount</span>
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
                      <div class="col-span-12 md:col-span-6">
                        <SearchableDropdown
                          v-model="line.salary_component"
                          :options="deductionComponentOptions"
                          placeholder="Select deduction component"
                          @change="(val) => onDeductionComponentChange(index, val)"
                        />
                      </div>

                      <!-- Amount -->
                      <div class="col-span-12 md:col-span-5 relative">
                        <span class="absolute left-3 top-1/2 -translate-y-1/2 text-xs font-semibold text-[#656A72] dark:text-white/60 font-mono">
                          $
                        </span>
                        <input 
                          type="number" 
                          v-model.number="line.amount" 
                          placeholder="0.00" 
                          step="any"
                          class="field-input !pl-8 !h-9 tabular-nums"
                        />
                      </div>

                      <!-- Delete Action -->
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

                  <!-- Add Deduction Line Button -->
                  <div class="flex justify-start pt-1">
                    <button 
                      type="button" 
                      @click="addDeductionLine" 
                      class="btn-secondary"
                    >
                      <span class="material-symbols-outlined text-base">add</span>
                      Add Row
                    </button>
                  </div>
                </div>
              </div>

              <!-- SECTION 5: Totals Summary Labels -->
              <div class="inset-panel !p-5 space-y-5">
                <h3 class="field-label">
                  4. Totals and net pay
                </h3>

                <div class="grid grid-cols-1 sm:grid-cols-3 gap-6">
                  <!-- Gross Pay label -->
                  <div class="flex flex-col border-b sm:border-b-0 sm:border-r border-black/[0.07] dark:border-white/10 pb-4 sm:pb-0 sm:pr-6">
                    <span class="field-label">Gross pay (USD)</span>
                    <span class="text-[20px] font-semibold tabular-nums mt-1 text-[#17181B] dark:text-white">
                      {{ formatCurrency(grossPayCalculated) }}
                    </span>
                    <span class="text-xs text-[#5C6169] dark:text-white/65 font-semibold font-mono mt-0.5">gross_pay</span>
                  </div>

                  <!-- Gross Year To Date label -->
                  <div class="flex flex-col border-b sm:border-b-0 sm:border-r border-black/[0.07] dark:border-white/10 pb-4 sm:pb-0 sm:pr-6">
                    <span class="field-label">Gross year to date (USD)</span>
                    <span class="text-[20px] font-semibold tabular-nums mt-1 text-[#17181B] dark:text-white">
                      {{ formatCurrency(formData.gross_year_to_date) }}
                    </span>
                    <span class="text-xs text-[#5C6169] dark:text-white/65 font-semibold font-mono mt-0.5">gross_year_to_date</span>
                  </div>

                  <!-- Total Deduction label -->
                  <div class="flex flex-col">
                    <span class="field-label">Total deductions (USD)</span>
                    <span class="text-[20px] font-semibold tabular-nums mt-1 text-red-600 dark:text-red-400">
                      {{ formatCurrency(totalDeductionsCalculated) }}
                    </span>
                    <span class="text-xs text-[#5C6169] dark:text-white/65 font-semibold font-mono mt-0.5">total_deduction</span>
                  </div>
                </div>

                <div class="pt-5 border-t border-black/[0.07] dark:border-white/10 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <div>
                    <span class="field-label">Estimated take-home</span>
                    <p class="text-xs text-[#656A72] dark:text-white/60 mt-0.5">Calculated as Gross Pay minus Total Deductions.</p>
                  </div>
                  <span class="text-[20px] font-semibold tabular-nums text-accent dark:text-accent-light">
                    {{ formatCurrency(grossPayCalculated - totalDeductionsCalculated) }}
                  </span>
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
              
              <!-- Save Draft Button -->
              <button 
                type="button"
                class="btn-primary flex items-center gap-2 disabled:opacity-70" 
                @click="handleSave(false)"
                :disabled="submitting || loadingOptions || loadingDetails"
              >
                <span v-if="submitting && !submitFlag" class="material-symbols-outlined text-base animate-spin">progress_activity</span>
                <span v-else class="material-symbols-outlined text-base">save</span>
                Save Draft
              </button>

              <!-- Submit Button -->
              <button 
                type="button"
                class="btn-primary flex items-center gap-2 disabled:opacity-70" 
                @click="handleSave(true)"
                :disabled="submitting || loadingOptions || loadingDetails"
                style="background-color: #5B4BC4 !important; color: #ffffff !important;"
              >
                <span v-if="submitting && submitFlag" class="material-symbols-outlined text-base animate-spin" style="color: #ffffff !important;">progress_activity</span>
                <span v-else class="material-symbols-outlined text-base" style="color: #ffffff !important;">check_circle</span>
                Submit Slip
              </button>
            </div>
          </footer>
        </div>
      </template>
    </Dialog>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { Dialog, call } from 'frappe-ui';
import SearchableDropdown from '../../../components/SearchableDropdown.vue';
import { getErrorMessage } from '@/utils';
import DateField from '../../../components/DateField.vue'

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

// Dropdown options loaded from API
const employees = ref([]);
const companies = ref([]);
const companyCurrency = ref('USD');
const earningComponents = ref([]);

const isInitializing = ref(false);
const deductionComponents = ref([]);
const pendingTimesheets = ref([]);


const loadingOptions = ref(false);
const loadingDetails = ref(false);
const submitting = ref(false);
const submitFlag = ref(false); // true if clicking submit, false if draft
const submitError = ref('');
const errors = ref({});

const getInitialFormData = () => {
  const today = new Date().toISOString().split('T')[0];
  return {
    name: '',
    employee: '',
    posting_date: today,
    company: '',
    payroll_frequency: 'Monthly',
    start_date: '',
    end_date: '',
    salary_slip_based_on_timesheet: 0,
    working_days: 0,
    payment_days: 0,
    absent_days: 0,
    present_days: 0,
    holiday_days: 0,
    gross_pay: 0,
    total_deduction: 0,
    net_pay: 0,
    gross_year_to_date: 0,
    hour_rate: 0,
    total_working_hours: 0,
    timesheet_salary_component: '',
    earnings: [],
    deductions: [],
    timesheets: []
  };
};

const formData = ref(getInitialFormData());

const frequencyOptions = [
  { label: 'Monthly', value: 'Monthly' },
  { label: 'Fortnightly', value: 'Fortnightly' },
  { label: 'Weekly', value: 'Weekly' },
  { label: 'Daily', value: 'Daily' }
];

const employeeOptions = computed(() => {
  return employees.value.map(e => ({
    label: `${e.employee_name} (${e.name})`,
    value: e.name
  }));
});

const companyOptions = computed(() => {
  return companies.value.map(c => ({
    label: c.company_name || c.name,
    value: c.name
  }));
});

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

const grossPayCalculated = computed(() => {
  return formData.value.earnings.reduce((sum, item) => sum + (parseFloat(item.amount) || 0), 0);
});

const totalDeductionsCalculated = computed(() => {
  return formData.value.deductions.reduce((sum, item) => sum + (parseFloat(item.amount) || 0), 0);
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

// Row item actions
const addEarningLine = () => {
  formData.value.earnings.push({
    salary_component: '',
    abbr: '',
    amount: 0
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
    line.abbr = comp.salary_component_abbr || '';
    line.amount = comp.amount ? parseFloat(comp.amount) : 0;
  }
};

const addDeductionLine = () => {
  formData.value.deductions.push({
    salary_component: '',
    abbr: '',
    amount: 0
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
    line.abbr = comp.salary_component_abbr || '';
    line.amount = comp.amount ? parseFloat(comp.amount) : 0;
  }
};

// Fetch auto prefill calculations for Employee, dates, and timesheets
const fetchPrefillDetails = async () => {
  if (!formData.value.employee || !formData.value.start_date || !formData.value.end_date) {
    return;
  }

  loadingDetails.value = true;
  try {
    const res = await call('arijentek_core.api.payroll.get_employee_salary_slip_details', {
      employee: formData.value.employee,
      start_date: formData.value.start_date,
      end_date: formData.value.end_date
    });

    if (res) {
      if (res.company) formData.value.company = res.company;
      if (res.currency) companyCurrency.value = res.currency;
      
      if (!isInitializing.value) {
        formData.value.working_days = res.working_days || 0;
        formData.value.payment_days = res.payment_days || 0;
        formData.value.absent_days = res.absent_days || 0;
        formData.value.holiday_days = res.holiday_days || 0;
        formData.value.present_days = res.present_days || 0;
      }
      formData.value.gross_year_to_date = res.gross_year_to_date || 0;
      if (res.hour_rate && !formData.value.hour_rate) {
        formData.value.hour_rate = res.hour_rate || 0;
      }
      if (res.timesheet_salary_component) {
        formData.value.timesheet_salary_component = res.timesheet_salary_component || '';
      }
      if (res.salary_slip_based_on_timesheet !== undefined) {
        formData.value.salary_slip_based_on_timesheet = res.salary_slip_based_on_timesheet ? 1 : 0;
      }

      // Populate default earnings and deductions if they are empty
      if (!isEdit.value || (formData.value.earnings.length === 0 && formData.value.deductions.length === 0)) {
        formData.value.earnings = (res.earnings || []).map(e => ({
          salary_component: e.salary_component,
          abbr: e.abbr,
          amount: parseFloat(e.amount) || 0
        }));

        formData.value.deductions = (res.deductions || []).map(d => ({
          salary_component: d.salary_component,
          abbr: d.abbr,
          amount: parseFloat(d.amount) || 0
        }));
      }

      // Map pending timesheets
      pendingTimesheets.value = (res.timesheets || []).map(t => ({
        name: t.name,
        total_hours: parseFloat(t.total_hours) || 0,
        rate: parseFloat(t.base_billing_amount && t.total_hours ? (t.base_billing_amount / t.total_hours) : 0),
        amount: parseFloat(t.base_billing_amount) || 0
      }));

      // Populate default timesheets table if not editing
      if (!isEdit.value) {
        formData.value.timesheets = pendingTimesheets.value.map(t => ({
          time_sheet: t.name,
          working_hours: t.total_hours
        }));
        formData.value.total_working_hours = formData.value.timesheets.reduce(
          (sum, t) => sum + (parseFloat(t.working_hours) || 0),
          0
        );
      }
    }
  } catch (err) {
    console.error('Failed to prefill salary slip details:', err);
  } finally {
    loadingDetails.value = false;
  }
};

watch(
  [() => formData.value.start_date, () => formData.value.payroll_frequency],
  ([newStartDate, newFreq]) => {
    if (!newStartDate || !newFreq) return;
    
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

watch(
  () => formData.value.employee,
  async (newEmp) => {
    if (!newEmp) {
      formData.value.salary_slip_based_on_timesheet = 0;
      formData.value.hour_rate = 0;
      formData.value.timesheet_salary_component = '';
      return;
    }
    try {
      const res = await call('arijentek_core.api.payroll.get_employee_timesheet_setting', { employee: newEmp });
      if (res) {
        formData.value.salary_slip_based_on_timesheet = res.salary_slip_based_on_timesheet ? 1 : 0;
        if (res.hour_rate) formData.value.hour_rate = res.hour_rate;
        if (res.salary_component) formData.value.timesheet_salary_component = res.salary_component;
      }
    } catch (e) {
      console.error('Failed to fetch employee timesheet setting:', e);
    }
  }
);

watch(
  () => [formData.value.employee, formData.value.start_date, formData.value.end_date],
  () => {
    fetchPrefillDetails();
  }
);

// Load options and defaults
const loadOptions = async () => {
  loadingOptions.value = true;
  try {
    // 1. Fetch employee list
    const empRes = await call('arijentek_core.api.payroll.get_employee_list');
    if (empRes) {
      employees.value = empRes;
    }

    // 2. Fetch structure options (companies, currencies, component lists)
    const optRes = await call('arijentek_core.api.payroll.get_salary_structure_options');
    if (optRes) {
      companies.value = optRes.companies || [];
      earningComponents.value = optRes.earning_components || [];
      deductionComponents.value = optRes.deduction_components || [];
      if (optRes.default_company) {
        formData.value.company = optRes.default_company;
      }
      if (optRes.default_currency) {
        companyCurrency.value = optRes.default_currency;
      }
    }
  } catch (err) {
    console.error('Failed to load salary slip default options:', err);
  } finally {
    loadingOptions.value = false;
  }
};

watch(show, async (newVal) => {
  if (newVal) {
    isInitializing.value = true;
    formData.value = getInitialFormData();
    submitError.value = '';
    errors.value = {};
    pendingTimesheets.value = [];
    
    await loadOptions();

    if (isEdit.value && props.editData) {
      loadingDetails.value = true;
      try {
        const d = await call('arijentek_core.api.payroll.get_salary_slip_details', {
          slip_name: props.editData.name || props.editData.id
        });
        if (d) {
          formData.value.name = d.name || d.id;
          formData.value.employee = d.employee;
          formData.value.posting_date = d.posting_date || formData.value.posting_date;
          formData.value.company = d.company;
          formData.value.payroll_frequency = d.payroll_frequency || 'Monthly';
          formData.value.start_date = d.start_date;
          formData.value.end_date = d.end_date;
          formData.value.salary_slip_based_on_timesheet = 
            d.salary_slip_based_on_timesheet === 1 || 
            d.salary_slip_based_on_timesheet === true || 
            d.salary_slip_based_on_timesheet === 'Yes' ||
            d.salary_slip_based_on_timesheet === '1' 
              ? 1 : 0;
          formData.value.working_days = d.working_days || 0;
          formData.value.payment_days = d.payment_days || 0;
          formData.value.absent_days = d.absent_days || 0;
          formData.value.present_days = d.present_days || 0;
          formData.value.holiday_days = d.holiday_days || 0;
          formData.value.hour_rate = d.hour_rate || 0;
          formData.value.total_working_hours = d.total_working_hours || 0;
          
          // Load child tables
          if (d.earnings && d.earnings.length > 0) {
            formData.value.earnings = d.earnings.map(e => ({
              salary_component: e.salary_component || e.component,
              abbr: e.abbr,
              amount: parseFloat(e.amount) || 0
            }));
          }
          if (d.deductions && d.deductions.length > 0) {
            formData.value.deductions = d.deductions.map(dd => ({
              salary_component: dd.salary_component || dd.component,
              abbr: dd.abbr,
              amount: parseFloat(dd.amount) || 0
            }));
          }
          if (d.timesheets && d.timesheets.length > 0) {
            formData.value.timesheets = d.timesheets.map(t => ({
              time_sheet: t.time_sheet || t.name,
              working_hours: parseFloat(t.working_hours) || 0
            }));
          }
        }
      } catch (err) {
        console.error('Failed to load salary slip details:', err);
      } finally {
        loadingDetails.value = false;
      }
      
      // Fetch fresh prefill info (like gross_year_to_date) without overwriting manual components
      await fetchPrefillDetails();
    }

    // Defer resetting initialization flag so any cascading watchers complete first
    setTimeout(() => {
      isInitializing.value = false;
    }, 200);
  } else {
    isInitializing.value = false;
  }
});

// Calculate and set timesheet amount in the earnings table
watch(
  () => [formData.value.total_working_hours, formData.value.hour_rate, formData.value.timesheet_salary_component, formData.value.salary_slip_based_on_timesheet],
  () => {
    if (formData.value.salary_slip_based_on_timesheet) {
      const componentName = formData.value.timesheet_salary_component || 'Basic';
      const amount = parseFloat(((formData.value.total_working_hours || 0) * (formData.value.hour_rate || 0)).toFixed(2));
      
      const existing = formData.value.earnings.find(e => e.salary_component === componentName);
      if (existing) {
        existing.amount = amount;
      } else {
        // If not found, add it
        const comp = earningComponents.value.find(c => c.name === componentName);
        formData.value.earnings.push({
          salary_component: componentName,
          abbr: comp ? (comp.salary_component_abbr || '') : 'Basic',
          amount: amount
        });
      }
    }
  }
);

watch(
  () => formData.value.start_date,
  (newStart) => {
    if (!newStart) return;
    if (!formData.value.end_date || formData.value.end_date < newStart) {
      formData.value.end_date = newStart;
    }
  }
);

const validate = () => {
  errors.value = {};
  let isValid = true;

  if (!formData.value.employee) {
    errors.value.employee = 'Employee is required';
    isValid = false;
  }
  if (!formData.value.posting_date) {
    errors.value.posting_date = 'Posting Date is required';
    isValid = false;
  }
  if (!formData.value.company) {
    errors.value.company = 'Company is required';
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

  return isValid;
};

const handleSave = async (submit) => {
  submitError.value = '';
  if (!validate()) return;

  submitting.value = true;
  submitFlag.value = submit;
  
  // Set total calculated amounts into the document
  formData.value.gross_pay = grossPayCalculated.value;
  formData.value.total_deduction = totalDeductionsCalculated.value;
  formData.value.net_pay = grossPayCalculated.value - totalDeductionsCalculated.value;
  formData.value.submit = submit;

  try {
    const res = await call('arijentek_core.api.payroll.save_salary_slip', {
      doc: formData.value
    });
    emit('save', formData.value);
    show.value = false;
  } catch (err) {
    submitError.value = getErrorMessage(err, 'Failed to save salary slip');
  } finally {
    submitting.value = false;
  }
};
</script>

<style scoped>
/* Scoped styles if needed */
</style>
