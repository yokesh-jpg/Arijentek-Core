<template>
  <Dialog :options="{ size: '3xl' }" v-model="show">
    <template #body>
      <div class="modal-panel">
        <header class="modal-header">
          <div>
            <h3 class="modal-title truncate">Holiday list details</h3>
            <p class="text-[12px] text-[#656A72] dark:text-white/60 truncate tabular-nums">
              {{ holidayList?.holiday_list_name || holidayList?.name || holidayListId }}
            </p>
          </div>
          <div class="flex items-center gap-1 shrink-0">
          <button v-if="holidayList && canEdit" class="btn-icon-ghost" aria-label="Edit" title="Edit" @click="$emit('edit', holidayList)"><span class="material-symbols-outlined !text-[18px]">edit</span></button>
          <button v-if="holidayList && canDelete" class="btn-danger-ghost" aria-label="Delete" title="Delete" @click="$emit('delete', holidayList)"><span class="material-symbols-outlined !text-[18px]">delete</span></button>
          <button @click="show = false" class="btn-icon-ghost shrink-0" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span></button>
        </div>
        </header>

        <div class="flex-1 overflow-y-auto px-6 py-5 flex flex-col gap-6">
          <div v-if="loading" class="flex justify-center py-12">
            <span class="w-5 h-5 rounded-full border-2 border-black/10 dark:border-white/15 border-t-accent animate-spin"></span>
          </div>
          
          <div v-else-if="error" class="text-[13px] text-red-600 dark:text-red-400 text-center py-6">
            {{ error }}
          </div>

          <div v-else-if="holidayList" class="space-y-6">
            <!-- Summary Cards -->
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-x-6 gap-y-4">
              <div>
                <p class="status-label">From date</p>
                <p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ formatDate(holidayList.from_date) }}</p>
              </div>
              <div>
                <p class="status-label">To date</p>
                <p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ formatDate(holidayList.to_date) }}</p>
              </div>
              <div>
                <p class="status-label">Total holidays</p>
                <p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ holidayList.total_holidays || holidayList.holidays?.length || 0 }}</p>
              </div>
            </div>

            <!-- Holidays Table -->
            <div class="table-card !rounded-[12px]">
              <div class="pb-2.5">
                <p class="status-label">Holidays</p>
              </div>
              <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse">
                  <thead>
                    <tr>
                      <th class="table-th">#</th>
                      <th class="table-th">Date</th>
                      <th class="table-th">Description</th>
                      <th class="!text-center table-th">Type</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(holiday, index) in sortedHolidays" :key="index" class="border-b last:border-0 border-black/[0.05] dark:border-white/[0.06]">
                      <td class="table-td">{{ index + 1 }}</td>
                      <td class="table-td">
                        <p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ formatDate(holiday.holiday_date) }}</p>
                        <p class="text-xs font-medium text-gray-600 dark:text-white/80">{{ getDayOfWeek(holiday.holiday_date) }}</p>
                      </td>
                      <td class="table-td">
                        {{ holiday.description }}
                      </td>
                      <td class="!text-center table-td">
                        <span v-if="holiday.is_half_day" class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold tag-accent">Half day</span>
                        <span v-else class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold tag-neutral">Full day</span>
                      </td>
                    </tr>
                    <tr v-if="!sortedHolidays || sortedHolidays.length === 0">
                      <td colspan="4" class="px-6 py-12 text-center text-sm font-medium text-gray-600 dark:text-white/80">
                        No holidays defined in this list.
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      	<footer class="px-5 py-4 border-t border-black/[0.07] dark:border-white/10 shrink-0">
					<button class="btn-secondary w-full" @click="show = false">Close</button>
				</footer>
			</div>
    </template>
  </Dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { Dialog, call } from 'frappe-ui';
import { getErrorMessage } from '@/utils.js';

const props = defineProps({
  /* Passed down by the list so the dialog offers the same actions as its row. */
  canEdit: { type: Boolean, default: false },
  canDelete: { type: Boolean, default: false },
  modelValue: { type: Boolean, default: false },
  holidayListId: { type: String, default: '' }
});

const emit = defineEmits(['update:modelValue', 'delete', 'edit']);

const show = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
});

const holidayList = ref(null);
const loading = ref(true);
const error = ref('');

const fetchHolidayListDetails = async () => {
  if (!props.holidayListId) {
    error.value = "No Holiday List ID provided.";
    loading.value = false;
    return;
  }
  
  loading.value = true;
  error.value = '';
  
  try {
    const data = await call('arijentek_core.api.leave.get_holiday_list', {
      name: props.holidayListId
    });
    
    if (data) {
      holidayList.value = data;
    } else {
      error.value = "Holiday List not found.";
    }
  } catch (err) {
    error.value = getErrorMessage(err, "Failed to fetch holiday list details.");
  } finally {
    loading.value = false;
  }
};

watch(show, (newVal) => {
  if (newVal && props.holidayListId) {
    fetchHolidayListDetails();
  } else {
    holidayList.value = null;
    error.value = '';
  }
});

const sortedHolidays = computed(() => {
  if (!holidayList.value?.holidays) return [];
  return [...holidayList.value.holidays].sort((a, b) => new Date(a.holiday_date) - new Date(b.holiday_date));
});

const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
};

const getDayOfWeek = (dateStr) => {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleDateString("en-US", {
    weekday: "long"
  });
};
</script>
