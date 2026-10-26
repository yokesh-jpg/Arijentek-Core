<template>
  <div class="space-y-5 tab-fill">
    <!-- ===== Header ===== -->
    <div class="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
      <div>
        <h2 class="section-title">Expense claims</h2>
        <p class="section-subtitle">What staff have spent, and what has been signed off.</p>
      </div>
      <div class="flex items-center gap-2">
        <button v-if="canCreate" @click="openCreateModal" class="btn-primary shrink-0">
          <span class="material-symbols-outlined !text-[18px]">add</span>
          Add claim
        </button>
      </div>
    </div>

    <!-- ===== Filters ===== -->
    <div class="glass-card !p-3 flex flex-wrap items-center gap-2">
      <div class="relative flex-[2] min-w-[220px]">
        <span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/55 pointer-events-none">search</span>
        <input v-model="filterSearchId" type="text" placeholder="Search by claim ID" class="field-input !pl-9" aria-label="Search by claim ID" />
      </div>
      <div v-if="showEmployeeFilter" class="flex-1 min-w-[180px]">
        <label class="sr-only">Employee</label>
        <SearchableDropdown
          v-model="selectedEmployee"
          :options="employeeList"
          labelKey="employee_name"
          valueKey="name"
          placeholder="All employees"
          showAllOption
          allOptionLabel="All employees"
        />
      </div>
      <div class="flex-1 min-w-[160px]">
        <label class="sr-only">Status</label>
        <SearchableDropdown
          v-model="filterStatus"
          :options="['Open', 'Approved', 'Rejected']"
          placeholder="All statuses"
          showAllOption
          allOptionLabel="All statuses"
        />
      </div>
      <div class="flex-1 min-w-[200px]">
        <label class="sr-only">Date range</label>
        <DateRangePicker
          v-model:fromDate="filterFromDate"
          v-model:toDate="filterToDate"
          v-model:preset="selectedPreset"
        />
      </div>
    </div>

    <!-- Counted over the full filtered set (server-side), so the strip
         matches the whole result, not just the rows on screen. -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div v-for="st in claimStats" :key="st.label" class="glass-card !p-4">
        <p class="text-xs font-medium text-[#5C6169] dark:text-white/60">{{ st.label }}</p>
        <p class="text-2xl font-semibold tracking-tight mt-1.5 tabular-nums" :class="st.tone || 'text-[#17181B] dark:text-white'">{{ st.value }}</p>
      </div>
    </div>

    <!-- ===== Table (server-side pagination) ===== -->
    <DataTable
      :columns="listColumns"
      :rows="pager.state.rows"
      :actions="actionsForClaim"
      :row-key="'name'"
      :loading="pager.state.loading"
      empty-text="No expense claims. Nothing matches the current filters."
      :show-pager="true"
      :total="pager.state.total"
      :page="pager.state.page"
      :page-size="pager.state.size"
      :on-row-click="(claim) => handleView(claim)"
      @update:page="pager.state.page = $event"
      @update:page-size="pager.setPageSize($event)"
    >
      <template #cell-claim="{ row }">
        <span class="block tabular-nums break-words leading-snug sm:truncate">{{ row.name }}</span>
        <!-- Below sm the employee and date columns are gone, so they
             ride along under the claim id rather than vanishing. -->
        <span class="block sm:hidden text-xs font-normal text-[#5C6169] dark:text-white/60 leading-snug">
          {{ row.employee_name || row.employee }} · {{ formatDate(row.posting_date) }}
        </span>
      </template>
      <template #cell-date="{ row }">
        {{ formatDate(row.posting_date) }}
      </template>
      <template #cell-employee="{ row }">
        <span class="truncate">{{ row.employee_name || row.employee }}</span>
      </template>
      <template #cell-approver="{ row }">
        <span class="truncate max-w-[180px]">{{ row.expense_approver_name || row.expense_approver || '—' }}</span>
      </template>
      <template #cell-amount="{ row }">
        {{ formatCurrency(row.total_claimed_amount) }}
      </template>
      <template #cell-status="{ row }">
        <span class="premium-tag" :class="getStatusClasses(row.status)">{{ getDisplayStatus(row.status) }}</span>
      </template>
    </DataTable>

    <!-- Create Modal -->
    <CreateExpenseClaim
      v-model="showCreateClaimModal"
      :editId="selectedEditId"
      @save="onSaveClaim"
    />

    <!-- View Modal -->
    <div v-if="showViewModal" class="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 bg-[#0B0B0E]/70 backdrop-blur-sm" @click="showViewModal = false">
      <div class="relative w-full max-w-2xl" @click.stop>
        <ViewExpenseClaim v-if="selectedViewId" :id="selectedViewId" @close="showViewModal = false" @refresh="onViewRefresh" @edit="handleEdit" />
      </div>
    </div>
  </div>
</template>


<script setup>
import DataTable from '@/components/DataTable.vue'
import { useServerPager } from '@/composables/useServerPager.js'
import { notify, ask } from '@/utils/feedback.js'
import { ref, computed, onMounted, watch } from 'vue';
import { call } from 'frappe-ui';
import CreateExpenseClaim from '../../forms/expense/create_expense_claim.vue';
import ViewExpenseClaim from '../../page_views/expense/view_expense_claim.vue';
import SearchableDropdown from '@/components/SearchableDropdown.vue';
import DateRangePicker from '@/components/DateRangePicker.vue';
import { useEmployeeStore } from '@/stores/employee';
import { getErrorMessage } from '@/utils';

const employeeStore = useEmployeeStore();
const showCreateClaimModal = ref(false);
const canCreate = ref(false);

const showViewModal = ref(false);
const selectedViewId = ref('');
const selectedEditId = ref('');

function openCreateModal() {
  selectedEditId.value = '';
  showCreateClaimModal.value = true;
}

function handleView(claim) {
  selectedViewId.value = claim.name;
  showViewModal.value = true;
}

function handleEdit(claim) {
  showViewModal.value = false;
  selectedEditId.value = claim.name;
  showCreateClaimModal.value = true;
}

async function handleApprove(claim) {
  if (!await ask('Are you sure you want to approve this expense claim?')) return;
  try {
    const res = await call('arijentek_core.api.expense.update_expense_claim_status', {
      name: claim.name,
      status: 'Approved'
    });
    if (res && res.success === false) {
      notify(res.error || 'Failed to approve claim');
      return;
    }
    await pager.fetchPage();
  } catch (e) {
    console.error('Failed to approve claim:', e);
    notify(getErrorMessage(e, 'Failed to approve claim'));
  }
}

async function handleReject(claim) {
  if (!await ask('Are you sure you want to reject this expense claim?')) return;
  try {
    const res = await call('arijentek_core.api.expense.update_expense_claim_status', {
      name: claim.name,
      status: 'Rejected'
    });
    if (res && res.success === false) {
      notify(res.error || 'Failed to reject claim');
      return;
    }
    await pager.fetchPage();
  } catch (e) {
    console.error('Failed to reject claim:', e);
    notify(getErrorMessage(e, 'Failed to reject claim'));
  }
}

async function handleDelete(claim) {
  if (!await ask('Are you sure you want to delete this expense claim?')) return;
  try {
    const res = await call('arijentek_core.api.expense.delete_expense_claim', {
      name: claim.name
    });
    if (res && res.success === false) {
      notify(res.error || 'Failed to delete claim');
      return;
    }
    await pager.fetchPage();
  } catch (e) {
    console.error('Failed to delete claim:', e);
    notify(getErrorMessage(e, 'Failed to delete claim'));
  }
}

const canApprove = ref(false);
const canEdit = ref(false);
const canDelete = ref(false);
const employeeList = ref([]);
const showEmployeeFilter = computed(() => canApprove.value && employeeList.value.length > 0);

const selectedEmployee = ref('');
const filterStatus = ref('');
const filterFromDate = ref('');
const filterToDate = ref('');
const selectedPreset = ref('All Time');
const filterSearchId = ref('');

/* Server-side stats over the full filtered set (COUNT + SUM), so the strip
   reflects the whole result, not just the rows on screen. */
const serverStats = ref({ count: 0, total_amount: 0, approved_amount: 0, rejected_amount: 0 });

/* Four facts off the server-side stats. */
const claimStats = computed(() => [
  { label: 'Claims', value: String(serverStats.value.count) },
  { label: 'Total', value: formatCurrency(serverStats.value.total_amount) },
  { label: 'Approved', value: formatCurrency(serverStats.value.approved_amount), tone: 'text-green-700 dark:text-green-300' },
  { label: 'Rejected', value: formatCurrency(serverStats.value.rejected_amount), tone: 'text-red-600 dark:text-red-400' },
]);

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

async function checkPermissions() {
  try {
    const [approveRes, editRes, deleteRes, createRes] = await Promise.all([
      call('arijentek_core.api.expense.can_approve_expense_claim'),
      call('arijentek_core.api.expense.can_edit_expense_claim'),
      call('arijentek_core.api.expense.can_delete_expense_claim'),
      call('arijentek_core.api.expense.can_create_expense_claim')
    ]);
    canApprove.value = !!approveRes;
    canEdit.value = !!editRes;
    canDelete.value = !!deleteRes;
    canCreate.value = !!createRes;

    if (canApprove.value) {
      const list = await call('arijentek_core.api.expense.get_employee_list');
      employeeList.value = list || [];
    } else {
      employeeList.value = [];
    }
  } catch (e) {
    console.error("Error checking permissions", e);
  }
}

/* Server-side fetch: `page`/`page_size` are passed to the API (LIMIT/OFFSET),
   and the response holds the current page + total + stats. Returns { rows,
   total } for useServerPager. Handles both the paginated dict (page_size >
   0) and the legacy list (page_size = 0) responses. */
async function fetchClaims(page, size) {
  const params = {
    page: page,
    page_size: size,
    search_text: filterSearchId.value || "",
  };
  if (selectedEmployee.value && selectedEmployee.value !== 'All') {
    params.employee = selectedEmployee.value;
  }
  if (filterStatus.value && filterStatus.value !== 'All') {
    params.status = filterStatus.value;
  }
  const isAllTime = selectedPreset.value === "All Time";
  if (!isAllTime && filterFromDate.value && filterToDate.value) {
    params.start_date = filterFromDate.value;
    params.end_date = filterToDate.value;
  }

  try {
    const res = await call('arijentek_core.api.expense.get_expense_claim', params);
    const rows = Array.isArray(res) ? res : (res?.data || []);
    const total = Array.isArray(res) ? res.length : Number(res?.total || 0);
    if (res && !Array.isArray(res) && res.stats) {
      serverStats.value = res.stats;
    }
    return { rows, total };
  } catch (e) {
    console.error("Failed to fetch claims", e);
    return { rows: [], total: 0 };
  }
}

/* Server-side pager: one page at a time (LIMIT/OFFSET). Stale-while-revalidate
   keeps the previous page visible while the next loads; a stale fetch is dropped. */
const pager = useServerPager((page, size) => fetchClaims(page, size), { size: 10 });

/* Column declarations for the list (order = render order; `className`
   carries the responsive hiding). */
const listColumns = [
  { key: "claim", label: "Claim", className: "table-td-strong" },
  { key: "date", label: "Date", className: "hidden lg:table-cell" },
  { key: "employee", label: "Employee", className: "hidden sm:table-cell" },
  { key: "approver", label: "Approver", className: "hidden xl:table-cell" },
  { key: "amount", label: "Amount", className: "text-right tabular-nums" },
  { key: "status", label: "Status", className: "hidden md:table-cell" },
];

/* Per-row actions, gated by permission. The gate mirrors the old template:
   rows are only editable/approvable/rejectable when Draft. */
function actionsForClaim(claim) {
  return [
    { label: 'Edit', icon: 'edit', show: canEdit.value && claim.status === 'Draft', onClick: () => handleEdit(claim) },
    { label: 'Approve', icon: 'check_circle', show: canApprove.value && claim.status === 'Draft', onClick: () => handleApprove(claim) },
    { label: 'Reject', icon: 'cancel', danger: true, show: canApprove.value && claim.status === 'Draft', onClick: () => handleReject(claim) },
    { divider: true },
    { label: 'Delete', icon: 'delete', danger: true, show: canDelete.value, onClick: () => handleDelete(claim) },
  ];
}

function onSaveClaim() {
  pager.fetchPage();
}

function onViewRefresh() {
  pager.fetchPage();
}

// Filter changes reset to page 1. The pager's own [page, size] watch re-fetches
// when the page actually changes; if it is already 1, fetch directly so a filter
// change on page 1 still refreshes.
watch([filterSearchId, selectedEmployee, filterStatus, filterFromDate, filterToDate], () => {
  if (pager.state.page !== 1) {
    pager.state.page = 1;
  } else {
    pager.fetchPage();
  }
});

onMounted(async () => {
  await employeeStore.init();
  await checkPermissions();
  await pager.fetchPage();
});
</script>
