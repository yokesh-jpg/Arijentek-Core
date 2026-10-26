<template>
	<div class="space-y-5 tab-fill">
		<!-- ===== Header ===== -->
		<div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
			<div>
				<h2 class="section-title">Issues</h2>
				<p class="section-subtitle">Workplace issues raised by staff, and where each one stands.</p>
			</div>
			<div class="flex items-center gap-2">
				<button v-if="permissions.can_create" @click="handleCreate" class="btn-primary shrink-0">
					<span class="material-symbols-outlined !text-[18px]">add</span>
					Raise issue
				</button>
			</div>
		</div>

		<!-- ===== Stats =====
		     Open and Investigated are the two that need somebody to act, so
		     they lead; Resolved is the count you check against them. -->
		<div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
			<div v-for="st in issueStats" :key="st.label" class="glass-card !p-4">
				<p class="text-xs font-medium text-[#5C6169] dark:text-white/60">{{ st.label }}</p>
				<p class="text-2xl font-semibold tracking-tight mt-1.5 tabular-nums" :class="st.tone || 'text-[#17181B] dark:text-white'">{{ st.value }}</p>
			</div>
		</div>

		<!-- ===== Filters ===== -->
		<div class="glass-card !p-3">
			<div class="flex flex-wrap items-center gap-2">
				<div class="relative flex-[2] min-w-[220px]">
					<span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/55 pointer-events-none">search</span>
					<input v-model="filters.search" @input="debouncedFetch" type="text" placeholder="Search by ID or subject" aria-label="Search issues" class="field-input !pl-9" />
				</div>
				<div class="flex-1 min-w-[180px]">
					<label class="sr-only">Date range</label>
					<DateRangePicker @change="handleDateChange" />
				</div>
				<div class="flex-1 min-w-[160px]">
					<label class="sr-only">Status</label>
					<SearchableDropdown
						v-model="filters.status"
						:options="['Open', 'Investigated', 'Resolved', 'Invalid']"
						placeholder="All statuses"
						:showAllOption="true"
						allOptionLabel="All statuses"
					/>
				</div>
				<div class="flex-1 min-w-[160px]">
					<label class="sr-only">Issue type</label>
					<SearchableDropdown
						v-model="filters.grievance_type"
						:options="issueTypes"
						valueKey="name"
						labelKey="name"
						placeholder="All types"
						:showAllOption="true"
						allOptionLabel="All types"
					/>
				</div>
				<div v-if="permissions.can_submit" class="flex-1 min-w-[160px]">
					<label class="sr-only">Raised by</label>
					<SearchableDropdown
						v-model="filters.employee"
						:options="employees"
						valueKey="name"
						labelKey="employee_name"
						placeholder="All employees"
						:showAllOption="true"
						allOptionLabel="All employees"
					/>
				</div>
			</div>
		</div>

		<!-- ===== List ===== -->
		<DataTable
			:columns="listColumns"
			:rows="pager.state.rows"
			:actions="issueActions"
			:row-key="'name'"
			:on-row-click="openViewModal"
			:loading="pager.state.loading"
			:empty-text="hasFilters ? 'No issues match these filters.' : 'No issues have been raised.'"
			:show-pager="true"
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
		>
			<template #cell-subject="{ row }">
				<div class="max-w-[320px]">
					<span class="block truncate font-medium text-[#17181B] dark:text-white">{{ row.subject }}</span>
					<span class="block text-[12px] font-normal text-[#656A72] dark:text-white/55 tabular-nums">{{ row.name }}</span>
					<span class="sm:hidden block text-xs font-normal text-[#5C6169] dark:text-white/60 mt-0.5">
						{{ row.employee_name || row.raised_by || '—' }} · {{ formatDate(row.date) }}
					</span>
				</div>
			</template>
			<template #cell-raised_by="{ row }">
				<span class="truncate">{{ row.employee_name || row.raised_by || '—' }}</span>
			</template>
			<template #cell-grievance_type="{ row }">
				{{ row.grievance_type || '—' }}
			</template>
			<template #cell-date="{ row }">
				<span class="whitespace-nowrap tabular-nums">{{ formatDate(row.date) }}</span>
			</template>
			<template #cell-status="{ row }">
				<span class="premium-tag" :class="statusTag(row.status)">{{ row.status || 'Unknown' }}</span>
			</template>
		</DataTable>

		<!-- Create/Edit Issue Modal -->
		<CreateIssue
			v-model="showCreateModal"
			:editData="selectedEditData"
			:targetStatus="selectedTargetStatus"
			@save="pager.fetchPage"
		/>

		<!-- View Issue Modal -->
		<ViewIssue
			v-model="showViewModal"
			:issueId="selectedViewId"
			@edit="editIssue"
			@delete="deleteIssue"
			@changeStatus="({ issue, targetStatus }) => changeStatusModal(issue, targetStatus)"
		/>
	</div>
</template>

<script setup>
import DataTable from '@/components/DataTable.vue'
import { useServerPager } from '@/composables/useServerPager.js'
import { notify, ask } from '@/utils/feedback.js'
import { ref, computed, onMounted, watch } from 'vue';
import { call } from 'frappe-ui';
import DateRangePicker from '../../../components/DateRangePicker.vue';
import SearchableDropdown from '../../../components/SearchableDropdown.vue';
import CreateIssue from '../../forms/issues/create_issue.vue';
import ViewIssue from '../../page_views/issues/view_issue.vue';
import { getErrorMessage } from '@/utils';

const issueTypes = ref([]);
const employees = ref([]);
const statsData = ref({ total: 0, Open: 0, Investigated: 0, Resolved: 0, Invalid: 0 });

const showCreateModal = ref(false);
const selectedEditData = ref(null);
const selectedTargetStatus = ref(null);

const showViewModal = ref(false);
const selectedViewId = ref(null);

const openViewModal = (issue) => {
  selectedViewId.value = issue.name;
  showViewModal.value = true;
};

const filters = ref({
  search: '',
  dateRange: null, // [start, end]
  status: '',
  employee: '',
  grievance_type: ''
});

const permissions = ref({
  can_edit: false,
  can_delete: false,
  can_create: false,
  can_submit: false
});

const fetchPermissions = async () => {
  try {
    const editPerm = await call('arijentek_core.api.issues.can_edit_employee_grievance');
    permissions.value.can_edit = !!editPerm;
    
    const deletePerm = await call('arijentek_core.api.issues.can_delete_employee_grievance');
    permissions.value.can_delete = !!deletePerm;

    const createPerm = await call('arijentek_core.api.issues.can_create_employee_grievance');
    permissions.value.can_create = !!createPerm;

    const submitPerm = await call('arijentek_core.api.issues.can_submit_employee_grievance');
    permissions.value.can_submit = !!submitPerm;
  } catch (error) {
    console.error("Failed to fetch permissions:", error);
  }
};

const fetchFilterOptions = async () => {
  try {
    const [typeRes, empRes] = await Promise.all([
      call('arijentek_core.api.issues.get_issues_types'),
      call('arijentek_core.api.issues.get_employees')
    ]);
    issueTypes.value = typeRes || [];
    employees.value = empRes || [];
  } catch (error) {
    console.error("Failed to fetch filter options:", error);
  }
};

const handleDateChange = (val) => {
  if (val && val.fromDate && val.toDate) {
    filters.value.dateRange = [val.fromDate, val.toDate];
  } else {
    filters.value.dateRange = null;
  }
};

let debounceTimer;
const debouncedFetch = () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    triggerFilterRefresh();
  }, 300);
};

function triggerFilterRefresh() {
  if (pager.state.page !== 1) {
    pager.state.page = 1;
  } else {
    pager.fetchPage();
  }
}

/* Server-side fetch: `page`/`pageSize` are passed to get_issues (LIMIT/OFFSET).
   Returns { rows, total } for useServerPager. */
const fetchIssues = async (page, pageSize) => {
  try {
    const params = {
      page: page || 1,
      page_size: pageSize || pager.state.size || 10,
      search_term: filters.value.search || null,
      status: filters.value.status || null,
      grievance_type: filters.value.grievance_type || null,
      employee: filters.value.employee || null,
    };
    
    if (filters.value.dateRange && filters.value.dateRange.length === 2) {
      params.from_date = filters.value.dateRange[0];
      params.to_date = filters.value.dateRange[1];
    }
    
    const res = await call('arijentek_core.api.issues.get_issues', params);
    if (res && res.stats) {
      statsData.value = res.stats;
    }
    const rows = Array.isArray(res) ? res : (res?.data || []);
    const total = Array.isArray(res) ? res.length : Number(res?.total || 0);
    return { rows, total };
  } catch (error) {
    console.error("Failed to fetch issues:", error);
    return { rows: [], total: 0 };
  }
};

/* Server-side pager: one page at a time (LIMIT/OFFSET). Stale-while-revalidate
   keeps the previous page visible while the next loads; a stale fetch is dropped. */
const pager = useServerPager((page, size) => fetchIssues(page, size), { size: 10 });

/* Column declarations for the list view (order = render order; `className`
   carries responsive hiding). */
const listColumns = [
  { key: 'subject', label: 'Issue', className: 'table-td-strong' },
  { key: 'raised_by', label: 'Raised by', className: 'hidden md:table-cell' },
  { key: 'grievance_type', label: 'Type', className: 'hidden sm:table-cell' },
  { key: 'date', label: 'Date', className: 'whitespace-nowrap tabular-nums hidden sm:table-cell' },
  { key: 'status', label: 'Status' },
];

const handleCreate = () => {
  selectedEditData.value = null;
  selectedTargetStatus.value = null;
  showCreateModal.value = true;
};

const editIssue = (issue) => {
  selectedEditData.value = issue;
  selectedTargetStatus.value = null;
  showCreateModal.value = true;
};

const changeStatusModal = (issue, targetStatus) => {
  selectedEditData.value = issue;
  selectedTargetStatus.value = targetStatus;
  showCreateModal.value = true;
};

/* Per-row actions, gated by permission. 2+ actions fold into the More dropdown
   (RowActions maxInline=1) in DataTable. */
function issueActions(issue) {
  const canAmend = issue.status === 'Open' || permissions.value.can_submit;
  return [
    {
      label: 'Investigate',
      icon: 'search_insights',
      show: permissions.value.can_submit && issue.status === 'Open',
      onClick: () => changeStatusModal(issue, 'Investigated'),
    },
    {
      label: 'Resolve',
      icon: 'check_circle',
      show: permissions.value.can_submit && (issue.status === 'Open' || issue.status === 'Investigated'),
      onClick: () => changeStatusModal(issue, 'Resolved'),
    },
    {
      label: 'Mark invalid',
      icon: 'block',
      show: permissions.value.can_submit && issue.status !== 'Invalid',
      onClick: () => changeStatusModal(issue, 'Invalid'),
    },
    { divider: true },
    {
      label: 'Edit',
      icon: 'edit',
      show: permissions.value.can_edit && canAmend,
      onClick: () => editIssue(issue),
    },
    {
      label: 'Delete',
      icon: 'delete',
      danger: true,
      show: permissions.value.can_delete && canAmend,
      onClick: () => deleteIssue(issue),
    },
  ];
}

const deleteIssue = async (issue) => {
  if (!await ask(`Are you sure you want to delete issue ${issue.name}?`)) return;
  
  try {
    await call('arijentek_core.api.issues.delete_issues', { name: issue.name });
    await pager.fetchPage();
  } catch (err) {
    console.error(err);
    notify(getErrorMessage(err, 'Failed to delete issue'));
  }
};

watch(
  [
    () => filters.value.status,
    () => filters.value.grievance_type,
    () => filters.value.employee,
    () => filters.value.dateRange,
  ],
  () => {
    triggerFilterRefresh();
  }
);

onMounted(async () => {
  await fetchPermissions();
  await fetchFilterOptions();
  await pager.fetchPage();
});

/* ---- presentation helpers -------------------------------------------- */

/* Open and Investigated are the two that still need somebody; they are
   coloured so the pair reads at a glance against the Resolved count. */
const issueStats = computed(() => [
  { label: 'Total', value: statsData.value.total },
  { label: 'Open', value: statsData.value.Open, tone: statsData.value.Open ? 'text-red-700 dark:text-red-400' : '' },
  { label: 'Investigated', value: statsData.value.Investigated, tone: statsData.value.Investigated ? 'text-amber-800 dark:text-amber-400' : '' },
  { label: 'Resolved', value: statsData.value.Resolved },
]);

const hasFilters = computed(() => {
  const f = filters.value;
  return !!(f.search || f.status || f.grievance_type || f.employee || (f.dateRange && f.dateRange.length === 2));
});

function clearFilters() {
  filters.value = { search: '', dateRange: null, status: '', employee: '', grievance_type: '' };
  triggerFilterRefresh();
}

/* The four statuses map onto the shared tag colours: Open still needs action,
   Investigated is in hand, Resolved is done, Invalid is closed without one. */
function statusTag(status) {
  if (status === 'Open') return 'tag-red';
  if (status === 'Investigated') return 'tag-amber';
  if (status === 'Resolved') return 'tag-emerald';
  return 'tag-neutral';
}

function formatDate(dateStr) {
  if (!dateStr) return '—';
  /* Parsed as local midnight: a bare 'YYYY-MM-DD' is read as UTC, which
     names the previous day east of UTC. */
  const d = new Date(String(dateStr) + 'T00:00:00');
  if (isNaN(d.getTime())) return String(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}
</script>
