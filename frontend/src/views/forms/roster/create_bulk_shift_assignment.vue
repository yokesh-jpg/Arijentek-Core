<template>
  <Teleport to="body">
    <div v-if="modelValue" class="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="close"></div>
      <div class="modal-panel relative max-w-4xl">
        <header class="modal-header">
          <div class="min-w-0">
            <h3 class="modal-title">Assign shifts in bulk</h3>
            <p class="text-[12px] text-[#656A72] dark:text-white/60">Set the shift on the left, then pick who it applies to.</p>
          </div>
          <button type="button" @click="close" class="btn-icon-ghost shrink-0" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span></button>
        </header>

        <div v-if="bulkAssignConflict || rosterStore.bulkAssignError" class="mx-5 mt-4 flex items-start gap-2.5 p-3.5 rounded-[12px] bg-red-500/[0.07] border border-red-500/20">
          <span class="material-symbols-outlined !text-[18px] text-red-600 dark:text-red-400 shrink-0">error</span>
          <p class="text-[13px] text-red-700 dark:text-red-400">{{ bulkAssignConflict || rosterStore.bulkAssignError }}</p>
        </div>

        <div class="flex flex-col md:flex-row flex-1 min-h-0 overflow-hidden">
          <!-- The shift being assigned. The tinted column it sat in was a second
               surface inside the dialog; a rule separates it from the list. -->
          <div class="w-full md:w-[320px] shrink-0 px-5 py-5 md:border-r border-b md:border-b-0 border-black/[0.06] dark:border-white/[0.08] overflow-y-auto">
            <div class="space-y-4">
              <div>
                <label class="field-label">Shift type <span class="text-red-600 dark:text-red-400">*</span></label>
                <div class="flex items-center gap-2">
                  <div class="flex-1 min-w-0">
                    <SearchableDropdown
                      v-model="bulkForm.shift_type"
                      :options="rosterStore.shiftTypes"
                      labelKey="name"
                      valueKey="name"
                      placeholder="Select shift type"
                    />
                  </div>
                  <button
                    v-if="canCreateShiftType"
                    @click.prevent="showCreateShiftTypeModal = true"
                    type="button"
                    class="btn-add-option"
                    title="Add a new shift type"
                    aria-label="Add a new shift type"
                  >
                    <span class="material-symbols-outlined !text-[18px]">add</span>
                  </button>
                </div>
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="field-label">From date <span class="text-red-600 dark:text-red-400">*</span></label>
                  <DateField v-model="bulkForm.start_date" />
                </div>
                <div>
                  <label class="field-label">To date</label>
                  <DateField v-model="bulkForm.end_date" :min="bulkForm.start_date" />
                </div>
              </div>
              <div>
                <label class="field-label">Shift location</label>
                <div class="flex items-center gap-2">
                  <div class="flex-1 min-w-0">
                    <SearchableDropdown
                      v-model="bulkForm.shift_location"
                      :options="rosterStore.shiftLocations"
                      labelKey="name"
                      valueKey="name"
                      :showAllOption="true"
                      allOptionLabel="None"
                      placeholder="None"
                    />
                  </div>
                  <button
                    v-if="canCreateShiftLocation"
                    @click.prevent="showCreateShiftLocationModal = true"
                    type="button"
                    class="btn-add-option"
                    title="Add a new shift location"
                    aria-label="Add a new shift location"
                  >
                    <span class="material-symbols-outlined !text-[18px]">add</span>
                  </button>
                </div>
              </div>

              <div class="modal-section">
                <label class="flex items-center gap-2 text-[13px] font-medium text-[#17181B] dark:text-white cursor-pointer select-none">
                  <input type="checkbox" v-model="bulkForm.schedule_enabled" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40" />
                  Repeat on a schedule
                </label>
                <div v-if="bulkForm.schedule_enabled" class="mt-4 space-y-4">
                  <p v-if="!bulkForm.start_date || !bulkForm.end_date || bulkForm.start_date === bulkForm.end_date" class="text-xs text-amber-800 dark:text-amber-300">
                    Set a To date that is later than the From date to repeat this shift.
                  </p>
                  <div :class="{ 'opacity-50 pointer-events-none': !bulkForm.start_date || !bulkForm.end_date || bulkForm.start_date === bulkForm.end_date }">
                    <label class="field-label">Repeat on</label>
                    <div class="flex flex-wrap gap-1.5">
                      <label
                        v-for="day in ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']"
                        :key="day"
                        class="relative cursor-pointer select-none"
                      >
                        <input type="checkbox" :value="day" v-model="bulkForm.repeat_on_days" class="peer sr-only" />
                        <span class="inline-flex items-center justify-center h-9 min-w-[40px] px-2 rounded-[12px] text-[13px] font-medium border border-black/[0.09] dark:border-white/[0.14] text-[#5C6169] dark:text-white/70 peer-checked:bg-accent peer-checked:border-accent peer-checked:text-white peer-focus-visible:ring-2 peer-focus-visible:ring-accent/40 transition-colors">{{ day.substring(0, 3) }}</span>
                      </label>
                    </div>
                  </div>
                  <div :class="{ 'opacity-50 pointer-events-none': !bulkForm.start_date || !bulkForm.end_date || bulkForm.start_date === bulkForm.end_date }">
                    <label class="field-label">Frequency</label>
                    <SearchableDropdown
                      v-model="bulkForm.frequency"
                      :options="rosterStore.frequencyOptions"
                      placeholder="Frequency"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Who it applies to. The filters belong with the list they narrow,
               not at the bottom of the shift settings. -->
          <div class="flex-1 min-w-0 flex flex-col min-h-[320px]">
            <div class="px-5 pt-4 pb-3 grid grid-cols-1 sm:grid-cols-2 gap-3 border-b border-black/[0.06] dark:border-white/[0.08]">
              <div class="relative">
                <span class="material-symbols-outlined !text-[18px] absolute left-3.5 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/60 pointer-events-none">search</span>
                <input type="text" v-model="bulkFilter.search" placeholder="Search employees" class="field-input !pl-10" aria-label="Search employees" />
              </div>
              <SearchableDropdown
                v-model="bulkFilter.department"
                :options="rosterStore.deptDesignationList.departments"
                :showAllOption="true"
                allOptionLabel="All departments"
                placeholder="All departments"
              />
            </div>
            <div class="flex-1 overflow-y-auto">
              <table class="w-full">
                <thead class="sticky top-0 z-[1]">
                  <tr class="bg-white dark:bg-surface-1 border-b border-black/[0.07] dark:border-white/10">
                    <th class="table-th w-10"><input type="checkbox" :checked="isAllBulkSelected" @change="toggleAllBulk" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40" aria-label="Select all" /></th>
                    <th class="table-th">Employee</th>
                    <th class="table-th">Department</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="emp in filteredBulkEmployees"
                    :key="emp.name"
                    class="cursor-pointer border-b last:border-0 border-black/[0.05] dark:border-white/[0.06] hover:bg-black/[0.02] dark:hover:bg-white/[0.04] transition-colors"
                    :class="selectedBulkEmployees.includes(emp.name) && 'bg-accent/[0.05]'"
                    @click="toggleBulkEmployee(emp.name)"
                  >
                    <td class="table-td"><input type="checkbox" :value="emp.name" v-model="selectedBulkEmployees" @click.stop class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40" :aria-label="'Select ' + emp.employee_name" /></td>
                    <td class="table-td-strong">{{ emp.employee_name }}</td>
                    <td class="table-td">{{ emp.department || '—' }}</td>
                  </tr>
                  <tr v-if="filteredBulkEmployees.length === 0">
                    <td colspan="3" class="py-12 text-center text-[13px] text-[#656A72] dark:text-white/55">No employees match these filters.</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <footer class="modal-footer justify-between">
          <p class="text-[12px] text-[#656A72] dark:text-white/60 tabular-nums">
            {{ selectedBulkEmployees.length }} of {{ filteredBulkEmployees.length }} selected
          </p>
          <div class="flex items-center gap-2">
            <button type="button" @click="close" class="btn-secondary">Cancel</button>
            <button type="button" @click="submit" :disabled="rosterStore.bulkAssignSubmitting || selectedBulkEmployees.length === 0 || !bulkForm.shift_type || !bulkForm.start_date" class="btn-primary">
              <span v-if="rosterStore.bulkAssignSubmitting" class="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></span>
              {{ selectedBulkEmployees.length ? `Assign to ${selectedBulkEmployees.length} ${selectedBulkEmployees.length === 1 ? 'person' : 'people'}` : 'Assign' }}
            </button>
          </div>
        </footer>
      </div>
    </div>

    <ShiftTypeForm
      v-if="showCreateShiftTypeModal"
      @close="showCreateShiftTypeModal = false"
      @saved="onShiftTypeSaved"
    />

    <ShiftLocationForm
      v-if="showCreateShiftLocationModal"
      @close="showCreateShiftLocationModal = false"
      @saved="onShiftLocationSaved"
    />
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { useRosterStore } from '@/stores/roster';
import { useEmployeeStore } from '@/stores/employee';
import SearchableDropdown from '@/components/SearchableDropdown.vue';
import DateField from '../../../components/DateField.vue';
import ShiftTypeForm from './shift_type.vue';
import ShiftLocationForm from './shift_location.vue';

const props = defineProps({
  modelValue: { type: Boolean, default: false }
});

const emit = defineEmits(['update:modelValue', 'success']);
const rosterStore = useRosterStore();

const bulkForm = ref({ shift_type: '', start_date: '', end_date: '', shift_location: '', schedule_enabled: false, repeat_on_days: [], frequency: 'Every Week' });
const bulkFilter = ref({ department: '', designation: '', search: '' });
const selectedBulkEmployees = ref([]);
const bulkAssignConflict    = ref('');

const canCreateShiftType = ref(false);
const canCreateShiftLocation = ref(false);
const showCreateShiftTypeModal = ref(false);
const showCreateShiftLocationModal = ref(false);

async function checkPermissions() {
  try {
    const [canType, canLoc] = await Promise.all([
      rosterStore.checkCanCreateShiftType(),
      rosterStore.checkCanCreateShiftLocation(),
    ]);
    canCreateShiftType.value = !!canType;
    canCreateShiftLocation.value = !!canLoc;
  } catch (err) {
    console.error('Failed to check shift permissions:', err);
    canCreateShiftType.value = false;
    canCreateShiftLocation.value = false;
  }
}

async function onShiftTypeSaved(newShiftName) {
  await rosterStore.fetchShiftTypes();
  if (newShiftName) {
    bulkForm.value.shift_type = newShiftName;
  }
  showCreateShiftTypeModal.value = false;
}

async function onShiftLocationSaved(newLocationName) {
  await rosterStore.fetchShiftLocations();
  if (newLocationName) {
    bulkForm.value.shift_location = newLocationName;
  }
  showCreateShiftLocationModal.value = false;
}

watch(() => props.modelValue, (val) => {
  if (val) {
    bulkForm.value    = { shift_type: '', start_date: '', end_date: '', shift_location: '', schedule_enabled: false, repeat_on_days: [], frequency: 'Every Week' };
    bulkFilter.value  = { department: '', designation: '', search: '' };
    selectedBulkEmployees.value = [];
    bulkAssignConflict.value    = '';
    if (rosterStore.shiftTypes.length === 0) rosterStore.fetchShiftTypes();
    if (rosterStore.addRosterEmployees.length === 0) rosterStore.fetchAddRosterEmployees();
    if (rosterStore.shiftLocations.length === 0) rosterStore.fetchShiftLocations();
    if (rosterStore.frequencyOptions.length === 0) rosterStore.fetchFrequencyOptions();
    checkPermissions();
  }
});

function close() { emit('update:modelValue', false); }

const filteredBulkEmployees = computed(() => {
  let list = rosterStore.addRosterEmployees;
  if (bulkFilter.value.department) list = list.filter(e => e.department === bulkFilter.value.department);
  if (bulkFilter.value.designation) list = list.filter(e => e.designation === bulkFilter.value.designation);
  if (bulkFilter.value.search) { const s = bulkFilter.value.search.toLowerCase(); list = list.filter(e => e.employee_name.toLowerCase().includes(s)); }
  return list;
});

const isAllBulkSelected = computed(() => filteredBulkEmployees.value.length > 0 && filteredBulkEmployees.value.every(e => selectedBulkEmployees.value.includes(e.name)));

function toggleAllBulk(e) {
  if (e.target.checked) { 
    const n = [...selectedBulkEmployees.value]; 
    filteredBulkEmployees.value.forEach(emp => { if (!n.includes(emp.name)) n.push(emp.name); }); 
    selectedBulkEmployees.value = n; 
  } else { 
    const ids = filteredBulkEmployees.value.map(e => e.name); 
    selectedBulkEmployees.value = selectedBulkEmployees.value.filter(id => !ids.includes(id)); 
  }
}

function toggleBulkEmployee(empId) {
  const idx = selectedBulkEmployees.value.indexOf(empId);
  if (idx === -1) selectedBulkEmployees.value.push(empId);
  else selectedBulkEmployees.value.splice(idx, 1);
}

async function submit() {
  bulkAssignConflict.value = '';
  if (selectedBulkEmployees.value.length === 0) return;

  if (bulkForm.value.start_date && bulkForm.value.end_date && bulkForm.value.end_date < bulkForm.value.start_date) {
    bulkAssignConflict.value = 'To date cannot be earlier than From date.';
    return;
  }

  if (bulkForm.value.schedule_enabled && (!bulkForm.value.start_date || !bulkForm.value.end_date || bulkForm.value.start_date === bulkForm.value.end_date)) {
    bulkAssignConflict.value = 'From date and To date are needed, and To date must not be the same as From date for scheduling.';
    return;
  }

  const conflictRes = await rosterStore.checkShiftConflict(selectedBulkEmployees.value, bulkForm.value.start_date, bulkForm.value.end_date || bulkForm.value.start_date, null, false, []);
  if (conflictRes?.has_conflict) { bulkAssignConflict.value = conflictRes.message; return; }
  const success = await rosterStore.submitBulkAssign(
    selectedBulkEmployees.value, 
    bulkForm.value.shift_type, 
    bulkForm.value.start_date, 
    bulkForm.value.end_date || bulkForm.value.start_date, 
    bulkForm.value.shift_location, 
    bulkForm.value.schedule_enabled, 
    bulkForm.value.repeat_on_days, 
    bulkForm.value.frequency
  );
  if (success) {
    if (rosterStore.bulkAssignResult?.failed?.length > 0) {
      bulkAssignConflict.value = `Failed to assign ${rosterStore.bulkAssignResult.failed.length} shifts: ${rosterStore.bulkAssignResult.failed.map(f => f.message).join(' | ')}`;
    } else { 
      emit('success');
      close(); 
    }
  }
}
</script>
