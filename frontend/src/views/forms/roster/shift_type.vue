<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-[110] flex items-center justify-center p-4">
    <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="$emit('close')"></div>
    <div class="modal-panel relative max-w-sm">
      <header class="modal-header">
        <h3 class="modal-title">{{ isEditing ? 'Edit shift type' : 'Add shift type' }}</h3>
        <button type="button" @click="$emit('close')" class="btn-icon-ghost shrink-0" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span></button>
      </header>
      <div class="flex-1 overflow-y-auto px-6 py-5">
      <div class="space-y-4">
        <div>
          <label class="field-label">Shift name <span class="text-red-600 dark:text-red-400">*</span></label>
          <input
            type="text"
            v-model="shiftName"
            placeholder="e.g. Morning Shift"
            class="field-input"
          />
        </div>
        
        <div class="flex gap-4">
          <div class="flex-1">
            <label class="field-label">Start time <span class="text-red-600 dark:text-red-400">*</span></label>
            <TimeField v-model="startTime" />
          </div>
          
          <div class="flex-1">
            <label class="field-label">End time <span class="text-red-600 dark:text-red-400">*</span></label>
            <TimeField v-model="endTime" />
          </div>
        </div>
      </div>

      <div v-if="error" class="mt-4 flex items-start gap-2.5 p-3.5 rounded-[12px] bg-red-500/[0.07] border border-red-500/20">
        <span class="material-symbols-outlined !text-[18px] text-red-600 dark:text-red-400 shrink-0">error</span>
        <p class="text-[13px] text-red-700 dark:text-red-400">{{ error }}</p>
      </div>
      </div>

      <footer class="modal-footer justify-end">
        <button type="button" @click="$emit('close')" :disabled="isSubmitting" class="btn-secondary">Cancel</button>
        <button type="button" @click="saveShiftType" :disabled="!shiftName || !startTime || !endTime || isSubmitting" class="btn-primary">
          <span v-if="isSubmitting" class="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></span>
          {{ isSubmitting ? 'Saving…' : 'Save' }}
        </button>
      </footer>
    </div>
  </div>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue';
import { createResource } from 'frappe-ui';
import { getErrorMessage } from '../../../utils.js';

const props = defineProps({
  editingShift: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['close', 'saved']);

const isEditing = computed(() => !!props.editingShift);
const originalName = ref('');
const shiftName = ref('');
const startTime = ref('');
const endTime = ref('');
const error = ref('');
const isSubmitting = ref(false);

import { onMounted, computed } from 'vue';
import TimeField from '../../../components/TimeField.vue'

onMounted(() => {
  if (props.editingShift) {
    originalName.value = props.editingShift.name || '';
    shiftName.value = props.editingShift.name || '';
    startTime.value = props.editingShift.start_time || '';
    endTime.value = props.editingShift.end_time || '';
  }
});

const saveResource = createResource({
  url: "arijentek_core.api.roster.save_shift_type",
  auto: false
});

const editResource = createResource({
  url: "arijentek_core.api.roster.edit_shift_type",
  auto: false
});

async function saveShiftType() {
  error.value = '';
  isSubmitting.value = true;
  
  try {
    let res;
    if (isEditing.value) {
      res = await editResource.submit({
        original_name: originalName.value,
        shift_name: shiftName.value,
        start_time: startTime.value.length === 5 ? `${startTime.value}:00` : startTime.value,
        end_time: endTime.value.length === 5 ? `${endTime.value}:00` : endTime.value
      });
    } else {
      res = await saveResource.submit({
        shift_name: shiftName.value,
        start_time: startTime.value.length === 5 ? `${startTime.value}:00` : startTime.value,
        end_time: endTime.value.length === 5 ? `${endTime.value}:00` : endTime.value
      });
    }
    
    // Frappe sometimes returns error in res object without throwing
    if (res && res.exc) {
       throw new Error("Failed to save shift type.");
    }
    
    emit('saved', shiftName.value);
  } catch (err) {
    error.value = getErrorMessage(err, "Failed to save shift type.");
  } finally {
    isSubmitting.value = false;
  }
}
</script>
