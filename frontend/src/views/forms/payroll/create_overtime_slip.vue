<template>
  <Teleport to="body">
    <Dialog :options="{ size: '3xl' }" v-model="show">
      <template #body>
        <div class="modal-panel relative w-full overflow-hidden flex flex-col max-h-[90vh]">
          <!-- Custom Header -->
          <header class="modal-header shrink-0 flex justify-between items-center">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-[12px] bg-accent/[0.10] dark:bg-accent/20 border border-accent/30 dark:border-accent/30 flex items-center justify-center text-accent dark:text-accent-light shrink-0 shadow-sm">
                <span class="material-symbols-outlined text-xl">receipt_long</span>
              </div>
              <div>
                <h3 class="modal-title">
                  {{ editId ? 'Edit overtime slip' : 'New overtime slip' }}
                </h3>
                <p class="text-xs font-medium text-[#5C6169] dark:text-white/65">
                  {{ editId ? 'Update employee overtime slip details' : 'Create employee overtime slip and detail entries' }}
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
              <p class="text-xs font-medium text-[#5C6169] dark:text-white/65">Loading overtime slip details...</p>
            </div>

            <template v-else>
              <!-- Submit Error message -->
              <div v-if="errorMessage" class="p-4 bg-red-50 border border-red-100 rounded-[12px] flex items-start gap-3">
                <span class="material-symbols-outlined text-red-500 dark:text-red-400 text-lg shrink-0">error</span>
                <div class="text-xs font-medium text-red-700 dark:text-red-400 leading-relaxed">{{ errorMessage }}</div>
              </div>

              <!-- Header Fields Grid -->
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <!-- Employee (SearchableDropdown) -->
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

                <!-- Posting Date -->
                <div class="flex flex-col gap-2">
                  <label class="field-label">
                    Posting Date <span class="text-red-500 dark:text-red-400">*</span>
                  </label>
                  <DateField v-model="formData.posting_date" />
                </div>

                <!-- Start Date -->
                <div class="flex flex-col gap-2">
                  <label class="field-label">
                    Start Date <span class="text-red-500 dark:text-red-400">*</span>
                  </label>
                  <DateField v-model="formData.start_date" />
                </div>

                <!-- End Date -->
                <div class="flex flex-col gap-2">
                  <label class="field-label">
                    End Date <span class="text-red-500 dark:text-red-400">*</span>
                  </label>
                  <DateField v-model="formData.end_date" :min="formData.start_date" />
                </div>
              </div>

              <!-- Overtime Details Table Section -->
              <div class="space-y-3 pt-2">
                <h4 class="text-[13px] font-semiboldr text-[#17181B] dark:text-white">Overtime Details</h4>

                <div class="border border-black/[0.07] dark:border-white/10 rounded-[16px] overflow-visible">
                  <table class="w-full text-left border-collapse overflow-visible">
                    <thead>
                      <tr class="bg-black/[0.02] dark:bg-white/[0.04] border-b border-black/[0.07] dark:border-white/10 rounded-t-2xl">
                        <th class="table-th">Date</th>
                        <th class="table-th">Overtime Type</th>
                        <th class="table-th w-28">Hours</th>
                        <th class="table-th w-28">Std Hours</th>
                        <th class="table-th w-12 !text-center"></th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-black/[0.05] dark:divide-white/[0.06] overflow-visible">
                      <tr v-for="(row, idx) in formData.overtime_details" :key="idx" class="hover:bg-black/[0.03] dark:hover:bg-white/[0.06] relative" :style="{ zIndex: formData.overtime_details.length - idx + 10 }">
                        <td class="p-2.5">
                          <DateField v-model="row.date" />
                        </td>
                        <td class="p-2.5 relative z-20">
                          <div class="flex items-center gap-2">
                            <div class="flex-1 min-w-0">
                              <SearchableDropdown
                                v-model="row.overtime_type"
                                :options="overtimeTypeOptions"
                                placeholder="Select type"
                              />
                            </div>
                            <button
                              v-if="canCreateOvertimeType"
                              type="button"
                              @click.prevent="openCreateOvertimeTypeModal(idx)"
                              class="btn-add-option"
                              title="Add a new overtime type"
                              aria-label="Add a new overtime type"
                            >
                              <span class="material-symbols-outlined !text-[18px]">add</span>
                            </button>
                          </div>
                        </td>
                        <td class="p-2.5">
                          <input
                            type="number"
                            step="0.5"
                            min="0"
                            v-model.number="row.overtime_duration"
                            required
                            class="field-input w-full"
                          />
                        </td>
                        <td class="p-2.5">
                          <input
                            type="number"
                            step="0.5"
                            min="0"
                            v-model.number="row.standard_working_hours"
                            required
                            class="field-input w-full"
                          />
                        </td>
                        <td class="p-2.5 text-center">
                          <button
                            type="button"
                            @click="removeDetailRow(idx)"
                            class="p-1.5 text-red-400 hover:text-red-600 dark:text-red-400 rounded-[12px] hover:bg-red-50 dark:hover:bg-red-900/20 transition-all"
                            title="Remove Entry"
                          >
                            <span class="material-symbols-outlined text-sm">delete</span>
                          </button>
                        </td>
                      </tr>
                      <tr v-if="formData.overtime_details.length === 0">
                        <td colspan="5" class="p-6 text-center text-xs text-[#656A72] dark:text-white/60">
                          No overtime detail entries. Click "Add Entry" below to add overtime hours.
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <!-- Bottom Bar: Left Add Entry Button & Right Total Hours -->
                <div class="flex items-center justify-between pt-1">
                  <button
                    type="button"
                    @click="addDetailRow"
                    class="btn-secondary"
                  >
                    <span class="material-symbols-outlined text-sm">add</span>
                    Add Entry
                  </button>

                  <p class="text-xs font-medium text-[#5C6169] dark:text-white/65">
                    Total Hours: <span class="font-semibold text-accent dark:text-accent-light text-sm">{{ computedTotalHours }} hrs</span>
                  </p>
                </div>
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

        <!-- Sub-dialog for creating Overtime Type -->
        <CreateOvertimeType
          v-model="showCreateOvertimeTypeDialog"
          @save="onOvertimeTypeSaved"
        />
      </template>
    </Dialog>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { Dialog, call } from 'frappe-ui';
import SearchableDropdown from '@/components/SearchableDropdown.vue';
import CreateOvertimeType from './create_overtime_type.vue';
import { getErrorMessage } from '@/utils';
import DateField from '../../../components/DateField.vue'
import { usePayrollStore } from '@/stores/payroll';
import { storeToRefs } from 'pinia';

const props = defineProps({
  modelValue: Boolean,
  editId: String,
});

const emit = defineEmits(['update:modelValue', 'save']);

const payrollStore = usePayrollStore();
const { canCreateOvertimeType } = storeToRefs(payrollStore);

const loading = ref(false);
const saving = ref(false);
const errorMessage = ref('');

const employeeOptions = ref([]);
const overtimeTypeOptions = ref([]);

const showCreateOvertimeTypeDialog = ref(false);
const activeRowIndexForNewType = ref(null);

function openCreateOvertimeTypeModal(rowIndex = null) {
  activeRowIndexForNewType.value = rowIndex;
  showCreateOvertimeTypeDialog.value = true;
}

async function onOvertimeTypeSaved(newType) {
  await fetchDropdownOptions();
  const createdName = typeof newType === 'string' ? newType : (newType?.name || newType?.value);
  if (createdName) {
    if (activeRowIndexForNewType.value !== null && formData.value.overtime_details[activeRowIndexForNewType.value]) {
      formData.value.overtime_details[activeRowIndexForNewType.value].overtime_type = createdName;
    } else if (formData.value.overtime_details.length > 0) {
      const lastIdx = formData.value.overtime_details.length - 1;
      formData.value.overtime_details[lastIdx].overtime_type = createdName;
    }
  }
}

const todayDate = new Date().toISOString().split('T')[0];

const formData = ref({
  name: '',
  employee: '',
  posting_date: todayDate,
  start_date: todayDate,
  end_date: todayDate,
  overtime_details: [],
});

const show = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
});

const computedTotalHours = computed(() => {
  if (!formData.value.overtime_details) return 0;
  return formData.value.overtime_details.reduce((sum, row) => sum + (parseFloat(row.overtime_duration) || 0), 0);
});

function getDefaultOvertimeType() {
  const options = overtimeTypeOptions.value || [];
  const standardOpt = options.find(
    (opt) => (opt.value || opt.label || '').toLowerCase() === 'standard overtime'
  );
  if (standardOpt) {
    return standardOpt.value;
  }
  return options[0]?.value || 'Standard OverTime';
}

function addDetailRow() {
  formData.value.overtime_details.push({
    date: formData.value.start_date || todayDate,
    overtime_type: getDefaultOvertimeType(),
    overtime_duration: 1,
    standard_working_hours: 8,
  });
}

function removeDetailRow(index) {
  formData.value.overtime_details.splice(index, 1);
}

async function fetchDropdownOptions() {
  try {
    const [empRes, otTypeRes] = await Promise.all([
      call('arijentek_core.api.payroll.get_employee_list'),
      call('arijentek_core.api.payroll.get_overtime_type_list'),
    ]);

    employeeOptions.value = (empRes || []).map((emp) => ({
      value: emp.name,
      label: emp.employee_name ? `${emp.employee_name} (${emp.name})` : emp.name,
    }));

    overtimeTypeOptions.value = (otTypeRes || []).map((ot) => ({
      value: ot.value || ot.name,
      label: ot.label || ot.name,
    }));

    if (!props.editId && formData.value.overtime_details?.length) {
      const defaultType = getDefaultOvertimeType();
      formData.value.overtime_details.forEach((row) => {
        if (!row.overtime_type) {
          row.overtime_type = defaultType;
        }
      });
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
      const res = await call('arijentek_core.api.payroll.get_overtime_slip_details', { name: props.editId });
      if (res) {
        formData.value = {
          name: res.name || '',
          employee: res.employee || '',
          posting_date: res.posting_date || todayDate,
          start_date: res.start_date || todayDate,
          end_date: res.end_date || todayDate,
          overtime_details: (res.overtime_details || []).map((d) => ({
            date: d.date || res.start_date,
            overtime_type: d.overtime_type || '',
            overtime_duration: d.overtime_duration || 0,
            standard_working_hours: d.standard_working_hours || 8,
          })),
        };
      }
    } catch (e) {
      console.error('Failed to load overtime slip details:', e);
      errorMessage.value = getErrorMessage(e, 'Failed to load overtime slip details.');
    } finally {
      loading.value = false;
    }
  } else {
    formData.value = {
      name: '',
      employee: '',
      posting_date: todayDate,
      start_date: todayDate,
      end_date: todayDate,
      overtime_details: [],
    };
    addDetailRow();
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

async function submitForm() {
  errorMessage.value = '';
  if (!formData.value.employee) {
    errorMessage.value = 'Employee is required.';
    return;
  }
  if (!formData.value.start_date || !formData.value.end_date) {
    errorMessage.value = 'Start Date and End Date are required.';
    return;
  }
  if (formData.value.start_date && formData.value.end_date && formData.value.end_date < formData.value.start_date) {
    errorMessage.value = 'End Date cannot be earlier than Start Date.';
    return;
  }
  if (!formData.value.overtime_details || formData.value.overtime_details.length === 0) {
    errorMessage.value = 'Please add at least one overtime detail entry.';
    return;
  }
  const missingType = formData.value.overtime_details.some((row) => !row.overtime_type);
  if (missingType) {
    errorMessage.value = 'Please select an Overtime Type for each detail row.';
    return;
  }

  saving.value = true;
  try {
    await call('arijentek_core.api.payroll.save_overtime_slip', { doc: formData.value });
    emit('save');
    show.value = false;
  } catch (e) {
    console.error('Failed to save overtime slip:', e);
    errorMessage.value = getErrorMessage(e, 'Failed to save Overtime Slip.');
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
