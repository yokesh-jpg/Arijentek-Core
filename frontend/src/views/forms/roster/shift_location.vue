<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-[110] flex items-center justify-center p-4">
    <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="$emit('close')"></div>
    <div class="modal-panel relative max-w-sm">
      <header class="modal-header">
        <h3 class="modal-title">{{ isEditing ? 'Edit shift location' : 'Add shift location' }}</h3>
        <button type="button" @click="$emit('close')" class="btn-icon-ghost shrink-0" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span></button>
      </header>
      <div class="flex-1 overflow-y-auto px-6 py-5">
      <div class="">
        <label class="field-label">Location name <span class="text-red-600 dark:text-red-400">*</span></label>
        <input
          type="text"
          v-model="locationName"
          placeholder="e.g. Main Office"
          class="field-input"
          @keyup.enter="saveLocation"
        />
      </div>

      <div v-if="error" class="mt-4 flex items-start gap-2.5 p-3.5 rounded-[12px] bg-red-500/[0.07] border border-red-500/20">
        <span class="material-symbols-outlined !text-[18px] text-red-600 dark:text-red-400 shrink-0">error</span>
        <p class="text-[13px] text-red-700 dark:text-red-400">{{ error }}</p>
      </div>
      </div>

      <footer class="modal-footer justify-end">
        <button type="button" @click="$emit('close')" :disabled="isSubmitting" class="btn-secondary">Cancel</button>
        <button type="button" @click="saveLocation" :disabled="!locationName || isSubmitting" class="btn-primary">
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
  editingLocation: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['close', 'saved']);

import { computed, onMounted } from 'vue';

const isEditing = computed(() => !!props.editingLocation);
const originalName = ref('');
const locationName = ref('');
const isSubmitting = ref(false);
const error = ref('');

const saveLocationResource = createResource({
  url: "arijentek_core.api.roster.save_shift_location",
  auto: false,
});

const editLocationResource = createResource({
  url: "arijentek_core.api.roster.edit_shift_location",
  auto: false,
});

onMounted(() => {
  if (props.editingLocation) {
    originalName.value = props.editingLocation.name || props.editingLocation.location_name || '';
    locationName.value = props.editingLocation.location_name || props.editingLocation.name || '';
  }
});

const saveLocation = async () => {
  if (!locationName.value) return;
  
  isSubmitting.value = true;
  error.value = '';
  
  try {
    let res;
    if (isEditing.value) {
      res = await editLocationResource.submit({
        original_name: originalName.value,
        location_name: locationName.value
      });
    } else {
      res = await saveLocationResource.submit({
        location_name: locationName.value
      });
    }
    
    if (res && res.exc) {
       throw new Error("Failed to save location");
    }

    emit('saved', locationName.value);
  } catch (err) {
    error.value = getErrorMessage(err, "Failed to save location");
  } finally {
    isSubmitting.value = false;
  }
};
</script>
