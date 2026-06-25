<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from "vue";
import { useRoute } from "vue-router";
import { managerApi, expensesApi, attendanceApi } from "../services/api";
import { useAuthStore } from "../stores/auth";
import {
  CheckCircle,
  XCircle,
  Calendar,
  User,
  Clock,
  Briefcase,
  AlertCircle,
  DollarSign,
  Receipt,
  X,
  FileText,
  ChevronDown,
} from "lucide-vue-next";

interface LeaveApplication {
  name: string;
  employee_name: string;
  leave_type: string;
  from_date: string;
  to_date: string;
  total_leave_days: number;
  description: string;
  creation: string;
  status: string;
  employee: string;
}

interface ExpenseClaim {
  name: string;
  employee_name: string;
  total_claimed_amount: number;
  posting_date: string;
  status: string;
  approval_status: string;
  company: string;
  payable_account?: string;
  remark?: string;
  expense_type?: string;
  amount?: number;
  description?: string;
  expenses?: any[];
  proofs?: string[];
  proof?: string;
}

const route = useRoute();
const activeTab = ref<"leave" | "expense" | "attendance">((route.query.tab as "leave" | "expense" | "attendance") || "leave");

watch(
  () => route.query.tab,
  (newTab) => {
    if (newTab === "leave" || newTab === "expense" || newTab === "attendance") {
      activeTab.value = newTab;
    }
  }
);
const leaves = ref<LeaveApplication[]>([]);
const expenses = ref<ExpenseClaim[]>([]);
const loading = ref(true);
const processing = ref<string | null>(null);
const error = ref("");
const successMessage = ref("");

// Approval Modal State
const showApproveModal = ref(false);
const selectedClaim = ref<ExpenseClaim | null>(null);
const payableAccount = ref("");
const payableAccounts = ref<{ value: string; label: string }[]>([]);
const isApproving = ref(false);
const approvalError = ref("");
const modalAction = ref<"Approve" | "Reject">("Approve");

// Detail Modal State
const showDetailModal = ref(false);
const selectedDetail = ref<ExpenseClaim | null>(null);

// Leave Detail Modal State
const showLeaveDetailModal = ref(false);
const selectedLeaveDetail = ref<LeaveApplication | null>(null);

function openLeaveDetailModal(leave: LeaveApplication) {
  selectedLeaveDetail.value = leave;
  showLeaveDetailModal.value = true;
}

// Attendance Request State
interface AttendanceRequest {
  name: string;
  employee: string;
  employee_name: string;
  from_date: string;
  to_date: string;
  reason: string;
  explanation: string;
  creation: string;
  status: string;
}

const authStore = useAuthStore();
const isSystemManager = computed(() => authStore.isSystemManager);
const attendanceRequests = ref<AttendanceRequest[]>([]);
const filterAttendanceEmployee = ref("");
const attendanceEmployees = ref<any[]>([]);
const showAttendanceDetailModal = ref(false);
const selectedAttendanceDetail = ref<AttendanceRequest | null>(null);

function openAttendanceDetailModal(req: AttendanceRequest) {
  selectedAttendanceDetail.value = req;
  showAttendanceDetailModal.value = true;
}

// Filters State
const todayVal = new Date();
const currentYear = todayVal.getFullYear();
const currentMonth = String(todayVal.getMonth() + 1).padStart(2, "0");
const lastDayOfMonth = String(new Date(currentYear, todayVal.getMonth() + 1, 0).getDate()).padStart(2, "0");

const filterStatus = ref("Draft");
const filterFromDate = ref(`${currentYear}-${currentMonth}-01`);
const filterToDate = ref(`${currentYear}-${currentMonth}-${lastDayOfMonth}`);
const filterLeaveEmployee = ref("");
const filterExpenseEmployee = ref("");
const leaveEmployees = ref<any[]>([]);
const expenseEmployees = ref<any[]>([]);

const selectedPreset = ref("This Month");
const showDropdown = ref(false);

watch(showApproveModal, (val) => {
  if (val) {
    document.body.classList.add("overflow-hidden");
  } else {
    if (!showDetailModal.value && !showLeaveDetailModal.value) {
      document.body.classList.remove("overflow-hidden");
    }
  }
});

watch(showDetailModal, (val) => {
  if (val) {
    document.body.classList.add("overflow-hidden");
  } else {
    if (!showApproveModal.value && !showLeaveDetailModal.value) {
      document.body.classList.remove("overflow-hidden");
    }
  }
});

watch(showLeaveDetailModal, (val) => {
  if (val) {
    document.body.classList.add("overflow-hidden");
  } else {
    if (!showApproveModal.value && !showDetailModal.value && !showAttendanceDetailModal.value) {
      document.body.classList.remove("overflow-hidden");
    }
  }
});

watch(showAttendanceDetailModal, (val) => {
  if (val) {
    document.body.classList.add("overflow-hidden");
  } else {
    if (!showApproveModal.value && !showDetailModal.value && !showLeaveDetailModal.value) {
      document.body.classList.remove("overflow-hidden");
    }
  }
});

function handleWindowClick(e: MouseEvent) {
  const target = e.target as HTMLElement;
  if (!target.closest(".date-picker-container")) {
    showDropdown.value = false;
  }
}

onUnmounted(() => {
  document.body.classList.remove("overflow-hidden");
  window.removeEventListener("click", handleWindowClick);
});

async function fetchLeaveEmployees() {
  try {
    const data = await managerApi.getLeaveApproverEmployees();
    leaveEmployees.value = Array.isArray(data) ? data : [];
  } catch (e) {
    console.error("Failed to load leave employees:", e);
  }
}

async function fetchExpenseEmployees() {
  try {
    const data = await expensesApi.getExpenseApproverEmployees();
    expenseEmployees.value = Array.isArray(data) ? data : [];
  } catch (e) {
    console.error("Failed to load expense employees:", e);
  }
}

async function fetchAttendanceEmployees() {
  try {
    const data = await managerApi.getLeaveApproverEmployees();
    attendanceEmployees.value = Array.isArray(data) ? data : [];
  } catch (e) {
    console.error("Failed to load attendance employees:", e);
  }
}

async function loadAttendanceRequests(silent = false) {
  if (!silent) loading.value = true;
  try {
    const reqs = await managerApi.getTeamAttendanceRequests(
      filterStatus.value,
      filterFromDate.value,
      filterToDate.value,
      filterAttendanceEmployee.value
    );
    attendanceRequests.value = Array.isArray(reqs) ? reqs : [];
  } catch (e) {
    console.error(e);
    error.value = "Failed to load attendance requests";
  } finally {
    if (!silent) loading.value = false;
  }
}

async function handleProcessAttendanceRequest(name: string, action: "Approve" | "Reject") {
  if (processing.value) return;
  processing.value = name;
  error.value = "";
  successMessage.value = "";

  try {
    const res = await managerApi.processAttendanceRequest(name, action);
    if (res.status === "success") {
      successMessage.value = `Attendance request ${action === "Approve" ? "approved" : "rejected"} successfully`;
      attendanceRequests.value = attendanceRequests.value.filter((r) => r.name !== name);
    } else {
      error.value = res.message || "Action failed";
    }
  } catch (e: any) {
    error.value = e.message || "Error processing request";
  } finally {
    processing.value = null;
    setTimeout(() => {
      successMessage.value = "";
      error.value = "";
    }, 3000);
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

async function loadLeaves() {
  loading.value = true;
  try {
    const leavesData = await managerApi.getTeamLeaves(
      filterStatus.value,
      filterFromDate.value,
      filterToDate.value,
      filterLeaveEmployee.value
    );
    leaves.value = Array.isArray(leavesData) ? leavesData : [];
  } catch (e) {
    console.error(e);
    error.value = "Failed to load leaves";
  } finally {
    loading.value = false;
  }
}

async function loadExpenses() {
  loading.value = true;
  try {
    const expensesData = await expensesApi.getTeamExpenses(
      filterStatus.value,
      filterFromDate.value,
      filterToDate.value,
      filterExpenseEmployee.value
    );
    expenses.value = Array.isArray(expensesData) ? expensesData : [];
  } catch (e) {
    console.error(e);
    error.value = "Failed to load expenses";
  } finally {
    loading.value = false;
  }
}

watch([filterStatus, filterFromDate, filterToDate, filterLeaveEmployee], () => {
  if (activeTab.value === "leave") {
    loadLeaves();
  }
});

watch([filterStatus, filterFromDate, filterToDate, filterExpenseEmployee], () => {
  if (activeTab.value === "expense") {
    loadExpenses();
  }
});

watch([filterStatus, filterFromDate, filterToDate, filterAttendanceEmployee], () => {
  if (activeTab.value === "attendance") {
    loadAttendanceRequests();
  }
});

watch(activeTab, () => {
  if (activeTab.value === "leave") {
    loadLeaves();
  } else if (activeTab.value === "expense") {
    loadExpenses();
  } else if (activeTab.value === "attendance") {
    loadAttendanceRequests();
  }
});

async function loadData() {
  loading.value = true;
  try {
    const promises: Promise<any>[] = [
      managerApi.getTeamLeaves(
        filterStatus.value,
        filterFromDate.value,
        filterToDate.value,
        filterLeaveEmployee.value
      ),
      expensesApi.getTeamExpenses(
        filterStatus.value,
        filterFromDate.value,
        filterToDate.value,
        filterExpenseEmployee.value
      ),
      fetchLeaveEmployees(),
      fetchExpenseEmployees(),
    ];
    if (isSystemManager.value) {
      promises.push(loadAttendanceRequests(true));
      promises.push(fetchAttendanceEmployees());
    }
    const results = await Promise.all(promises);
    leaves.value = Array.isArray(results[0]) ? results[0] : [];
    expenses.value = Array.isArray(results[1]) ? results[1] : [];
  } catch (e) {
    console.error(e);
    error.value = "Failed to load data";
  } finally {
    loading.value = false;
  }
}

async function handleProcessLeave(appId: string, status: "Approved" | "Rejected") {
  if (processing.value) return;
  processing.value = appId;
  error.value = "";
  successMessage.value = "";

  try {
    const res = await managerApi.processLeave(appId, status);
    if (res.status === "success" || res.success) {
      successMessage.value = `Leave ${status} successfully`;
      leaves.value = leaves.value.filter((a) => a.name !== appId);
    } else {
      error.value = res.error || "Action failed";
    }
  } catch (e: any) {
    error.value = e.message || "Error processing request";
  } finally {
    processing.value = null;
    setTimeout(() => {
      successMessage.value = "";
      error.value = "";
    }, 3000);
  }
}

async function handleProcessExpense(appId: string, status: "Approve" | "Reject") {
  if (processing.value) return;
  processing.value = appId;
  error.value = "";
  successMessage.value = "";

  try {
    const res = await expensesApi.process(appId, status);
    if (res.status === "success" || res.success) {
      successMessage.value = `Expense ${status}d successfully`;
      expenses.value = expenses.value.filter((a) => a.name !== appId);
    } else {
      error.value = res.error || "Action failed";
    }
  } catch (e: any) {
    error.value = e.message || "Error processing request";
  } finally {
    processing.value = null;
    setTimeout(() => {
      successMessage.value = "";
      error.value = "";
    }, 3000);
  }
}

async function openProcessModal(claim: ExpenseClaim, action: "Approve" | "Reject") {
  selectedClaim.value = claim;
  modalAction.value = action;
  payableAccount.value = "";
  approvalError.value = "";
  payableAccounts.value = [];
  showApproveModal.value = true;

  if (claim.company) {
    try {
      const res = await expensesApi.getPayableAccounts(claim.company);
      payableAccounts.value = Array.isArray(res) ? res : [];
    } catch (e: any) {
      console.error("Failed to load payable accounts", e);
    }
  }
}

async function submitProcess() {
  if (!selectedClaim.value) return;
  if (!payableAccount.value) {
    approvalError.value = "Please select a Payable Account.";
    return;
  }

  isApproving.value = true;
  approvalError.value = "";

  try {
    const res = await expensesApi.process(selectedClaim.value.name, modalAction.value, payableAccount.value);
    if (res.status === "success" || res.success) {
      successMessage.value = `Expense ${modalAction.value === "Approve" ? "approved" : "rejected"} successfully`;
      expenses.value = expenses.value.filter((a) => a.name !== selectedClaim.value?.name);
      showApproveModal.value = false;
      selectedClaim.value = null;
    } else {
      approvalError.value = res.error || "Action failed";
    }
  } catch (e: any) {
    approvalError.value = e.message || "Error processing request";
  } finally {
    isApproving.value = false;
  }
}

function openDetailModal(exp: ExpenseClaim) {
  selectedDetail.value = exp;
  showDetailModal.value = true;
}

function formatDate(dateStr: string) {
  if (!dateStr) return "";
  if (typeof dateStr === "string" && dateStr.includes("-")) {
    const parts = dateStr.split("T")[0].split("-");
    if (parts.length === 3) {
      const [year, month, day] = parts;
      return `${day}/${month}/${year}`;
    }
  }
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return dateStr;
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const year = date.getFullYear();
  return `${day}/${month}/${year}`;
}

function statusColor(status: string) {
  if (status === "Approved" || status === "Paid") {
    return "text-[var(--success-text)] bg-[var(--success-bg)] border-[var(--success-text)]/20";
  }
  if (status === "Rejected") {
    return "text-[var(--danger-text)] bg-[var(--danger-bg)] border-[var(--danger-text)]/20";
  }
  return "text-[var(--warning-text)] bg-[var(--warning-bg)] border-[var(--warning-text)]/20";
}

onMounted(() => {
  loadData();
  window.addEventListener("click", handleWindowClick);
});
</script>

<template>
  <div>
    <div class="mb-8 animate-fade-in">
      <h1 class="text-2xl sm:text-3xl font-bold text-white">Team Approvals</h1>
      <p class="text-sm text-slate-500 mt-1">Manage requests from your team</p>
    </div>

    <!-- Tabs -->
    <div class="flex gap-4 mb-6 border-b border-white/5">
      <button
        @click="activeTab = 'leave'"
        class="pb-2 text-sm font-medium transition-colors relative"
        :class="activeTab === 'leave' ? 'text-teal-400' : 'text-slate-500 hover:text-slate-300'"
      >
        Leave Requests
        <span
          v-if="activeTab === 'leave'"
          class="absolute bottom-0 left-0 w-full h-0.5 bg-teal-500 rounded-full"
        ></span>
      </button>
      <button
        @click="activeTab = 'expense'"
        class="pb-2 text-sm font-medium transition-colors relative"
        :class="activeTab === 'expense' ? 'text-teal-400' : 'text-slate-500 hover:text-slate-300'"
      >
        Expense Claims
        <span
          v-if="activeTab === 'expense'"
          class="absolute bottom-0 left-0 w-full h-0.5 bg-teal-500 rounded-full"
        ></span>
      </button>
      <button
        v-if="isSystemManager"
        @click="activeTab = 'attendance'"
        class="pb-2 text-sm font-medium transition-colors relative"
        :class="activeTab === 'attendance' ? 'text-teal-400' : 'text-slate-500 hover:text-slate-300'"
      >
        Attendance Requests
        <span
          v-if="activeTab === 'attendance'"
          class="absolute bottom-0 left-0 w-full h-0.5 bg-teal-500 rounded-full"
        ></span>
      </button>
    </div>

    <!-- Alert Messages -->
    <div
      v-if="error"
      class="mb-4 p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-sm flex items-center gap-2"
    >
      <AlertCircle :size="16" />
      {{ error }}
    </div>
    <div
      v-if="successMessage"
      class="mb-4 p-3 bg-green-500/10 border border-green-500/20 text-green-400 rounded-lg text-sm flex items-center gap-2"
    >
      <CheckCircle :size="16" />
      {{ successMessage }}
    </div>

    <!-- Loading Skeleton -->
    <div v-if="loading" class="space-y-4">
      <div v-for="i in 3" :key="i" class="glass-card p-6 animate-pulse">
        <div class="h-4 bg-white/10 w-1/3 mb-2 rounded"></div>
        <div class="h-4 bg-white/5 w-1/2 rounded"></div>
      </div>
    </div>

    <!-- Leave Tab -->
    <div v-else-if="activeTab === 'leave'" class="space-y-4">
      <!-- Filters -->
      <div class="flex flex-col sm:flex-row gap-4 p-4 bg-white/5 border border-white/10 rounded-2xl animate-fade-in relative z-20">
        <!-- Status Filter -->
        <div class="flex-1">
          <label class="block text-[10px] font-semibold text-slate-400 uppercase mb-1.5 tracking-wider">Status</label>
          <div class="relative w-full">
            <select v-model="filterStatus" class="input-dark appearance-none pr-10 text-xs py-2 px-3">
              <option value="">All Statuses</option>
              <option value="Draft">Pending</option>
              <option value="Approved">Approved</option>
              <option value="Rejected">Rejected</option>
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
                class="w-full text-left px-2.5 py-1.5 rounded-lg transition-colors font-medium"
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

        <!-- Employee List Filter -->
        <div class="flex-1">
          <label class="block text-[10px] font-semibold text-slate-400 uppercase mb-1.5 tracking-wider">Employee</label>
          <div class="relative w-full">
            <select v-model="filterLeaveEmployee" class="input-dark appearance-none pr-10 text-xs py-2 px-3">
              <option value="">All Employees</option>
              <option v-for="emp in leaveEmployees" :key="emp.name" :value="emp.name">
                {{ emp.employee_name }}
              </option>
            </select>
            <ChevronDown class="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400" :size="14" />
          </div>
        </div>
      </div>

      <div
        v-if="leaves.length === 0"
        class="glass-card p-12 flex flex-col items-center justify-center text-center animate-fade-in"
      >
        <div class="w-16 h-16 rounded-full bg-slate-800/50 flex items-center justify-center mb-4">
          <CheckCircle class="text-emerald-400" :size="32" />
        </div>
        <h3 class="text-lg font-medium text-white mb-1">No leaves found</h3>
        <p class="text-slate-500">No leave requests match the selected filters.</p>
      </div>

      <div v-else class="glass-card overflow-hidden animate-slide-up w-full">
        <div class="w-full overflow-x-auto">
          <table class="w-full min-w-max text-left text-sm border-collapse">
            <thead>
              <tr class="text-xs font-semibold text-slate-500 uppercase border-b border-white/5 bg-white/[0.02]">
                <th class="px-6 py-4">Employee Name</th>
                <th class="px-6 py-4">Leave Type</th>
                <th class="px-6 py-4">Period</th>
                <th class="px-6 py-4 text-center">Days</th>
                <th class="px-6 py-4 text-center">Status / Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-white/5">
              <tr
                v-for="app in leaves"
                :key="app.name"
                @click="openLeaveDetailModal(app)"
                class="hover:bg-white/5 cursor-pointer transition-colors"
              >
                <td class="px-6 py-4">
                  <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center font-bold text-sm">
                      {{ app.employee_name.charAt(0) }}
                    </div>
                    <span class="font-medium text-white">{{ app.employee_name }}</span>
                  </div>
                </td>
                <td class="px-6 py-4 text-slate-400">{{ app.leave_type }}</td>
                <td class="px-6 py-4 text-slate-400">
                  {{ formatDate(app.from_date) }} — {{ formatDate(app.to_date) }}
                </td>
                <td class="px-6 py-4 text-center font-bold text-white">{{ app.total_leave_days }}</td>
                <td class="px-6 py-4 text-center" @click.stop>
                  <div v-if="app.status === 'Open'" class="flex items-center justify-center gap-2">
                    <button
                      @click="handleProcessLeave(app.name, 'Approved')"
                      :disabled="!!processing"
                      class="flex items-center justify-center gap-1.5 px-3 py-1.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-lg hover:bg-emerald-500/20 transition-colors disabled:opacity-50 text-xs font-medium cursor-pointer"
                    >
                      <CheckCircle :size="14" />
                      Approve
                    </button>
                    <button
                      @click="handleProcessLeave(app.name, 'Rejected')"
                      :disabled="!!processing"
                      class="flex items-center justify-center gap-1.5 px-3 py-1.5 bg-red-500/10 text-red-400 border border-red-500/20 rounded-lg hover:bg-red-500/20 transition-colors disabled:opacity-50 text-xs font-medium cursor-pointer"
                    >
                      <XCircle :size="14" />
                      Reject
                    </button>
                  </div>
                  <div v-else class="flex items-center justify-center">
                    <span class="inline-flex px-2.5 py-1 rounded-full text-xs font-medium border" :class="statusColor(app.status)">
                      {{ app.status }}
                    </span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Expense Tab -->
    <div v-else-if="activeTab === 'expense'" class="space-y-4">
      <!-- Filters -->
      <div class="flex flex-col sm:flex-row gap-4 p-4 bg-white/5 border border-white/10 rounded-2xl animate-fade-in relative z-20">
        <!-- Status Filter -->
        <div class="flex-1">
          <label class="block text-[10px] font-semibold text-slate-400 uppercase mb-1.5 tracking-wider">Status</label>
          <div class="relative w-full">
            <select v-model="filterStatus" class="input-dark appearance-none pr-10 text-xs py-2 px-3">
              <option value="">All Statuses</option>
              <option value="Draft">Pending</option>
              <option value="Approved">Approved</option>
              <option value="Rejected">Rejected</option>
              <option value="Paid">Paid</option>
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
                class="w-full text-left px-2.5 py-1.5 rounded-lg transition-colors font-medium"
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

        <!-- Employee List Filter -->
        <div class="flex-1">
          <label class="block text-[10px] font-semibold text-slate-400 uppercase mb-1.5 tracking-wider">Employee</label>
          <div class="relative w-full">
            <select v-model="filterExpenseEmployee" class="input-dark appearance-none pr-10 text-xs py-2 px-3">
              <option value="">All Employees</option>
              <option v-for="emp in expenseEmployees" :key="emp.name" :value="emp.name">
                {{ emp.employee_name }}
              </option>
            </select>
            <ChevronDown class="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400" :size="14" />
          </div>
        </div>
      </div>

      <div
        v-if="expenses.length === 0"
        class="glass-card p-12 flex flex-col items-center justify-center text-center animate-fade-in"
      >
        <div class="w-16 h-16 rounded-full bg-slate-800/50 flex items-center justify-center mb-4">
          <CheckCircle class="text-emerald-400" :size="32" />
        </div>
        <h3 class="text-lg font-medium text-white mb-1">No expenses found</h3>
        <p class="text-slate-500">No expense claims match the selected filters.</p>
      </div>

      <div v-else class="glass-card overflow-hidden animate-slide-up w-full">
        <div class="w-full overflow-x-auto">
          <table class="w-full min-w-max text-left text-sm border-collapse">
            <thead>
              <tr class="text-xs font-semibold text-slate-500 uppercase border-b border-white/5 bg-white/[0.02]">
                <th class="px-6 py-4">Employee Name</th>
                <th class="px-6 py-4">Posting Date</th>
                <th class="px-6 py-4">Amount</th>
                <th class="px-6 py-4 text-center">Status / Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-white/5">
              <tr
                v-for="exp in expenses"
                :key="exp.name"
                @click="openDetailModal(exp)"
                class="hover:bg-white/5 cursor-pointer transition-colors"
              >
                <td class="px-6 py-4">
                  <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-full bg-pink-500/20 text-pink-400 flex items-center justify-center font-bold text-sm">
                      {{ exp.employee_name.charAt(0) }}
                    </div>
                    <span class="font-medium text-white">{{ exp.employee_name }}</span>
                  </div>
                </td>
                <td class="px-6 py-4 text-slate-400">{{ formatDate(exp.posting_date) }}</td>
                <td class="px-6 py-4 font-bold text-white">₹{{ Number(exp.total_claimed_amount).toLocaleString() }}</td>
                <td class="px-6 py-4 text-center" @click.stop>
                  <div v-if="exp.approval_status === 'Draft'" class="flex items-center justify-center gap-2">
                    <button
                      @click="openProcessModal(exp, 'Approve')"
                      :disabled="!!processing"
                      class="flex items-center justify-center gap-1.5 px-3 py-1.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-lg hover:bg-emerald-500/20 transition-colors disabled:opacity-50 text-xs font-medium cursor-pointer"
                    >
                      <CheckCircle :size="14" />
                      Approve
                    </button>
                    <button
                      @click="openProcessModal(exp, 'Reject')"
                      :disabled="!!processing"
                      class="flex items-center justify-center gap-1.5 px-3 py-1.5 bg-red-500/10 text-red-400 border border-red-500/20 rounded-lg hover:bg-red-500/20 transition-colors disabled:opacity-50 text-xs font-medium cursor-pointer"
                    >
                      <XCircle :size="14" />
                      Reject
                    </button>
                  </div>
                  <div v-else class="flex items-center justify-center">
                    <span class="inline-flex px-2.5 py-1 rounded-full text-xs font-medium border" :class="statusColor(exp.approval_status)">
                      {{ exp.approval_status }}
                    </span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Attendance Request Tab -->
    <div v-else-if="activeTab === 'attendance'" class="space-y-4">
      <!-- Filters -->
      <div class="flex flex-col sm:flex-row gap-4 p-4 bg-white/5 border border-white/10 rounded-2xl animate-fade-in relative z-20">
        <!-- Status Filter -->
        <div class="flex-1">
          <label class="block text-[10px] font-semibold text-slate-400 uppercase mb-1.5 tracking-wider">Status</label>
          <div class="relative w-full">
            <select v-model="filterStatus" class="input-dark appearance-none pr-10 text-xs py-2 px-3">
              <option value="">All Statuses</option>
              <option value="Draft">Pending</option>
              <option value="Approved">Approved</option>
              <option value="Rejected">Rejected</option>
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
                class="w-full text-left px-2.5 py-1.5 rounded-lg transition-colors font-medium"
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

        <!-- Employee List Filter -->
        <div class="flex-1">
          <label class="block text-[10px] font-semibold text-slate-400 uppercase mb-1.5 tracking-wider">Employee</label>
          <div class="relative w-full">
            <select v-model="filterAttendanceEmployee" class="input-dark appearance-none pr-10 text-xs py-2 px-3">
              <option value="">All Employees</option>
              <option v-for="emp in attendanceEmployees" :key="emp.name" :value="emp.name">
                {{ emp.employee_name }}
              </option>
            </select>
            <ChevronDown class="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400" :size="14" />
          </div>
        </div>
      </div>

      <div
        v-if="attendanceRequests.length === 0"
        class="glass-card p-12 flex flex-col items-center justify-center text-center animate-fade-in"
      >
        <div class="w-16 h-16 rounded-full bg-slate-800/50 flex items-center justify-center mb-4">
          <CheckCircle class="text-emerald-400" :size="32" />
        </div>
        <h3 class="text-lg font-medium text-white mb-1">No attendance requests found</h3>
        <p class="text-slate-500">No attendance requests match the selected filters.</p>
      </div>

      <div v-else class="glass-card overflow-hidden animate-slide-up w-full">
        <div class="w-full overflow-x-auto">
          <table class="w-full min-w-max text-left text-sm border-collapse">
            <thead>
              <tr class="text-xs font-semibold text-slate-500 uppercase border-b border-white/5 bg-white/[0.02]">
                <th class="px-6 py-4">Employee Name</th>
                <th class="px-6 py-4">Reason</th>
                <th class="px-6 py-4">Period</th>
                <th class="px-6 py-4 text-center">Status / Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-white/5">
              <tr
                v-for="req in attendanceRequests"
                :key="req.name"
                @click="openAttendanceDetailModal(req)"
                class="hover:bg-white/5 cursor-pointer transition-colors"
              >
                <td class="px-6 py-4">
                  <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-full bg-teal-500/20 text-teal-400 flex items-center justify-center font-bold text-sm">
                      {{ req.employee_name.charAt(0) }}
                    </div>
                    <span class="font-medium text-white">{{ req.employee_name }}</span>
                  </div>
                </td>
                <td class="px-6 py-4 text-slate-400">{{ req.reason }}</td>
                <td class="px-6 py-4 text-slate-400">
                  {{ formatDate(req.from_date) }} — {{ formatDate(req.to_date) }}
                </td>
                <td class="px-6 py-4 text-center" @click.stop>
                  <div v-if="req.status === 'Open'" class="flex items-center justify-center gap-2">
                    <button
                      @click="handleProcessAttendanceRequest(req.name, 'Approve')"
                      :disabled="!!processing"
                      class="flex items-center justify-center gap-1.5 px-3 py-1.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-lg hover:bg-emerald-500/20 transition-colors disabled:opacity-50 text-xs font-medium cursor-pointer"
                    >
                      <CheckCircle :size="14" />
                      Approve
                    </button>
                    <button
                      @click="handleProcessAttendanceRequest(req.name, 'Reject')"
                      :disabled="!!processing"
                      class="flex items-center justify-center gap-1.5 px-3 py-1.5 bg-red-500/10 text-red-400 border border-red-500/20 rounded-lg hover:bg-red-500/20 transition-colors disabled:opacity-50 text-xs font-medium cursor-pointer"
                    >
                      <XCircle :size="14" />
                      Reject
                    </button>
                  </div>
                  <div v-else class="flex items-center justify-center">
                    <span class="inline-flex px-2.5 py-1 rounded-full text-xs font-medium border" :class="statusColor(req.status)">
                      {{ req.status }}
                    </span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Process Expense Modal -->
    <div v-if="showApproveModal && selectedClaim" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showApproveModal = false"></div>
      <div class="glass-card w-full max-w-2xl p-6 relative animate-scale-in max-h-[90vh] overflow-y-auto no-scrollbar">
        <button
          @click="showApproveModal = false"
          class="absolute right-4 top-4 text-slate-500 hover:text-white"
        >
          <X :size="20" />
        </button>

        <h2 class="text-xl font-bold text-white mb-6 flex items-center gap-2">
          <Receipt class="text-teal-400" /> {{ modalAction === 'Approve' ? 'Approve' : 'Reject' }} Expense Claim
        </h2>

        <form @submit.prevent="submitProcess" class="space-y-4">
          <!-- Error -->
          <div
            v-if="approvalError"
            class="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2"
          >
            <AlertCircle :size="16" /> {{ approvalError }}
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-medium text-slate-400 mb-1.5 uppercase">Employee Name</label>
              <input
                type="text"
                disabled
                :value="selectedClaim.employee_name"
                class="input-dark opacity-60 cursor-not-allowed py-2 px-3"
              />
            </div>
            <div>
              <label class="block text-xs font-medium text-slate-400 mb-1.5 uppercase">Posting Date</label>
              <input
                type="text"
                disabled
                :value="formatDate(selectedClaim.posting_date)"
                class="input-dark opacity-60 cursor-not-allowed py-2 px-3"
              />
            </div>
          </div>

          <!-- Expense Lines Table -->
          <div>
            <label class="block text-xs font-medium text-slate-400 mb-1.5 uppercase">Expense Items</label>
            <div class="border border-white/10 rounded-lg overflow-hidden">
              <table class="w-full text-left border-collapse text-[11px]">
                <thead class="bg-white/5 border-b border-white/10 text-slate-400 font-medium">
                  <tr>
                    <th class="p-2">Date</th>
                    <th class="p-2">Type</th>
                    <th class="p-2">Amount</th>
                    <th class="p-2">Description</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-white/5 text-slate-300">
                  <tr v-for="(line, idx) in selectedClaim.expenses" :key="idx" class="hover:bg-white/[0.02]">
                    <td class="p-2 whitespace-nowrap">{{ formatDate(line.expense_date) }}</td>
                    <td class="p-2 whitespace-nowrap">{{ line.expense_type }}</td>
                    <td class="p-2 font-medium text-white">₹{{ Number(line.amount).toLocaleString() }}</td>
                    <td class="p-2 text-slate-400 max-w-[200px] truncate" :title="line.description">{{ line.description || '-' }}</td>
                  </tr>
                  <tr v-if="!selectedClaim.expenses || selectedClaim.expenses.length === 0">
                    <td colspan="4" class="p-2 text-center text-slate-500">No lines found.</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div v-if="selectedClaim.remark">
            <label class="block text-xs font-medium text-slate-400 mb-1.5 uppercase">Remark / Notes</label>
            <textarea
              disabled
              rows="2"
              :value="selectedClaim.remark"
              class="input-dark opacity-60 cursor-not-allowed resize-none"
            ></textarea>
          </div>

          <!-- Attached Proofs -->
          <div v-if="selectedClaim.proofs && selectedClaim.proofs.length > 0" class="bg-white/5 p-4 rounded-xl border border-white/5 text-xs">
            <p class="text-slate-500 text-xs uppercase mb-2">Attached Proofs</p>
            <div class="space-y-2">
              <div v-for="(proofUrl, idx) in selectedClaim.proofs" :key="idx" class="flex items-center gap-2">
                <FileText :size="16" class="text-teal-400" />
                <a :href="proofUrl" target="_blank" class="text-teal-400 hover:underline hover:text-teal-300 font-medium truncate max-w-[400px]">
                  Proof Attachment {{ idx + 1 }}
                </a>
              </div>
            </div>
          </div>
          <div v-else-if="selectedClaim.proof" class="bg-white/5 p-4 rounded-xl border border-white/5 text-xs">
            <p class="text-slate-500 text-xs uppercase mb-2">Attached Proof</p>
            <div class="flex items-center gap-2">
              <FileText :size="16" class="text-teal-400" />
              <a :href="selectedClaim.proof" target="_blank" class="text-teal-400 hover:underline hover:text-teal-300 font-medium">
                View Receipt / Bill
              </a>
            </div>
          </div>

          <div class="flex items-center justify-between border-t border-white/5 pt-4">
            <span class="text-xs text-slate-500 uppercase">Total Claim Amount</span>
            <span class="text-xl font-bold text-white">₹{{ Number(selectedClaim.total_claimed_amount).toLocaleString() }}</span>
          </div>

          <div>
            <label class="block text-xs font-medium text-slate-400 mb-1.5 uppercase">Payable Account</label>
            <select
              v-model="payableAccount"
              required
              class="input-dark"
            >
              <option value="" disabled>Select Payable Account</option>
              <option v-for="acc in payableAccounts" :key="acc.value" :value="acc.value">
                {{ acc.label || acc.value }}
              </option>
            </select>
          </div>

          <button
            type="submit"
            :disabled="isApproving"
            class="w-full mt-4 bg-gradient-to-r text-white font-medium py-2.5 rounded-lg shadow-lg flex items-center justify-center gap-2"
            :class="modalAction === 'Approve' ? 'from-teal-500 to-emerald-500 hover:from-teal-400 hover:to-emerald-400' : 'from-red-500 to-rose-500 hover:from-red-400 hover:to-rose-400'"
          >
            <span
              v-if="isApproving"
              class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"
            ></span>
            <span v-else>{{ modalAction === 'Approve' ? 'Approve' : 'Reject' }}</span>
          </button>
        </form>
      </div>
    </div>

    <!-- Claim Details Modal -->
    <div v-if="showDetailModal && selectedDetail" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showDetailModal = false"></div>
      <div class="glass-card w-full max-w-2xl p-6 relative animate-scale-in max-h-[90vh] overflow-y-auto no-scrollbar">
        <button
          @click="showDetailModal = false"
          class="absolute right-4 top-4 text-slate-500 hover:text-white"
        >
          <X :size="20" />
        </button>

        <h2 class="text-xl font-bold text-white mb-6 flex items-center gap-2">
          <FileText class="text-teal-400" /> Claim Details
        </h2>

        <div class="space-y-6">
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p class="text-slate-500 text-xs font-semibold">Reference ID</p>
              <p class="text-white font-medium mt-1">{{ selectedDetail.name }}</p>
            </div>
            <div>
              <p class="text-slate-500 text-xs font-semibold">Status</p>
              <span
                class="inline-block px-2.5 py-1 rounded-full text-xs font-semibold border mt-1"
                :class="statusColor(selectedDetail.approval_status)"
              >
                {{ selectedDetail.approval_status }}
              </span>
            </div>
            <div>
              <p class="text-slate-500 text-xs font-semibold">Posting Date</p>
              <p class="text-white font-medium mt-1">{{ formatDate(selectedDetail.posting_date) }}</p>
            </div>
            <div>
              <p class="text-slate-500 text-xs font-semibold">Employee</p>
              <p class="text-white font-medium mt-1">{{ selectedDetail.employee_name }}</p>
            </div>
            <div v-if="selectedDetail.payable_account">
              <p class="text-slate-500 text-xs font-semibold">Payable Account</p>
              <p class="text-white font-medium mt-1">{{ selectedDetail.payable_account }}</p>
            </div>
          </div>

          <!-- Table of lines -->
          <div class="border border-white/10 rounded-xl overflow-x-auto">
            <table class="w-full text-left border-collapse text-xs">
              <thead class="bg-white/5 border-b border-white/10 text-slate-400 font-medium">
                <tr>
                  <th class="p-3">Date</th>
                  <th class="p-3">Type</th>
                  <th class="p-3">Amount</th>
                  <th class="p-3">Description</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-white/5 text-slate-300">
                <tr v-for="(line, idx) in selectedDetail.expenses" :key="idx" class="hover:bg-white/[0.02]">
                  <td class="p-3 whitespace-nowrap">{{ formatDate(line.expense_date) }}</td>
                  <td class="p-3 whitespace-nowrap">{{ line.expense_type }}</td>
                  <td class="p-3 font-medium text-white">₹{{ Number(line.amount).toLocaleString() }}</td>
                  <td class="p-3 text-slate-400">{{ line.description || '-' }}</td>
                </tr>
                <tr v-if="!selectedDetail.expenses || selectedDetail.expenses.length === 0">
                  <td colspan="4" class="p-3 text-center text-slate-500">No lines found.</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="selectedDetail.remark" class="bg-white/5 p-4 rounded-xl border border-white/10">
            <p class="text-slate-500 text-xs uppercase mb-1 font-semibold">Remark / Notes</p>
            <p class="text-slate-300 text-sm whitespace-pre-wrap">{{ selectedDetail.remark }}</p>
          </div>

          <div v-if="selectedDetail.proofs && selectedDetail.proofs.length > 0" class="bg-white/5 p-4 rounded-xl border border-white/10 text-xs">
            <p class="text-slate-500 text-xs uppercase mb-2 font-semibold">Attached Proofs</p>
            <div class="space-y-2">
              <div v-for="(proofUrl, idx) in selectedDetail.proofs" :key="idx" class="flex items-center gap-2">
                <FileText :size="16" class="text-teal-400" />
                <a :href="proofUrl" target="_blank" class="text-teal-400 hover:underline hover:text-teal-300 font-medium truncate max-w-[400px]">
                  Proof Attachment {{ idx + 1 }}
                </a>
              </div>
            </div>
          </div>
          <div v-else-if="selectedDetail.proof" class="bg-white/5 p-4 rounded-xl border border-white/10 text-xs">
            <p class="text-slate-500 text-xs uppercase mb-2 font-semibold">Attached Proof</p>
            <div class="flex items-center gap-2">
              <FileText :size="16" class="text-teal-400" />
              <a :href="selectedDetail.proof" target="_blank" class="text-teal-400 hover:underline hover:text-teal-300 font-medium">
                View Receipt / Bill
              </a>
            </div>
          </div>

          <div class="flex items-center justify-between border-t border-white/10 pt-4">
            <span class="text-sm text-slate-500 font-semibold">Total Claim Amount</span>
            <span class="text-xl font-bold text-white">₹{{ Number(selectedDetail.total_claimed_amount).toLocaleString() }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Leave Details Modal -->
    <div v-if="showLeaveDetailModal && selectedLeaveDetail" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showLeaveDetailModal = false"></div>
      <div class="glass-card w-full max-w-2xl p-6 relative animate-scale-in max-h-[90vh] overflow-y-auto no-scrollbar">
        <button
          @click="showLeaveDetailModal = false"
          class="absolute right-4 top-4 text-slate-500 hover:text-white"
        >
          <X :size="20" />
        </button>

        <h2 class="text-xl font-bold text-white mb-6 flex items-center gap-2">
          <FileText class="text-teal-400" /> Leave Request Details
        </h2>

        <div class="space-y-6">
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p class="text-slate-500 text-xs font-semibold">Reference ID</p>
              <p class="text-white font-medium mt-1">{{ selectedLeaveDetail.name }}</p>
            </div>
            <div>
              <p class="text-slate-500 text-xs font-semibold">Status</p>
              <span
                class="inline-block px-2.5 py-1 rounded-full text-xs font-semibold border mt-1"
                :class="statusColor(selectedLeaveDetail.status)"
              >
                {{ selectedLeaveDetail.status }}
              </span>
            </div>
            <div>
              <p class="text-slate-500 text-xs font-semibold">Applied Date</p>
              <p class="text-white font-medium mt-1">{{ formatDate(selectedLeaveDetail.creation) }}</p>
            </div>
            <div>
              <p class="text-slate-500 text-xs font-semibold">Employee</p>
              <p class="text-white font-medium mt-1">{{ selectedLeaveDetail.employee_name }}</p>
            </div>
            <div>
              <p class="text-slate-500 text-xs font-semibold">Leave Type</p>
              <p class="text-white font-medium mt-1">{{ selectedLeaveDetail.leave_type }}</p>
            </div>
            <div>
              <p class="text-slate-500 text-xs font-semibold">Total Days</p>
              <p class="text-white font-medium mt-1">{{ selectedLeaveDetail.total_leave_days }}</p>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p class="text-slate-500 text-xs font-semibold">From Date</p>
              <p class="text-white font-medium mt-1">{{ formatDate(selectedLeaveDetail.from_date) }}</p>
            </div>
            <div>
              <p class="text-slate-500 text-xs font-semibold">To Date</p>
              <p class="text-white font-medium mt-1">{{ formatDate(selectedLeaveDetail.to_date) }}</p>
            </div>
          </div>

          <div v-if="selectedLeaveDetail.description" class="bg-white/5 p-4 rounded-xl border border-white/10">
            <p class="text-slate-500 text-xs uppercase mb-1 font-semibold">Reason / Description</p>
            <p class="text-slate-300 text-sm whitespace-pre-wrap">{{ selectedLeaveDetail.description }}</p>
          </div>

          <!-- Approve/Reject buttons inside Detail Modal if it is still Open -->
          <div v-if="selectedLeaveDetail.status === 'Open'" class="flex items-center gap-4 border-t border-white/10 pt-6">
            <button
              @click="handleProcessLeave(selectedLeaveDetail.name, 'Approved'); showLeaveDetailModal = false;"
              :disabled="!!processing"
              class="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-medium rounded-lg shadow-lg active:scale-95 transition-all text-sm cursor-pointer"
            >
              <CheckCircle :size="16" />
              Approve Leave
            </button>
            <button
              @click="handleProcessLeave(selectedLeaveDetail.name, 'Rejected'); showLeaveDetailModal = false;"
              :disabled="!!processing"
              class="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-red-500 to-rose-500 text-white font-medium rounded-lg shadow-lg active:scale-95 transition-all text-sm cursor-pointer"
            >
              <XCircle :size="16" />
              Reject Leave
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Attendance Request Details Modal -->
    <div v-if="showAttendanceDetailModal && selectedAttendanceDetail" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showAttendanceDetailModal = false"></div>
      <div class="glass-card w-full max-w-2xl p-6 relative animate-scale-in max-h-[90vh] overflow-y-auto no-scrollbar">
        <button
          @click="showAttendanceDetailModal = false"
          class="absolute right-4 top-4 text-slate-500 hover:text-white"
        >
          <X :size="20" />
        </button>

        <h2 class="text-xl font-bold text-white mb-6 flex items-center gap-2">
          <FileText class="text-teal-400" /> Attendance Request Details
        </h2>

        <div class="space-y-6">
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p class="text-slate-500 text-xs font-semibold">Reference ID</p>
              <p class="text-white font-medium mt-1">{{ selectedAttendanceDetail.name }}</p>
            </div>
            <div>
              <p class="text-slate-500 text-xs font-semibold">Status</p>
              <span
                class="inline-block px-2.5 py-1 rounded-full text-xs font-semibold border mt-1"
                :class="statusColor(selectedAttendanceDetail.status)"
              >
                {{ selectedAttendanceDetail.status }}
              </span>
            </div>
            <div>
              <p class="text-slate-500 text-xs font-semibold">Applied Date</p>
              <p class="text-white font-medium mt-1">{{ formatDate(selectedAttendanceDetail.creation) }}</p>
            </div>
            <div>
              <p class="text-slate-500 text-xs font-semibold">Employee</p>
              <p class="text-white font-medium mt-1">{{ selectedAttendanceDetail.employee_name }}</p>
            </div>
            <div>
              <p class="text-slate-500 text-xs font-semibold">Reason</p>
              <p class="text-white font-medium mt-1">{{ selectedAttendanceDetail.reason }}</p>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p class="text-slate-500 text-xs font-semibold">From Date</p>
              <p class="text-white font-medium mt-1">{{ formatDate(selectedAttendanceDetail.from_date) }}</p>
            </div>
            <div>
              <p class="text-slate-500 text-xs font-semibold">To Date</p>
              <p class="text-white font-medium mt-1">{{ formatDate(selectedAttendanceDetail.to_date) }}</p>
            </div>
          </div>

          <div v-if="selectedAttendanceDetail.explanation" class="bg-white/5 p-4 rounded-xl border border-white/10">
            <p class="text-slate-500 text-xs uppercase mb-1 font-semibold">Explanation / Description</p>
            <p class="text-slate-300 text-sm whitespace-pre-wrap">{{ selectedAttendanceDetail.explanation }}</p>
          </div>

          <!-- Approve/Reject buttons inside Detail Modal if it is still Open -->
          <div v-if="selectedAttendanceDetail.status === 'Open'" class="flex items-center gap-4 border-t border-white/10 pt-6">
            <button
              @click="handleProcessAttendanceRequest(selectedAttendanceDetail.name, 'Approve'); showAttendanceDetailModal = false;"
              :disabled="!!processing"
              class="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-medium rounded-lg shadow-lg active:scale-95 transition-all text-sm cursor-pointer"
            >
              <CheckCircle :size="16" />
              Approve Request
            </button>
            <button
              @click="handleProcessAttendanceRequest(selectedAttendanceDetail.name, 'Reject'); showAttendanceDetailModal = false;"
              :disabled="!!processing"
              class="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-red-500 to-rose-500 text-white font-medium rounded-lg shadow-lg active:scale-95 transition-all text-sm cursor-pointer"
            >
              <XCircle :size="16" />
              Reject Request
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
