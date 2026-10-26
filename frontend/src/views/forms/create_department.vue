<template>
  <Dialog :options="{ size: '2xl' }" v-model="show">
    <template #body>
      <div class="modal-panel">
        <!-- Custom Header -->
        <header class="modal-header">
          <div>
            <h3 class="modal-title">{{ editId ? 'Edit department' : 'Add new department' }}</h3>
            <p class="text-[12px] text-[#656A72] dark:text-white/60">{{ editId ? editId : 'Fill in the department details below' }}</p>
          </div>
          <button @click="show = false" class="btn-icon-ghost shrink-0" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span>
          </button>
        </header>

        <!-- Main Content -->
        <div class="flex-1 px-5 py-5 overflow-y-auto flex flex-col gap-5">
        <div class="flex flex-col gap-4">
          <div class="flex flex-col gap-1.5">
            <label class="field-label">Department name <span class="text-red-500 dark:text-red-400">*</span></label>
            <input v-model="formData.department_name" type="text" class="field-input">
            <p v-if="errors.department_name" class="field-error">{{ errors.department_name }}</p>
          </div>
          
          <p class="status-label pt-5 border-t border-black/[0.07] dark:border-white/10">Approvers</p>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="field-label">Expense approver</label>
              <SearchableDropdown v-model="formData.expense_approver" :options="teamStore.usersListResource?.data || []" placeholder="Select expense approver" />
            </div>
            
            <div class="flex flex-col gap-1.5">
              <label class="field-label">Shift approver</label>
              <SearchableDropdown v-model="formData.shift_approver" :options="teamStore.usersListResource?.data || []" placeholder="Select shift approver" />
            </div>
            
            <div class="flex flex-col gap-1.5">
              <label class="field-label">Leave approver</label>
              <SearchableDropdown v-model="formData.leave_approver" :options="teamStore.usersListResource?.data || []" placeholder="Select leave approver" />
            </div>
          </div>
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
              {{ submitting ? 'Saving…' : 'Save department' }}
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
import SearchableDropdown from '../../components/SearchableDropdown.vue';
import { useTeamStore } from '../../stores/team';
import { getErrorMessage } from '../../utils.js';

const teamStore = useTeamStore();

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
  department_name: '',
  expense_approver: '',
  shift_approver: '',
  leave_approver: ''
});

const formData = ref(getInitialFormData());

watch(show, async (newVal) => {
  if (newVal) {
    formData.value = getInitialFormData();
    errors.value = {};
    if (props.editId) {
      await fetchDepartmentDetails();
    }
  }
});

const fetchDepartmentDetails = async () => {
  try {
    const data = await call('arijentek_core.api.teams_permissons.get_department_list', {
      department_id: props.editId
    });
    if (data) {
      formData.value = {
        name: data.name,
        department_name: data.department_name,
        expense_approver: data.expense_approver || '',
        shift_approver: data.shift_approver || '',
        leave_approver: data.leave_approver || ''
      };
    }
  } catch (err) {
    submitError.value = getErrorMessage(err, 'Failed to fetch department details');
  }
};

const errors = ref({});
const submitError = ref('');
const submitting = ref(false);

const validate = () => {
  errors.value = {};
  let isValid = true;

  if (!formData.value.department_name) {
    errors.value.department_name = 'Department Name is mandatory';
    isValid = false;
  }

  return isValid;
};

const handleSave = async () => {
  submitError.value = '';
  if (validate()) {
    submitting.value = true;
    try {
      await call('arijentek_core.api.teams_permissons.create_department', { department_data: formData.value });
      emit('save', formData.value);
      show.value = false;
    } catch (err) {
      submitError.value = getErrorMessage(err, 'Failed to create department');
    } finally {
      submitting.value = false;
    }
  }
};
</script>
