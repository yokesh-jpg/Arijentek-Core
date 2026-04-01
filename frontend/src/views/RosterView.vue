<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { attendanceApi } from "../services/api";
import { CalendarDays, ChevronDown, ChevronLeft, ChevronRight, Users } from "lucide-vue-next";

const loading = ref(true);

const _today = new Date();
const selectedMonth = ref(_today.getMonth() + 1);
const selectedYear = ref(_today.getFullYear());

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

function statusColor(status: string): string {
  const map: Record<string, string> = {
    Present: "#22c55e",
    Absent: "#ef4444",
    "Half Day": "#f59e0b",
    "On Leave": "#3b82f6",
    WO: "#6b7280",
    H: "#a855f7",
    "-": "transparent",
  };
  return map[status] || "#374151";
}

function statusBg(status: string): string {
  const map: Record<string, string> = {
    Present: "rgba(34,197,94,0.15)",
    Absent: "rgba(239,68,68,0.15)",
    "Half Day": "rgba(245,158,11,0.15)",
    "On Leave": "rgba(59,130,246,0.15)",
    WO: "rgba(107,114,128,0.1)",
    H: "rgba(168,85,247,0.15)",
    "-": "rgba(255,255,255,0.02)",
  };
  return map[status] || "rgba(255,255,255,0.03)";
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
    const data = await attendanceApi.getRoster(selectedMonth.value, selectedYear.value);
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

watch([selectedMonth, selectedYear], loadData);
onMounted(loadData);
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
    <div class="flex flex-wrap gap-3 mb-6">
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
          class="w-5 h-5 rounded-md flex items-center justify-center text-[9px] font-bold"
          :style="{ backgroundColor: statusBg(item.status), color: statusColor(item.status) }"
        >
          {{ statusLabel(item.status) }}
        </div>
        {{ item.label }}
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="w-10 h-10 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
    </div>

    <!-- Roster Grid -->
    <div v-else-if="employees.length" class="glass-card overflow-hidden animate-slide-up">
      <div class="overflow-x-auto">
        <table class="w-full border-collapse" style="min-width: 800px">
          <thead>
            <tr class="border-b border-white/[0.06]">
              <th
                class="sticky left-0 z-10 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 py-3 min-w-[180px]"
                :style="{
                  backgroundColor: 'var(--surface)',
                  borderRight: '1px solid var(--border-color)',
                }"
              >
                Employee
              </th>
              <th
                v-for="d in dates"
                :key="d.date"
                class="text-center text-[10px] font-semibold uppercase tracking-wider px-1 py-3 min-w-[32px]"
                :style="{ color: d.is_weekend ? 'var(--accent)' : 'var(--text-tertiary)' }"
              >
                <div>{{ d.weekday.charAt(0) }}</div>
                <div
                  class="text-[11px] font-bold"
                  :style="{ color: d.is_weekend ? 'var(--accent)' : 'var(--text-secondary)' }"
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
              class="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors"
            >
              <td
                class="sticky left-0 z-10 px-4 py-3"
                :style="{
                  backgroundColor: 'var(--surface)',
                  borderRight: '1px solid var(--border-color)',
                }"
              >
                <p class="text-sm font-medium text-white truncate max-w-[160px]">
                  {{ emp.employee_name }}
                </p>
                <p class="text-[10px] text-slate-500 truncate">{{ emp.shift }}</p>
              </td>
              <td
                v-for="d in emp.dates"
                :key="d.date"
                class="text-center px-0.5 py-2"
                :title="statusTooltip(d.status, d.date)"
              >
                <div
                  class="w-7 h-7 mx-auto rounded-md flex items-center justify-center text-[10px] font-bold cursor-default transition-all hover:scale-110"
                  :style="{
                    backgroundColor: statusBg(d.status),
                    color: statusColor(d.status),
                  }"
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
      <p class="text-slate-500 text-sm">No employees found in your department</p>
    </div>
  </div>
</template>
