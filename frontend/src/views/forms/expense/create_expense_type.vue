<template>
  <Dialog :options="{ size: 'lg' }" v-model="show">
    <template #body>
      <div class="modal-panel">
      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-black/[0.07] dark:border-white/10">
        <h3 class="text-lg font-semibold text-[#17181B] dark:text-white ">
          {{ isEdit ? 'Edit expense type' : 'New expense type' }}
        </h3>
        <button @click="show = false" class="p-2 text-[#656A72] dark:text-white/60 hover:text-[#17181B] dark:hover:text-white hover:bg-black/[0.04] dark:hover:bg-white/[0.06] rounded-[12px] transition-all">
          <span class="material-symbols-outlined text-sm">close</span>
        </button>
      </div>

      <!-- Body -->
      <div class="flex-1 px-5 py-5 overflow-y-auto space-y-6">
        <!-- Name -->
        <div class="space-y-2">
          <label class="field-label">Expense type name</label>
          <input 
            type="text" 
            v-model="formData.name"
            class="field-input"
            placeholder="e.g. Travel, Meals, Supplies"
          />
        </div>

        <!-- Default Account -->
        <div class="space-y-2">
          <label class="field-label">Default account</label>
          <SearchableDropdown
            v-model="formData.default_account"
            :options="accountOptions"
            placeholder="Search or select an account"
          />
        </div>

        <!-- Description -->
        <div class="space-y-2">
          <label class="field-label">Description</label>
          <textarea 
            v-model="formData.description"
            rows="3"
            class="field-input"
            placeholder="Optional description"
          ></textarea>
        </div>
      </div>

      <!-- Footer -->
      <div class="p-6 border-t border-black/[0.07] dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.05] flex justify-end gap-3">
        <button 
          @click="show = false"
          class="btn-secondary"
        >
          Cancel
        </button>
        <button 
          @click="submitForm"
          :disabled="submitting || !formData.name"
          class="btn-primary"
        >
          <span v-if="submitting" class="w-4 h-4 border-2 border-white/20 border-t-white dark:border-white/20 dark:border-t-white rounded-full animate-spin"></span>
          <span v-else>{{ isEdit ? 'Save changes' : 'Create' }}</span>
        </button>
      </div>

      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { notify } from '@/utils/feedback.js'
import { ref, watch, onMounted, computed } from 'vue';
import { Dialog, call } from 'frappe-ui';
import { getErrorMessage } from '@/utils';
import SearchableDropdown from '@/components/SearchableDropdown.vue';

const props = defineProps({
  modelValue: Boolean,
  editData: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['update:modelValue', 'save']);

const show = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
});

const formData = ref({
  name: '',
  default_account: '',
  description: ''
});

const isEdit = ref(false);
const submitting = ref(false);
const accountOptions = ref([]);

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    if (props.editData) {
      isEdit.value = true;
      formData.value = {
        name: props.editData.name || '',
        default_account: props.editData.default_account || '',
        description: props.editData.description || ''
      };
    } else {
      isEdit.value = false;
      formData.value = {
        name: '',
        default_account: '',
        description: ''
      };
    }
    
    if (accountOptions.value.length === 0) {
      fetchAccounts();
    } else if (!isEdit.value && !formData.value.default_account) {
      setDefaultAdminAccount();
    }
  }
});

function setDefaultAdminAccount() {
  const adminAcc = accountOptions.value.find(acc =>
    (acc.label || '').toLowerCase().includes('administrative expenses')
  );
  if (adminAcc) {
    formData.value.default_account = adminAcc.value;
  }
}

async function fetchAccounts() {
  try {
    const res = await call('arijentek_core.api.expense.get_default_expense_accounts');
    accountOptions.value = (res || []).map(acc => ({
      label: `${acc.account_name} (${acc.name})`,
      value: acc.name
    }));
    if (!isEdit.value && !formData.value.default_account) {
      setDefaultAdminAccount();
    }
  } catch (e) {
    console.error("Failed to fetch expense accounts", e);
  }
}

async function submitForm() {
  if (!formData.value.name) return;
  
  submitting.value = true;
  try {
    const payload = {
      name: formData.value.name,
      description: formData.value.description,
      default_account: formData.value.default_account,
    };
    
    if (isEdit.value) {
      payload.is_edit = true;
      payload.original_name = props.editData.name;
    }
    
    await call('arijentek_core.api.expense.save_expense_type', payload);
    
    emit('save');
    emit('update:modelValue', false);
  } catch (e) {
    console.error("Failed to save expense type", e);
    notify(getErrorMessage(e, "Failed to save expense type"));
  } finally {
    submitting.value = false;
  }
}
</script>
