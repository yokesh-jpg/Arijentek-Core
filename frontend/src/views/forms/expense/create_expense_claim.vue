<template>
  <Dialog :options="{ size: '3xl' }" v-model="show">
    <template #body>
      <div class="modal-panel">
        <header class="modal-header">
          <div class="min-w-0">
            <h3 class="modal-title">{{ isEdit ? 'Edit expense claim' : 'New expense claim' }}</h3>
            <p class="text-[12px] text-[#656A72] dark:text-white/60 truncate">{{ isEdit ? editId : 'What was spent, on what, and who approves it.' }}</p>
          </div>
          <button @click="show = false" class="btn-icon-ghost shrink-0" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span></button>
        </header>

        <div v-if="!canCreate" class="empty-state">
          <span class="material-symbols-outlined !text-[28px] text-[#C4C7CC] dark:text-white/25">lock</span>
          <p class="empty-state-text">You don't have permission to create expense claims.</p>
        </div>

        <div v-else class="flex-1 overflow-y-auto px-6 py-5">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-x-4 gap-y-4">
            <div>
              <label class="field-label">Employee <span class="text-red-600 dark:text-red-400">*</span></label>
              <SearchableDropdown
                v-if="canApprove"
                v-model="formData.employee"
                :options="employeeList"
                labelKey="employee_name"
                valueKey="name"
                placeholder="Select employee"
                @update:modelValue="onEmployeeChange"
              />
              <p v-else class="field-static">{{ currentEmployeeName || 'Loading…' }}</p>
              <p v-if="errors.employee" class="field-error">{{ errors.employee }}</p>
            </div>

            <div>
              <label class="field-label">Expense approver <span class="text-red-600 dark:text-red-400">*</span></label>
              <SearchableDropdown
                v-model="formData.expense_approver"
                :options="mappedApproversList"
                placeholder="Select approver"
              />
              <p v-if="errors.expense_approver" class="field-error">{{ errors.expense_approver }}</p>
            </div>

            <div>
              <label class="field-label">Posting date <span class="text-red-600 dark:text-red-400">*</span></label>
              <DateField v-model="formData.posting_date" />
              <p v-if="errors.posting_date" class="field-error">{{ errors.posting_date }}</p>
            </div>
          </div>

          <!-- ===== Expense lines ===== -->
          <div class="modal-section">
            <p class="status-label flex items-center gap-1.5 mb-3">
              <span class="material-symbols-outlined !text-[16px]">receipt_long</span>
              Expense lines
            </p>

            <!-- Column headings, desktop only; on a phone each line stacks and
                 the placeholders name the fields. -->
            <div class="hidden md:grid grid-cols-[150px_minmax(0,1.3fr)_110px_minmax(0,1.4fr)_36px] gap-2.5 mb-1.5">
              <span class="field-label !mb-0">Date</span>
              <span class="field-label !mb-0">Type</span>
              <span class="field-label !mb-0 text-right">Amount</span>
              <span class="field-label !mb-0">Description</span>
              <span class="sr-only">Remove</span>
            </div>

            <div class="space-y-2.5">
              <div
                v-for="(line, index) in formData.expenses"
                :key="index"
                class="grid grid-cols-1 md:grid-cols-[150px_minmax(0,1.3fr)_110px_minmax(0,1.4fr)_36px] gap-2.5 md:items-center p-3 md:p-0 rounded-[12px] md:rounded-none border md:border-0 border-black/[0.07] dark:border-white/10"
              >
                <DateField v-model="line.expense_date" />

                <!-- The "+" sits beside the field it adds to, as in the POS
                     Purchase Order form - not up in the column heading. -->
                <div class="flex items-center gap-2 min-w-0">
                  <div class="flex-1 min-w-0">
                    <SearchableDropdown
                      v-model="line.expense_type"
                      :options="expenseStore.expenseTypes"
                      labelKey="name"
                      valueKey="name"
                      placeholder="Select type"
                    />
                  </div>
                  <button
                    v-if="canCreateType"
                    type="button"
                    class="btn-add-option"
                    title="Add a new expense type"
                    aria-label="Add a new expense type"
                    @click="showCreateTypeModal = true"
                  >
                    <span class="material-symbols-outlined !text-[18px]">add</span>
                  </button>
                </div>

                <input type="number" v-model="line.amount" placeholder="0.00" min="0" step="0.01" class="field-input text-right tabular-nums" aria-label="Amount" />

                <input type="text" v-model="line.description" placeholder="What it was for" class="field-input" aria-label="Description" />

                <div class="flex md:justify-center justify-end">
                  <button
                    type="button"
                    @click="removeExpenseLine(index)"
                    class="btn-danger-ghost"
                    :aria-label="'Remove line ' + (index + 1)"
                    title="Remove line"
                  >
                    <span class="material-symbols-outlined !text-[18px]">delete</span>
                  </button>
                </div>
              </div>
            </div>

            <button type="button" @click="addExpenseLine" class="btn-secondary !h-9 mt-3">
              <span class="material-symbols-outlined !text-[18px]">add</span>
              Add line
            </button>
          </div>

          <!-- ===== Attachments ===== -->
          <div class="modal-section">
            <div class="flex items-center justify-between gap-3 mb-3">
              <p class="status-label flex items-center gap-1.5">
                <span class="material-symbols-outlined !text-[16px]">attach_file</span>
                Attachments
              </p>
              <button type="button" @click="$refs.fileInput.click()" class="btn-secondary !h-9">
                <span class="material-symbols-outlined !text-[18px]">upload</span>
                Add files
              </button>
              <input type="file" multiple class="hidden" ref="fileInput" @change="onFilesSelected" />
            </div>

            <ul v-if="attachments.length > 0" class="table-card !rounded-[12px] divide-y divide-black/[0.05] dark:divide-white/[0.06]">
              <li v-for="(file, index) in attachments" :key="index" class="flex items-center justify-between gap-3 px-3.5 py-2.5">
                <div class="flex items-center gap-2.5 min-w-0">
                  <span class="material-symbols-outlined !text-[18px] text-[#656A72] dark:text-white/55 shrink-0">description</span>
                  <span class="text-[13px] text-[#17181B] dark:text-white truncate">{{ file.file_name || file.name }}</span>
                </div>
                <div class="flex items-center gap-2 shrink-0">
                  <span v-if="file.isExisting" class="text-[12px] text-[#656A72] dark:text-white/55">Saved</span>
                  <button type="button" @click="removeAttachment(index)" class="btn-danger-ghost !w-8 !h-8" :aria-label="'Remove ' + (file.file_name || file.name)" title="Remove">
                    <span class="material-symbols-outlined !text-[16px]">close</span>
                  </button>
                </div>
              </li>
            </ul>
            <p v-else class="py-5 text-center text-[13px] text-[#656A72] dark:text-white/55 rounded-[12px] border border-dashed border-black/[0.1] dark:border-white/[0.14]">
              No attachments yet. Receipts help the approver.
            </p>
          </div>
        </div>

        <!-- The total sits in the footer so it stays in view while amounts are
             entered; at the end of the scroll area it was cut off. -->
        <footer v-if="canCreate" class="modal-footer justify-between">
          <div class="min-w-0">
            <p v-if="submitError" class="text-[13px] text-red-700 dark:text-red-400">{{ submitError }}</p>
            <template v-else>
              <p class="status-label">Total</p>
              <p class="text-[18px] font-semibold text-[#17181B] dark:text-white tabular-nums leading-tight">{{ formatCurrency(totalClaimedAmount) }}</p>
            </template>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <button class="btn-secondary" @click="show = false" :disabled="submitting">Cancel</button>
            <button class="btn-primary" @click="handleSave" :disabled="submitting">
              <span v-if="submitting" class="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></span>
              {{ submitting ? 'Saving…' : (isEdit ? 'Save changes' : 'Save claim') }}
            </button>
          </div>
        </footer>
      </div>
    </template>
  </Dialog>

  <CreateExpenseType
    v-model="showCreateTypeModal"
    @save="onTypeSaved"
  />
</template>

<script setup>
import { notify, ask } from '@/utils/feedback.js'
import { ref, computed, watch, onMounted } from 'vue';
import { Dialog, call } from 'frappe-ui';
import { getErrorMessage } from '../../../utils.js';
import { useExpenseStore } from '../../../stores/expense';
import { useEmployeeStore } from '../../../stores/employee';
import SearchableDropdown from '../../../components/SearchableDropdown.vue';
import CreateExpenseType from './create_expense_type.vue';
import DateField from '../../../components/DateField.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  editId: { type: String, default: '' }
});

const emit = defineEmits(['update:modelValue', 'save']);

const isEdit = computed(() => !!props.editId);

const expenseStore = useExpenseStore();
const employeeStore = useEmployeeStore();

const show = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
});

const canCreate = ref(true);
const canApprove = ref(false);
const canCreateType = ref(false);
const showCreateTypeModal = ref(false);
const currentEmployeeName = ref('');
const employeeList = ref([]);
const approversList = ref([]);

const mappedApproversList = computed(() => approversList.value.map(a => ({
  label: a.full_name || a.name,
  value: a.name
})));

const getInitialFormData = () => ({
  name: '',
  employee: '',
  expense_approver: '',
  posting_date: new Date().toISOString().substring(0, 10),
  expenses: [
    { expense_date: new Date().toISOString().substring(0, 10), expense_type: "", amount: 0, description: "" }
  ]
});

const formData = ref(getInitialFormData());
const errors = ref({});
const submitError = ref('');
const submitting = ref(false);

const fileInput = ref(null);
const attachments = ref([]);

const totalClaimedAmount = computed(() => {
  return formData.value.expenses.reduce((sum, item) => sum + parseFloat(item.amount || 0), 0);
});

onMounted(async () => {
  await employeeStore.init();
  currentEmployeeName.value = employeeStore.employee?.employee_name || '';
  
  if (expenseStore.expenseTypes.length === 0) {
    expenseStore.fetchTypes();
  }
});

watch(show, async (newVal) => {
  if (newVal) {
    formData.value = getInitialFormData();
    errors.value = {};
    submitError.value = '';
    attachments.value = [];
    
    try {
      const canCreateRes = await call('arijentek_core.api.expense.can_create_expense_claim');
      canCreate.value = !!canCreateRes;
      
      const canApproveRes = await call('arijentek_core.api.expense.can_approve_expense_claim');
      canApprove.value = !!canApproveRes;
      
      const canCreateTypeRes = await call('arijentek_core.api.expense.can_create_expense_types');
      canCreateType.value = !!canCreateTypeRes;
      
      if (canCreate.value) {
        if (canApprove.value) {
          const employees = await call('arijentek_core.api.expense.get_employee_list');
          employeeList.value = employees || [];
        }

        if (isEdit.value) {
          const res = await call('arijentek_core.api.expense.get_expense_claim', { name: props.editId });
          if (res && res.length > 0) {
            const claim = res[0];
            formData.value = {
              name: claim.name,
              employee: claim.employee,
              expense_approver: claim.expense_approver || '',
              posting_date: claim.posting_date || new Date().toISOString().substring(0, 10),
              payable_account: claim.payable_account || '',
              remark: claim.remark || '',
              expenses: claim.expenses && claim.expenses.length > 0 ? claim.expenses : [{ expense_date: claim.posting_date || new Date().toISOString().substring(0, 10), expense_type: "", amount: 0, description: "" }]
            };

            // fetch existing attachments
            try {
              const files = await call('frappe.client.get_list', {
                doctype: 'File',
                filters: {
                  attached_to_doctype: 'Expense Claim',
                  attached_to_name: props.editId
                },
                fields: ['name', 'file_name', 'file_url']
              });
              if (files && files.length > 0) {
                files.forEach(f => {
                  f.isExisting = true;
                  attachments.value.push(f);
                });
              }
            } catch(e) {
              console.error("Failed to fetch attachments", e);
            }

            await onEmployeeChange(); // fetch approvers for this employee
            formData.value.expense_approver = claim.expense_approver || ''; // ensure it's set after loading list
          }
        } else {
          formData.value.employee = employeeStore.employee?.name || '';
          await onEmployeeChange();
        }
      }
    } catch (e) {
      console.error(e);
      submitError.value = getErrorMessage(e, 'Error checking permissions');
    }
  }
});

const onEmployeeChange = async () => {
  approversList.value = [];
  // formData.value.expense_approver = ''; // Don't clear immediately to allow existing value if set
  if (formData.value.employee) {
    try {
      const data = await call('arijentek_core.api.expense.get_expense_approvers', {
        employee: formData.value.employee
      });
      if (data && data.department_approvers) {
        approversList.value = data.department_approvers;
      }
      if (data && data.expense_approver && !isEdit.value) {
        formData.value.expense_approver = data.expense_approver;
      }
    } catch (e) {
      console.error('Failed to fetch approvers', e);
    }
  }
};

const addExpenseLine = () => {
  formData.value.expenses.push({
    expense_date: formData.value.posting_date,
    expense_type: "",
    amount: 0,
    description: ""
  });
};

const removeExpenseLine = (idx) => {
  formData.value.expenses.splice(idx, 1);
  if (formData.value.expenses.length === 0) {
    addExpenseLine();
  }
};

const onFilesSelected = (e) => {
  const files = Array.from(e.target.files);
  files.forEach(f => {
    attachments.value.push(f);
  });
  e.target.value = '';
};

const removeAttachment = async (index) => {
  const file = attachments.value[index];
  if (file.isExisting) {
    if (await ask('Are you sure you want to delete this attachment? It will be removed immediately.')) {
      try {
        await call('frappe.client.delete', { doctype: 'File', name: file.name });
        attachments.value.splice(index, 1);
      } catch (err) {
        notify(getErrorMessage(err, 'Failed to delete file'));
      }
    }
  } else {
    attachments.value.splice(index, 1);
  }
};

const onTypeSaved = async () => {
  await expenseStore.fetchTypes();
};

const formatCurrency = (amount) => {
  if (amount === null || amount === undefined) return "$0";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(amount);
};

const validate = () => {
  errors.value = {};
  let isValid = true;
  if (!formData.value.employee) {
    errors.value.employee = 'Employee is required';
    isValid = false;
  }
  if (!formData.value.expense_approver) {
    errors.value.expense_approver = 'Expense Approver is required';
    isValid = false;
  }
  if (!formData.value.posting_date) {
    errors.value.posting_date = 'Posting Date is required';
    isValid = false;
  }
  if (formData.value.expenses.length === 0) {
    submitError.value = "Please add at least one expense line.";
    return false;
  }
  for (const item of formData.value.expenses) {
    if (!item.expense_type) {
      submitError.value = "Please select an Expense Type for all lines.";
      return false;
    }
    if (parseFloat(item.amount || 0) <= 0) {
      submitError.value = "Amount must be greater than zero for all lines.";
      return false;
    }
  }
  return isValid;
};

const handleSave = async () => {
  submitError.value = '';
  if (validate()) {
    submitting.value = true;
    try {
      const payload = { ...formData.value };
      const response = await expenseStore.submitClaimResource.submit(payload);
      if (response && response.success === false) {
        throw new Error(response.error);
      }
      
      const claimName = response.name || formData.value.name;
      
      if (claimName && attachments.value.length > 0) {
        const newFiles = attachments.value.filter(f => !f.isExisting);
        for (const file of newFiles) {
          const form = new FormData();
          form.append('file', file, file.name);
          form.append('is_private', 1);
          form.append('doctype', 'Expense Claim');
          form.append('docname', claimName);
          
          await fetch('/api/method/upload_file', {
            method: 'POST',
            headers: {
              'Accept': 'application/json',
              'X-Frappe-CSRF-Token': window.csrf_token || ''
            },
            body: form
          });
        }
      }
      
      emit('save', formData.value);
      show.value = false;
    } catch (err) {
      submitError.value = getErrorMessage(err, 'Failed to save expense claim');
    } finally {
      submitting.value = false;
    }
  }
};
</script>

<style scoped>
</style>
