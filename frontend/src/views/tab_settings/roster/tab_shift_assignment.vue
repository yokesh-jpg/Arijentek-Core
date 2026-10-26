<!--
  tab_shift_assignment.vue
  Extracted from RosterView.vue — the "assignment" tab section (lines 631–870).
  Includes: matrix view, list view, bulk assign modal, quick assign modal, shift details modal.
-->
<template>
  <div class="space-y-4 sm:space-y-6 tab-fill">
    <!-- ===== Header ===== -->
    <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
      <div>
        <h2 class="section-title">Shift assignments</h2>
        <p class="section-subtitle">Who is rostered where, across the month.</p>
      </div>
      <div class="flex items-center gap-2 flex-wrap">
        <div class="seg-group">
          <button
            @click="showListView = false"
            class="seg-item"
            :class="{ 'seg-item-active': !showListView }"
          >
            <span class="material-symbols-outlined !text-[16px]">grid_view</span>
            <span class="hidden sm:inline">Matrix</span>
          </button>
          <button
            @click="showListView = true"
            class="seg-item"
            :class="{ 'seg-item-active': showListView }"
          >
            <span class="material-symbols-outlined !text-[16px]">view_list</span>
            <span class="hidden sm:inline">List</span>
          </button>
        </div>
        <button v-if="canAddRoster" @click="openBulkAssignModal" class="btn-primary">
          <span class="material-symbols-outlined !text-[18px]">group_add</span>
          Bulk assign
        </button>
      </div>
    </div>

    <!-- ===== Filters =====
         Labels sit above their control rather than beside it, so the row wraps
         cleanly instead of breaking a label away from its dropdown. -->
    <!-- Filters. Open on a laptop, behind a button on a phone — four always-open
         dropdowns pushed the roster itself off the first screen. -->
    <button
      @click="filtersOpen = !filtersOpen"
      class="btn-secondary lg:hidden w-full justify-between"
      :aria-expanded="filtersOpen"
    >
      <span class="inline-flex items-center gap-2">
        <span class="material-symbols-outlined !text-[18px]">tune</span>
        Filters
        <span v-if="activeFilterCount" class="min-w-[18px] h-[18px] px-1 grid place-items-center rounded-[12px] bg-accent text-white text-xs font-semibold tabular-nums">{{ activeFilterCount }}</span>
      </span>
      <span class="material-symbols-outlined !text-[18px] transition-transform" :class="{ 'rotate-180': filtersOpen }">expand_more</span>
    </button>

    <div class="glass-card !p-3" :class="filtersOpen ? '' : 'hidden lg:block'">
      <div class="flex flex-wrap items-center gap-2">
        <div class="flex-1 min-w-[170px]">
          <label class="sr-only">Month</label>
          <SearchableDropdown
            v-model="selectedMonthKeyAssignment"
            :options="monthOptions"
            labelKey="label"
            valueKey="value"
            placeholder="Select month"
          />
        </div>
        <div v-if="canAddRoster" class="flex-1 min-w-[170px]">
          <label class="sr-only">Employee</label>
          <SearchableDropdown
            v-model="filterMatrixEmployee"
            :options="rosterStore.addRosterEmployees"
            labelKey="employee_name"
            valueKey="name"
            :showAllOption="true"
            allOptionLabel="All employees"
            placeholder="All employees"
          />
        </div>
        <div v-if="canAddRoster" class="flex-1 min-w-[170px]">
          <label class="sr-only">Department</label>
          <SearchableDropdown
            v-model="filterMatrixDept"
            :options="rosterStore.deptDesignationList.departments"
            :showAllOption="true"
            allOptionLabel="All departments"
            placeholder="All departments"
          />
        </div>
        <div v-if="canAddRoster" class="flex-1 min-w-[170px]">
          <label class="sr-only">Designation</label>
          <SearchableDropdown
            v-model="filterMatrixDesig"
            :options="rosterStore.deptDesignationList.designations"
            :showAllOption="true"
            allOptionLabel="All designations"
            placeholder="All designations"
          />
        </div>
      </div>
    </div>

    <!-- ===== Matrix ===== -->
    <div v-if="!showListView" class="table-card relative">
      <div
        v-if="rosterStore.shiftMatrixLoading"
        class="absolute inset-0 z-30 grid place-items-center bg-white/70 dark:bg-[#18181b]/70 backdrop-blur-sm"
      >
        <div class="flex flex-col items-center gap-2">
          <span class="material-symbols-outlined !text-[28px] text-accent dark:text-accent-light animate-spin">progress_activity</span>
          <span class="text-[13px] text-[#5C6169] dark:text-white/65">Loading roster…</span>
        </div>
      </div>

      <div v-if="!rosterStore.shiftMatrix.employees.length && !rosterStore.shiftMatrixLoading" class="empty-state">
        <span class="material-symbols-outlined !text-[28px] text-[#C4C7CC] dark:text-white/25">group_off</span>
        <p class="empty-state-text">No one matches these filters.</p>
      </div>

      <div
        v-else
        ref="matrixScrollContainer"
        class="overflow-auto no-scrollbar select-none cursor-grab active:cursor-grabbing"
        style="max-height: 68vh"
        @mousedown="handleMatrixMouseDown"
        @mouseleave="handleMatrixMouseLeave"
        @mouseup="handleMatrixMouseUp"
        @mousemove="handleMatrixMouseMove"
      >
        <table class="w-full border-collapse min-w-max">
          <thead class="sticky top-0 z-20">
            <tr>
              <th
                class="sticky left-0 z-30 table-th !py-3.5 bg-[#F7F7F9] dark:bg-[#1f1f23] border-b border-r border-black/[0.06] dark:border-white/[0.07] w-[132px] min-w-[132px] max-w-[132px] lg:w-[220px] lg:min-w-[220px] lg:max-w-none shadow-[6px_0_12px_-8px_rgba(0,0,0,0.18)]"
              >
                Employee
              </th>
              <th
                v-for="day in rosterStore.shiftMatrix.days"
                :key="day.date"
                class="px-2 py-2.5 text-center border-b border-black/[0.06] dark:border-white/[0.07] w-[108px] min-w-[108px] max-w-[108px] lg:w-[132px] lg:min-w-[132px] lg:max-w-none"
                :class="isMatrixToday(day) ? 'bg-accent/[0.10] dark:bg-accent/[0.18]' : day.is_weekend ? 'bg-black/[0.035] dark:bg-white/[0.05]' : 'bg-[#F7F7F9] dark:bg-[#1f1f23]'"
              >
                <div
                  class="text-xs font-medium tracking-wide"
                  :class="isMatrixToday(day) ? 'text-accent dark:text-accent-light' : 'text-[#656A72] dark:text-white/55'"
                >
                  {{ day.day_short }}
                </div>
                <div
                  class="text-[14px] font-semibold tabular-nums leading-tight"
                  :class="isMatrixToday(day) ? 'text-accent dark:text-accent-light' : day.is_weekend ? 'text-[#656A72] dark:text-white/55' : 'text-[#17181B] dark:text-white'"
                >
                  {{ day.day_num }}
                </div>
              </th>
            </tr>
          </thead>

          <tbody>
            <tr
              v-for="emp in rosterStore.shiftMatrix.employees"
              :key="emp.name"
              class="group/row border-b border-black/[0.05] dark:border-white/[0.06] last:border-0"
            >
              <td
                class="sticky left-0 z-10 w-[132px] max-w-[132px] lg:w-auto lg:max-w-none px-2.5 lg:px-4 py-2.5 border-r border-black/[0.06] dark:border-white/[0.07] bg-white dark:bg-[#1a1a1e] group-hover/row:bg-[#FAFAFC] dark:group-hover/row:bg-[#212126] shadow-[6px_0_12px_-8px_rgba(0,0,0,0.12)] transition-colors"
              >
                <div class="flex items-center gap-2 lg:gap-3 min-w-0">
                  <span class="avatar-chip">{{ initials(emp.employee_name) }}</span>
                  <div class="min-w-0">
                    <p class="text-[13px] font-medium text-[#17181B] dark:text-white truncate" :title="emp.employee_name">
                      {{ emp.employee_name }}
                    </p>
                    <p class="hidden lg:block text-xs text-[#5C6169] dark:text-white/60 truncate" :title="emp.designation || emp.department">
                      {{ emp.designation || emp.department || 'No department' }}
                    </p>
                  </div>
                </div>
              </td>

              <td
                v-for="day in rosterStore.shiftMatrix.days"
                :key="day.date"
                class="p-1.5 align-top group/cell transition-colors"
                :class="isMatrixToday(day) ? 'bg-accent/[0.05] dark:bg-accent/[0.09]' : day.is_weekend ? 'bg-black/[0.02] dark:bg-white/[0.025]' : ''"
              >
                <div v-if="emp.shifts[day.date]" class="flex flex-col gap-1.5">
                  <button
                    v-for="sh in emp.shifts[day.date]"
                    :key="sh.name"
                    @click="openShiftDetails(emp, day.date, sh)"
                    class="w-full h-[52px] px-2.5 py-1.5 rounded-[10px] text-left bg-accent/[0.09] dark:bg-accent/[0.16] border border-accent/[0.14] dark:border-accent/25 hover:bg-accent/[0.16] dark:hover:bg-accent/25 hover:border-accent/35 transition-colors"
                  >
                    <span class="block text-xs font-medium text-accent dark:text-accent-light truncate" :title="sh.shift_type">
                      {{ sh.shift_type }}
                    </span>
                    <span
                      v-if="sh.start_time || sh.end_time"
                      class="block text-xs tabular-nums text-accent/70 dark:text-accent-light/70 truncate whitespace-nowrap mt-0.5"
                    >
                      {{ formatTime(sh.start_time) }} – {{ formatTime(sh.end_time) }}
                    </span>
                  </button>
                </div>

                <!-- Empty cell. The add button is quiet until you reach for it,
                     so a month of blanks does not read as a wall of buttons. -->
                <div v-else class="h-[52px] grid place-items-center">
                  <button
                    v-if="canAddRoster"
                    @click="openQuickAssign(emp, day.date)"
                    class="w-8 h-8 grid place-items-center rounded-full text-[#656A72] dark:text-white/30 hover:text-accent dark:hover:text-accent-light hover:bg-accent/[0.10] transition-all lg:opacity-0 lg:group-hover/row:opacity-100 focus:opacity-100"
                    :title="`Assign a shift to ${emp.employee_name}`"
                    :aria-label="`Assign a shift to ${emp.employee_name}`"
                  >
                    <span class="material-symbols-outlined !text-[18px]">add</span>
                  </button>
                  <span v-else class="text-xs text-[#C4C7CC] dark:text-white/20">—</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ===== List ===== -->
    <div v-if="showListView">
      <DataTable
        :columns="listColumns"
        :rows="pager.state.rows"
        :actions="actionsForRow"
        :row-key="'name'"
        :loading="pager.state.loading"
        :total="pager.state.total"
        :page="pager.state.page"
        :page-size="pager.state.size"
        :empty-text="'No shift assignments match these filters.'"
        :on-row-click="(row) => openShiftDetails(row, row.start_date, row)"
        @update:page="pager.state.page = $event"
        @update:page-size="pager.setPageSize($event)"
      >
        <template #cell-name="{ row }">
          <span class="font-mono text-xs font-semibold text-accent dark:text-accent-light">{{ row.name }}</span>
        </template>
        <template #cell-employeeName="{ row }">
          <span class="block truncate">{{ row.employee_name }}</span>
          <span class="sm:hidden block text-xs font-normal tabular-nums text-[#5C6169] dark:text-white/60 whitespace-nowrap">
            {{ formatDate(row.start_date) }}<template v-if="row.end_date && row.end_date !== row.start_date"> – {{ formatDate(row.end_date) }}</template>
          </span>
        </template>
        <template #cell-department="{ row }">
          {{ row.department || '—' }}
        </template>
        <template #cell-shift_type="{ row }">
          <span class="premium-tag tag-accent">{{ row.shift_type }}</span>
        </template>
        <template #cell-start_date="{ row }">
          <span class="tabular-nums whitespace-nowrap">{{ formatDate(row.start_date) }}</span>
        </template>
        <template #cell-end_date="{ row }">
          <span class="tabular-nums whitespace-nowrap">{{ row.end_date ? formatDate(row.end_date) : '—' }}</span>
        </template>
      </DataTable>
    </div>

    <!-- Quick Assign Modal -->
    <CreateShiftAssignment
      v-model="showQuickAssignModal"
      :initialData="quickAssignData"
      @success="handleAssignmentSuccess"
    />

    <!-- Bulk Assign Modal -->
    <CreateBulkShiftAssignment
      v-model="rosterStore.showBulkAssignModal"
      @success="handleAssignmentSuccess"
    />

    <!-- Shift Assignment Detail Modal -->
    <Teleport to="body">
      <div v-if="showShiftAssignmentModal" @click.self="showShiftAssignmentModal = false" class="fixed inset-0 z-[100] flex items-center justify-center bg-[#0B0B0E]/70 backdrop-blur-sm p-4 md:p-6">
        <div class="w-full max-w-2xl" @click.stop>
          <ShiftAssignmentPageView
            :id="selectedShiftAssignmentId"
            :selectedDate="selectedShiftAssignmentDate"
            :isModal="true"
            @close="showShiftAssignmentModal = false"
            @edit="handleEditAssignment"
            @delete="handleDeleteAssignment"
          />
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { notify, ask } from '@/utils/feedback.js'
import DataTable from '@/components/DataTable.vue'
import { ref, computed, onMounted, watch } from 'vue';
import { call } from 'frappe-ui';
import { useRosterStore } from '@/stores/roster';
import ShiftAssignmentPageView from '@/views/page_views/ShiftAssignmentPageView.vue';
import CreateShiftAssignment from '@/views/forms/roster/create_shift_assignment.vue';
import CreateBulkShiftAssignment from '@/views/forms/roster/create_bulk_shift_assignment.vue';
import SearchableDropdown from '@/components/SearchableDropdown.vue';
import SelectField from '../../../components/SelectField.vue'
import { useServerPager } from '@/composables/useServerPager';

const rosterStore = useRosterStore();

// Permissions
const canAddRoster  = ref(false);
const canDeleteRoster = ref(false);

// View state
const showListView = ref(false);
watch(showListView, (val) => { if (val) pager.fetchPage(); });

// Filters
const _today = new Date();
const selectedMonthAssignment = ref(_today.getMonth() + 1);
const selectedYearAssignment  = ref(_today.getFullYear());

const selectedMonthKeyAssignment = computed({
  get: () => `${selectedYearAssignment.value}-${selectedMonthAssignment.value}`,
  set: (val) => {
    const [y, m] = val.split('-').map(Number);
    selectedYearAssignment.value = y;
    selectedMonthAssignment.value = m;
  },
});

const monthOptions = computed(() => {
  const opts = [];
  const now = new Date();
  for (let offset = -12; offset <= 2; offset++) {
    const d = new Date(now.getFullYear(), now.getMonth() + offset, 1);
    const m = d.getMonth() + 1;
    const y = d.getFullYear();
    opts.push({ value: `${y}-${m}`, label: d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' }), month: m, year: y });
  }
  return opts;
});

const filterMatrixDept     = ref('');
const filterMatrixEmployee = ref('');
const filterMatrixDesig    = ref('');

watch([selectedMonthKeyAssignment, filterMatrixDept, filterMatrixDesig, filterMatrixEmployee], async () => {
  if (selectedMonthKeyAssignment.value) {
    const [year, month] = selectedMonthKeyAssignment.value.split('-');
    await rosterStore.fetchShiftMatrix(month, year, filterMatrixDept.value, filterMatrixDesig.value, filterMatrixEmployee.value);
    if (showListView.value) {
      if (pager.state.page !== 1) pager.state.page = 1;
      else pager.fetchPage();
    }
  }
});

// Matrix drag-to-scroll
const matrixScrollContainer = ref(null);
const isMatrixMouseDown = ref(false);
let matrixStartX = 0;
let matrixScrollLeft = 0;

function handleMatrixMouseDown(e) {
  if (!matrixScrollContainer.value) return;
  isMatrixMouseDown.value = true;
  matrixStartX = e.pageX - matrixScrollContainer.value.offsetLeft;
  matrixScrollLeft = matrixScrollContainer.value.scrollLeft;
}
function handleMatrixMouseLeave() { isMatrixMouseDown.value = false; }
function handleMatrixMouseUp()    { isMatrixMouseDown.value = false; }
function handleMatrixMouseMove(e) {
  if (!isMatrixMouseDown.value || !matrixScrollContainer.value) return;
  e.preventDefault();
  const x = e.pageX - matrixScrollContainer.value.offsetLeft;
  matrixScrollContainer.value.scrollLeft = matrixScrollLeft - (x - matrixStartX) * 1.5;
}

// List view
/* The matrix header needs to know which column is today. The payload does not
   carry is_today on matrix days, so it is derived from the local date — not
   from toISOString, which rolls over a day early east of UTC. */
const filtersOpen = ref(false);

/* Shown on the Filters button so an applied filter is not invisible once the
   panel is closed. */
const activeFilterCount = computed(
  () => [filterMatrixDept.value, filterMatrixDesig.value, filterMatrixEmployee.value].filter(Boolean).length
);

function isMatrixToday(day) {
  const n = new Date();
  const local = [n.getFullYear(), String(n.getMonth() + 1).padStart(2, '0'), String(n.getDate()).padStart(2, '0')].join('-');
  return day?.date === local;
}

function initials(name) {
  return (name || '?')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join('');
}

/* Server-side paging for the list view. The API already returns
   { assignments, total, page, page_size } — the pager tracks the page and
   fetches one page at a time. Changing the size always returns to the
   first page (useServerPager.setPageSize). */
async function fetchAssignmentsPage(page, pageSize) {
  const params = { month: selectedMonthAssignment.value, year: selectedYearAssignment.value, page, page_size: pageSize };
  if (filterMatrixDept.value)     params.department = filterMatrixDept.value;
  if (filterMatrixDesig.value)    params.designation = filterMatrixDesig.value;
  if (filterMatrixEmployee.value) params.employee = filterMatrixEmployee.value;
  const res = await call('arijentek_core.api.roster.get_shift_assignment_list', params);
  return { rows: res.assignments || [], total: Number(res.total) || 0 };
}

const pager = useServerPager((page, size) => fetchAssignmentsPage(page, size), { size: 10 });

const listColumns = [
  { key: 'name', label: 'ID', className: 'whitespace-nowrap' },
  { key: 'employeeName', label: 'Employee', className: 'table-td-strong max-w-[180px] sm:max-w-none' },
  { key: 'department', label: 'Department', className: 'hidden md:table-cell' },
  { key: 'shift_type', label: 'Shift type' },
  { key: 'start_date', label: 'From', className: 'hidden sm:table-cell' },
  { key: 'end_date', label: 'To', className: 'hidden sm:table-cell' },
];

function actionsForRow(row) {
  return [
    { label: 'View assignment', icon: 'visibility', onClick: () => openShiftDetails(row, row.start_date, row) },
    { label: 'Edit assignment', icon: 'edit', onClick: () => editListAssignment(row) },
    { divider: true },
    { label: 'Delete assignment', icon: 'delete', danger: true, show: canDeleteRoster.value, onClick: () => onDeleteMatrixRoster(row.name) },
  ];
}

// Delete
async function onDeleteMatrixRoster(assignmentName, deleteDate = null) {
  if (await ask('Delete this shift assignment?')) {
    const res = await rosterStore.deleteRoster(assignmentName, deleteDate);
    if (res.success) {
      const [year, month] = selectedMonthKeyAssignment.value.split('-');
      await rosterStore.fetchShiftMatrix(month, year, filterMatrixDept.value, filterMatrixDesig.value, filterMatrixEmployee.value);
      if (showListView.value) {
        if (pager.state.page !== 1) pager.state.page = 1;
        else pager.fetchPage();
      }
    } else { notify(res.message); }
  }
}

// Shift Assignment Detail Modal
const showShiftAssignmentModal      = ref(false);
const selectedShiftAssignmentId     = ref('');
const selectedShiftAssignmentDate   = ref('');

function openShiftDetails(emp, date, shift) {
  if (shift?.name) {
    selectedShiftAssignmentId.value   = shift.name;
    selectedShiftAssignmentDate.value = date;
    showShiftAssignmentModal.value    = true;
  }
}

function editListAssignment(a) {
  quickAssignData.value = {
    empId: a.employee, empName: a.employee_name, date: a.start_date,
    endDate: a.end_date || a.start_date, shiftType: a.shift_type || '', shiftLocation: a.shift_location || '',
    assignment_name: a.name, schedule_enabled: false, repeat_on_days: [], frequency: 'Every Week'
  };
  showQuickAssignModal.value = true;
}

function handleEditAssignment(details) {
  showShiftAssignmentModal.value = false;
  quickAssignData.value = {
    empId: details.employee, empName: details.employee_name, date: details.date,
    endDate: details.date, shiftType: details.shift_type || '', shiftLocation: details.shift_location || '',
    assignment_name: details.assignment_id, schedule_enabled: false, repeat_on_days: [], frequency: 'Every Week'
  };
  showQuickAssignModal.value = true;
}

async function handleDeleteAssignment(details) {
  if (!await ask('Are you sure you want to delete this shift assignment?')) return;
  try {
    const res = await rosterStore.deleteRoster(details.assignment_id, details.delete_date);
    if (res && res.success === false) { notify(res.message || 'Failed to delete shift assignment.'); return; }
    showShiftAssignmentModal.value = false;
    const [year, month] = selectedMonthKeyAssignment.value.split('-');
    await rosterStore.fetchShiftMatrix(month, year, filterMatrixDept.value, filterMatrixDesig.value, filterMatrixEmployee.value);
  } catch { notify('Failed to delete shift assignment.'); }
}

// Quick Assign
const showQuickAssignModal = ref(false);
const quickAssignData      = ref({ empId: '', empName: '', date: '', endDate: '', shiftType: '', shiftLocation: '', assignment_name: '', schedule_enabled: false, repeat_on_days: [], frequency: 'Every Week' });

function openQuickAssign(emp, date) {
  quickAssignData.value = { empId: emp.name, empName: emp.employee_name, date, endDate: date, shiftType: '', shiftLocation: '', assignment_name: '', schedule_enabled: false, repeat_on_days: [], frequency: 'Every Week' };
  showQuickAssignModal.value = true;
}

async function handleAssignmentSuccess() {
  const [year, month] = selectedMonthKeyAssignment.value.split('-');
  await rosterStore.fetchShiftMatrix(month, year, filterMatrixDept.value, filterMatrixDesig.value, filterMatrixEmployee.value);
  if (showListView.value) {
    if (pager.state.page !== 1) pager.state.page = 1;
    else pager.fetchPage();
  }
}

// Bulk Assign
function openBulkAssignModal() {
  rosterStore.showBulkAssignModal = true;
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function formatTime(timeStr) {
  if (!timeStr || timeStr === 'None') return '';
  const parts = timeStr.split(':');
  return parts.length >= 2 ? `${parts[0]}:${parts[1]}` : timeStr;
}

onMounted(async () => {
  try { canAddRoster.value   = await rosterStore.checkCanAddRoster(); }   catch { canAddRoster.value = false; }
  try { canDeleteRoster.value = await rosterStore.checkCanDeleteRoster(); } catch { canDeleteRoster.value = false; }

  await rosterStore.fetchDeptDesignations();
  await rosterStore.fetchShiftMatrix(selectedMonthAssignment.value, selectedYearAssignment.value, '', '');
});
</script>
