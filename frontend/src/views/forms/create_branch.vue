<template>
  <Dialog :options="{ size: 'md' }" v-model="show">
    <template #body>
      <div class="modal-panel">
        <!-- Custom Header -->
        <header class="modal-header">
          <div>
            <h3 class="modal-title">{{ editId ? 'Edit branch' : 'Add new branch' }}</h3>
            <p class="text-[12px] text-[#656A72] dark:text-white/60">{{ editId ? editId : 'Fill in the branch details below' }}</p>
          </div>
          <button @click="show = false" class="btn-icon-ghost shrink-0" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span>
          </button>
        </header>

        <!-- Main Content -->
        <div class="flex-1 px-5 py-5 overflow-y-auto flex flex-col gap-5">
        <div class="flex flex-col gap-1.5">
          <label class="field-label">Branch name <span class="text-red-500 dark:text-red-400">*</span></label>
          <input v-model="formData.branch_name" type="text" class="field-input" placeholder="e.g. Headquarters">
          <p v-if="errors.branch_name" class="field-error">{{ errors.branch_name }}</p>
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
            {{ submitting ? 'Saving…' : 'Save branch' }}
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
  branch_name: ''
});

const formData = ref(getInitialFormData());

watch(show, async (newVal) => {
  if (newVal) {
    formData.value = getInitialFormData();
    errors.value = {};
    submitError.value = '';
    if (props.editId) {
      await fetchBranchDetails();
    }
  }
});

const fetchBranchDetails = async () => {
  try {
    const data = await call('arijentek_core.api.teams_permissons.get_branch_list', {
      branch_id: props.editId
    });
    if (data) {
      formData.value = {
        name: data.name,
        branch_name: data.branch_name
      };
    }
  } catch (err) {
    submitError.value = getErrorMessage(err, 'Failed to fetch branch details');
  }
};

const errors = ref({});
const submitError = ref('');
const submitting = ref(false);

const validate = () => {
  errors.value = {};
  let isValid = true;

  if (!formData.value.branch_name) {
    errors.value.branch_name = 'Branch Name is mandatory';
    isValid = false;
  }

  return isValid;
};

const handleSave = async () => {
  submitError.value = '';
  if (validate()) {
    submitting.value = true;
    try {
      await call('arijentek_core.api.teams_permissons.save_branch', { branch_data: formData.value });
      emit('save', formData.value);
      show.value = false;
    } catch (err) {
      submitError.value = getErrorMessage(err, 'Failed to save branch');
    } finally {
      submitting.value = false;
    }
  }
};
</script>
