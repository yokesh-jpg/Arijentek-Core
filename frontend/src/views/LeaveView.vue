<script setup lang="ts">
import { ref, onMounted, computed, onBeforeUnmount, watch } from "vue";
import { leaveApi, dashboardApi, managerApi, useCachedFetch } from "../services/api";
import { useAuthStore } from "../stores/auth";
import {
  Palmtree,
  Plus,
  X,
  Calendar,
  Clock,
  User,
  Briefcase,
  ChevronDown,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Loader2,
  Edit,
  Trash2,
  MoreVertical,
  FileText,
} from "lucide-vue-next";

const loading = ref(true);
const balance = ref<{ leave_type: string; balance: number; allocated: number }[]>([]);
const applications = ref<any[]>([]);
const leaveTypes = ref<string[]>([]);
const holidays = ref<{ holiday_date: string; description: string; weekly_off?: number }[]>([]);
const manager = ref<any>(null);

function getLeaveTypeLabel(leaveType: string): string {
  const item = balance.value.find((b) => b.leave_type === leaveType);
  return item ? `${leaveType} - ${item.balance}` : `${leaveType} - 0`;
}

const authStore = useAuthStore();

let isMounted = true;

// Holidays month filter
const _today = new Date();
const holidaysMonthFilter = ref<string>(
  `${_today.getFullYear()}-${String(_today.getMonth() + 1).padStart(2, "0")}`
);

// Apply form
const showApplyForm = ref(false);
const applyLoading = ref(false);
const applyError = ref("");
const applySuccess = ref("");
const isEditing = ref(false);
const editLeaveName = ref("");
const form = ref({
  leave_type: "",
  from_date: "",
  to_date: "",
  half_day: 0,
  reason: "",
});

const totalBalance = computed(() => balance.value.reduce((s, b) => s + b.balance, 0));

const holidaysMonthOptions = computed(() => {
  const now = new Date();
  const year = now.getFullYear();
  const opts: { value: string; label: string }[] = [{ value: "", label: "All months" }];
  for (let y = year; y <= year + 1; y++) {
    for (let m = 1; m <= 12; m++) {
      const value = `${y}-${String(m).padStart(2, "0")}`;
      const d = new Date(y, m - 1, 1);
      opts.push({
        value,
        label: d.toLocaleDateString("en-US", { month: "long", year: "numeric" }),
      });
    }
  }
  return opts;
});

const filteredHolidays = computed(() => {
  const list = holidays.value;
  if (!holidaysMonthFilter.value) return list;
  return list.filter((h) => h.holiday_date.startsWith(holidaysMonthFilter.value));
});

// Colors for leave types
const typeColorVars = [
  { bg: "rgba(20,184,166,0.1)", text: "var(--accent)", ring: "rgba(20,184,166,0.2)" },
  { bg: "var(--info-bg)", text: "var(--info-text)", ring: "rgba(59,130,246,0.2)" },
  { bg: "rgba(168,85,247,0.1)", text: "#a855f7", ring: "rgba(168,85,247,0.2)" },
  { bg: "var(--warning-bg)", text: "var(--warning-text)", ring: "rgba(245,158,11,0.2)" },
  { bg: "var(--danger-bg)", text: "var(--danger-text)", ring: "rgba(239,68,68,0.2)" },
  { bg: "var(--success-bg)", text: "var(--success-text)", ring: "rgba(34,197,94,0.2)" },
];
function getTypeColor(idx: number) {
  return typeColorVars[idx % typeColorVars.length];
}

const statusColorMap: Record<string, { bg: string; text: string }> = {
  Open: { bg: "var(--warning-bg)", text: "var(--warning-text)" },
  Approved: { bg: "var(--success-bg)", text: "var(--success-text)" },
  Rejected: { bg: "var(--danger-bg)", text: "var(--danger-text)" },
  Cancelled: { bg: "var(--neutral-bg)", text: "var(--neutral-text)" },
};
function getStatusStyle(status: string) {
  return statusColorMap[status] || statusColorMap["Cancelled"];
}

function statusIcon(status: string) {
  const m: Record<string, any> = {
    Open: Clock,
    Approved: CheckCircle2,
    Rejected: XCircle,
    Cancelled: XCircle,
  };
  return m[status] || Clock;
}

function getDefaultDateRange() {
  const now = new Date();
  const year = now.getFullYear();
  return { from: `${year}-01-01`, to: `${year}-12-31` };
}

// Filters & Employee state
const isSystemManager = computed(() => authStore.isSystemManager);
const leaveEmployees = ref<any[]>([]);
const selectedEmployee = ref<string>("");

const filterStatus = ref("");
const filterFromDate = ref("");
const filterToDate = ref("");
const selectedPreset = ref("All Time");
const showDropdown = ref(false);

const activeDropdown = ref<string | null>(null);

// Leave detail popup modal state
const showLeaveDetailModal = ref(false);
const selectedLeave = ref<any>(null);

function openLeaveDetail(app: any) {
  selectedLeave.value = app;
  showLeaveDetailModal.value = true;
}

function formatDate(dateStr: string) {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

// Delete popup confirmation state
const showDeletePopup = ref(false);
const deleteLoading = ref(false);
const leaveToDelete = ref<any>(null);
const deleteError = ref("");

const processing = ref<string | null>(null);

async function fetchLeaveEmployees() {
  try {
    const data = await managerApi.getLeaveApproverEmployees();
    leaveEmployees.value = Array.isArray(data) ? data : [];
  } catch (e) {
    console.error("Failed to load leave employees:", e);
  }
}

function applyPreset(preset: string) {
  selectedPreset.value = preset;
  if (preset === "Custom Range") {
    return;
  }
  
  const today = new Date();
  let from: Date | null = null;
  let to: Date | null = null;
  
  switch (preset) {
    case "Today":
      from = new Date(today);
      to = new Date(today);
      break;
    case "Yesterday":
      from = new Date(today);
      from.setDate(today.getDate() - 1);
      to = new Date(from);
      break;
    case "Last 7 Days":
      from = new Date(today);
      from.setDate(today.getDate() - 6);
      to = new Date(today);
      break;
    case "Last 30 Days":
      from = new Date(today);
      from.setDate(today.getDate() - 29);
      to = new Date(today);
      break;
    case "This Month":
      from = new Date(today.getFullYear(), today.getMonth(), 1);
      to = new Date(today.getFullYear(), today.getMonth() + 1, 0);
      break;
    case "Last Month":
      from = new Date(today.getFullYear(), today.getMonth() - 1, 1);
      to = new Date(today.getFullYear(), today.getMonth(), 0);
      break;
    case "All Time":
    default:
      from = null;
      to = null;
      break;
  }
  
  filterFromDate.value = from ? formatDateToISO(from) : "";
  filterToDate.value = to ? formatDateToISO(to) : "";
  showDropdown.value = false;
}

function formatDateToISO(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function handleWindowClick(e: MouseEvent) {
  const target = e.target as HTMLElement;
  if (!target.closest(".date-picker-container")) {
    showDropdown.value = false;
  }
  if (!target.closest(".action-dropdown-container")) {
    activeDropdown.value = null;
  }
}

async function handleProcessLeave(appId: string, status: "Approved" | "Rejected") {
  if (processing.value) return;
  processing.value = appId;
  try {
    const res = await managerApi.processLeave(appId, status);
    if (res.status === "success" || res.success) {
      applySuccess.value = `Leave application ${status.toLowerCase()} successfully!`;
      await loadData();
    } else {
      alert(res.error || "Action failed");
    }
  } catch (e: any) {
    alert(e.message || "Error processing leave request");
  } finally {
    processing.value = null;
    activeDropdown.value = null;
  }
}

function confirmDeleteApprovedRejected(app: any) {
  leaveToDelete.value = app;
  deleteError.value = "";
  showDeletePopup.value = true;
  activeDropdown.value = null;
}

async function handleApprovedRejectedDelete() {
  if (!leaveToDelete.value) return;
  deleteLoading.value = true;
  deleteError.value = "";
  try {
    const res = await leaveApi.deleteApprovedRejected(leaveToDelete.value.name);
    if (res.success) {
      applySuccess.value = "Leave application and attendance records deleted successfully!";
      showDeletePopup.value = false;
      leaveToDelete.value = null;
      await loadData();
    } else {
      deleteError.value = res.error || "Failed to delete";
    }
  } catch (e: any) {
    deleteError.value = e.message || "Error deleting leave application";
  } finally {
    deleteLoading.value = false;
  }
}

function getEmployeeName(empId: string): string {
  const emp = leaveEmployees.value.find((e) => e.name === empId);
  return emp ? emp.employee_name : empId;
}

async function loadData(onlyApplications = false) {
  // loading.value = true;
  const { from, to } = getDefaultDateRange();
  const empKey = selectedEmployee.value || "self";

  if (!onlyApplications) {
    if (selectedEmployee.value === "all") {
      balance.value = [];
      leaveTypes.value = [];
      manager.value = null;
      holidays.value = [];
      loading.value = false;
    } else {
      useCachedFetch(`leave_balance_${empKey}`, () => leaveApi.getBalance(selectedEmployee.value || undefined), (data) => {
        if (!isMounted) return;
        const list = Array.isArray(data) ? data : data || [];
        if (Array.isArray(list)) {
          balance.value = list;
          loading.value = false;
        }
      });

      useCachedFetch(`leave_types_${empKey}`, () => leaveApi.getTypes(selectedEmployee.value || authStore.employee || undefined), (data) => {
        if (isMounted && Array.isArray(data)) leaveTypes.value = data;
      });

      useCachedFetch(`reporting_info_${empKey}`, () => dashboardApi.getReportingInfo(selectedEmployee.value || undefined), (data) => {
        if (isMounted && data) manager.value = data;
      });

      useCachedFetch(
        `holidays_${empKey}`,
        () => leaveApi.getHolidays(from, to, true, selectedEmployee.value || undefined),
        (data) => {
          if (isMounted && Array.isArray(data)) holidays.value = data;
        }
      );
    }
  }

  const appKey = `leave_applications_${empKey}_${filterStatus.value}_${filterFromDate.value}_${filterToDate.value}`;
  const fetchFn = selectedEmployee.value === "all"
    ? () => managerApi.getTeamLeaves(filterStatus.value || undefined, filterFromDate.value || undefined, filterToDate.value || undefined)
    : () => leaveApi.getApplications(selectedEmployee.value || undefined, filterStatus.value || undefined, filterFromDate.value || undefined, filterToDate.value || undefined);

  useCachedFetch(appKey, fetchFn, (data) => {
    if (!isMounted) return;
    const list = Array.isArray(data) ? data : data || [];
    if (Array.isArray(list)) applications.value = list;
  });
}

function openApplyForm() {
  isEditing.value = false;
  editLeaveName.value = "";
  form.value = {
    leave_type: leaveTypes.value[0] || "",
    from_date: "",
    to_date: "",
    half_day: 0,
    reason: "",
  };
  applyError.value = "";
  applySuccess.value = "";
  showApplyForm.value = true;
}

function editLeave(app: any) {
  isEditing.value = true;
  editLeaveName.value = app.name;
  form.value = {
    leave_type: app.leave_type,
    from_date: app.from_date ? app.from_date.substring(0, 10) : "",
    to_date: app.to_date ? app.to_date.substring(0, 10) : "",
    half_day: app.half_day || 0,
    reason: app.description || "",
  };
  applyError.value = "";
  applySuccess.value = "";
  showApplyForm.value = true;
}

async function submitLeave() {
  applyError.value = "";
  applySuccess.value = "";

  if (form.value.half_day && form.value.from_date !== form.value.to_date) {
    applyError.value = "For a half-day leave, the From Date and To Date must be the same.";
    return;
  }

  applyLoading.value = true;
  try {
    const payload = {
      ...form.value,
      ...(isEditing.value ? { name: editLeaveName.value } : {}),
    };
    const result = await leaveApi.apply(payload);
    if (!isMounted) return;
    if (result.success) {
      applySuccess.value = isEditing.value
        ? `Leave application ${result.name} updated successfully!`
        : `Leave application ${result.name} submitted successfully!`;
      showApplyForm.value = false;
      await loadData();
    } else {
      applyError.value = result.error || "Failed to submit";
    }
  } catch (e: any) {
    if (isMounted) applyError.value = e.message || "Something went wrong";
  } finally {
    if (isMounted) applyLoading.value = false;
  }
}

async function deleteLeave(name: string) {
  if (!confirm("Are you sure you want to delete this leave application?")) return;
  try {
    const result = await leaveApi.delete(name);
    if (result.success) {
      await loadData();
    } else {
      alert(result.error || "Failed to delete");
    }
  } catch (e: any) {
    alert(e.message || "Failed to delete");
  }
}

async function cancelLeave(name: string) {
  if (!confirm("Cancel this leave application?")) return;
  try {
    const result = await leaveApi.cancel(name);
    if (result.success) await loadData();
  } catch (e: any) {
    alert(e.message || "Failed to cancel");
  }
}

onMounted(async () => {
  await fetchLeaveEmployees();
  if (isSystemManager.value || leaveEmployees.value.length > 0) {
    selectedEmployee.value = "all";
  } else {
    loadData();
  }
  window.addEventListener("click", handleWindowClick);
});

onBeforeUnmount(() => {
  isMounted = false;
  window.removeEventListener("click", handleWindowClick);
});

watch(selectedEmployee, () => {
  loadData(false);
});

watch([filterStatus, filterFromDate, filterToDate], () => {
  loadData(true);
});

watch(() => form.value.half_day, (val) => {
  if (val && form.value.from_date) {
    form.value.to_date = form.value.from_date;
  }
});

watch(() => form.value.from_date, (val) => {
  if (form.value.half_day && val) {
    form.value.to_date = val;
  }
});
</script>

<template>
  <div>
    <!-- Header -->
    <div
      class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8 animate-fade-in"
    >
      <div>
        <h1 class="text-2xl sm:text-3xl font-bold" :style="{ color: 'var(--heading-color)' }">
          Leave Management
        </h1>
        <p class="text-sm mt-1" :style="{ color: 'var(--text-tertiary)' }">
          Track, apply and manage leaves
        </p>
      </div>
      <button @click="openApplyForm" class="btn-accent flex items-center gap-2 self-start">
        <Plus :size="18" />
        Apply Leave
      </button>
    </div>

    <!-- Filters (visible if leave_approver/system manager) -->
    <div v-if="isSystemManager || leaveEmployees.length" class="flex flex-col sm:flex-row gap-4 p-4 bg-white/5 border border-white/10 rounded-2xl animate-fade-in relative z-20 mb-6">
      <!-- Employee List Filter -->
      <div class="flex-1">
        <label class="block text-[10px] font-semibold text-slate-400 uppercase mb-1.5 tracking-wider">Employee</label>
        <div class="relative w-full">
          <select v-model="selectedEmployee" class="input-dark appearance-none pr-10 text-xs py-2 px-3">
            <option value="all">All Employees</option>
            <option v-for="emp in leaveEmployees" :key="emp.name" :value="emp.name">
              {{ emp.employee_name }}
            </option>
          </select>
          <ChevronDown class="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400" :size="14" />
        </div>
      </div>

      <!-- Status Filter -->
      <div class="flex-1">
        <label class="block text-[10px] font-semibold text-slate-400 uppercase mb-1.5 tracking-wider">Status</label>
        <div class="relative w-full">
          <select v-model="filterStatus" class="input-dark appearance-none pr-10 text-xs py-2 px-3">
            <option value="">All Statuses</option>
            <option value="Open">Pending</option>
            <option value="Approved">Approved</option>
            <option value="Rejected">Rejected</option>
            <option value="Cancelled">Cancelled</option>
          </select>
          <ChevronDown class="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400" :size="14" />
        </div>
      </div>

      <!-- Date Range Filter -->
      <div class="flex-1 date-picker-container relative">
        <label class="block text-[10px] font-semibold text-slate-400 uppercase mb-1.5 tracking-wider">Date Range</label>
        <button
          type="button"
          @click="showDropdown = !showDropdown"
          class="input-dark text-xs py-2 px-3 flex items-center justify-between gap-2 text-left cursor-pointer w-full"
        >
          <span>{{ selectedPreset }}</span>
          <ChevronDown :size="14" class="text-slate-400" />
        </button>

        <div
          v-if="showDropdown"
          class="absolute left-0 mt-2 z-40 bg-[var(--surface)] border border-[var(--border-color)] rounded-xl shadow-2xl p-3 flex gap-4 min-w-[160px]"
        >
          <!-- Presets List -->
          <div class="w-36 flex flex-col gap-1 text-xs">
            <button
              v-for="preset in ['All Time', 'Today', 'Yesterday', 'Last 7 Days', 'Last 30 Days', 'This Month', 'Last Month', 'Custom Range']"
              :key="preset"
              type="button"
              @click="applyPreset(preset)"
              class="w-full text-left px-2.5 py-1.5 rounded-lg transition-colors font-medium text-white"
              :class="selectedPreset === preset ? 'bg-teal-500/20 text-teal-500' : 'text-[var(--text-secondary)] hover:bg-[var(--row-hover)] hover:text-[var(--text-primary)]'"
            >
              {{ preset }}
            </button>
          </div>

          <!-- Custom Range Date Inputs -->
          <div v-if="selectedPreset === 'Custom Range'" class="w-48 pl-4 border-l border-[var(--border-color)] space-y-3 text-xs flex flex-col justify-center">
            <div class="space-y-1">
              <span class="text-[10px] text-[var(--text-tertiary)] uppercase font-semibold">From</span>
              <input type="date" v-model="filterFromDate" class="input-dark text-xs py-1.5 px-2.5" />
            </div>
            <div class="space-y-1">
              <span class="text-[10px] text-[var(--text-tertiary)] uppercase font-semibold">To</span>
              <input type="date" v-model="filterToDate" class="input-dark text-xs py-1.5 px-2.5" />
            </div>
            <button
              type="button"
              @click="showDropdown = false"
              class="w-full py-1.5 bg-gradient-to-r from-teal-500 to-emerald-500 text-white rounded-lg font-medium text-xs shadow-lg active:scale-95 transition-all text-center cursor-pointer mt-1"
            >
              Apply Range
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <div
        class="w-10 h-10 border-2 rounded-full animate-spin"
        :style="{ borderColor: 'var(--border-color)', borderTopColor: 'var(--accent)' }"
      />
    </div>

    <div v-else class="space-y-6 animate-slide-up">
      <!-- Manager Info -->
      <div v-if="manager?.reporting_manager || manager?.leave_approver" class="glass-card p-5">
        <h3
          class="text-sm font-semibold uppercase tracking-wider mb-4"
          :style="{ color: 'var(--text-secondary)' }"
        >
          Reporting & Approval
        </h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div v-if="manager.reporting_manager" class="flex items-center gap-3">
            <div
              class="w-10 h-10 rounded-xl flex items-center justify-center"
              :style="{ backgroundColor: 'var(--info-bg)', color: 'var(--info-text)' }"
            >
              <User :size="18" :stroke-width="1.8" />
            </div>
            <div>
              <p class="text-xs" :style="{ color: 'var(--text-tertiary)' }">Reporting Manager</p>
              <p class="text-sm font-medium" :style="{ color: 'var(--heading-color)' }">
                {{ manager.reporting_manager.employee_name }}
              </p>
              <p class="text-xs" :style="{ color: 'var(--text-tertiary)' }">
                {{ manager.reporting_manager.designation }}
              </p>
            </div>
          </div>
          <div v-if="manager.leave_approver" class="flex items-center gap-3">
            <div
              class="w-10 h-10 rounded-xl flex items-center justify-center"
              :style="{ backgroundColor: 'rgba(168,85,247,0.1)', color: '#a855f7' }"
            >
              <Briefcase :size="18" :stroke-width="1.8" />
            </div>
            <div>
              <p class="text-xs" :style="{ color: 'var(--text-tertiary)' }">Leave Approver</p>
              <p class="text-sm font-medium" :style="{ color: 'var(--heading-color)' }">
                {{ manager.leave_approver.employee_name }}
              </p>
              <p class="text-xs" :style="{ color: 'var(--text-tertiary)' }">
                {{ manager.leave_approver.designation }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- Holidays -->
      <div v-if="holidays.length" class="glass-card p-5">
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
          <div>
            <h3
              class="text-sm font-semibold uppercase tracking-wider"
              :style="{ color: 'var(--text-secondary)' }"
            >
              Company Holidays
            </h3>
            <p class="text-xs mt-1" :style="{ color: 'var(--text-tertiary)' }">
              From assigned Holiday List
            </p>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <label class="text-xs whitespace-nowrap" :style="{ color: 'var(--text-tertiary)' }"
              >Filter:</label
            >
            <div class="relative">
              <select
                v-model="holidaysMonthFilter"
                class="input-dark appearance-none pr-8 pl-3 py-2 text-sm cursor-pointer min-w-[160px]"
              >
                <option v-for="opt in holidaysMonthOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
              <ChevronDown
                :size="14"
                class="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none"
                :style="{ color: 'var(--text-tertiary)' }"
              />
            </div>
          </div>
        </div>
        <div class="relative">
          <div
            class="holidays-scroll grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-h-64 overflow-y-auto overflow-x-hidden"
          >
            <div
              v-for="h in filteredHolidays"
              :key="h.holiday_date"
              class="flex items-center gap-3 py-2 px-3 rounded-lg"
              :style="{
                backgroundColor: 'var(--glass-bg)',
                border: '1px solid var(--border-color)',
              }"
            >
              <div
                class="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
                :style="{ backgroundColor: 'var(--warning-bg)', color: 'var(--warning-text)' }"
              >
                <Calendar :size="18" :stroke-width="1.8" />
              </div>
              <div class="min-w-0">
                <p class="text-sm font-medium" :style="{ color: 'var(--heading-color)' }">
                  {{
                    new Date(h.holiday_date).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    })
                  }}
                </p>
                <p class="text-xs truncate" :style="{ color: 'var(--text-tertiary)' }">
                  {{ h.description || "Holiday" }}
                </p>
              </div>
            </div>
          </div>
          <p
            v-if="filteredHolidays.length === 0"
            class="text-sm py-6 text-center"
            :style="{ color: 'var(--text-tertiary)' }"
          >
            No holidays in selected month
          </p>
        </div>
      </div>

      <!-- Leave Balance Cards -->
      <div v-if="selectedEmployee !== 'all'">
        <h3
          class="text-sm font-semibold uppercase tracking-wider mb-4"
          :style="{ color: 'var(--text-secondary)' }"
        >
          Leave Balance
        </h3>
        <p class="text-xs mb-4" :style="{ color: 'var(--text-tertiary)' }">
          {{ selectedEmployee ? `Allocated leave types for ${getEmployeeName(selectedEmployee)}` : 'Your allocated leave types' }}
        </p>
        <div v-if="balance.length" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          <div
            v-for="(b, idx) in balance"
            :key="b.leave_type"
            class="glass-card-hover p-5"
            :style="{
              boxShadow: `inset 0 0 0 1px ${getTypeColor(idx).ring}`,
            }"
          >
            <p
              class="text-sm font-medium mb-2 truncate"
              :title="b.leave_type"
              :style="{ color: 'var(--text-secondary)' }"
            >
              {{ b.leave_type }}
            </p>
            <p class="text-3xl font-bold" :style="{ color: getTypeColor(idx).text }">
              {{ b.balance }}<span class="text-lg font-normal opacity-50">/{{ b.allocated }}</span>
            </p>
            <p class="text-xs mt-1" :style="{ color: 'var(--text-tertiary)' }">days remaining</p>
          </div>
          <div
            class="glass-card p-5"
            :style="{ boxShadow: 'inset 0 0 0 1px rgba(20,184,166,0.2)' }"
          >
            <p class="text-sm font-medium mb-2" :style="{ color: 'var(--text-secondary)' }">
              Total
            </p>
            <p class="text-3xl font-bold" :style="{ color: 'var(--accent)' }">{{ totalBalance }}</p>
            <p class="text-xs mt-1" :style="{ color: 'var(--text-tertiary)' }">days remaining</p>
          </div>
        </div>
        <div v-else class="glass-card p-8 text-center">
          <Palmtree :size="32" class="mx-auto mb-2" :style="{ color: 'var(--text-tertiary)' }" />
          <p class="text-sm" :style="{ color: 'var(--text-tertiary)' }">
            No leave balance data available
          </p>
        </div>
      </div>

      <!-- Applications List -->
      <div>
        <h3
          class="text-sm font-semibold uppercase tracking-wider mb-4"
          :style="{ color: 'var(--text-secondary)' }"
        >
          {{ selectedEmployee === 'all' ? 'Team Applications' : (selectedEmployee ? `${getEmployeeName(selectedEmployee)}'s Applications` : 'My Applications') }}
        </h3>
        <div v-if="applications.length" class="glass-card overflow-hidden">
          <!-- Desktop table -->
          <div class="hidden sm:block overflow-x-auto">
            <table class="w-full">
              <thead>
                <tr :style="{ borderBottom: '1px solid var(--border-color)' }">
                  <th
                    class="text-left text-xs font-semibold uppercase tracking-wider px-5 py-3"
                    :style="{ color: 'var(--text-tertiary)' }"
                  >
                    Employee
                  </th>
                  <th
                    class="text-left text-xs font-semibold uppercase tracking-wider px-5 py-3"
                    :style="{ color: 'var(--text-tertiary)' }"
                  >
                    Type
                  </th>
                  <th
                    class="text-left text-xs font-semibold uppercase tracking-wider px-5 py-3"
                    :style="{ color: 'var(--text-tertiary)' }"
                  >
                    Period
                  </th>
                  <th
                    class="text-center text-xs font-semibold uppercase tracking-wider px-5 py-3"
                    :style="{ color: 'var(--text-tertiary)' }"
                  >
                    Days
                  </th>
                  <th
                    class="text-center text-xs font-semibold uppercase tracking-wider px-5 py-3"
                    :style="{ color: 'var(--text-tertiary)' }"
                  >
                    Status
                  </th>
                  <th
                    class="text-right text-xs font-semibold uppercase tracking-wider px-5 py-3"
                    :style="{ color: 'var(--text-tertiary)' }"
                  >
                    Action
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="app in applications"
                  :key="app.name"
                  class="transition-colors cursor-pointer hover:bg-white/[0.02]"
                  :style="{ borderBottom: '1px solid var(--border-color)' }"
                  @click="openLeaveDetail(app)"
                >
                  <td class="px-5 py-4">
                    <p class="text-sm font-medium" :style="{ color: 'var(--text-secondary)' }">
                      {{ app.employee_name || app.employee || authStore.employeeName }}
                    </p>
                  </td>
                  <td class="px-5 py-4">
                    <p class="text-sm font-medium" :style="{ color: 'var(--heading-color)' }">
                      {{ app.leave_type }}
                    </p>
                  </td>
                  <td class="px-5 py-4">
                    <p class="text-sm" :style="{ color: 'var(--text-secondary)' }">
                      {{
                        new Date(app.from_date).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                        })
                      }}
                      <template v-if="app.from_date !== app.to_date">
                        —
                        {{
                          new Date(app.to_date).toLocaleDateString("en-US", {
                            month: "short",
                            day: "numeric",
                          })
                        }}
                      </template>
                    </p>
                  </td>
                  <td class="px-5 py-4 text-center">
                    <span
                      class="text-sm font-semibold"
                      :style="{ color: 'var(--heading-color)' }"
                      >{{ app.total_leave_days }}</span
                    >
                  </td>
                  <td class="px-5 py-4 text-center">
                    <span
                      class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold"
                      :style="{
                        backgroundColor: getStatusStyle(app.status).bg,
                        color: getStatusStyle(app.status).text,
                      }"
                    >
                      {{ app.status }}
                    </span>
                  </td>
                  <td class="px-5 py-4 text-right" @click.stop>
                    <div
                      v-if="app.status === 'Open' || ((app.status === 'Approved' || app.status === 'Rejected') && (isSystemManager || leaveEmployees.length))"
                      class="relative inline-block text-left action-dropdown-container"
                    >
                      <button
                        @click.stop="activeDropdown = activeDropdown === app.name ? null : app.name"
                        class="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs text-slate-300 hover:text-white cursor-pointer transition-colors"
                      >
                        More
                        <ChevronDown :size="12" />
                      </button>

                      <div
                        v-if="activeDropdown === app.name"
                        class="absolute right-0 mt-1 w-36 rounded-xl shadow-2xl bg-[var(--surface)] border border-[var(--border-color)] z-30 py-1"
                      >
                        <!-- Edit Action (Own leaves only) -->
                        <button
                          v-if="app.status === 'Open' && app.employee === authStore.employee"
                          @click="editLeave(app); activeDropdown = null;"
                          class="w-full text-left px-3 py-2 text-xs hover:bg-white/5 transition-colors text-slate-300 hover:text-white flex items-center gap-2 cursor-pointer"
                        >
                          <Edit :size="14" />
                          Edit
                        </button>

                        <!-- Delete (Open) Action (Own leaves only) -->
                        <button
                          v-if="app.status === 'Open' && app.employee === authStore.employee"
                          @click="deleteLeave(app.name); activeDropdown = null;"
                          class="w-full text-left px-3 py-2 text-xs hover:bg-red-500/10 transition-colors text-red-400 flex items-center gap-2 cursor-pointer font-medium"
                        >
                          <Trash2 :size="14" />
                          Delete
                        </button>

                        <!-- Approve Action (Manager only for others' leaves) -->
                        <button
                          v-if="app.status === 'Open' && app.employee !== authStore.employee && (isSystemManager || leaveEmployees.length)"
                          @click="handleProcessLeave(app.name, 'Approved')"
                          class="w-full text-left px-3 py-2 text-xs hover:bg-emerald-500/10 transition-colors text-emerald-400 flex items-center gap-2 cursor-pointer font-medium"
                        >
                          <CheckCircle2 :size="14" />
                          Approve
                        </button>

                        <!-- Reject Action (Manager only for others' leaves) -->
                        <button
                          v-if="app.status === 'Open' && app.employee !== authStore.employee && (isSystemManager || leaveEmployees.length)"
                          @click="handleProcessLeave(app.name, 'Rejected')"
                          class="w-full text-left px-3 py-2 text-xs hover:bg-red-500/10 transition-colors text-red-500 flex items-center gap-2 cursor-pointer font-medium"
                        >
                          <XCircle :size="14" />
                          Reject
                        </button>

                        <!-- Delete (Approved/Rejected) Action (Manager only) -->
                        <button
                          v-if="(app.status === 'Approved' || app.status === 'Rejected') && (isSystemManager || leaveEmployees.length)"
                          @click="confirmDeleteApprovedRejected(app)"
                          class="w-full text-left px-3 py-2 text-xs hover:bg-red-500/10 transition-colors text-red-400 flex items-center gap-2 cursor-pointer font-medium"
                        >
                          <Trash2 :size="14" />
                          Delete
                        </button>
                      </div>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <!-- Mobile cards -->
          <div class="sm:hidden divide-y" :style="{ borderColor: 'var(--border-color)' }">
            <div
              v-for="app in applications"
              :key="app.name"
              class="p-4 space-y-2 cursor-pointer hover:bg-white/[0.01] active:bg-white/[0.02] transition-colors"
              @click="openLeaveDetail(app)"
            >
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-[10px] font-semibold tracking-wide uppercase mb-0.5" :style="{ color: 'var(--text-secondary)' }">
                    {{ app.employee_name || app.employee || authStore.employeeName }}
                  </p>
                  <p class="text-sm font-medium" :style="{ color: 'var(--heading-color)' }">
                    {{ app.leave_type }}
                  </p>
                </div>
                <span
                  class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold"
                  :style="{
                    backgroundColor: getStatusStyle(app.status).bg,
                    color: getStatusStyle(app.status).text,
                  }"
                >
                  {{ app.status }}
                </span>
              </div>
              <p class="text-xs" :style="{ color: 'var(--text-tertiary)' }">
                {{
                  new Date(app.from_date).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                  })
                }}
                <template v-if="app.from_date !== app.to_date">
                  —
                  {{
                    new Date(app.to_date).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                    })
                  }}
                </template>
                &middot; {{ app.total_leave_days }} day{{ app.total_leave_days !== 1 ? "s" : "" }}
              </p>
              <!-- Mobile Actions Dropdown -->
              <div
                v-if="app.status === 'Open' || ((app.status === 'Approved' || app.status === 'Rejected') && (isSystemManager || leaveEmployees.length))"
                class="relative inline-block text-left action-dropdown-container mt-1.5"
                @click.stop
              >
                <button
                  @click.stop="activeDropdown = activeDropdown === app.name ? null : app.name"
                  class="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs text-slate-300 hover:text-white cursor-pointer transition-colors"
                >
                  Actions
                  <ChevronDown :size="12" />
                </button>

                <div
                  v-if="activeDropdown === app.name"
                  class="absolute left-0 mt-1 w-36 rounded-xl shadow-2xl bg-[var(--surface)] border border-[var(--border-color)] z-30 py-1"
                >
                  <!-- Edit Action (Own leaves only) -->
                  <button
                    v-if="app.status === 'Open' && app.employee === authStore.employee"
                    @click="editLeave(app); activeDropdown = null;"
                    class="w-full text-left px-3 py-2 text-xs hover:bg-white/5 transition-colors text-slate-300 hover:text-white flex items-center gap-2 cursor-pointer"
                  >
                    <Edit :size="14" />
                    Edit
                  </button>

                  <!-- Delete (Open) Action (Own leaves only) -->
                  <button
                    v-if="app.status === 'Open' && app.employee === authStore.employee"
                    @click="deleteLeave(app.name); activeDropdown = null;"
                    class="w-full text-left px-3 py-2 text-xs hover:bg-red-500/10 transition-colors text-red-400 flex items-center gap-2 cursor-pointer font-medium"
                  >
                    <Trash2 :size="14" />
                    Delete
                  </button>

                  <!-- Approve Action (Manager only for others' leaves) -->
                  <button
                    v-if="app.status === 'Open' && app.employee !== authStore.employee && (isSystemManager || leaveEmployees.length)"
                    @click="handleProcessLeave(app.name, 'Approved')"
                    class="w-full text-left px-3 py-2 text-xs hover:bg-emerald-500/10 transition-colors text-emerald-400 flex items-center gap-2 cursor-pointer font-medium"
                  >
                    <CheckCircle2 :size="14" />
                    Approve
                  </button>

                  <!-- Reject Action (Manager only for others' leaves) -->
                  <button
                    v-if="app.status === 'Open' && app.employee !== authStore.employee && (isSystemManager || leaveEmployees.length)"
                    @click="handleProcessLeave(app.name, 'Rejected')"
                    class="w-full text-left px-3 py-2 text-xs hover:bg-red-500/10 transition-colors text-red-500 flex items-center gap-2 cursor-pointer font-medium"
                  >
                    <XCircle :size="14" />
                    Reject
                  </button>

                  <!-- Delete (Approved/Rejected) Action (Manager only) -->
                  <button
                    v-if="(app.status === 'Approved' || app.status === 'Rejected') && (isSystemManager || leaveEmployees.length)"
                    @click="confirmDeleteApprovedRejected(app)"
                    class="w-full text-left px-3 py-2 text-xs hover:bg-red-500/10 transition-colors text-red-400 flex items-center gap-2 cursor-pointer font-medium"
                  >
                    <Trash2 :size="14" />
                    Delete
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="glass-card p-8 text-center">
          <Calendar :size="32" class="mx-auto mb-2" :style="{ color: 'var(--text-tertiary)' }" />
          <p class="text-sm" :style="{ color: 'var(--text-tertiary)' }">
            No leave applications yet
          </p>
        </div>
      </div>
    </div>

    <!-- Leave Detail Modal -->
    <transition name="modal">
      <div
        v-if="showLeaveDetailModal && selectedLeave"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-sm"
        style="background-color: var(--overlay-bg);"
        @click.self="showLeaveDetailModal = false"
      >
        <div class="modal-content glass-card w-full max-w-lg p-6 space-y-6">
          <!-- Header -->
          <div class="flex items-center justify-between border-b border-white/[0.06] pb-4">
            <div>
              <h2 class="text-lg font-semibold text-white flex items-center gap-2">
                <FileText :size="20" class="text-teal-400" />
                Leave Application Details
              </h2>
              <p class="text-xs text-slate-400 mt-1">
                {{ selectedLeave.employee_name || selectedLeave.employee || authStore.employeeName }}
              </p>
            </div>
            <button
              @click="showLeaveDetailModal = false"
              class="p-1 transition-colors text-slate-500 hover:text-white"
            >
              <X :size="20" />
            </button>
          </div>

          <!-- Details Grid -->
          <div class="space-y-5">
            <div class="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span class="block text-xs text-slate-500 font-medium uppercase tracking-wider mb-0.5">Application ID</span>
                <span class="text-white font-medium font-mono text-xs">{{ selectedLeave.name }}</span>
              </div>
              <div>
                <span class="block text-xs text-slate-500 font-medium uppercase tracking-wider mb-0.5">Status</span>
                <span
                  class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium"
                  :style="{
                    backgroundColor: getStatusStyle(selectedLeave.status).bg,
                    color: getStatusStyle(selectedLeave.status).text,
                  }"
                >
                  {{ selectedLeave.status }}
                </span>
              </div>
              <div>
                <span class="block text-xs text-slate-500 font-medium uppercase tracking-wider mb-0.5">Leave Type</span>
                <span class="text-white font-medium">{{ selectedLeave.leave_type }}</span>
              </div>
              <div>
                <span class="block text-xs text-slate-500 font-medium uppercase tracking-wider mb-0.5">Total Days</span>
                <span class="text-white font-medium">{{ selectedLeave.total_leave_days }} day{{ selectedLeave.total_leave_days !== 1 ? 's' : '' }}</span>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span class="block text-xs text-slate-500 font-medium uppercase tracking-wider mb-0.5">From Date</span>
                <span class="text-white font-medium">{{ formatDate(selectedLeave.from_date) }}</span>
              </div>
              <div>
                <span class="block text-xs text-slate-500 font-medium uppercase tracking-wider mb-0.5">To Date</span>
                <span class="text-white font-medium">{{ formatDate(selectedLeave.to_date) }}</span>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span class="block text-xs text-slate-500 font-medium uppercase tracking-wider mb-0.5">Half Day</span>
                <span class="text-white font-medium">{{ selectedLeave.half_day ? 'Yes' : 'No' }}</span>
              </div>
            </div>

            <div v-if="selectedLeave.description" class="bg-white/[0.03] p-4 rounded-xl border border-white/[0.06]">
              <p class="text-xs text-slate-500 uppercase mb-1 font-semibold">Reason</p>
              <p class="text-slate-300 text-sm whitespace-pre-wrap">{{ selectedLeave.description }}</p>
            </div>

            <!-- Approve/Reject buttons for managers on Open requests of others -->
            <div v-if="selectedLeave.status === 'Open' && selectedLeave.employee !== authStore.employee && (isSystemManager || leaveEmployees.length)" class="flex items-center gap-3 border-t border-white/[0.06] pt-5">
              <button
                @click="handleProcessLeave(selectedLeave.name, 'Approved'); showLeaveDetailModal = false;"
                :disabled="!!processing"
                class="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-medium rounded-lg shadow-lg active:scale-95 transition-all text-sm cursor-pointer"
              >
                <CheckCircle2 :size="16" />
                Approve
              </button>
              <button
                @click="handleProcessLeave(selectedLeave.name, 'Rejected'); showLeaveDetailModal = false;"
                :disabled="!!processing"
                class="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-red-500 to-rose-500 text-white font-medium rounded-lg shadow-lg active:scale-95 transition-all text-sm cursor-pointer"
              >
                <XCircle :size="16" />
                Reject
              </button>
            </div>
          </div>

          <!-- Close button -->
          <div class="flex pt-2">
            <button
              type="button"
              @click="showLeaveDetailModal = false"
              class="w-full px-4 py-2.5 text-sm font-medium rounded-lg text-slate-300 hover:text-white bg-white/5 hover:bg-white/10 border border-white/[0.08] transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Apply Leave Modal -->
    <transition name="modal">
      <div
        v-if="showApplyForm"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-sm"
        :style="{ backgroundColor: 'var(--overlay-bg)' }"
        @click.self="showApplyForm = false"
      >
        <div class="modal-content glass-card w-full max-w-md p-6 space-y-5">
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold" :style="{ color: 'var(--heading-color)' }">
              {{ isEditing ? "Edit Leave Application" : "Apply for Leave" }}
            </h2>
            <button
              @click="showApplyForm = false"
              class="p-1 transition-colors"
              :style="{ color: 'var(--text-tertiary)' }"
            >
              <X :size="20" />
            </button>
          </div>

          <form @submit.prevent="submitLeave" class="space-y-4">
            <div>
              <label
                class="block text-sm font-medium mb-1.5"
                :style="{ color: 'var(--text-secondary)' }"
                >Leave Type <span :style="{ color: 'var(--danger-text)' }">*</span></label
              >
              <div class="relative">
                <select
                  v-model="form.leave_type"
                  class="input-dark appearance-none pr-10 cursor-pointer"
                  :disabled="!leaveTypes.length"
                >
                  <option value="" disabled>Select leave type</option>
                  <option v-for="t in leaveTypes" :key="t" :value="t">
                    {{ getLeaveTypeLabel(t) }}
                  </option>
                  <option v-if="!leaveTypes.length" value="" disabled>No leave types</option>
                </select>
                <ChevronDown
                  :size="16"
                  class="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none"
                  :style="{ color: 'var(--text-tertiary)' }"
                />
              </div>
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label
                  class="block text-sm font-medium mb-1.5"
                  :style="{ color: 'var(--text-secondary)' }"
                  >From <span :style="{ color: 'var(--danger-text)' }">*</span></label
                >
                <input type="date" v-model="form.from_date" required class="input-dark" />
              </div>
              <div>
                <label
                  class="block text-sm font-medium mb-1.5"
                  :style="{ color: 'var(--text-secondary)' }"
                  >To <span :style="{ color: 'var(--danger-text)' }">*</span></label
                >
                <input type="date" v-model="form.to_date" required class="input-dark" />
              </div>
            </div>

            <label class="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                :true-value="1"
                :false-value="0"
                v-model="form.half_day"
                class="w-4 h-4 rounded"
                :style="{ accentColor: 'var(--accent)' }"
              />
              <span class="text-sm" :style="{ color: 'var(--text-secondary)' }">Half day</span>
            </label>

            <div>
              <label
                class="block text-sm font-medium mb-1.5"
                :style="{ color: 'var(--text-secondary)' }"
              >
                Reason <span :style="{ color: 'var(--text-tertiary)' }">(optional)</span>
              </label>
              <textarea
                v-model="form.reason"
                rows="3"
                class="input-dark resize-none"
                placeholder="Briefly describe the reason..."
              ></textarea>
            </div>

            <div
              v-if="applyError"
              class="flex items-start gap-2 text-sm p-3 rounded-xl"
              :style="{ backgroundColor: 'var(--danger-bg)', color: 'var(--danger-text)' }"
            >
              <AlertCircle :size="16" class="mt-0.5 shrink-0" />
              {{ applyError }}
            </div>

            <button
              type="submit"
              :disabled="applyLoading || !form.leave_type || !form.from_date || !form.to_date"
              class="btn-accent w-full flex items-center justify-center gap-2"
            >
              <Loader2 v-if="applyLoading" :size="18" class="animate-spin" />
              <span>{{ applyLoading ? "Submitting..." : (isEditing ? "Update Application" : "Submit Application") }}</span>
            </button>
          </form>
        </div>
      </div>
    </transition>

    <!-- Delete Confirmation Modal -->
    <transition name="modal">
      <div
        v-if="showDeletePopup"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-sm"
        :style="{ backgroundColor: 'var(--overlay-bg)' }"
        @click.self="showDeletePopup = false"
      >
        <div class="modal-content glass-card w-full max-w-md p-6 space-y-5">
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold text-white">
              Confirm Delete
            </h2>
            <button
              @click="showDeletePopup = false"
              class="p-1 transition-colors"
              :style="{ color: 'var(--text-tertiary)' }"
            >
              <X :size="20" />
            </button>
          </div>

          <div class="space-y-3">
            <p class="text-sm text-slate-300">
              Are you sure you want to delete this approved/rejected leave application?
            </p>
            <div class="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-xs text-red-400 flex items-start gap-2">
              <AlertCircle :size="16" class="shrink-0 mt-0.5" />
              <span>
                <strong>Warning:</strong> This action will delete the attendance records for the leave period and delete the leave application itself.
              </span>
            </div>
          </div>

          <div
            v-if="deleteError"
            class="flex items-start gap-2 text-sm p-3 rounded-xl animate-fade-in"
            :style="{ backgroundColor: 'var(--danger-bg)', color: 'var(--danger-text)' }"
          >
            <AlertCircle :size="16" class="mt-0.5 shrink-0" />
            {{ deleteError }}
          </div>

          <div class="flex justify-end gap-3">
            <button
              @click="showDeletePopup = false"
              class="px-4 py-2 rounded-xl text-sm font-medium border border-[var(--border-color)] text-slate-300 hover:bg-white/5 transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              @click="handleApprovedRejectedDelete"
              :disabled="deleteLoading"
              class="px-4 py-2 rounded-xl text-sm font-medium bg-red-500 text-white hover:bg-red-600 transition-colors flex items-center gap-2 cursor-pointer"
            >
              <Loader2 v-if="deleteLoading" :size="16" class="animate-spin" />
              Done
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Success toast -->
    <transition name="modal">
      <div
        v-if="applySuccess"
        class="fixed bottom-24 lg:bottom-8 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2 px-5 py-3 rounded-xl shadow-lg"
        :style="{
          backgroundColor: 'var(--success-bg)',
          border: '1px solid var(--success-text)',
          color: 'var(--success-text)',
        }"
      >
        <CheckCircle2 :size="18" />
        <span class="text-sm font-medium">{{ applySuccess }}</span>
        <button @click="applySuccess = ''" class="ml-2 opacity-60 hover:opacity-100">
          <X :size="16" />
        </button>
      </div>
    </transition>
  </div>
</template>
