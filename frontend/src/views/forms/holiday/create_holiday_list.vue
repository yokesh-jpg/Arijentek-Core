<template>
  <Dialog :options="{ size: '3xl' }" v-model="show">
    <template #body>
      <div class="modal-panel !max-h-[88vh]">
        <div class="modal-header">
          <div class="min-w-0">
            <h3 class="modal-title">{{ editId ? 'Edit holiday list' : 'New holiday list' }}</h3>
            <p class="text-xs text-[#5C6169] dark:text-white/60 mt-0.5 truncate">
              {{ editId || 'The non-working days a roster is measured against.' }}
            </p>
          </div>
          <button @click="show = false" class="modal-close" aria-label="Close">
            <span class="material-symbols-outlined !text-[20px]">close</span>
          </button>
        </div>

        <div class="modal-body !space-y-5">
          <div>
            <label class="field-label" for="hl-name">List name <span class="text-red-500 dark:text-red-400">*</span></label>
            <input id="hl-name" v-model="formData.holiday_list_name" type="text" class="field-input" placeholder="e.g. Zevar Retail 2026" />
            <p v-if="errors.holiday_list_name" class="field-error">{{ errors.holiday_list_name }}</p>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="field-label" for="hl-from">From <span class="text-red-500 dark:text-red-400">*</span></label>
              <DateField v-model="formData.from_date" id="hl-from" @change="onFromDateChange" />
              <p v-if="errors.from_date" class="field-error">{{ errors.from_date }}</p>
            </div>
            <div>
              <label class="field-label" for="hl-to">To <span class="text-red-500 dark:text-red-400">*</span></label>
              <DateField v-model="formData.to_date" id="hl-to" :min="formData.from_date" />
              <p v-if="errors.to_date" class="field-error">{{ errors.to_date }}</p>
            </div>
          </div>

          <!-- ===== The two bulk fillers =====
               Both only add rows to the table below, so they sit together in
               one quiet panel above it rather than as two full-width sections
               that read like separate forms. -->
          <div class="rounded-[14px] border border-black/[0.07] dark:border-white/[0.09] bg-black/[0.02] dark:bg-white/[0.03] p-4 space-y-4">
            <p class="text-[13px] font-medium text-[#17181B] dark:text-white">Fill the list</p>

            <div class="grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-3 items-end">
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label class="field-label">Repeat a weekday</label>
                  <SearchableDropdown v-model="weeklyDay" :options="weekDays" placeholder="Select a day" />
                </div>
                <label class="flex items-center gap-2 h-9 sm:self-end cursor-pointer">
                  <input type="checkbox" v-model="weeklyIsHalfDay" class="w-4 h-4 rounded accent-accent" />
                  <span class="text-[13px] text-[#4A4D55] dark:text-white/60">Half day</span>
                </label>
              </div>
              <button @click="addWeeklyHolidays" class="btn-secondary shrink-0" :disabled="isAddWeeklyDisabled">
                <span class="material-symbols-outlined !text-[18px]">add</span>
                Add
              </button>
            </div>

            <div class="h-px bg-black/[0.06] dark:bg-white/[0.08]"></div>

            <div class="grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-3 items-end">
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label class="field-label">Public holidays for</label>
                  <SearchableDropdown v-model="selectedCountry" :options="countries" placeholder="Select a country" />
                </div>
                <div v-if="subdivisions.length > 0">
                  <label class="field-label">State or region</label>
                  <SearchableDropdown
                    v-model="selectedSubdivision"
                    :options="subdivisions"
                    placeholder="Select a subdivision"
                    :showAllOption="true"
                    allOptionLabel="All subdivisions"
                  />
                </div>
              </div>
              <button @click="fetchRegionalHolidays" class="btn-secondary shrink-0" :disabled="!selectedCountry || !formData.from_date || !formData.to_date || fetchingRegional">
                <span v-if="fetchingRegional" class="material-symbols-outlined !text-[18px] animate-spin">progress_activity</span>
                <span v-else class="material-symbols-outlined !text-[18px]">download</span>
                {{ fetchingRegional ? 'Fetching…' : 'Fetch' }}
              </button>
            </div>

            <p class="text-xs text-[#656A72] dark:text-white/55">Both need the dates above to be set first.</p>
          </div>

          <!-- ===== The list itself ===== -->
          <div class="space-y-2.5">
            <div class="flex items-center justify-between gap-3">
              <h4 class="text-[13px] font-semibold text-[#17181B] dark:text-white">
                Days off
                <span v-if="holidays.length" class="text-[#656A72] dark:text-white/55 tabular-nums font-normal">· {{ holidays.length }}</span>
              </h4>
              <div class="flex items-center gap-1">
                <button @click="addSingleHoliday" class="btn-ghost !text-accent dark:!text-accent-light hover:!bg-accent/[0.08]">
                  <span class="material-symbols-outlined !text-[16px]">add</span>
                  Add a day
                </button>
                <button v-if="holidays.length" @click="removeAllHolidays" class="btn-icon-ghost hover:text-red-500 dark:text-red-400" title="Remove every day" aria-label="Remove every day">
                  <span class="material-symbols-outlined !text-[18px]">delete_sweep</span>
                </button>
              </div>
            </div>

            <div v-if="holidays.length === 0" class="rounded-[14px] border border-dashed border-black/[0.12] dark:border-white/[0.14] py-8 px-5 text-center">
              <p class="text-[13px] text-[#5C6169] dark:text-white/60">No days yet. Repeat a weekday, fetch a country's public holidays, or add one by hand.</p>
            </div>

            <!-- Below sm, five columns of inputs cannot fit a 343px panel -
                 every row's controls landed outside it. So the phone gets one
                 card per day instead of a table row. -->
            <div v-else class="sm:hidden space-y-2">
              <div
                v-for="(h, i) in holidays"
                :key="'m' + i"
                class="rounded-[14px] border border-black/[0.07] dark:border-white/[0.09] bg-black/[0.02] dark:bg-white/[0.03] p-3 space-y-2"
              >
                <div class="flex items-center justify-between gap-2">
                  <span class="text-xs font-medium text-[#656A72] dark:text-white/55 tabular-nums">Day {{ i + 1 }}</span>
                  <button @click="removeHoliday(i)" class="btn-icon-ghost hover:text-red-500 dark:text-red-400" title="Remove" aria-label="Remove this day">
                    <span class="material-symbols-outlined !text-[18px]">delete</span>
                  </button>
                </div>
                <DateField v-model="h.date" aria-label="Holiday date" />
                <input v-model="h.description" type="text" class="field-input !h-10" placeholder="What it is" aria-label="Holiday description" />
                <label class="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" v-model="h.is_half_day" class="w-4 h-4 rounded accent-accent" />
                  <span class="text-[13px] text-[#4A4D55] dark:text-white/60">Half day</span>
                </label>
              </div>
            </div>

            <div v-if="holidays.length" class="table-card hidden sm:block">
              <table class="w-full border-collapse">
                <thead class="table-head">
                  <tr>
                    <th class="table-th w-10 text-right">#</th>
                    <th class="table-th">Date</th>
                    <th class="table-th">Description</th>
                    <th class="table-th text-center w-[72px]">Half day</th>
                    <th class="table-th w-[52px]"><span class="sr-only">Remove</span></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(h, i) in holidays" :key="i" class="table-row">
                    <td class="table-td text-right tabular-nums !px-2 text-[#656A72] dark:text-white/55">{{ i + 1 }}</td>
                    <td class="table-td !py-2">
                      <DateField v-model="h.date" aria-label="Holiday date" />
                    </td>
                    <td class="table-td !py-2">
                      <input v-model="h.description" type="text" class="field-input !h-9 !text-[13px]" placeholder="What it is" aria-label="Holiday description" />
                    </td>
                    <td class="table-td !py-2 text-center">
                      <input type="checkbox" v-model="h.is_half_day" class="w-4 h-4 rounded accent-accent" aria-label="Half day" />
                    </td>
                    <td class="table-td !py-2 !px-2 text-center">
                      <button @click="removeHoliday(i)" class="btn-icon-ghost hover:text-red-500 dark:text-red-400" title="Remove" aria-label="Remove this day">
                        <span class="material-symbols-outlined !text-[18px]">delete</span>
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <p v-if="submitError" class="field-error !text-[13px]" role="alert">{{ submitError }}</p>
        </div>

        <div class="modal-footer justify-end">
          <button class="btn-secondary" @click="show = false" :disabled="submitting">Cancel</button>
          <button class="btn-primary" @click="handleSave" :disabled="submitting">
            <span v-if="submitting" class="material-symbols-outlined !text-[18px] animate-spin">progress_activity</span>
            {{ submitting ? 'Saving…' : 'Save list' }}
          </button>
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { ask } from '@/utils/feedback.js'
import { ref, computed, watch, nextTick } from 'vue';
import { Dialog, call } from 'frappe-ui';
import { getErrorMessage } from '../../../utils.js';
import { useLeaveStore } from '../../../stores/leave.js';
import SearchableDropdown from '../../../components/SearchableDropdown.vue';
import DateField from '../../../components/DateField.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  editId: { type: String, default: '' }
});

const emit = defineEmits(['update:modelValue', 'save']);

const show = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
});

const weekDays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const weekDayMap = { Sunday: 0, Monday: 1, Tuesday: 2, Wednesday: 3, Thursday: 4, Friday: 5, Saturday: 6 };

/* Local calendar date. toISOString() converts to UTC first, so east of UTC it
   names the previous day - the generated weekly offs were landing a day early. */
const ymd = (d) => [d.getFullYear(), String(d.getMonth() + 1).padStart(2, '0'), String(d.getDate()).padStart(2, '0')].join('-');

const weeklyDay = ref('');
const weeklyIsHalfDay = ref(false);

const isAddWeeklyDisabled = computed(() => {
  return !weeklyDay.value || !formData.value.from_date || !formData.value.to_date;
});

const selectedCountry = ref('');
const selectedSubdivision = ref('');
const fetchingRegional = ref(false);

const leaveStore = useLeaveStore();
const countries = computed(() => leaveStore.countries);
const subdivisionsByCountry = computed(() => leaveStore.subdivisionsByCountry);

const subdivisions = computed(() => {
  return selectedCountry.value ? (subdivisionsByCountry.value[selectedCountry.value] || []) : [];
});

watch(selectedCountry, () => {
  selectedSubdivision.value = '';
});

const getInitialFormData = () => ({
  holiday_list_name: '',
  from_date: '',
  to_date: ''
});

const formData = ref(getInitialFormData());
const holidays = ref([]);
const errors = ref({});
const submitError = ref('');
const submitting = ref(false);

watch(show, async (newVal) => {
  if (newVal) {
    formData.value = getInitialFormData();
    holidays.value = [];
    weeklyDay.value = '';
    weeklyIsHalfDay.value = false;
    selectedCountry.value = '';
    selectedSubdivision.value = '';
    errors.value = {};
    submitError.value = '';
    if (countries.value.length === 0) {
      await leaveStore.fetchCountries();
    }
    if (props.editId) {
      await fetchDetails();
    }
  }
});

function calculateOneYearEnd(fromDateStr) {
  if (!fromDateStr) return '';
  const parts = fromDateStr.split('-').map(Number);
  if (parts.length !== 3 || parts.some(isNaN)) return '';
  const [year, month, day] = parts;
  
  // Create date locally to avoid UTC timezone shifts
  const d = new Date(year, month - 1, day);
  // Full year period ends on: start date + 1 year - 1 day
  d.setFullYear(d.getFullYear() + 1);
  d.setDate(d.getDate() - 1);
  
  return ymd(d);
}

const isLoadingDetails = ref(false);

const fetchDetails = async () => {
  isLoadingDetails.value = true;
  try {
    const data = await call('arijentek_core.api.leave.get_holiday_list', {
      name: props.editId
    });
    if (data) {
      formData.value.holiday_list_name = data.holiday_list_name || '';
      formData.value.from_date = data.from_date || '';
      formData.value.to_date = data.to_date || '';
      if (data.holidays) {
        holidays.value = data.holidays.map(h => ({
          date: h.holiday_date || h.date,
          description: h.description,
          is_half_day: h.is_half_day || false
        }));
      }
    }
    // The from_date watcher fires on the next tick (async), so wait for it
    // before clearing the guard — otherwise it overwrites to_date with the
    // computed one-year end after the server value has already been set.
    await nextTick();
  } catch (err) {
    submitError.value = getErrorMessage(err, 'Failed to fetch holiday list details');
  } finally {
    isLoadingDetails.value = false;
  }
};

const onFromDateChange = (val) => {
  const fromVal = val || formData.value.from_date;
  if (fromVal) {
    formData.value.to_date = calculateOneYearEnd(fromVal);
  }
};

watch(() => formData.value.from_date, (newFrom, oldFrom) => {
  if (isLoadingDetails.value) return;
  if (newFrom && newFrom !== oldFrom) {
    formData.value.to_date = calculateOneYearEnd(newFrom);
  }
});

const addSingleHoliday = () => {
  holidays.value.push({ date: '', description: '', is_half_day: false });
};

const removeHoliday = (index) => {
  holidays.value.splice(index, 1);
};

const removeAllHolidays = async () => {
  if (await ask('Are you sure you want to delete all holidays?')) {
    holidays.value = [];
  }
};

const addWeeklyHolidays = () => {
  if (!weeklyDay.value || !formData.value.from_date || !formData.value.to_date) return;

  const [fy, fm, fd] = formData.value.from_date.split('-').map(Number);
  const [ty, tm, td] = formData.value.to_date.split('-').map(Number);
  const from = new Date(fy, fm - 1, fd);
  const to = new Date(ty, tm - 1, td);
  const targetDay = weekDayMap[weeklyDay.value];
  const current = new Date(from);

  while (current <= to) {
    if (current.getDay() === targetDay) {
      const dateStr = ymd(current);
      const existing = holidays.value.some(h => h.date === dateStr);
      if (!existing) {
        holidays.value.push({
          date: dateStr,
          description: `${weeklyDay.value} - Weekly Holiday`,
          is_half_day: weeklyIsHalfDay.value
        });
      }
    }
    current.setDate(current.getDate() + 1);
  }

  holidays.value.sort((a, b) => a.date.localeCompare(b.date));
  weeklyDay.value = '';
  weeklyIsHalfDay.value = false;
};

const fetchRegionalHolidays = async () => {
  if (!selectedCountry.value || !formData.value.from_date || !formData.value.to_date) return;
  fetchingRegional.value = true;
  submitError.value = '';
  try {
    const data = await call('arijentek_core.api.leave.get_local_holidays', {
      country: selectedCountry.value,
      from_date: formData.value.from_date,
      to_date: formData.value.to_date,
      subdivision: selectedSubdivision.value || null
    });
    
    if (data && data.length > 0) {
      const newHolidays = [];
      data.forEach(h => {
        const existing = holidays.value.some(eh => eh.date === h.date);
        if (!existing) {
          newHolidays.push(h);
        }
      });
      holidays.value = [...holidays.value, ...newHolidays].sort((a, b) => a.date.localeCompare(b.date));
      if (newHolidays.length === 0) {
        submitError.value = 'No new holidays found for the selected country and date range';
      }
    } else {
      submitError.value = 'No holidays found for the selected country and date range';
    }
  } catch (err) {
    submitError.value = getErrorMessage(err, 'Failed to fetch regional holidays');
  } finally {
    fetchingRegional.value = false;
  }
};

const validate = () => {
  errors.value = {};
  let isValid = true;

  if (!formData.value.holiday_list_name) {
    errors.value.holiday_list_name = 'Holiday List Name is mandatory';
    isValid = false;
  }
  if (!formData.value.from_date) {
    errors.value.from_date = 'From Date is mandatory';
    isValid = false;
  }
  if (!formData.value.to_date) {
    errors.value.to_date = 'To Date is mandatory';
    isValid = false;
  }


  for (const h of holidays.value) {
    if (!h.date) {
      submitError.value = 'All holidays must have a date';
      isValid = false;
      break;
    }
    if (!h.description) {
      submitError.value = 'All holidays must have a description';
      isValid = false;
      break;
    }
  }

  return isValid;
};

const handleSave = async () => {
  submitError.value = '';
  if (validate()) {
    submitting.value = true;
    try {
      await call('arijentek_core.api.leave.save_holiday_list', {
        holiday_list_data: {
          name: props.editId || '',
          ...formData.value,
          holidays: holidays.value
        }
      });
      emit('save', formData.value);
      show.value = false;
    } catch (err) {
      submitError.value = getErrorMessage(err, 'Failed to save holiday list');
    } finally {
      submitting.value = false;
    }
  }
};
</script>
