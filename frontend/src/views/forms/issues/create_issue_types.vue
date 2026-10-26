<template>
  <Dialog :options="{ size: 'xl' }" v-model="show">
    <template #body>
      <div class="modal-panel">
        <!-- Custom Header -->
        <header class="modal-header">
          <div class="flex items-center gap-3">
            <div>
              <h3 class="modal-title">
                {{ isEdit ? 'Edit issue type' : 'Create issue type' }}
              </h3>
              <p class="text-[12px] text-[#656A72] dark:text-white/60">
                Define a category for employee issues.
              </p>
            </div>
          </div>
          <button @click="show = false" class="btn-icon-ghost shrink-0" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span>
          </button>
        </header>

        <!-- Form Body -->
        <div class="px-5 py-5 overflow-y-auto space-y-6 flex-1">
          <!-- Submit Error message -->
          <div v-if="submitError" class="p-4 bg-red-50 border border-red-100 rounded-[12px] flex items-start gap-3">
            <span class="material-symbols-outlined text-red-500 dark:text-red-400 text-lg shrink-0">error</span>
            <div class="text-xs font-medium text-red-700 dark:text-red-400 leading-relaxed">{{ submitError }}</div>
          </div>

          <!-- Core Form Section -->
          <div class="modal-section space-y-4">
            <!-- Name Input -->
            <div class="flex flex-col gap-2">
              <label class="field-label">
                Name <span class="text-red-500 dark:text-red-400">*</span>
              </label>
              <input 
                v-model="formData.name" 
                type="text"
                placeholder="e.g. Workplace Safety"
                class="field-input"
                :class="{ 'border-red-400 focus:border-red-500 focus:ring-red-500/20': errors.name }"
              />
              <p v-if="errors.name" class="field-error">
                <span class="material-symbols-outlined text-sm">error</span>
                {{ errors.name }}
              </p>
            </div>

            <!-- Description Textarea -->
            <div class="flex flex-col gap-2">
              <label class="field-label">
                Description
              </label>
              <textarea 
                v-model="formData.description" 
                rows="4"
                placeholder="Briefly describe this issue type..."
                class="field-input"
              ></textarea>
            </div>
          </div>
        </div>

        <!-- Footer Actions -->
        <footer class="modal-footer justify-end">
          <button @click="show = false" class="btn-secondary">Cancel</button>
          <button 
            @click="submitForm" 
            :disabled="submitting || !formData.name || loadingData" 
            class="btn-primary"
          >
            <span v-if="submitting || loadingData" class="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></span>
            {{ isEdit ? 'Save changes' : 'Add issue type' }}
          </button>
        </footer>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue';
import { Dialog, call } from 'frappe-ui';
import { getErrorMessage } from '@/utils';

const show = defineModel();
const emit = defineEmits(['save']);

const props = defineProps({
  editData: {
    type: Object,
    default: null
  }
});

const submitting = ref(false);
const loadingData = ref(false);
const submitError = ref('');
const formData = ref({ name: '', description: '', original_name: '' });
const errors = ref({});

const isEdit = computed(() => !!props.editData);

watch(show, async (newVal) => {
  if (newVal) {
    submitError.value = '';
    errors.value = {};
    if (props.editData && props.editData.name) {
      loadingData.value = true;
      try {
        const res = await call('arijentek_core.api.issues.get_issues_types', { id: props.editData.name });
        if (res && res.length > 0) {
          formData.value = { 
            name: res[0].name || '', 
            description: res[0].description || '',
            original_name: res[0].name || ''
          };
        }
      } catch (err) {
        console.error("Failed to fetch grievance type details", err);
        submitError.value = getErrorMessage(err, "Failed to load record details.");
      } finally {
        loadingData.value = false;
      }
    } else {
      formData.value = { name: '', description: '', original_name: '' };
    }
  }
});

function validate() {
  errors.value = {};
  let isValid = true;
  if (!formData.value.name.trim()) {
    errors.value.name = 'Name is required';
    isValid = false;
  }
  return isValid;
}

async function submitForm() {
  submitError.value = '';
  if (!validate()) return;

  submitting.value = true;
  try {
    await call('arijentek_core.api.issues.save_issue_type', { doc: formData.value });
    emit('save');
    show.value = false;
  } catch (err) {
    console.error(err);
    submitError.value = getErrorMessage(err, 'Failed to save issue type');
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
</style>
