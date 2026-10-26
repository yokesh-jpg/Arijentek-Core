<template>
  <Teleport to="body">
    <div v-if="modelValue" class="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="close"></div>
      <div class="modal-panel relative max-w-md">
        <header class="modal-header">
          <h3 class="modal-title">{{ formData.assignment_name ? 'Edit shift' : 'Assign a shift' }}</h3>
          <button type="button" @click="close" class="btn-icon-ghost shrink-0" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span></button>
        </header>

        <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
          <div>
            <label class="field-label">Employee</label>
            <SearchableDropdown
              v-if="rosterStore.addRosterEmployees && rosterStore.addRosterEmployees.length > 0"
              v-model="formData.empId"
              :options="rosterStore.addRosterEmployees"
              labelKey="employee_name"
              valueKey="name"
              placeholder="Select employee"
            />
            <p v-else class="field-static">{{ formData.empName || formData.empId }}</p>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="field-label">From date <span class="text-red-600 dark:text-red-400">*</span></label>
              <DateField v-model="formData.date" />
            </div>
            <div>
              <label class="field-label">To date</label>
              <DateField v-model="formData.endDate" :min="formData.date" />
            </div>
          </div>

          <div>
            <label class="field-label">Shift type <span class="text-red-600 dark:text-red-400">*</span></label>
            <SearchableDropdown
              v-model="formData.shiftType"
              :options="rosterStore.shiftTypes"
              labelKey="name"
              valueKey="name"
              placeholder="Select shift"
            />
          </div>

          <div>
            <label class="field-label">Shift location</label>
            <SearchableDropdown
              v-model="formData.shiftLocation"
              :options="rosterStore.shiftLocations"
              labelKey="name"
              valueKey="name"
              :showAllOption="true"
              allOptionLabel="None"
              placeholder="None"
            />
          </div>

          <!-- Repeating is a refinement of the dates above, so it sits under a
               rule rather than in a tinted box of its own. -->
          <div class="modal-section">
            <label class="flex items-center gap-2 text-[13px] font-medium text-[#17181B] dark:text-white cursor-pointer select-none">
              <input type="checkbox" v-model="formData.schedule_enabled" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40" />
              Repeat on a schedule
            </label>

            <div v-if="formData.schedule_enabled" class="mt-4 space-y-4">
              <p v-if="!formData.date || !formData.endDate || formData.date === formData.endDate" class="text-xs text-amber-800 dark:text-amber-300">
                Set a To date that is later than the From date to repeat this shift.
              </p>
              <div :class="{ 'opacity-50 pointer-events-none': !formData.date || !formData.endDate || formData.date === formData.endDate }">
                <label class="field-label">Repeat on</label>
                <div class="flex flex-wrap gap-1.5">
                  <label
                    v-for="day in ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']"
                    :key="day"
                    class="relative cursor-pointer select-none"
                  >
                    <input type="checkbox" :value="day" v-model="formData.repeat_on_days" class="peer sr-only" />
                    <span class="inline-flex items-center justify-center h-9 min-w-[44px] px-2 rounded-[12px] text-[13px] font-medium border border-black/[0.09] dark:border-white/[0.14] text-[#5C6169] dark:text-white/70 peer-checked:bg-accent peer-checked:border-accent peer-checked:text-white peer-focus-visible:ring-2 peer-focus-visible:ring-accent/40 transition-colors">{{ day.substring(0, 3) }}</span>
                  </label>
                </div>
              </div>
              <div :class="{ 'opacity-50 pointer-events-none': !formData.date || !formData.endDate || formData.date === formData.endDate }">
                <label class="field-label">Frequency</label>
                <SearchableDropdown
                  v-model="formData.frequency"
                  :options="rosterStore.frequencyOptions"
                  placeholder="Frequency"
                />
              </div>
            </div>
          </div>

          <div v-if="conflict" class="flex items-start gap-2.5 p-3.5 rounded-[12px] bg-red-500/[0.07] border border-red-500/20">
            <span class="material-symbols-outlined !text-[18px] text-red-600 dark:text-red-400 shrink-0">error</span>
            <p class="text-[13px] text-red-700 dark:text-red-400">{{ conflict }}</p>
          </div>
        </div>

        <footer class="modal-footer justify-end">
          <button type="button" @click="close" class="btn-secondary">Cancel</button>
          <button type="button" @click="submit" :disabled="submitting" class="btn-primary">
            <span v-if="submitting" class="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></span>
            {{ formData.assignment_name ? 'Save changes' : 'Assign shift' }}
          </button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue';
import { useRosterStore } from '@/stores/roster';
import SearchableDropdown from '@/components/SearchableDropdown.vue';
import DateField from '../../../components/DateField.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  initialData: { type: Object, default: () => ({}) }
});

const emit = defineEmits(['update:modelValue', 'success']);

const rosterStore = useRosterStore();

const formData = ref({ empId: '', empName: '', date: '', endDate: '', shiftType: '', shiftLocation: '', assignment_name: '', schedule_enabled: false, repeat_on_days: [], frequency: 'Every Week' });
const submitting = ref(false);
const conflict = ref('');

watch(() => props.modelValue, (val) => {
  if (val) {
    formData.value = {
      empId: '',
      empName: '',
      date: '',
      endDate: '',
      shiftType: '',
      shiftLocation: '',
      assignment_name: '',
      schedule_enabled: false,
      repeat_on_days: [],
      frequency: 'Every Week',
      ...props.initialData
    };
    conflict.value = '';
    if (rosterStore.shiftTypes.length === 0) rosterStore.fetchShiftTypes();
    if (rosterStore.shiftLocations.length === 0) rosterStore.fetchShiftLocations();
    if (rosterStore.frequencyOptions.length === 0) rosterStore.fetchFrequencyOptions();
  }
});

function close() {
  emit('update:modelValue', false);
}

async function submit() {
  conflict.value = '';

  if (!formData.value.empId) {
    conflict.value = 'Employee is mandatory';
    return;
  }
  if (!formData.value.date) {
    conflict.value = 'From Date is mandatory';
    return;
  }
  if (!formData.value.shiftType) {
    conflict.value = 'Shift Type is mandatory';
    return;
  }
  if (formData.value.date && formData.value.endDate && formData.value.endDate < formData.value.date) {
    conflict.value = 'To date cannot be earlier than From date';
    return;
  }

  submitting.value = true;
  try {
    if (formData.value.schedule_enabled && (!formData.value.date || !formData.value.endDate || formData.value.date === formData.value.endDate)) {
      conflict.value = 'From date and To date are needed, and To date must not be the same as From date for scheduling.';
      return;
    }

    const conflictRes = await rosterStore.checkShiftConflict([formData.value.empId], formData.value.date, formData.value.endDate || formData.value.date, formData.value.assignment_name, false, []);
    if (conflictRes?.has_conflict) { conflict.value = conflictRes.message; return; }
    
    const payload = { 
      employee: formData.value.empId, 
      shift_type: formData.value.shiftType, 
      start_date: formData.value.date, 
      end_date: formData.value.endDate || formData.value.date, 
      shift_location: formData.value.shiftLocation || null, 
      assignment_name: formData.value.assignment_name,
      schedule_enabled: formData.value.schedule_enabled,
      repeat_on_days: formData.value.repeat_on_days,
      frequency: formData.value.frequency
    };
    
    await rosterStore.submitAddRoster(payload);
    
    if (rosterStore.addRosterError) {
      conflict.value = rosterStore.addRosterError;
      return;
    }

    emit('success');
    close();
  } finally { 
    submitting.value = false; 
  }
}
</script>
