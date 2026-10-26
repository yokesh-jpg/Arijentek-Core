<!--
  tab_roster_dashboard.vue
  Extracted from RosterView.vue — the "dashboard" tab section.
  Includes: weekly/monthly schedule cards, stats row, shift request table with approve/reject/edit/delete.
-->
<template>
  <div class="space-y-8">
    <!-- Header -->
    <div>
      <h2 class="section-title">My roster</h2>
      <p class="section-subtitle">Your work schedule.</p>
    </div>

    <!-- ===== Toolbar =====
         The date stepper takes the leftover width so it is the widest control
         on a phone, which is right: it is the one you touch most. -->
    <div class="flex flex-wrap items-center gap-2">
      <div class="order-1 flex items-center h-10 flex-1 min-w-[200px] sm:flex-none sm:min-w-[260px] rounded-full border border-black/[0.09] dark:border-white/[0.14] bg-white dark:bg-white/[0.06]">
        <button @click="goToPrev" class="w-9 h-full grid place-items-center rounded-l-[8px] text-[#5C6169] dark:text-white/65 hover:text-accent transition-colors" aria-label="Previous period">
          <span class="material-symbols-outlined !text-[18px]">chevron_left</span>
        </button>
        <span class="flex-1 text-center text-[13px] font-medium text-[#17181B] dark:text-white truncate px-1">{{ rangeDisplay }}</span>
        <button @click="goToNext" class="w-9 h-full grid place-items-center rounded-r-[8px] text-[#5C6169] dark:text-white/65 hover:text-accent transition-colors" aria-label="Next period">
          <span class="material-symbols-outlined !text-[18px]">chevron_right</span>
        </button>
      </div>

      <button
        @click="goToToday"
        class="btn-secondary order-2 shrink-0"
      >
        <span class="material-symbols-outlined !text-[18px]">today</span>
        <span>Today</span>
      </button>

      <div class="order-3 seg-group shrink-0">
        <button @click="viewMode = 'weekly'" class="seg-item" :class="{ 'seg-item-active': viewMode === 'weekly' }">Weekly</button>
        <button @click="viewMode = 'monthly'" class="seg-item" :class="{ 'seg-item-active': viewMode === 'monthly' }">Monthly</button>
      </div>

      <!-- Approvers only. Full width on a phone because a name needs the room. -->
      <div v-if="isShiftApprover && rosterStore.addRosterEmployees.length > 0" class="order-5 sm:order-4 w-full sm:w-[200px]">
        <SearchableDropdown
          v-model="selectedEmployee"
          :options="rosterStore.addRosterEmployees"
          labelKey="employee_name"
          valueKey="name"
          :showAllOption="true"
          allOptionLabel="My roster"
          placeholder="Select employee" />
      </div>

      <div class="order-4 sm:order-5 flex items-center gap-2 w-full sm:w-auto sm:ml-auto">
        <button
          v-if="canAssignShift || isShiftApprover"
          @click="openRosterModal"
          class="btn-secondary flex-1 sm:flex-none justify-center"
        >
          <span class="material-symbols-outlined !text-[18px]">assignment_add</span>
          Add roster
        </button>
        <button
          v-if="employeeStore.employee?.name || canAssignShift || isShiftApprover"
          @click="openRequestModal()"
          class="btn-primary flex-1 sm:flex-none justify-center"
        >
          <span class="material-symbols-outlined !text-[18px]">add</span>
          Shift request
        </button>
      </div>
    </div>

    <!-- ===== Summary =====
         Four across, matching the rest of the app. The target card is the one
         filled surface, because it is the only figure you are measured on. -->
    <div v-if="rosterStore.loading" class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
      <div v-for="i in 4" :key="i" class="glass-card !p-4 sm:!p-5 animate-pulse">
        <div class="h-3 w-20 rounded bg-black/[0.07] dark:bg-white/10 mb-3"></div>
        <div class="h-7 w-16 rounded bg-black/[0.07] dark:bg-white/10"></div>
      </div>
    </div>
    <div v-else class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
      <div class="glass-card !p-4 sm:!p-5">
        <p class="text-xs font-medium text-[#5C6169] dark:text-white/65">Working days</p>
        <p class="mt-2 flex items-baseline gap-1">
          <span class="text-2xl font-semibold text-[#17181B] dark:text-white tabular-nums leading-none">{{ viewMode === 'weekly' ? rosterStore.workingDays : rosterStore.monthlyWorkingDays }}</span>
          <span class="text-[13px] text-[#656A72] dark:text-white/55 tabular-nums">/ {{ viewMode === 'weekly' ? '07' : new Date(monthStart.getFullYear(), monthStart.getMonth() + 1, 0).getDate() }}</span>
        </p>
        <p class="text-xs text-[#5C6169] dark:text-white/60 mt-2 flex items-center gap-1.5">
          <span class="material-symbols-outlined !text-[14px] text-green-700 dark:text-green-400">check_circle</span>
          On track this {{ viewMode === 'weekly' ? 'week' : 'month' }}
        </p>
      </div>

      <div class="glass-card !p-4 sm:!p-5">
        <p class="text-xs font-medium text-[#5C6169] dark:text-white/65">Completed</p>
        <p class="text-2xl font-semibold text-[#17181B] dark:text-white tabular-nums leading-none mt-2">{{ completedShifts }}</p>
        <div class="h-1.5 rounded-full bg-black/[0.06] dark:bg-white/[0.10] mt-3 overflow-hidden">
          <div class="h-full rounded-full bg-accent transition-[width] duration-500" :style="{ width: completedPercent + '%' }"></div>
        </div>
      </div>

      <div class="glass-card !p-4 sm:!p-5">
        <p class="text-xs font-medium text-[#5C6169] dark:text-white/65">Hours worked</p>
        <p class="mt-2 flex items-baseline gap-1">
          <span class="text-2xl font-semibold text-[#17181B] dark:text-white tabular-nums leading-none">{{ viewMode === 'weekly' ? rosterStore.hoursWorked.toFixed(1) : rosterStore.monthlyHoursWorked.toFixed(1) }}</span>
          <span class="text-[13px] text-[#656A72] dark:text-white/55">hrs</span>
        </p>
        <p class="text-xs text-[#5C6169] dark:text-white/60 mt-2">this {{ viewMode === 'weekly' ? 'week' : 'month' }}</p>
      </div>

      <div class="rounded-[18px] p-4 sm:p-5 text-white bg-gradient-to-br from-accent to-accent-hover shadow-[0_14px_34px_-14px_rgb(var(--accent-rgb)/0.55)]">
        <p class="text-xs font-medium text-white/85">Target hours</p>
        <p class="text-2xl font-semibold tabular-nums leading-none mt-2">{{ viewMode === 'weekly' ? rosterStore.targetHours.toFixed(1) : rosterStore.monthlyTargetHours.toFixed(1) }}</p>
        <p class="text-xs text-white/85 mt-2 flex items-center gap-1.5">
          <span class="material-symbols-outlined !text-[14px]">info</span>
          {{ viewMode === 'weekly' ? rosterStore.remainingHours.toFixed(1) : rosterStore.monthlyRemainingHours.toFixed(1) }} remaining
        </p>
      </div>
    </div>

    <!-- ===== Week strip =====
         Seven columns at lg, a drag-scroller below it. -->
    <div
      v-if="viewMode === 'weekly'"
      ref="scrollContainer"
      class="flex lg:grid lg:grid-cols-7 gap-3 overflow-x-auto lg:overflow-visible pb-2 lg:pb-0 no-scrollbar select-none cursor-grab active:cursor-grabbing lg:cursor-default"
      @mousedown="handleMouseDown"
      @mouseleave="handleMouseLeave"
      @mouseup="handleMouseUp"
      @mousemove="handleMouseMove"
    >
      <div
        v-for="day in rosterStore.weeklySchedule"
        :key="day.date"
        :data-today="day.is_today"
        class="min-w-[170px] lg:min-w-0 flex flex-col rounded-[16px] p-3.5 transition-colors"
        :class="dayIsEmpty(day) ? 'border border-dashed border-black/[0.10] dark:border-white/[0.14]' : day.is_today ? 'border-2 border-accent bg-white dark:bg-surface-2 shadow-[0_10px_30px_-16px_rgb(var(--accent-rgb)/0.6)]' : 'border border-black/[0.07] dark:border-white/[0.08] bg-white dark:bg-surface-2'"
      >
        <!-- Date header -->
        <!-- flex-wrap: only the today cell carries both the chip and the add
             button, and at large text those two do not fit a 111px day cell.
             Wrapping costs nothing at normal size, where the row still fits. -->
        <div class="flex flex-wrap items-start justify-between gap-2 mb-3">
          <div>
            <p class="text-xs font-medium tracking-wide text-[#656A72] dark:text-white/55">
              {{ day.day_short }}
            </p>
            <p
              class="text-xl font-semibold tabular-nums leading-tight"
              :class="day.is_today ? 'text-accent dark:text-accent-light' : 'text-[#17181B] dark:text-white'"
            >
              {{ day.day_num }}
            </p>
          </div>
          <div class="flex items-center gap-1 shrink-0">
            <span v-if="day.is_today" class="premium-tag tag-accent !px-2 !py-0.5">Today</span>
            <button
              v-if="canAddOrRequestForDay(day)"
              @click.stop="handleAddShiftClick(day.date)"
              class="w-7 h-7 grid place-items-center rounded-full text-[#656A72] dark:text-white/60 hover:text-accent hover:bg-accent/[0.08] transition-colors"
              :title="canAssignShift ? 'Assign shift' : 'Request shift'"
              :aria-label="canAssignShift ? 'Assign shift' : 'Request shift'"
            >
              <span class="material-symbols-outlined !text-[18px]">add</span>
            </button>
          </div>
        </div>

        <!-- Holiday -->
        <div v-if="day.status === 'holiday'" class="flex-1 grid place-content-center text-center py-4">
          <span class="material-symbols-outlined !text-[22px] text-accent dark:text-accent-light mx-auto">celebration</span>
          <p class="text-[13px] font-medium text-[#17181B] dark:text-white mt-1.5">
            {{ day.shift?.shift_name || day.shift?.name || 'Holiday' }}
          </p>
          <p class="text-xs text-[#5C6169] dark:text-white/60 mt-0.5">Holiday</p>
        </div>

        <!-- Approved leave -->
        <div v-else-if="day.status === 'on_leave'" class="flex-1 grid place-content-center text-center py-4">
          <span class="material-symbols-outlined !text-[22px] text-[#D97706] mx-auto">park</span>
          <p class="text-[13px] font-medium text-[#17181B] dark:text-white mt-1.5">
            {{ day.shift?.shift_name || day.shift?.name || 'Leave' }}
          </p>
          <p class="text-xs text-[#5C6169] dark:text-white/60 mt-0.5">Approved leave</p>
        </div>

        <!-- Nothing rostered: weekend reads as weekend, a weekday as free -->
        <div v-else-if="dayIsEmpty(day)" class="flex-1 grid place-content-center text-center py-6">
          <span class="material-symbols-outlined !text-[22px] text-[#C4C7CC] dark:text-white/25 mx-auto">
            {{ isWeekend(day) ? 'bedtime' : 'light_mode' }}
          </span>
          <p class="text-xs font-medium tracking-wide text-[#656A72] dark:text-white/55 mt-1.5">
            {{ isWeekend(day) ? 'Weekend' : 'Off duty' }}
          </p>
        </div>

        <!-- Rostered shifts -->
        <div v-else class="flex-1 flex flex-col gap-2">
          <div
            v-for="(sh, idx) in (day.shifts || [day.shift])"
            :key="(sh?.shift_assignment || sh?.name) + idx"
            class="rounded-[12px] p-2.5 transition-colors"
            :class="[
              day.is_today ? 'bg-accent/[0.07]' : 'bg-black/[0.03] dark:bg-white/[0.05]',
              isShiftYetToAssign(sh) ? 'cursor-pointer hover:bg-black/[0.06] dark:hover:bg-white/[0.08] group/yet border border-dashed border-black/10 dark:border-white/15' : ''
            ]"
            @click="isShiftYetToAssign(sh) ? handleAddShiftClick(day.date) : null"
            :title="isShiftYetToAssign(sh) ? (canAssignShift ? 'Click to assign shift' : 'Click to request shift') : undefined"
          >
            <div class="flex items-center justify-between gap-1.5">
              <p class="text-[13px] font-medium text-[#17181B] dark:text-white leading-snug">
                {{ sh?.shift_name || sh?.name || '—' }}
              </p>
              <span
                v-if="isShiftYetToAssign(sh)"
                class="material-symbols-outlined !text-[16px] text-[#656A72] dark:text-white/50 group-hover/yet:text-accent transition-colors shrink-0"
                :title="canAssignShift ? 'Assign shift' : 'Request shift'"
              >
                add_circle
              </span>
            </div>
            <p class="text-xs text-[#5C6169] dark:text-white/65 tabular-nums mt-0.5">
              {{ sh?.start_time && sh?.end_time ? `${sh.start_time.slice(0, 5)} – ${sh.end_time.slice(0, 5)}` : '—' }}
            </p>

            <!-- State line. The reference's cards say where the day stands;
                 ours only ever said the shift's name and times. -->
            <p
              v-if="idx === 0"
              class="text-xs font-medium mt-2 flex items-center gap-1"
              :class="dayState(day).tone"
            >
              <span class="material-symbols-outlined !text-[14px]">{{ dayState(day).icon }}</span>
              {{ dayState(day).label }}
            </p>
          </div>

          <router-link
            v-if="day.is_today"
            to="/attendance?tab=timesheet"
            class="mt-auto btn-primary w-full"
          >
            <span class="material-symbols-outlined !text-[16px]">schedule</span>
            Open timesheet
          </router-link>
        </div>
      </div>
    </div>

    <!-- Monthly View — 7-column calendar grid -->
    <div v-if="viewMode === 'monthly'" class="bg-white dark:bg-white/5 rounded-[12px] shadow-sm overflow-hidden">
      <div v-if="rosterStore.monthlyLoading" class="p-8 text-center">
        <p class="text-[#656A72] dark:text-white/55 text-sm">Loading...</p>
      </div>
      <div v-else>
        <div class="grid grid-cols-7 border-b border-gray-100 dark:border-white/10">
          <div v-for="dow in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']" :key="dow" class="py-3 text-center text-xs font-semibold text-[#656A72] dark:text-white/55 uppercase tracking-wider">{{ dow }}</div>
        </div>
        <template v-for="week in calendarWeeks" :key="week[0].date">
          <div class="grid grid-cols-7 border-b border-gray-50 dark:border-white/5 last:border-b-0">
            <div v-for="day in week" :key="day.date" class="min-h-[72px] p-2 border-r border-gray-50 dark:border-white/5 last:border-r-0 transition-colors"
              :class="[ day.is_today ? 'bg-emerald-50/50 dark:bg-emerald-500/10' : '', !day.is_current_month ? 'bg-gray-50/30 dark:bg-white/[0.02]' : '', day.status === 'holiday' && day.is_current_month ? 'bg-blue-50/30 dark:bg-blue-500/5' : '', day.status === 'pending' && day.is_current_month ? 'bg-orange-50/30 dark:bg-orange-500/5' : '', ]"
            >
              <div class="flex items-center justify-between mb-1">
                <span class="text-sm font-semibold leading-none" :class="!day.is_current_month ? 'text-gray-300 dark:text-white/20' : day.is_today ? 'text-white bg-[#5B4BC4] dark:bg-emerald-500 rounded-full w-6 h-6 flex items-center justify-center' : 'text-gray-700 dark:text-white'">{{ day.day_num }}</span>
                <button
                  v-if="day.is_current_month && canAddOrRequestForDay(day)"
                  @click.stop="handleAddShiftClick(day.date)"
                  class="p-0.5 hover:bg-gray-100 dark:hover:bg-white/10 rounded-full text-[#656A72] dark:text-white/60 hover:text-accent dark:hover:text-accent-light flex items-center justify-center transition-colors"
                  :title="canAssignShift ? 'Assign shift' : 'Request shift'"
                  :aria-label="canAssignShift ? 'Assign shift' : 'Request shift'"
                >
                  <span class="material-symbols-outlined text-sm">add</span>
                </button>
              </div>
              <div v-if="!day.is_current_month" class="flex-1 flex items-center justify-center mt-1"><span class="text-xs text-gray-300 dark:text-white/10">—</span></div>
              <div v-else-if="day.status === 'holiday'" class="mt-0.5">
                <p class="text-xs font-semibold text-blue-600 dark:text-blue-400 leading-tight truncate">{{ day.shift?.shift_name || day.shift?.name }}</p>
                <p class="text-xs text-blue-500 dark:text-blue-400 mt-0.5 flex items-center gap-0.5"><span class="material-symbols-outlined text-xs">celebration</span>Holiday</p>
              </div>
              <div
                v-else-if="day.status === 'pending'"
                class="mt-0.5 cursor-pointer group/monthpending"
                @click="handleAddShiftClick(day.date)"
                :title="canAssignShift ? 'Assign shift' : 'Request shift'"
              >
                <div class="flex items-center justify-between gap-1">
                  <p class="text-xs font-semibold text-orange-600 dark:text-orange-400 leading-tight truncate">{{ day.shift?.shift_name || day.shift?.name }}</p>
                  <span class="material-symbols-outlined !text-[13px] text-orange-500/70 group-hover/monthpending:text-accent transition-colors">add</span>
                </div>
                <p class="text-xs text-orange-500 dark:text-orange-400 mt-0.5 flex items-center gap-0.5"><span class="material-symbols-outlined text-xs">schedule</span>Pending</p>
              </div>
              <div v-else-if="day.status === 'on_leave'" class="mt-0.5">
                <p class="text-xs font-semibold text-amber-600 dark:text-amber-400 leading-tight truncate">{{ day.shift?.shift_name || day.shift?.name }}</p>
                <p class="text-xs text-amber-500 dark:text-amber-400 mt-0.5">Leave</p>
              </div>
              <div v-else class="mt-0.5 space-y-1">
                <div v-for="(sh, idx) in (day.shifts || [day.shift])" :key="(sh?.shift_assignment || sh?.name) + idx" class="group/shift flex items-center justify-between gap-1">
                  <div
                    class="truncate"
                    :class="isShiftYetToAssign(sh) ? 'cursor-pointer hover:opacity-80' : ''"
                    @click="isShiftYetToAssign(sh) ? handleAddShiftClick(day.date) : null"
                    :title="isShiftYetToAssign(sh) ? (canAssignShift ? 'Click to assign shift' : 'Click to request shift') : undefined"
                  >
                    <p class="text-xs font-semibold text-[#5B4BC4] dark:text-emerald-400 leading-tight truncate">{{ sh?.shift_name || sh?.name || "—" }}</p>
                    <p v-if="sh?.start_time" class="text-xs text-[#656A72] dark:text-white/55 leading-none mt-0.5">{{ sh.start_time.slice(0, 5) }} – {{ sh.end_time.slice(0, 5) }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- Shift Request List -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
      <div>
        <h2 class="text-sm font-semibold text-[#17181B] dark:text-white">Shift requests</h2>
        <p class="text-xs text-[#5C6169] dark:text-white/60 mt-0.5">Your shift change requests and their status.</p>
      </div>
      <div class="flex items-center gap-3 flex-wrap">
        <div v-if="isShiftApprover" class="flex flex-col min-w-[200px]">
          <SearchableDropdown
            v-model="filterEmployee"
            :options="rosterStore.addRosterEmployees"
            labelKey="employee_name"
            valueKey="name"
            :showAllOption="true"
            allOptionLabel="All employees"
            placeholder="All employees" />
        </div>
        <div class="flex flex-col min-w-[150px]">
          <SearchableDropdown
            v-model="filterStatus"
            :options="['Draft', 'Approved', 'Rejected']"
            :showAllOption="true"
            allOptionLabel="All statuses"
            placeholder="All statuses" />
        </div>
      </div>
    </div>

    <DataTable
      v-if="pager.state.rows.length || pager.state.loading"
      :columns="listColumns"
      :rows="pager.state.rows"
      :actions="actionsForRow"
      :row-key="'name'"
      :loading="pager.state.loading"
      :total="pager.state.total"
      :page="pager.state.page"
      :page-size="pager.state.size"
      :empty-text="hasActiveFilter ? 'No matching shift requests' : 'No shift requests yet'"
      @update:page="pager.state.page = $event"
      @update:page-size="pager.setPageSize($event)"
    >
      <template #cell-name="{ row }">
        <span class="text-[13px] font-semibold font-mono text-accent dark:text-accent-light">{{ row.name }}</span>
      </template>
      <template #cell-employeeName="{ row }">
        <span class="font-medium">{{ row.employee_name || row.employee }}</span>
      </template>
      <template #cell-shift="{ row }">
        <div>
          <p class="font-medium">{{ row.shift_type }}</p>
          <p class="text-xs text-[#5C6169] dark:text-white/60 mt-0.5">
            {{ formatDate(row.from_date) }}<span v-if="row.to_date && row.to_date !== row.from_date"> — {{ formatDate(row.to_date) }}</span>
          </p>
        </div>
      </template>
      <template #cell-status="{ row }">
        <span class="premium-tag" :class="{ 'tag-amber': row.status === 'Draft', 'tag-emerald': row.status === 'Approved', 'tag-red': row.status === 'Rejected' }">
          {{ row.status }}
        </span>
      </template>
    </DataTable>

    <div v-else class="table-card empty-state">
      <template v-if="hasActiveFilter">
        <span class="material-symbols-outlined">search_off</span>
        <p class="empty-state-title">No matching shift requests</p>
        <p class="empty-state-text">Try a different employee or status.</p>
      </template>
      <template v-else>
        <span class="material-symbols-outlined">swap_horiz</span>
        <p class="empty-state-title">No shift requests yet</p>
        <button @click="openRequestModal()" class="mt-1 text-xs font-semibold text-accent dark:text-accent-light hover:underline">Request a shift change</button>
      </template>
    </div>

    <!-- Request Change Modal -->
    <CreateShiftRequest
      v-model="rosterStore.showRequestModal"
      :editId="rosterStore.editingRequestId"
      :isShiftApprover="isShiftApprover"
      :canAddRoster="canAssignShift"
      :selectedEmployeeForNew="selectedEmployee"
      :initialDate="requestInitialDate"
      @success="handleRequestSuccess"
    />

    <!-- Quick Assign Modal -->
    <CreateShiftAssignment
      v-model="rosterStore.showAddRosterModal"
      :initialData="quickAssignData"
      @success="handleAssignmentSuccess"
    />
  </div>
</template>

<script setup>
import { notify, ask } from '@/utils/feedback.js'
import DataTable from '@/components/DataTable.vue'
import { ref, computed, onMounted, nextTick, watch } from 'vue';
import { useEmployeeStore } from '@/stores/employee';
import { useRosterStore } from '@/stores/roster';
import { useAttendanceStore } from '@/stores/attendance';
import SearchableDropdown from '@/components/SearchableDropdown.vue';
import CreateShiftAssignment from '@/views/forms/roster/create_shift_assignment.vue';
import CreateShiftRequest from '@/views/forms/roster/create_shift_request.vue';
import { getErrorMessage } from '@/utils';
import SelectField from '../../../components/SelectField.vue'
import { useServerPager } from '@/composables/useServerPager'
import { call } from 'frappe-ui'

/* A day with no shifts is "empty" regardless of what the backend calls its
   status — the old markup treated 'pending' as an orange warning, which is how
   every Saturday ended up looking like a problem. */
/* One bar per rostered day. Scheduled is the full bar, worked is the fill, so
   an under-run reads as a gap rather than as a second number to compare. */
const chartDays = computed(() =>
	(rosterStore.weeklySchedule || [])
		.filter((d) => !dayIsEmpty(d))
		.map((d) => ({
			date: d.date,
			day_short: d.day_short,
			is_today: d.is_today,
			scheduled: Number(d.scheduled_hours ?? 0),
			actual: Number(d.actual_hours ?? 0),
		}))
);

const scheduledTotal = computed(() =>
	chartDays.value.reduce((sum, d) => sum + d.scheduled, 0)
);

const chartMax = computed(() =>
	Math.max(1, ...chartDays.value.map((d) => Math.max(d.scheduled, d.actual)))
);

function barHeight(hours) {
	return `${Math.max(6, (Number(hours || 0) / chartMax.value) * 100)}%`;
}

/* DEMO BUILD: there is no roster-report endpoint. Emits the week as CSV from
   what is already on screen so the button does something honest; devs should
   point this at the real export. */
function downloadRosterReport() {
	const rows = [['Date', 'Day', 'Scheduled hours', 'Worked hours']];
	for (const d of chartDays.value) rows.push([d.date, d.day_short, d.scheduled, d.actual]);
	const csv = rows.map((r) => r.join(',')).join('\n');
	const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
	const a = document.createElement('a');
	a.href = url;
	a.download = `roster-${chartDays.value[0]?.date || 'week'}.csv`;
	a.click();
	URL.revokeObjectURL(url);
}

const completedShifts = computed(() => {
	const today = new Date();
	today.setHours(0, 0, 0, 0);
	return (rosterStore.weeklySchedule || []).filter((d) => {
		if (dayIsEmpty(d)) return false;
		return new Date(d.date + 'T00:00:00') < today;
	}).length;
});
const completedPercent = computed(() => {
	const total = (rosterStore.weeklySchedule || []).filter((d) => !dayIsEmpty(d)).length;
	return total ? Math.round((completedShifts.value / total) * 100) : 0;
});

function dayIsEmpty(day) {
	const list = day?.shifts || (day?.shift ? [day.shift] : [])
	return list.filter(Boolean).length === 0
}

function isShiftYetToAssign(sh) {
	if (!sh) return true;
	const name = String(sh.shift_name || sh.name || '').trim().toLowerCase();
	return (
		name === 'yet to assign' ||
		name === 'pending' ||
		(!sh.start_time && !sh.end_time && !sh.shift_type && !sh.shift_assignment)
	);
}

function isYetToAssign(day) {
	if (!day) return false;
	if (day.status === 'holiday' || day.status === 'on_leave') return false;
	if (day.status === 'pending') return true;
	const list = day.shifts || (day.shift ? [day.shift] : []);
	if (list.length === 0) return true;
	return list.some((s) => isShiftYetToAssign(s));
}

function canAddOrRequestForDay(day) {
	if (!day) return false;
	return isYetToAssign(day) || dayIsEmpty(day) || day.status === 'holiday' || allowMultipleShifts.value;
}

function isWeekend(day) {
	if (!day?.date) return false
	const d = new Date(day.date + 'T00:00:00').getDay()
	return d === 0 || d === 6
}

/* Where the day stands, which is the thing the reference's cards lead with. */
function dayState(day) {
	if (day?.is_today) {
		return { label: 'Active shift', icon: 'radio_button_checked', tone: 'text-accent dark:text-accent-light' }
	}
	const today = new Date()
	today.setHours(0, 0, 0, 0)
	const d = new Date(day.date + 'T00:00:00')
	if (d < today) {
		return { label: 'Completed', icon: 'check_circle', tone: 'text-green-700 dark:text-green-400' }
	}
	return { label: 'Ready to start', icon: 'schedule', tone: 'text-[#5C6169] dark:text-white/60' }
}

const employeeStore = useEmployeeStore();
const rosterStore = useRosterStore();
const attendanceStore = useAttendanceStore();
const scrollContainer = ref(null);
const quickAssignData = ref({});

// Permissions
const canAddRoster = ref(false);
const canSubmitShiftAssignment = ref(false);
const allowMultipleShifts = ref(false);
const isShiftApprover = ref(false);
const canAssignShift = computed(() => Boolean(canSubmitShiftAssignment.value || canAddRoster.value));
const requestInitialDate = ref('');

// View state
const viewMode = ref('weekly');
const weekStart = ref(new Date());
const monthStart = ref(new Date());
const today = new Date().toISOString().split('T')[0];
const selectedEmployee = ref('');

// Filters
const filterEmployee = ref('');
const filterStatus = ref('');

// Approve/reject state
const updatingStatusId = ref(null);
const targetStatus = ref(null);

// Drag-to-scroll
const isMouseDown = ref(false);
let startX = 0;
let scrollLeft = 0;

// Server-side pagination for shift requests
async function fetchShiftRequestsPage(page, pageSize) {
  const res = await call('arijentek_core.api.roster.get_shift_requests_list', {
    page,
    page_size: pageSize,
    status: filterStatus.value || undefined,
    employee: filterEmployee.value || undefined,
  });
  return { rows: res.data || [], total: Number(res.total) || 0 };
}

const pager = useServerPager((page, size) => fetchShiftRequestsPage(page, size), { size: 10 });
const hasActiveFilter = computed(() => Boolean(filterEmployee.value || filterStatus.value));

const listColumns = [
  { key: 'name', label: 'Reference' },
  { key: 'employeeName', label: 'Employee' },
  { key: 'shift', label: 'Shift request' },
  { key: 'status', label: 'Status' },
];

function actionsForRow(row) {
  const canEditDelete = row.status === 'Draft' && (row.employee === employeeStore.employee?.name || row.can_approve);
  return [
    { label: 'Approve', icon: 'check', show: row.status === 'Draft' && row.can_approve, disabled: updatingStatusId.value === row.name, onClick: () => handleApproveReject(row.name, 'Approved') },
    { label: 'Reject', icon: 'close', show: row.status === 'Draft' && row.can_approve, disabled: updatingStatusId.value === row.name, onClick: () => handleApproveReject(row.name, 'Rejected') },
    { label: 'Edit', icon: 'edit', show: canEditDelete, onClick: () => handleEdit(row.name) },
    { label: 'Delete', icon: 'delete', danger: true, show: canEditDelete, disabled: rosterStore.cancelingId === row.name, onClick: () => handleDelete(row.name) },
  ];
}

watch([filterEmployee, filterStatus], () => {
  if (pager.state.page !== 1) pager.state.page = 1;
  else pager.fetchPage();
});

// Calendar
const calendarWeeks = computed(() => {
  const days = rosterStore.monthlyCalendar;
  if (!days.length) return [];
  const weeks = [];
  for (let i = 0; i < days.length; i += 7) weeks.push(days.slice(i, i + 7));
  return weeks;
});

const rangeDisplay = computed(() => {
  const opts = { month: 'short', day: 'numeric' };
  if (viewMode.value === 'weekly') {
    const start = weekStart.value;
    const end = new Date(start);
    end.setDate(end.getDate() + 6);
    return `${start.toLocaleDateString('en-US', opts)} – ${end.toLocaleDateString('en-US', opts)}, ${end.getFullYear()}`;
  }
  return monthStart.value.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
});

function getWeekStart(date) {
  const d = new Date(date);
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  return new Date(d.setDate(diff));
}

function toStr(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

async function loadWeek() {
  const empId = selectedEmployee.value || employeeStore.employee?.name;
  if (!empId) return;
  await rosterStore.fetchWeekly(empId, toStr(weekStart.value));
}

async function loadMonth() {
  const empId = selectedEmployee.value || employeeStore.employee?.name;
  if (!empId) return;
  await rosterStore.fetchMonthly(empId, monthStart.value.getFullYear(), monthStart.value.getMonth() + 1);
}

async function snapToToday() {
  await nextTick();
  if (!scrollContainer.value) return;
  const todayEl = scrollContainer.value.querySelector('[data-today]');
  if (todayEl) todayEl.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
}

async function goToPrev() {
  if (viewMode.value === 'weekly') {
    const d = new Date(weekStart.value); d.setDate(d.getDate() - 7); weekStart.value = d;
    await loadWeek(); snapToToday();
  } else {
    const d = new Date(monthStart.value); d.setMonth(d.getMonth() - 1); monthStart.value = d;
    await loadMonth();
  }
}

async function goToNext() {
  if (viewMode.value === 'weekly') {
    const d = new Date(weekStart.value); d.setDate(d.getDate() + 7); weekStart.value = d;
    await loadWeek(); snapToToday();
  } else {
    const d = new Date(monthStart.value); d.setMonth(d.getMonth() + 1); monthStart.value = d;
    await loadMonth();
  }
}

async function goToToday() {
  if (viewMode.value === 'weekly') {
    weekStart.value = getWeekStart(new Date()); await loadWeek(); snapToToday();
  } else {
    monthStart.value = new Date(); await loadMonth(); await snapToToday();
  }
}

watch(viewMode, (newMode) => {
  const empId = selectedEmployee.value || employeeStore.employee?.name;
  if (newMode === 'monthly' && empId) { monthStart.value = new Date(); loadMonth(); snapToToday(); }
});

watch(selectedEmployee, async (newEmp) => {
  if (newEmp) {
    await attendanceStore.init(newEmp);
    if (viewMode.value === 'weekly') await loadWeek(); else await loadMonth();
  }
});

// Drag-to-scroll handlers
function handleMouseDown(e) {
  if (!scrollContainer.value) return;
  isMouseDown.value = true;
  startX = e.pageX - scrollContainer.value.offsetLeft;
  scrollLeft = scrollContainer.value.scrollLeft;
}
function handleMouseLeave() { isMouseDown.value = false; }
function handleMouseUp() { isMouseDown.value = false; }
function handleMouseMove(e) {
  if (!isMouseDown.value || !scrollContainer.value) return;
  e.preventDefault();
  const x = e.pageX - scrollContainer.value.offsetLeft;
  scrollContainer.value.scrollLeft = scrollLeft - (x - startX) * 1.5;
}

function handleEdit(name) { openRequestModal(name); }
async function handleDelete(name) { await rosterStore.handleCancelRequest(name); await pager.fetchPage(); }

async function handleApproveReject(id, status) {
  const action = status === 'Approved' ? 'approve' : 'reject';
  if (!await ask(`Are you sure you want to ${action} this shift request?`)) return;

  updatingStatusId.value = id; targetStatus.value = status;
  try {
    await rosterStore.updateRequestStatus(id, status);
    if (status === 'Approved') await loadWeek();
    await pager.fetchPage();
  } catch (err) {
    notify(getErrorMessage(err, 'Failed to update status'));
  } finally { updatingStatusId.value = null; targetStatus.value = null; }
}

// Request modal
function openRequestModal(editId = null, date = '') {
  requestInitialDate.value = date;
  rosterStore.editingRequestId = editId;
  rosterStore.showRequestModal = true;
}

function handleAddShiftClick(date) {
  if (canAssignShift.value) {
    openAddRosterForDate(date);
  } else {
    openRequestModal(null, date);
  }
}

async function handleRequestSuccess() {
  if (viewMode.value === 'weekly') await loadWeek(); else await loadMonth();
  await pager.fetchPage();
}

// Add roster modal
function openRosterModal() { 
  const empId = selectedEmployee.value || employeeStore.employee?.name || '';
  const empName = rosterStore.addRosterEmployees.find(e => e.name === empId)?.employee_name || empId;
  quickAssignData.value = {
    empId,
    empName,
    date: today,
    endDate: today
  };
  rosterStore.showAddRosterModal = true; 
}

function openAddRosterForDate(date) {
  const empId = selectedEmployee.value || employeeStore.employee?.name || '';
  const empName = rosterStore.addRosterEmployees.find(e => e.name === empId)?.employee_name || empId;
  quickAssignData.value = {
    empId,
    empName,
    date,
    endDate: date
  };
  rosterStore.showAddRosterModal = true;
}

async function handleAssignmentSuccess() {
  if (viewMode.value === 'weekly') await loadWeek(); else await loadMonth();
}

onMounted(async () => {
  await employeeStore.init();
  weekStart.value = getWeekStart(new Date());
  monthStart.value = new Date();

  try { canAddRoster.value = await rosterStore.checkCanAddRoster(); } catch { canAddRoster.value = false; }
  try { canSubmitShiftAssignment.value = await rosterStore.checkCanSubmitShiftAssignment(); } catch { canSubmitShiftAssignment.value = false; }
  try { isShiftApprover.value = await rosterStore.checkIsShiftApprover(); if (isShiftApprover.value) await rosterStore.fetchAddRosterEmployees(); } catch { isShiftApprover.value = false; }
  try { allowMultipleShifts.value = await rosterStore.checkAllowMultipleShifts(); } catch { allowMultipleShifts.value = false; }

  if (employeeStore.employee?.name) selectedEmployee.value = employeeStore.employee.name;
  if (selectedEmployee.value) {
    await attendanceStore.init(selectedEmployee.value);
    await loadWeek();
  }
  await pager.fetchPage();
});
</script>

<style scoped>
.no-scrollbar::-webkit-scrollbar { display: none; }
.no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
</style>
