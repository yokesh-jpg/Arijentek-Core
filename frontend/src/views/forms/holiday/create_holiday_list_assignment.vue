<template>
  <Dialog :options="{ size: 'xl' }" v-model="show">
    <template #body>
      <div class="modal-panel !max-h-[88vh]">
        <div class="modal-header">
          <div class="min-w-0">
            <h3 class="modal-title">{{ editId ? 'Edit assignment' : 'Assign a holiday list' }}</h3>
            <p class="text-xs text-[#5C6169] dark:text-white/60 mt-0.5 truncate">
              {{ editId || 'Who this list of non-working days applies to.' }}
            </p>
          </div>
          <button @click="show = false" class="modal-close" aria-label="Close">
            <span class="material-symbols-outlined !text-[20px]">close</span>
          </button>
        </div>

        <div class="modal-body">
          <div>
            <label class="field-label" for="hla-list">Holiday list <span class="text-red-500 dark:text-red-400">*</span></label>
            <div class="flex items-center gap-2">
              <div class="flex-1 min-w-0">
                <SearchableDropdown
                  v-model="formData.holiday_list"
                  :options="leaveStore.holidayLists"
                  labelKey="holiday_list_name"
                  valueKey="name"
                  placeholder="Select a holiday list"
                  @update:modelValue="onHolidayListChange"
                />
              </div>
              <button
                v-if="canCreateHolidayList"
                @click.prevent="showCreateHolidayListModal = true"
                type="button"
                class="btn-add-option"
                title="Add a new holiday list"
                aria-label="Add a new holiday list"
              >
                <span class="material-symbols-outlined !text-[18px]">add</span>
              </button>
            </div>
            <p v-if="errors.holiday_list" class="field-error">{{ errors.holiday_list }}</p>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="field-label" for="hla-scope">Applies to <span class="text-red-500 dark:text-red-400">*</span></label>
              <div class="relative">
                <SelectField
                  id="hla-scope"
                  v-model="formData.applicable_for"
                  :options="[
                    { label: 'Everyone in the company', value: 'Company' },
                    { label: 'One employee', value: 'Employee' },
                  ]"
                  aria-label="Applies to"
                />
                <span class="material-symbols-outlined !text-[18px] absolute right-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/60 pointer-events-none">expand_more</span>
              </div>
              <p v-if="errors.applicable_for" class="field-error">{{ errors.applicable_for }}</p>
            </div>

            <div>
              <label class="field-label">Assigned to <span class="text-red-500 dark:text-red-400">*</span></label>
              <!-- Company scope has nothing to pick, so it states the answer
                   rather than offering a control that does nothing. -->
              <div v-if="formData.applicable_for === 'Company'" class="field-static">
                {{ formData.assigned_to || 'Loading company…' }}
              </div>
              <SearchableDropdown
                v-else
                v-model="formData.assigned_to"
                :options="leaveStore.employeeList"
                labelKey="employee_name"
                valueKey="name"
                placeholder="Select an employee"
              />
              <p v-if="errors.assigned_to" class="field-error">{{ errors.assigned_to }}</p>
            </div>
          </div>

          <div>
            <label class="field-label" for="hla-from">Starts from <span class="text-red-500 dark:text-red-400">*</span></label>
            <DateField v-model="formData.from_date" id="hla-from" />
            <p v-if="errors.from_date" class="field-error">{{ errors.from_date }}</p>
            <p class="text-xs text-[#656A72] dark:text-white/55 mt-1.5">Picking a list fills this with that list's own start date.</p>
          </div>

          <p v-if="submitError" class="field-error !text-[13px]" role="alert">{{ submitError }}</p>
        </div>

        <div class="modal-footer justify-end">
          <button class="btn-secondary" @click="show = false" :disabled="submitting">Cancel</button>
          <button class="btn-primary" @click="handleSave" :disabled="submitting">
            <span v-if="submitting" class="material-symbols-outlined !text-[18px] animate-spin">progress_activity</span>
            {{ submitting ? 'Saving…' : 'Save assignment' }}
          </button>
        </div>
      </div>
    </template>
  </Dialog>

  <CreateHolidayList
    v-model="showCreateHolidayListModal"
    @save="onHolidayListSaved"
  />
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { Dialog, call } from 'frappe-ui';
import { getErrorMessage } from '../../../utils.js';
import { useLeaveStore } from '../../../stores/leave.js';
import SearchableDropdown from '../../../components/SearchableDropdown.vue';
import DateField from '../../../components/DateField.vue'
import SelectField from '../../../components/SelectField.vue'
import CreateHolidayList from './create_holiday_list.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  editId: { type: String, default: '' }
});

const emit = defineEmits(['update:modelValue', 'save']);

const leaveStore = useLeaveStore();
const defaultCompany = ref('');

onMounted(async () => {
  leaveStore.fetchHolidayLists();
  leaveStore.fetchEmployeeList();
  try {
    const companies = await call('frappe.client.get_list', {
      doctype: 'Company',
      fields: ['name']
    });
    if (companies && companies.length > 0) {
      defaultCompany.value = companies[0].name;
      if (formData.value.applicable_for === 'Company' && !formData.value.assigned_to) {
        formData.value.assigned_to = defaultCompany.value;
      }
    }
  } catch (err) {
    console.error('Failed to fetch company', err);
  }
});

const show = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
});

const getInitialFormData = () => ({
  holiday_list: '',
  applicable_for: 'Company',
  assigned_to: '',
  from_date: ''
});

const formData = ref(getInitialFormData());
const errors = ref({});
const submitError = ref('');
const submitting = ref(false);

const showCreateHolidayListModal = ref(false);
const canCreateHolidayList = computed(() => leaveStore.canCreateHolidayList);

watch(show, async (newVal) => {
  if (newVal) {
    formData.value = getInitialFormData();
    errors.value = {};
    submitError.value = '';
    if (props.editId) {
      await fetchDetails();
    } else {
      if (formData.value.applicable_for === 'Company') {
        formData.value.assigned_to = defaultCompany.value;
      }
    }
  }
});

/* The company name arrives from an async fetch. If the dialog is opened before
   it lands - which is the normal case, since the tab and the dialog mount
   together - nothing used to fill the field and it read "Loading company…"
   for good. Backfill it when the name arrives. */
watch(defaultCompany, (name) => {
  if (name && formData.value.applicable_for === 'Company' && !formData.value.assigned_to) {
    formData.value.assigned_to = name;
  }
});

watch(() => formData.value.applicable_for, (newVal) => {
  if (newVal === 'Company') {
    formData.value.assigned_to = defaultCompany.value;
  } else {
    formData.value.assigned_to = '';
  }
});

const onHolidayListChange = () => {
  const selected = leaveStore.holidayLists.find(l => l.name === formData.value.holiday_list);
  if (selected && selected.from_date) {
    formData.value.from_date = selected.from_date;
  }
};

const onHolidayListSaved = async (savedFormData) => {
  await leaveStore.fetchHolidayLists();
  if (savedFormData?.holiday_list_name) {
    const newList = leaveStore.holidayLists.find(l => l.holiday_list_name === savedFormData.holiday_list_name);
    if (newList) {
      formData.value.holiday_list = newList.name;
      onHolidayListChange();
    }
  }
  showCreateHolidayListModal.value = false;
};

const fetchDetails = async () => {
  try {
    const data = await call('arijentek_core.api.leave.get_holiday_list_assignment', {
      name: props.editId
    });
    if (data) {
      formData.value.holiday_list = data.holiday_list || '';
      formData.value.applicable_for = data.applicable_for || 'Employee';
      formData.value.assigned_to = data.assigned_to || '';
      formData.value.from_date = data.from_date || '';
    }
  } catch (err) {
    submitError.value = getErrorMessage(err, 'Failed to fetch holiday list assignment details');
  }
};

const validate = () => {
  errors.value = {};
  let isValid = true;

  if (!formData.value.holiday_list) {
    errors.value.holiday_list = 'Holiday List is mandatory';
    isValid = false;
  }
  if (!formData.value.applicable_for) {
    errors.value.applicable_for = 'Applicable For is mandatory';
    isValid = false;
  }
  if (!formData.value.assigned_to) {
    errors.value.assigned_to = 'Assigned To is mandatory';
    isValid = false;
  }
  if (!formData.value.from_date) {
    errors.value.from_date = 'From Date is mandatory';
    isValid = false;
  }

  return isValid;
};

const handleSave = async () => {
  submitError.value = '';
  if (validate()) {
    submitting.value = true;
    try {
      const res = await call('arijentek_core.api.leave.save_holiday_list_assignment', {
        ...formData.value,
        name: props.editId || undefined
      });
      if (res && res.success === false) {
        throw new Error(res.error);
      }
      emit('save', formData.value);
      show.value = false;
    } catch (err) {
      submitError.value = getErrorMessage(err, 'Failed to save holiday list assignment');
    } finally {
      submitting.value = false;
    }
  }
};
</script>
