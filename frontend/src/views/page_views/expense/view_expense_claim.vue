<template>
  <div class="modal-panel max-w-3xl mx-auto" :class="{ 'h-full': !isModal }">
    <header class="flex items-start justify-between gap-3 px-5 py-4 border-b border-black/[0.07] dark:border-white/10 shrink-0">
      <div class="min-w-0">
        <h2 class="modal-title truncate">Expense claim</h2>
        <p v-if="claim?.employee_name" class="text-[13px] text-[#5C6169] dark:text-white/65 truncate">{{ claim.employee_name }}</p>
        <p class="text-[12px] text-[#656A72] dark:text-white/55 truncate tabular-nums">{{ claim?.name || id }}</p>
      </div>
      <div class="flex items-center gap-1 shrink-0">
        <span v-if="claim" class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold mr-1" :class="getStatusClasses(claim.status)">{{ getDisplayStatus(claim.status) }}</span>
        <RowActions v-if="claim" :actions="[
          		{ label: 'Edit', icon: 'edit', show: !!(canEdit && claim.status === 'Draft'), onClick: () => { handleEdit() } },
          		{ label: 'Approve', icon: 'check_circle', show: !!(canApprove && claim.status === 'Draft'), onClick: () => { handleApprove() } },
          		{ divider: true },
          		{ label: 'Reject', icon: 'cancel', danger: true, show: !!(canApprove && claim.status === 'Draft'), onClick: () => { handleReject() } },
          		{ label: 'Delete', icon: 'delete', danger: true, show: !!(canDelete), onClick: () => { handleDelete() } },
          	]" />
        <button @click="$emit('close')" class="btn-icon-ghost" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span></button>
      </div>
    </header>

    <div v-if="loading" class="flex flex-col items-center justify-center py-16 gap-3">
      <span class="w-5 h-5 rounded-full border-2 border-black/10 dark:border-white/15 border-t-accent animate-spin"></span>
      <span class="text-[13px] text-[#5C6169] dark:text-white/65">Loading details…</span>
    </div>

    <div v-else-if="!claim" class="empty-state">
      <span class="material-symbols-outlined !text-[28px] text-red-600 dark:text-red-400">error</span>
      <p class="empty-state-text">Could not load this expense claim</p>
    </div>

    <div v-else class="flex-1 overflow-y-auto px-6 py-5 flex flex-col">

      <!-- Details Section -->
      <div class="modal-section grid grid-cols-1 md:grid-cols-3 gap-x-6 gap-y-5">
        <div>
          <p class="status-label">Employee</p>
          <p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ claim.employee_name || claim.employee }}</p>
        </div>
        <div>
          <p class="status-label">Approver</p>
          <p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ claim.expense_approver || 'Pending' }}</p>
        </div>
        <div>
          <p class="status-label">Posting date</p>
          <span class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ formatDate(claim.posting_date) }}</span>
        </div>
        <div v-if="claim.payable_account">
          <p class="status-label">Payable account</p>
          <p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ claim.payable_account }}</p>
        </div>
        <div v-if="claim.remark" class="md:col-span-3">
          <p class="status-label">Remarks</p>
          <p class="text-[13px] text-[#17181B] dark:text-white/90 leading-relaxed whitespace-pre-wrap mt-1">{{ claim.remark }}</p>
        </div>
      </div>

      <!-- Expense lines -->
      <div class="mt-6 pt-5 border-t border-black/[0.07] dark:border-white/10">
        <p class="status-label flex items-center gap-1.5 mb-2.5">
          <span class="material-symbols-outlined !text-[16px]">receipt_long</span>
          Expense lines
        </p>
        
        <div class="table-card !rounded-[12px]">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr>
                <th class="table-th">Date</th>
                <th class="table-th">Type</th>
                <th class="table-th">Description</th>
                <th class="!text-right table-th">Amount</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!claim.expenses || claim.expenses.length === 0">
                <td colspan="4" class="py-8 text-center text-[13px] text-[#656A72] dark:text-white/55">No expense lines found.</td>
              </tr>
              <tr v-for="(line, idx) in claim.expenses" :key="idx" class="border-b last:border-0 border-black/[0.05] dark:border-white/[0.06]">
                <td class="table-td">{{ formatDate(line.expense_date) }}</td>
                <td class="table-td">{{ line.expense_type }}</td>
                <td class="table-td">{{ line.description || '-' }}</td>
                <td class="!text-right table-td">{{ formatCurrency(line.amount) }}</td>
              </tr>
            </tbody>
            <tfoot class="bg-black/[0.02] dark:bg-white/[0.04] border-t border-black/[0.07] dark:border-white/10">
              <tr>
                <td colspan="3" class="px-5 py-4 text-xs font-semibold text-[#656A72] dark:text-white/55 text-right">Total</td>
                <td class="!text-right table-td">{{ formatCurrency(claim.total_claimed_amount) }}</td>
              </tr>
            </tfoot>
          </table>
      </div>
      
      <!-- Attachments Section -->
      <div v-if="attachments.length > 0">
        <p class="status-label mb-2.5">
          Attachments
        </p>
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          <a v-for="file in attachments" :key="file.name" :href="file.file_url" target="_blank" class="flex items-center gap-3 p-3 bg-white dark:bg-white/[0.06] border border-black/[0.07] dark:border-white/10 rounded-[12px] hover:bg-black/[0.03] dark:hover:bg-white/[0.08] hover:border-accent/30 transition-all group shadow-sm">
            <div class="w-10 h-10 rounded-[12px] bg-green-500/[0.1] dark:bg-green-500/15 text-green-700 dark:text-green-300 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
              <span class="material-symbols-outlined">attachment</span>
            </div>
            <div class="overflow-hidden">
              <p class="text-[13px] font-medium text-[#17181B] dark:text-white truncate" :title="file.file_name">{{ file.file_name }}</p>
              <p class="text-xs text-[#5C6169] dark:text-white/65 mt-0.5">Click to view</p>
            </div>
          </a>
        </div>
      </div>
      
    </div>
      
    </div>

    <footer class="px-5 py-4 border-t border-black/[0.07] dark:border-white/10 shrink-0">
      <button class="btn-secondary w-full" @click="$emit('close')">Close</button>
    </footer>
  </div>
</template>

<script setup>
import { notify, ask } from '@/utils/feedback.js'
import { ref, onMounted, onUnmounted } from 'vue';
import { call } from 'frappe-ui';
import { getErrorMessage } from '@/utils';
import RowActions from '@/components/RowActions.vue';

const props = defineProps({
  id: {
    type: String,
    required: true
  },
  isModal: {
    type: Boolean,
    default: true
  }
});

const emit = defineEmits(['close', 'refresh', 'edit']);

const loading = ref(true);
const claim = ref(null);
const canApprove = ref(false);
const canEdit = ref(false);
const canDelete = ref(false);
const activeActionMenu = ref(false);
const attachments = ref([]);

function toggleActionMenu() {
  activeActionMenu.value = !activeActionMenu.value;
}

function closeActionMenu() {
  activeActionMenu.value = false;
}

const handleWindowClick = (e) => {
  if (!e.target.closest(".more_vert") && !e.target.closest(".dropdown-menu")) {
    closeActionMenu();
  }
};

async function checkPermissions() {
  try {
    const [approveRes, editRes, deleteRes] = await Promise.all([
      call('arijentek_core.api.expense.can_approve_expense_claim'),
      call('arijentek_core.api.expense.can_edit_expense_claim'),
      call('arijentek_core.api.expense.can_delete_expense_claim')
    ]);
    canApprove.value = !!approveRes;
    canEdit.value = !!editRes;
    canDelete.value = !!deleteRes;
  } catch (e) {
    console.error("Error checking permissions", e);
  }
}

async function handleApprove() {
  closeActionMenu();
  if (!await ask('Are you sure you want to approve this expense claim?')) return;
  try {
    const res = await call('arijentek_core.api.expense.update_expense_claim_status', {
      name: claim.value.name,
      status: 'Approved'
    });
    if (res && res.success === false) {
      notify(res.error || 'Failed to approve claim');
      return;
    }
    await fetchClaim();
    emit('refresh');
  } catch (e) {
    console.error('Failed to approve claim:', e);
    notify(getErrorMessage(e, 'Failed to approve claim'));
  }
}

async function handleReject() {
  closeActionMenu();
  if (!await ask('Are you sure you want to reject this expense claim?')) return;
  try {
    const res = await call('arijentek_core.api.expense.update_expense_claim_status', {
      name: claim.value.name,
      status: 'Rejected'
    });
    if (res && res.success === false) {
      notify(res.error || 'Failed to reject claim');
      return;
    }
    await fetchClaim();
    emit('refresh');
  } catch (e) {
    console.error('Failed to reject claim:', e);
    notify(getErrorMessage(e, 'Failed to reject claim'));
  }
}

function handleEdit() {
  closeActionMenu();
  emit('edit', claim.value);
}

async function handleDelete() {
  closeActionMenu();
  if (!await ask('Are you sure you want to delete this expense claim?')) return;
  try {
    const res = await call('arijentek_core.api.expense.delete_expense_claim', {
      name: claim.value?.name
    });
    if (res && res.success === false) {
      notify(res.error || 'Failed to delete claim');
      return;
    }
    emit('refresh');
    emit('close');
  } catch (e) {
    console.error('Failed to delete claim:', e);
    notify(getErrorMessage(e, 'Failed to delete claim'));
  }
}

const getDisplayStatus = (status) => {
  if (status === 'Draft') return 'Open';
  if (status === 'Submitted') return 'Approved';
  return status;
};

const getStatusClasses = (status) => {
  const s = status?.toLowerCase();
  if (s === "submitted" || s === "approved" || s === "paid") return "tag-emerald";
  if (s === "rejected" || s === "cancelled") return "tag-red";
  return "tag-neutral";
};

const formatCurrency = (amount) => {
  if (amount === null || amount === undefined) return "$0.00";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(amount);
};

const formatDate = (dateStr) => {
  if (!dateStr) return "-";
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
};

async function fetchClaim() {
  loading.value = true;
  try {
    const res = await call('arijentek_core.api.expense.get_expense_claim', { name: props.id });
      if (res && res.length > 0) {
        claim.value = res[0];
        
        // Fetch attachments
        try {
          const files = await call('frappe.client.get_list', {
            doctype: 'File',
            filters: {
              attached_to_doctype: 'Expense Claim',
              attached_to_name: props.id
            },
            fields: ['name', 'file_name', 'file_url']
          });
          attachments.value = files || [];
        } catch (fileErr) {
          console.error("Failed to fetch attachments", fileErr);
          attachments.value = [];
        }
      } else {
        claim.value = null;
        attachments.value = [];
      }
    } catch (e) {
      console.error("Failed to fetch claim details", e);
      claim.value = null;
      attachments.value = [];
    } finally {
    loading.value = false;
  }
}

onMounted(() => {
  window.addEventListener("click", handleWindowClick);
  checkPermissions();
  if (props.id) {
    fetchClaim();
  }
});

onUnmounted(() => {
  window.removeEventListener("click", handleWindowClick);
});
</script>
