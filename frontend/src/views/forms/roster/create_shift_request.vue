<template>
  <Teleport to="body">
    <div v-if="modelValue" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/40 dark:bg-black/60 backdrop-blur-sm" @click="close"></div>
      <form @submit.prevent="handleSubmit" class="modal-panel relative max-w-md">
        <header class="modal-header">
          <h3 class="modal-title">{{ isEditing ? 'Edit shift request' : 'Request a shift change' }}</h3>
          <button type="button" @click="close" class="btn-icon-ghost shrink-0" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span></button>
        </header>
        <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
          <div v-if="(isShiftApprover || canAddRoster) && rosterStore.addRosterEmployees.length > 0">
            <label class="field-label">Employee <span class="text-red-500 dark:text-red-400">*</span></label>
            <SearchableDropdown 
              v-model="form.employee" 
              :options="rosterStore.addRosterEmployees" 
              labelKey="employee_name" 
              valueKey="name" 
              placeholder="Select employee" />
          </div>
          <div>
            <label class="field-label">Approver <span class="text-red-500 dark:text-red-400">*</span></label>
            <SearchableDropdown
              v-model="form.approver"
              :options="rosterStore.shiftApprovers"
              labelKey="employee_name"
              valueKey="user"
              placeholder="Select approver"
              :disabled="submitting || rosterStore.shiftApprovers.length === 0"
            />
          </div>
          <div>
            <label class="field-label">Shift type <span class="text-red-500 dark:text-red-400">*</span></label>
            <SearchableDropdown
              v-model="form.shift_type"
              :options="rosterStore.shiftTypes"
              labelKey="name"
              valueKey="name"
              placeholder="Select shift type"
              :disabled="submitting || rosterStore.shiftTypes.length === 0"
            />
          </div>
          <div>
            <label class="field-label">From date <span class="text-red-500 dark:text-red-400">*</span></label>
            <DateField v-model="form.from_date" :min="minDate" :disabled="submitting" />
          </div>
          <div>
            <label class="field-label">To date</label>
            <DateField v-model="form.to_date" :min="form.from_date || minDate" :disabled="submitting" />
            <p class="text-xs text-[#656A72] dark:text-white/55 mt-1.5">Leave empty for a single day.</p>
          </div>
          <div v-if="rosterStore.submissionError" class="flex items-start gap-2.5 p-3.5 rounded-[12px] bg-red-500/[0.07] border border-red-500/20">
            <span class="material-symbols-outlined !text-[18px] text-red-600 dark:text-red-400 shrink-0">error</span>
            <p class="text-[13px] text-red-700 dark:text-red-400">{{ rosterStore.submissionError }}</p>
          </div>
        </div>
        <footer class="modal-footer justify-end">
          <button type="button" @click="close" :disabled="submitting" class="btn-secondary">Cancel</button>
          <button type="submit" :disabled="!canSubmit || submitting" class="btn-primary">
            <span v-if="submitting" class="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></span>
            {{ submitting ? 'Submitting…' : (isEditing ? 'Save changes' : 'Send request') }}
          </button>
        </footer>
      </form>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { useRosterStore } from '@/stores/roster';
import { useEmployeeStore } from '@/stores/employee';
import SearchableDropdown from '@/components/SearchableDropdown.vue';
import DateField from '../../../components/DateField.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  editId: { type: String, default: null },
  isShiftApprover: { type: Boolean, default: false },
  canAddRoster: { type: Boolean, default: false },
  selectedEmployeeForNew: { type: String, default: '' },
  initialDate: { type: String, default: '' }
});

const emit = defineEmits(['update:modelValue', 'success']);

const rosterStore = useRosterStore();
const employeeStore = useEmployeeStore();
const submitting = ref(false);

const form = ref({ approver: '', employee: '', shift_type: '', from_date: '', to_date: '', shift_location: '' });
const today = new Date().toISOString().split('T')[0];
const minDate = computed(() => (props.initialDate && props.initialDate < today ? props.initialDate : today));

const canSubmit = computed(() => {
  const base = form.value.approver && (form.value.employee || employeeStore.employee?.name) && form.value.shift_type && form.value.from_date && !submitting.value;
  if (!base) return false;
  if (form.value.to_date && form.value.to_date < form.value.from_date) return false;
  return true;
});
const isEditing = computed(() => !!props.editId);

watch(() => form.value.from_date, (newFrom) => {
  if (newFrom && form.value.to_date && form.value.to_date < newFrom) {
    form.value.to_date = newFrom;
  }
});

function close() {
  emit('update:modelValue', false);
}

watch(() => props.initialDate, (newDate) => {
  if (props.modelValue && !props.editId && newDate) {
    form.value.from_date = newDate;
    form.value.to_date = newDate;
  }
});

watch(() => props.modelValue, async (val) => {
  if (val) {
    submitting.value = false;
    rosterStore.submissionError = '';
    
    // Load lists if they are empty
    if (rosterStore.shiftApprovers.length === 0) rosterStore.fetchShiftApprovers();
    if (rosterStore.shiftTypes.length === 0) rosterStore.fetchShiftTypes();
    if (rosterStore.shiftLocations.length === 0) rosterStore.fetchShiftLocations();

    if (props.editId) {
      const req = rosterStore.shiftRequests.find(r => r.name === props.editId);
      if (req) {
        form.value = {
          approver: req.approver || rosterStore.defaultShiftApprover || '',
          employee: req.employee || employeeStore.employee?.name || '',
          shift_type: req.shift_type,
          from_date: req.from_date,
          to_date: req.to_date || '',
          shift_location: req.shift_location || ''
        };
      }
    } else {
      const initDate = props.initialDate || '';
      form.value = {
        approver: rosterStore.defaultShiftApprover || '',
        employee: props.selectedEmployeeForNew || employeeStore.employee?.name || '',
        shift_type: '',
        from_date: initDate,
        to_date: initDate,
        shift_location: ''
      };
    }

    if (!form.value.approver) {
      await rosterStore.fetchApprover(employeeStore.employee?.name);
      if (rosterStore.defaultShiftApprover) {
        form.value.approver = rosterStore.defaultShiftApprover;
      }
    }
  }
});

async function handleSubmit() {
  if (!canSubmit.value) return;
  submitting.value = true;
  try {
    await rosterStore.submitRequest({
      approver: form.value.approver,
      employee: form.value.employee || employeeStore.employee?.name,
      shift_type: form.value.shift_type,
      from_date: form.value.from_date,
      to_date: form.value.to_date || form.value.from_date,
      shift_location: form.value.shift_location || undefined
    });
    emit('success');
  } finally {
    submitting.value = false;
  }
}
</script>
