<template>
  <Dialog :options="{ size: 'md' }" v-model="show">
    <template #body>
      <div class="modal-panel">
        <!-- Custom Header -->
        <header class="modal-header">
          <div>
            <h3 class="modal-title">{{ editId ? 'Edit employee grade' : 'Add new employee grade' }}</h3>
            <p class="text-[12px] text-[#656A72] dark:text-white/60">{{ editId ? editId : 'Fill in the employee grade details below' }}</p>
          </div>
          <button @click="show = false" class="btn-icon-ghost shrink-0" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span>
          </button>
        </header>

        <!-- Main Content -->
        <div class="flex-1 px-5 py-5 overflow-y-auto flex flex-col gap-5">
        <div class="flex flex-col gap-1.5">
          <label class="field-label">Employee grade name <span class="text-red-500 dark:text-red-400">*</span></label>
          <input v-model="formData.grade_name" type="text" class="field-input" placeholder="e.g. A1, Grade A">
          <p v-if="errors.grade_name" class="field-error">{{ errors.grade_name }}</p>
        </div>
        </div>
        
        <!-- Actions -->
        <div class="px-5 py-4 border-t border-black/[0.06] dark:border-white/[0.08] shrink-0">
          <p v-if="submitError" class="text-[13px] text-red-600 dark:text-red-400 mb-3">{{ submitError }}</p>
          <div class="flex justify-end gap-2">
            <button 
              class="btn-secondary" 
            @click="show = false"
            :disabled="submitting"
          >
            Cancel
          </button>
          <button 
            class="btn-primary" 
            @click="handleSave"
            :disabled="submitting"
          >
            <span v-if="submitting" class="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></span>
            {{ submitting ? 'Saving…' : 'Save grade' }}
          </button>
        </div>
      </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { Dialog, call } from 'frappe-ui';
import { getErrorMessage } from '../../utils.js';

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  editId: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['update:modelValue', 'save']);

const show = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
});

const getInitialFormData = () => ({
  grade_name: ''
});

const formData = ref(getInitialFormData());

watch(show, async (newVal) => {
  if (newVal) {
    formData.value = getInitialFormData();
    errors.value = {};
    submitError.value = '';
    if (props.editId) {
      await fetchGradeDetails();
    }
  }
});

const fetchGradeDetails = async () => {
  try {
    const data = await call('arijentek_core.api.teams_permissons.get_employee_grade_list', {
      grade_id: props.editId
    });
    if (data) {
      formData.value = {
        name: data.name,
        grade_name: data.grade_name
      };
    }
  } catch (err) {
    submitError.value = getErrorMessage(err, 'Failed to fetch employee grade details');
  }
};

const errors = ref({});
const submitError = ref('');
const submitting = ref(false);

const validate = () => {
  errors.value = {};
  let isValid = true;

  if (!formData.value.grade_name) {
    errors.value.grade_name = 'Employee Grade Name is mandatory';
    isValid = false;
  }

  return isValid;
};

const handleSave = async () => {
  submitError.value = '';
  if (validate()) {
    submitting.value = true;
    try {
      await call('arijentek_core.api.teams_permissons.save_employee_grade', { grade_data: formData.value });
      emit('save', formData.value);
      show.value = false;
    } catch (err) {
      submitError.value = getErrorMessage(err, 'Failed to save employee grade');
    } finally {
      submitting.value = false;
    }
  }
};
</script>
