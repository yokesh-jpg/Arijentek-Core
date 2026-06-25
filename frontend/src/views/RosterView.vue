<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { attendanceApi } from "../services/api";
import { CalendarDays, ChevronDown, ChevronLeft, ChevronRight, Users } from "lucide-vue-next";

const loading = ref(true);

const _today = new Date();
const selectedMonth = ref(_today.getMonth() + 1);
const selectedYear = ref(_today.getFullYear());
const filterEmployee = ref("");
const reportingEmployees = ref<any[]>([]);

async function fetchReportingEmployees() {
  try {
    const data = await attendanceApi.getShiftApproverEmployees();
    reportingEmployees.value = Array.isArray(data) ? data : [];
  } catch (e) {
    console.error("Failed to load shift approver employees:", e);
  }
}

interface RosterDate {
  date: string;
  day: number;
  weekday: string;
  is_weekend: boolean;
}

interface EmployeeDateStatus {
  date: string;
  status: string;
  hours: number;
  is_weekend: boolean;
}

interface RosterEmployee {
  employee: string;
  employee_name: string;
  designation: string;
  shift: string;
  dates: EmployeeDateStatus[];
}

const employees = ref<RosterEmployee[]>([]);
const dates = ref<RosterDate[]>([]);
const holidays = ref<Record<string, { description: string; weekly_off: boolean }>>({});

const monthOptions = computed(() => {
  const opts: { value: string; label: string; month: number; year: number }[] = [];
  const now = new Date();
  for (let offset = -6; offset <= 2; offset++) {
    const d = new Date(now.getFullYear(), now.getMonth() + offset, 1);
    const m = d.getMonth() + 1;
    const y = d.getFullYear();
    opts.push({
      value: `${y}-${m}`,
      label: d.toLocaleDateString("en-US", { month: "long", year: "numeric" }),
      month: m,
      year: y,
    });
  }
  return opts;
});

const selectedMonthKey = computed({
  get: () => `${selectedYear.value}-${selectedMonth.value}`,
  set: (val: string) => {
    const [y, m] = val.split("-").map(Number);
    selectedYear.value = y;
    selectedMonth.value = m;
  },
});

function statusClass(status: string): string {
  const map: Record<string, string> = {
    Present: "status-present",
    Absent: "status-absent",
    "Half Day": "status-halfday",
    "On Leave": "status-leave",
    WO: "status-wo",
    H: "status-holiday",
    "-": "status-empty",
  };
  return map[status] || "status-empty";
}

function getThStatusClass(dateStr: string): string {
  if (employees.value.length !== 1) return "";
  const emp = employees.value[0];
  const dateStatus = emp.dates.find((d) => d.date === dateStr);
  if (!dateStatus) return "";
  
  const map: Record<string, string> = {
    Present: "th-status-present",
    Absent: "th-status-absent",
    "Half Day": "th-status-halfday",
    "On Leave": "th-status-leave",
    WO: "th-status-wo",
    H: "th-status-holiday",
  };
  return map[dateStatus.status] || "";
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    Present: "P",
    Absent: "A",
    "Half Day": "HD",
    "On Leave": "L",
    WO: "WO",
    H: "H",
    "-": "—",
  };
  return map[status] || status.charAt(0);
}

function statusTooltip(status: string, date: string): string {
  const holiday = holidays.value[date];
  if (holiday) return `${status} — ${holiday.description}`;
  return status;
}

async function loadData() {
  loading.value = true;
  try {
    const data = await attendanceApi.getRoster(
      selectedMonth.value,
      selectedYear.value,
      filterEmployee.value
    );
    if (data) {
      employees.value = data.employees || [];
      dates.value = data.dates || [];
      holidays.value = data.holidays || {};
    }
  } catch (e) {
    console.error("Roster load error", e);
  } finally {
    loading.value = false;
  }
}

function prevMonth() {
  if (selectedMonth.value === 1) {
    selectedMonth.value = 12;
    selectedYear.value -= 1;
  } else {
    selectedMonth.value -= 1;
  }
}

function nextMonth() {
  if (selectedMonth.value === 12) {
    selectedMonth.value = 1;
    selectedYear.value += 1;
  } else {
    selectedMonth.value += 1;
  }
}

const scrollContainer = ref<HTMLDivElement | null>(null);
let isDown = false;
let startX = 0;
let scrollLeft = 0;

function onMouseDown(e: MouseEvent) {
  if (!scrollContainer.value) return;
  isDown = true;
  scrollContainer.value.classList.add("active-drag");
  startX = e.pageX - scrollContainer.value.offsetLeft;
  scrollLeft = scrollContainer.value.scrollLeft;
}

function onMouseLeave() {
  isDown = false;
  if (scrollContainer.value) {
    scrollContainer.value.classList.remove("active-drag");
  }
}

function onMouseUp() {
  isDown = false;
  if (scrollContainer.value) {
    scrollContainer.value.classList.remove("active-drag");
  }
}

function onMouseMove(e: MouseEvent) {
  if (!isDown || !scrollContainer.value) return;
  e.preventDefault();
  const x = e.pageX - scrollContainer.value.offsetLeft;
  const walk = (x - startX) * 1.5; // adjust scroll speed multiplier as desired
  scrollContainer.value.scrollLeft = scrollLeft - walk;
}

watch([selectedMonth, selectedYear, filterEmployee], loadData);

onMounted(async () => {
  await fetchReportingEmployees();
  await loadData();
});
</script>

<template>
  <div>
    <!-- Header -->
    <div
      class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8 animate-fade-in"
    >
      <div>
        <h1 class="text-2xl sm:text-3xl font-bold text-white">Roster</h1>
        <p class="text-sm text-slate-500 mt-1">Department attendance overview</p>
      </div>
      <div class="flex items-center gap-2">
        <!-- Employee Filter -->
        <div v-if="reportingEmployees.length > 0" class="relative">
          <select
            v-model="filterEmployee"
            class="input-dark appearance-none pr-8 pl-3 py-2 text-sm cursor-pointer min-w-[180px] border border-white/10 rounded-lg"
          >
            <option value="">All Team Members</option>
            <option v-for="emp in reportingEmployees" :key="emp.name" :value="emp.name">
              {{ emp.employee_name }}
            </option>
          </select>
          <ChevronDown
            :size="14"
            class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none"
          />
        </div>

        <button
          @click="prevMonth"
          class="p-2 rounded-lg bg-white/[0.04] text-slate-400 hover:bg-white/[0.08] hover:text-white transition-all"
        >
          <ChevronLeft :size="18" />
        </button>
        <div class="relative">
          <select
            v-model="selectedMonthKey"
            class="input-dark appearance-none pr-8 pl-3 py-2 text-sm cursor-pointer min-w-[180px] border border-white/10 rounded-lg"
          >
            <option v-for="opt in monthOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
          <ChevronDown
            :size="14"
            class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none"
          />
        </div>
        <button
          @click="nextMonth"
          class="p-2 rounded-lg bg-white/[0.04] text-slate-400 hover:bg-white/[0.08] hover:text-white transition-all"
        >
          <ChevronRight :size="18" />
        </button>
      </div>
    </div>

    <!-- Legend -->
    <div class="flex flex-wrap gap-4 mb-6 bg-white/[0.02] border border-white/[0.04] p-3 px-4 rounded-xl w-max">
      <div
        v-for="item in [
          { label: 'Present', status: 'Present' },
          { label: 'Absent', status: 'Absent' },
          { label: 'Half Day', status: 'Half Day' },
          { label: 'On Leave', status: 'On Leave' },
          { label: 'Weekly Off', status: 'WO' },
          { label: 'Holiday', status: 'H' },
        ]"
        :key="item.status"
        class="flex items-center gap-2 text-xs text-slate-400"
      >
        <div
          class="status-badge legend-badge"
          :class="statusClass(item.status)"
        >
          {{ statusLabel(item.status) }}
        </div>
        <span class="font-medium text-slate-400">{{ item.label }}</span>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="w-10 h-10 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
    </div>

    <!-- Roster Grid -->
    <div v-else-if="employees.length" class="glass-card overflow-hidden animate-slide-up">
      <div
        ref="scrollContainer"
        class="overflow-x-auto drag-scroll-container"
        @mousedown="onMouseDown"
        @mouseleave="onMouseLeave"
        @mouseup="onMouseUp"
        @mousemove="onMouseMove"
      >
        <table class="w-full border-collapse" style="min-width: 800px">
          <thead>
            <tr class="border-b border-white/[0.06]">
              <th
                class="sticky-col text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 py-3 min-w-[180px]"
              >
                Employee
              </th>
              <th
                v-for="d in dates"
                :key="d.date"
                class="text-center px-1 py-3 min-w-[34px] col-border select-none th-status-transition"
                :class="[
                  d.is_weekend ? 'weekend-col' : '',
                  employees.length === 1 ? getThStatusClass(d.date) : ''
                ]"
                :title="holidays[d.date] ? holidays[d.date].description : undefined"
              >
                <div class="text-[9px] font-semibold tracking-wider text-slate-500 uppercase">
                  {{ d.weekday.charAt(0) }}
                </div>
                <div
                  class="text-[12px] font-bold mt-0.5 th-day-num"
                  :style="employees.length === 1 ? {} : { color: d.is_weekend ? 'var(--accent)' : 'var(--text-secondary)' }"
                >
                  {{ d.day }}
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="emp in employees"
              :key="emp.employee"
              class="border-b border-white/[0.03] transition-colors"
            >
              <td class="sticky-col px-4 py-3">
                <p class="text-sm font-medium text-white truncate max-w-[160px]">
                  {{ emp.employee_name }}
                </p>
                <p class="text-[10px] text-slate-500 truncate mt-0.5">{{ emp.shift }}</p>
              </td>
              <td
                v-for="d in emp.dates"
                :key="d.date"
                class="text-center px-0.5 py-1.5 col-border"
                :class="[d.is_weekend ? 'weekend-col' : '']"
                :title="statusTooltip(d.status, d.date)"
              >
                <div
                  class="status-badge mx-auto"
                  :class="statusClass(d.status)"
                >
                  {{ statusLabel(d.status) }}
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="glass-card p-12 text-center">
      <Users :size="40" class="mx-auto text-slate-600 mb-3" />
      <h3 class="text-lg font-medium text-white mb-1">No roster data</h3>
      <p class="text-slate-500 text-sm">No employees found</p>
    </div>
  </div>
</template>

<style scoped>
.drag-scroll-container {
  cursor: grab;
  user-select: none;
  -webkit-user-select: none;
}
.drag-scroll-container.active-drag {
  cursor: grabbing;
}

/* --- Readability & Premium UI Improvements --- */

/* Sticky column setup */
.sticky-col {
  position: sticky;
  left: 0;
  z-index: 10;
  background-color: var(--surface) !important;
  border-right: 1px solid var(--border-color);
}

.sticky-col::after {
  content: '';
  position: absolute;
  top: 0;
  right: -5px;
  bottom: 0;
  width: 5px;
  background: linear-gradient(to right, rgba(0, 0, 0, 0.2), transparent);
  pointer-events: none;
  opacity: 0.8;
}

:global(.light-mode) .sticky-col::after {
  background: linear-gradient(to right, rgba(0, 0, 0, 0.05), transparent);
}

/* Row hover highlight including the sticky cell */
tr:hover td {
  background-color: var(--row-hover);
}

tr:hover td.sticky-col {
  background-color: var(--surface-50) !important;
}

/* Column vertical borders for visual alignment tracking */
.col-border {
  border-right: 1px solid rgba(255, 255, 255, 0.03);
}

:global(.light-mode) .col-border {
  border-right: 1px solid rgba(0, 0, 0, 0.04);
}

/* Weekend column background highlighting */
.weekend-col {
  background-color: rgba(255, 255, 255, 0.015) !important;
}

:global(.light-mode) .weekend-col {
  background-color: rgba(0, 0, 0, 0.015) !important;
}

/* Premium Status Badges styling */
.status-badge {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  border-radius: 6px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid transparent;
  user-select: none;
}

.status-badge:hover {
  transform: scale(1.15);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.legend-badge {
  width: 22px;
  height: 22px;
  font-size: 9px;
  pointer-events: none;
}

.status-present {
  color: var(--success-text);
  background-color: var(--success-bg);
  border-color: rgba(34, 197, 94, 0.2);
}

.status-absent {
  color: var(--danger-text);
  background-color: var(--danger-bg);
  border-color: rgba(239, 68, 68, 0.2);
}

.status-halfday {
  color: var(--warning-text);
  background-color: var(--warning-bg);
  border-color: rgba(245, 158, 11, 0.2);
}

.status-leave {
  color: var(--info-text);
  background-color: var(--info-bg);
  border-color: rgba(59, 130, 246, 0.2);
}

.status-wo {
  color: var(--text-secondary);
  background-color: var(--neutral-bg);
  border-color: var(--border-color);
}

.status-holiday {
  color: #c084fc;
  background-color: rgba(168, 85, 247, 0.15);
  border-color: rgba(168, 85, 247, 0.25);
}

:global(.light-mode) .status-holiday {
  color: #7e22ce;
  background-color: rgba(168, 85, 247, 0.1);
  border-color: rgba(168, 85, 247, 0.15);
}

.status-empty {
  color: var(--text-tertiary);
  background-color: transparent;
  border-color: transparent;
  opacity: 0.3;
}

/* Dynamic TH Status Colors when showing only 1 employee */
.th-status-transition {
  transition: background-color 0.25s ease, border-bottom-color 0.25s ease;
}

.th-status-present {
  background-color: rgba(34, 197, 94, 0.04) !important;
  border-bottom: 2px solid var(--success-text) !important;
}
.th-status-present .th-day-num {
  color: var(--success-text) !important;
}

.th-status-absent {
  background-color: rgba(239, 68, 68, 0.04) !important;
  border-bottom: 2px solid var(--danger-text) !important;
}
.th-status-absent .th-day-num {
  color: var(--danger-text) !important;
}

.th-status-halfday {
  background-color: rgba(245, 158, 11, 0.04) !important;
  border-bottom: 2px solid var(--warning-text) !important;
}
.th-status-halfday .th-day-num {
  color: var(--warning-text) !important;
}

.th-status-leave {
  background-color: rgba(59, 130, 246, 0.04) !important;
  border-bottom: 2px solid var(--info-text) !important;
}
.th-status-leave .th-day-num {
  color: var(--info-text) !important;
}

.th-status-wo {
  background-color: rgba(100, 116, 139, 0.02) !important;
  border-bottom: 2px solid var(--text-tertiary) !important;
}
.th-status-wo .th-day-num {
  color: var(--text-secondary) !important;
}

.th-status-holiday {
  background-color: rgba(168, 85, 247, 0.04) !important;
  border-bottom: 2px solid #c084fc !important;
}
.th-status-holiday .th-day-num {
  color: #c084fc !important;
}

:global(.light-mode) .th-status-holiday {
  border-bottom-color: #7e22ce !important;
}
:global(.light-mode) .th-status-holiday .th-day-num {
  color: #7e22ce !important;
}
</style>
