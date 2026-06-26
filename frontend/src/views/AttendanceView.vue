<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { attendanceApi, leaveApi, managerApi, useCachedFetch } from "../services/api";
import ClockWidget from "../components/ClockWidget.vue";
import {
  CalendarCheck,
  CalendarX,
  CalendarClock,
  CalendarHeart,
  Calendar,
  ChevronDown,
  Clock,
  Plus,
  X,
  Pencil,
  Trash2,
  Eye,
  CheckCircle,
  XCircle,
  FileText,
} from "lucide-vue-next";

const loading = ref(true);

// Month filter — default to current month
const _today = new Date();
const selectedMonth = ref(_today.getMonth() + 1);
const selectedYear = ref(_today.getFullYear());

interface AttendanceRecord {
  name?: string;
  date: string;
  status: string;
  working_hours: number;
  break_hours?: number;
  in_time: string | null;
  out_time: string | null;
  employee?: string;
  employee_name?: string;
}

const records = ref<AttendanceRecord[]>([]);
const summary = ref<Record<string, number>>({});
const holidays = ref<{ holiday_date: string; description: string; weekly_off?: number }[]>([]);

// Employee list and selection
const employeeList = ref<{ name: string; employee_name: string }[]>([]);
const selectedEmployee = ref<string>("");
const showEmployeeFilter = computed(() => employeeList.value.length > 1);
const canMark = ref(false);

// View Attendance Modal state
const showViewModal = ref(false);
const selectedRecord = ref<AttendanceRecord | null>(null);
const breakLogs = ref<{ break_in: string | null; break_out: string | null; duration: number | null }[]>([]);
const loadingBreaks = ref(false);

async function viewRecord(rec: AttendanceRecord) {
  selectedRecord.value = rec;
  showViewModal.value = true;
  breakLogs.value = [];
  loadingBreaks.value = true;
  try {
    const res = await attendanceApi.getAttendanceBreaks(rec.employee, rec.date);
    breakLogs.value = res || [];
  } catch (e) {
    console.error("Failed to load break logs", e);
  } finally {
    loadingBreaks.value = false;
  }
}

// Add/Edit Attendance Modal state and form
const showAddModal = ref(false);
const submitting = ref(false);
const formError = ref("");
const statusOptions = ref<string[]>([]);
const editingRecordId = ref<string | null>(null);
const hadInTime = ref(false);
const hadOutTime = ref(false);

const addForm = ref({
  employee: "",
  date: "",
  status: "",
  in_time: "",
  out_time: "",
});

function openAddModal() {
  editingRecordId.value = null;
  hadInTime.value = false;
  hadOutTime.value = false;
  addForm.value = {
    employee: employeeList.value[0]?.name || "",
    date: new Date().toISOString().split("T")[0],
    status: statusOptions.value[0] || "Present",
    in_time: "",
    out_time: "",
  };
  formError.value = "";
  showAddModal.value = true;
}

const showRequestModal = ref(false);
const requestSubmitting = ref(false);
const requestFormError = ref("");
const editingRequestId = ref<string | null>(null);
const requestForm = ref({
  from_date: "",
  to_date: "",
  reason: "On Duty",
  explanation: "",
});

function openRequestModal() {
  editingRequestId.value = null;
  requestForm.value = {
    from_date: "",
    to_date: "",
    reason: "On Duty",
    explanation: "",
  };
  requestFormError.value = "";
  showRequestModal.value = true;
}

watch(() => requestForm.value.from_date, (newFromDate) => {
  if (newFromDate && !editingRequestId.value) {
    requestForm.value.to_date = newFromDate;
  }
});

async function submitRequestForm() {
  if (requestSubmitting.value) return;
  requestSubmitting.value = true;
  requestFormError.value = "";
  try {
    let res;
    if (editingRequestId.value) {
      res = await attendanceApi.updateRequest({
        name: editingRequestId.value,
        from_date: requestForm.value.from_date,
        to_date: requestForm.value.to_date,
        reason: "On Duty",
        explanation: requestForm.value.explanation,
      });
    } else {
      res = await attendanceApi.createRequest({
        from_date: requestForm.value.from_date,
        to_date: requestForm.value.to_date,
        reason: "On Duty",
        explanation: requestForm.value.explanation,
      });
    }
    if (res && res.status === "success") {
      showRequestModal.value = false;
      loadData();
      loadMyRequests();
    } else {
      requestFormError.value = res.message || "Failed to submit attendance request";
    }
  } catch (e: any) {
    requestFormError.value = e.message || "Something went wrong";
  } finally {
    requestSubmitting.value = false;
  }
}

// ===== My Attendance Requests =====
interface AttendanceRequestRecord {
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

const myRequests = ref<AttendanceRequestRecord[]>([]);
const loadingRequests = ref(false);
const showRequestDetailModal = ref(false);
const selectedRequest = ref<AttendanceRequestRecord | null>(null);
const requestProcessing = ref<string | null>(null);
const requestSuccessMessage = ref("");
const requestErrorMessage = ref("");

async function loadMyRequests() {
  loadingRequests.value = true;
  try {
    let allRequests: AttendanceRequestRecord[] = [];

    const mStr = String(selectedMonth.value).padStart(2, "0");
    const lastDay = new Date(selectedYear.value, selectedMonth.value, 0).getDate();
    const fromDate = `${selectedYear.value}-${mStr}-01`;
    const toDate = `${selectedYear.value}-${mStr}-${String(lastDay).padStart(2, "0")}`;
    const empFilter = selectedEmployee.value;

    // Try fetching own requests (if no specific employee is selected or if "all" is selected)
    if (!empFilter || empFilter === "all") {
      try {
        const myData = await attendanceApi.getMyRequests(undefined, fromDate, toDate);
        if (Array.isArray(myData)) {
          allRequests = [...myData];
        }
      } catch (e) {
        console.warn("Could not load own requests", e);
      }
    }

    // If manager, fetch team requests based on filters
    if (canMark.value) {
      try {
        const teamEmp = empFilter === "all" ? undefined : empFilter;
        const teamData = await managerApi.getTeamAttendanceRequests(undefined, fromDate, toDate, teamEmp);
        if (Array.isArray(teamData)) {
          // Merge by name to avoid duplicates
          const existingNames = new Set(allRequests.map((r) => r.name));
          for (const req of teamData) {
            if (!existingNames.has(req.name)) {
              allRequests.push(req);
            }
          }
        }
      } catch (e) {
        console.warn("Could not load team requests", e);
      }
    }

    // Sort by creation desc
    allRequests.sort((a, b) => {
      const dA = new Date(a.creation || 0).getTime();
      const dB = new Date(b.creation || 0).getTime();
      return dB - dA;
    });

    myRequests.value = allRequests;
  } catch (e) {
    console.error("Failed to load attendance requests", e);
  } finally {
    loadingRequests.value = false;
  }
}

function openRequestDetail(req: AttendanceRequestRecord) {
  selectedRequest.value = req;
  showRequestDetailModal.value = true;
}



async function handleApproveReject(name: string, action: "Approve" | "Reject") {
  if (requestProcessing.value) return;
  requestProcessing.value = name;
  requestErrorMessage.value = "";
  requestSuccessMessage.value = "";
  try {
    const res = await managerApi.processAttendanceRequest(name, action);
    if (res.status === "success") {
      requestSuccessMessage.value = `Attendance request ${action === "Approve" ? "approved" : "rejected"} successfully`;
      loadMyRequests();
      window.dispatchEvent(new CustomEvent("refresh-pending-counts"));
    } else {
      requestErrorMessage.value = res.message || "Action failed";
    }
  } catch (e: any) {
    requestErrorMessage.value = e.message || "Error processing request";
  } finally {
    requestProcessing.value = null;
    setTimeout(() => {
      requestSuccessMessage.value = "";
      requestErrorMessage.value = "";
    }, 3000);
  }
}

function requestStatusBadge(status: string) {
  const map: Record<string, string> = {
    Open: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    Approved: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    Rejected: "bg-red-500/10 text-red-400 border-red-500/20",
  };
  return map[status] || "bg-slate-500/10 text-slate-400 border-slate-500/20";
}

function extractTime(dtStr: string | null | undefined): string {
  if (!dtStr) return "";
  const parts = dtStr.split(/[ T]/);
  if (parts.length > 1) {
    return parts[1].substring(0, 5); // get HH:MM
  }
  return "";
}

function editAttendance(rec: AttendanceRecord) {
  editingRecordId.value = rec.name || null;
  hadInTime.value = !!rec.in_time;
  hadOutTime.value = !!rec.out_time;
  addForm.value = {
    employee: rec.employee || "",
    date: rec.date,
    status: rec.status,
    in_time: extractTime(rec.in_time),
    out_time: extractTime(rec.out_time),
  };
  formError.value = "";
  showAddModal.value = true;
}

async function submitForm() {
  if (submitting.value) return;
  submitting.value = true;
  formError.value = "";
  try {
    const res = await attendanceApi.submitManualAttendance({
      employee: addForm.value.employee,
      date: addForm.value.date,
      status: addForm.value.status,
      in_time: addForm.value.in_time || undefined,
      out_time: addForm.value.out_time || undefined,
      id: editingRecordId.value || undefined,
    });
    if (res && res.status === "success") {
      showAddModal.value = false;
      loadData();
    } else {
      formError.value = res.message || "Failed to submit attendance";
    }
  } catch (e: any) {
    formError.value = e.message || "Something went wrong";
  } finally {
    submitting.value = false;
  }
}

async function deleteAttendance(rec: AttendanceRecord) {
  if (!rec.name) {
    alert("Cannot delete this record: Attendance ID is missing.");
    return;
  }
  if (!confirm(`Are you sure you want to delete the attendance record for employee ${rec.employee_name || rec.employee} on ${rec.date}?`)) {
    return;
  }
  try {
    const res = await attendanceApi.deleteAttendance(rec.name);
    if (res && res.status === "success") {
      alert(res.message || "Attendance record deleted successfully.");
      loadData();
    } else {
      alert(res?.message || "Failed to delete attendance record.");
    }
  } catch (e: any) {
    alert(e.message || "An error occurred while deleting the attendance record.");
  }
}

// Month options (last 12 months + current + next 2)
const monthOptions = computed(() => {
  const opts: { value: string; label: string; month: number; year: number }[] = [];
  const now = new Date();
  // Go back 12 months and forward 2
  for (let offset = -12; offset <= 2; offset++) {
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

// Holiday month key for filtering
const holidayMonthKey = computed(
  () => `${selectedYear.value}-${String(selectedMonth.value).padStart(2, "0")}`
);

const filteredHolidays = computed(() => {
  return holidays.value.filter((h) => h.holiday_date.startsWith(holidayMonthKey.value));
});

// Stats cards
const stats = computed(() => {
  const s = summary.value || {};
  return [
    {
      label: "Present",
      value: s["Present"] || 0,
      icon: CalendarCheck,
      color: "text-emerald-400",
      bg: "bg-emerald-500/10",
    },
    {
      label: "Absent",
      value: s["Absent"] || 0,
      icon: CalendarX,
      color: "text-red-400",
      bg: "bg-red-500/10",
    },
    {
      label: "Half Day",
      value: s["Half Day"] || 0,
      icon: CalendarClock,
      color: "text-amber-400",
      bg: "bg-amber-500/10",
    },
    {
      label: "On Leave",
      value: s["On Leave"] || 0,
      icon: CalendarHeart,
      color: "text-blue-400",
      bg: "bg-blue-500/10",
    },
  ];
});

function statusColor(status: string) {
  const map: Record<string, string> = {
    Present: "text-emerald-400",
    Absent: "text-red-400",
    "Half Day": "text-amber-400",
    "On Leave": "text-blue-400",
  };
  return map[status] || "text-slate-400";
}

function statusBadge(status: string) {
  const map: Record<string, string> = {
    Present: "badge-success",
    Absent: "badge-danger",
    "Half Day": "badge-warning",
    "On Leave": "badge-info",
  };
  return map[status] || "badge-neutral";
}

function formatTime(timeStr: string | null) {
  if (!timeStr) return "—";
  try {
    const d = new Date(timeStr);
    if (isNaN(d.getTime())) return timeStr;
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return timeStr;
  }
}

function formatDate(dateStr: string) {
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
  } catch {
    return dateStr;
  }
}

async function loadData() {
  // loading.value = true; // Use cache
  const m = selectedMonth.value;
  const y = selectedYear.value;
  const emp = selectedEmployee.value;
  const key = `attendance_${y}_${m}_${emp || "self"}`;

  useCachedFetch(
    key,
    () => attendanceApi.getRecords(m, y, emp),
    (data) => {
      if (data) {
        records.value = data.records || [];
        summary.value = data.summary || {};
        loading.value = false;
      }
    }
  );

  const holKey = `holidays_${y}`;
  useCachedFetch(
    holKey,
    () => leaveApi.getHolidays(`${y}-01-01`, `${y}-12-31`),
    (data) => {
      if (Array.isArray(data)) holidays.value = data;
    }
  );
}

// Reload when month or employee changes
watch([selectedMonth, selectedYear, selectedEmployee], () => {
  loadData();
  loadMyRequests();
});

function onPunched() {
  // Reload attendance data after punch
  loadData();
}

onMounted(async () => {
  let listFetched = false;
  try {
    const emps = await attendanceApi.getShiftApproverEmployees();
    if (Array.isArray(emps)) {
      employeeList.value = emps;
      if (emps.length > 0) {
        selectedEmployee.value = emps[0].name;
        listFetched = true;
      }
    }
  } catch (e) {
    console.error("Failed to load employee list", e);
  }

  try {
    canMark.value = await attendanceApi.canMarkAttendance();
  } catch (e) {
    console.error("Failed to check attendance permission", e);
  }

  try {
    const statuses = await attendanceApi.getAttendanceStatusList();
    if (Array.isArray(statuses)) {
      statusOptions.value = statuses;
    }
  } catch (e) {
    console.error("Failed to load attendance statuses", e);
  }

  if (!listFetched) {
    await loadData();
  }

  loadMyRequests();
});

onUnmounted(() => {
});
</script>

<template>
  <div>
    <!-- Header -->
    <div
      class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8 animate-fade-in"
    >
      <div>
        <h1 class="text-2xl sm:text-3xl font-bold text-white">Attendance</h1>
        <p class="text-sm text-slate-500 mt-1">Track your daily attendance and working hours</p>
      </div>
    </div>

    <!-- Clock Widget -->
    <div class="glass-card p-6 sm:p-8 flex flex-col items-center justify-center mb-6 animate-fade-in">
      <h2 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-6">
        Today's Clock
      </h2>
      <ClockWidget @punched="onPunched" />
    </div>

    <!-- Filters and Action row -->
    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 animate-fade-in">
      <div>
        <button
          v-if="canMark"
          @click="openAddModal"
          class="btn-accent flex items-center gap-2"
        >
          <Plus :size="18" />
          Add Attendance
        </button>
        <button
          v-else
          @click="openRequestModal"
          class="btn-accent flex items-center gap-2"
        >
          <Plus :size="18" />
          Request Attendance
        </button>
      </div>

      <div class="flex flex-col sm:flex-row items-end sm:items-center gap-4 shrink-0">
        <!-- Employee selector -->
        <div v-if="showEmployeeFilter" class="flex items-center gap-2 shrink-0">
          <label class="text-xs text-slate-500 whitespace-nowrap">Employee:</label>
          <div class="relative">
            <select
              v-model="selectedEmployee"
              class="input-dark appearance-none pr-8 pl-3 py-2 text-sm cursor-pointer min-w-[180px] border border-white/10 rounded-lg"
            >
              <option value="all">All Employees</option>
              <option v-for="emp in employeeList" :key="emp.name" :value="emp.name">
                {{ emp.employee_name }}
              </option>
            </select>
            <ChevronDown
              :size="14"
              class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none"
            />
          </div>
        </div>

        <!-- Month selector -->
        <div class="flex items-center gap-2 shrink-0">
          <label class="text-xs text-slate-500 whitespace-nowrap">Month:</label>
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
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-12">
      <div class="w-10 h-10 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
    </div>

    <div v-else class="space-y-6 animate-slide-up">
      <!-- Summary Stats -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div v-for="stat in stats" :key="stat.label" class="glass-card-hover p-5">
          <div class="flex items-center justify-between mb-3">
            <span class="text-sm font-medium text-slate-400">{{ stat.label }}</span>
            <div
              :class="[stat.bg, stat.color]"
              class="w-9 h-9 rounded-xl flex items-center justify-center"
            >
              <component :is="stat.icon" :size="18" :stroke-width="1.8" />
            </div>
          </div>
          <p class="stat-number" :class="stat.color">{{ stat.value }}</p>
        </div>
      </div>

      <!-- Holidays for selected month -->
      <div v-if="filteredHolidays.length" class="glass-card p-5">
        <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
          Holidays in
          {{ monthOptions.find((o) => o.value === selectedMonthKey)?.label || "Selected Month" }}
        </h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <div
            v-for="h in filteredHolidays"
            :key="h.holiday_date"
            class="flex items-center gap-3 py-2 px-3 rounded-lg bg-white/[0.03] border border-white/[0.04]"
          >
            <div
              class="w-10 h-10 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center shrink-0"
            >
              <Calendar :size="18" :stroke-width="1.8" />
            </div>
            <div class="min-w-0">
              <p class="text-sm font-medium text-white">
                {{
                  new Date(h.holiday_date).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  })
                }}
              </p>
              <p class="text-xs text-slate-500 truncate">{{ h.description || "Holiday" }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Attendance Records Table -->
      <div>
        <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
          Attendance Records
        </h3>
        <div v-if="records.length" class="glass-card overflow-hidden">
          <!-- Desktop table -->
          <div class="hidden sm:block overflow-x-auto">
            <table class="w-full">
              <thead>
                <tr class="border-b border-white/[0.06]">
                  <th
                    class="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3"
                  >
                    Employee
                  </th>
                  <th
                    class="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3"
                  >
                    Date
                  </th>
                  <th
                    class="text-center text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3"
                  >
                    Status
                  </th>
                  <th
                    class="text-center text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3"
                  >
                    In Time
                  </th>
                  <th
                    class="text-center text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3"
                  >
                    Out Time
                  </th>
                  <th
                    class="text-center text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3"
                  >
                    Break Hours
                  </th>
                  <th
                    class="text-center text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3"
                  >
                    Hours
                  </th>
                  <th
                    v-if="canMark"
                    class="text-right text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3"
                  >
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="rec in records"
                  :key="rec.date"
                  class="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors cursor-pointer"
                  @click="viewRecord(rec)"
                >
                  <td class="px-5 py-4">
                    <p class="text-sm font-medium text-white">{{ rec.employee_name || rec.employee }}</p>
                  </td>
                  <td class="px-5 py-4">
                    <p class="text-sm font-medium text-white">{{ formatDate(rec.date) }}</p>
                  </td>
                  <td class="px-5 py-4 text-center">
                    <span :class="statusBadge(rec.status)">{{ rec.status }}</span>
                  </td>
                  <td class="px-5 py-4 text-center">
                    <span class="text-sm text-slate-300">{{ formatTime(rec.in_time) }}</span>
                  </td>
                  <td class="px-5 py-4 text-center">
                    <span class="text-sm text-slate-300">{{ formatTime(rec.out_time) }}</span>
                  </td>
                  <td class="px-5 py-4 text-center">
                    <span class="text-sm text-slate-300">
                      {{ rec.break_hours && rec.break_hours > 0 ? rec.break_hours.toFixed(1) + "h" : "—" }}
                    </span>
                  </td>
                  <td class="px-5 py-4 text-center">
                    <span class="text-sm font-semibold" :class="statusColor(rec.status)">
                      {{ rec.working_hours > 0 ? rec.working_hours.toFixed(1) + "h" : "—" }}
                    </span>
                  </td>
                  <td v-if="canMark" class="px-5 py-4 text-right" @click.stop>
                    <div class="flex items-center justify-end gap-2">
                      <button
                        @click="editAttendance(rec)"
                        class="p-1 rounded hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
                        title="Edit"
                      >
                        <Pencil :size="16" />
                      </button>
                      <button
                        @click="deleteAttendance(rec)"
                        class="p-1 rounded hover:bg-white/10 text-red-400 hover:text-red-300 transition-colors"
                        title="Delete"
                      >
                        <Trash2 :size="16" />
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <!-- Mobile cards -->
          <div class="sm:hidden divide-y divide-white/[0.04]">
            <div
              v-for="rec in records"
              :key="rec.date"
              class="p-4 space-y-2 cursor-pointer hover:bg-white/[0.01] active:bg-white/[0.02] transition-colors"
              @click="viewRecord(rec)"
            >
              <div class="flex items-center justify-between">
                <div>
                  <span class="text-slate-400 block text-xs mb-1 font-medium">
                    {{ rec.employee_name || rec.employee }}
                  </span>
                  <p class="text-sm font-medium text-white">{{ formatDate(rec.date) }}</p>
                </div>
                <span :class="statusBadge(rec.status)">{{ rec.status }}</span>
              </div>
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-4 text-xs text-slate-500">
                  <span v-if="rec.in_time">
                    <Clock :size="12" class="inline mr-1" />In: {{ formatTime(rec.in_time) }}
                  </span>
                  <span v-if="rec.out_time">
                    <Clock :size="12" class="inline mr-1" />Out: {{ formatTime(rec.out_time) }}
                  </span>
                  <span v-if="rec.break_hours && rec.break_hours > 0" class="text-slate-400">
                    Break: {{ rec.break_hours.toFixed(1) }}h
                  </span>
                  <span v-if="rec.working_hours > 0" :class="statusColor(rec.status)">
                    Work: {{ rec.working_hours.toFixed(1) }}h
                  </span>
                </div>
                <div v-if="canMark" class="flex items-center gap-2" @click.stop>
                  <button
                    @click="editAttendance(rec)"
                    class="p-1 rounded bg-white/[0.03] hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
                    title="Edit"
                  >
                    <Pencil :size="14" />
                  </button>
                  <button
                    @click="deleteAttendance(rec)"
                    class="p-1 rounded bg-white/[0.03] hover:bg-white/10 text-red-400 hover:text-red-300 transition-colors"
                    title="Delete"
                  >
                    <Trash2 :size="14" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="glass-card p-8 text-center">
          <CalendarCheck :size="32" class="mx-auto text-slate-600 mb-2" />
          <p class="text-slate-500 text-sm">No attendance records for this month</p>
        </div>
      </div>

      <!-- Attendance Requests Section -->
      <div>
        <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
          {{ canMark ? "Attendance Requests (My & Team)" : "My Attendance Requests" }}
        </h3>

        <!-- Success / Error Messages -->
        <div
          v-if="requestSuccessMessage"
          class="mb-4 p-3 text-sm rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
        >
          {{ requestSuccessMessage }}
        </div>
        <div
          v-if="requestErrorMessage"
          class="mb-4 p-3 text-sm rounded-lg bg-red-500/10 text-red-400 border border-red-500/20"
        >
          {{ requestErrorMessage }}
        </div>

        <!-- Loading -->
        <div v-if="loadingRequests" class="flex items-center justify-center py-8">
          <div class="w-8 h-8 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
        </div>

        <div v-else-if="myRequests.length" class="glass-card overflow-hidden">
          <!-- Desktop Table -->
          <div class="hidden sm:block overflow-x-auto">
            <table class="w-full">
              <thead>
                <tr class="border-b border-white/[0.06]">
                  <th class="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3">Employee</th>
                  <th class="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3">From Date</th>
                  <th class="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3">To Date</th>
                  <th class="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3">Reason</th>
                  <th class="text-center text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3">Status</th>
                  <th v-if="canMark" class="text-right text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="req in myRequests"
                  :key="req.name"
                  class="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors cursor-pointer"
                  @click="openRequestDetail(req)"
                >
                  <td class="px-5 py-4">
                    <span class="text-sm font-medium text-white">{{ req.employee_name }}</span>
                  </td>
                  <td class="px-5 py-4">
                    <span class="text-sm font-medium text-white">{{ formatDate(req.from_date) }}</span>
                  </td>
                  <td class="px-5 py-4">
                    <span class="text-sm font-medium text-white">{{ formatDate(req.to_date) }}</span>
                  </td>
                  <td class="px-5 py-4">
                    <span class="text-sm text-slate-300">{{ req.reason }}</span>
                  </td>
                  <td class="px-5 py-4 text-center">
                    <span
                      class="inline-flex px-2.5 py-1 rounded-full text-xs font-medium border"
                      :class="requestStatusBadge(req.status)"
                    >
                      {{ req.status }}
                    </span>
                  </td>
                  <td v-if="canMark" class="px-5 py-4 text-right" @click.stop>
                    <div class="flex items-center justify-end gap-2">
                      <button
                        v-if="req.status === 'Open'"
                        @click="handleApproveReject(req.name, 'Approve')"
                        :disabled="!!requestProcessing"
                        class="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 transition-colors"
                        title="Approve"
                      >
                        <CheckCircle :size="16" />
                      </button>
                      <button
                        v-if="req.status === 'Open'"
                        @click="handleApproveReject(req.name, 'Reject')"
                        :disabled="!!requestProcessing"
                        class="p-1.5 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
                        title="Reject"
                      >
                        <XCircle :size="16" />
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Mobile Cards -->
          <div class="sm:hidden divide-y divide-white/[0.04]">
            <div
              v-for="req in myRequests"
              :key="req.name"
              class="p-4 space-y-2 cursor-pointer hover:bg-white/[0.01] active:bg-white/[0.02] transition-colors"
              @click="openRequestDetail(req)"
            >
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-sm font-medium text-white mb-0.5">{{ req.employee_name }}</p>
                  <p class="text-sm font-medium text-slate-300">{{ formatDate(req.from_date) }} — {{ formatDate(req.to_date) }}</p>
                  <p class="text-xs text-slate-500 mt-0.5">{{ req.reason }}</p>
                </div>
                <span
                  class="inline-flex px-2.5 py-1 rounded-full text-xs font-medium border"
                  :class="requestStatusBadge(req.status)"
                >
                  {{ req.status }}
                </span>
              </div>
              <div class="flex items-center justify-between">
                <span v-if="req.explanation" class="text-xs text-slate-500 truncate max-w-[200px]">
                  {{ req.explanation }}
                </span>
                <span v-else class="text-xs text-slate-600">—</span>
                <div v-if="canMark" class="flex items-center gap-2" @click.stop>
                  <button
                    v-if="req.status === 'Open'"
                    @click="handleApproveReject(req.name, 'Approve')"
                    :disabled="!!requestProcessing"
                    class="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 transition-colors"
                    title="Approve"
                  >
                    <CheckCircle :size="14" />
                  </button>
                  <button
                    v-if="req.status === 'Open'"
                    @click="handleApproveReject(req.name, 'Reject')"
                    :disabled="!!requestProcessing"
                    class="p-1.5 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
                    title="Reject"
                  >
                    <XCircle :size="14" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="glass-card p-8 text-center">
          <FileText :size="32" class="mx-auto text-slate-600 mb-2" />
          <p class="text-slate-500 text-sm">No attendance requests found</p>
        </div>
      </div>
    </div>

    <!-- Add Attendance Modal -->
    <transition name="modal">
      <div
        v-if="showAddModal"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-sm"
        style="background-color: var(--overlay-bg);"
        @click.self="showAddModal = false"
      >
        <div class="modal-content glass-card w-full max-w-md p-6 space-y-5">
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold text-white">
              {{ editingRecordId ? "Edit Attendance" : "Add Attendance" }}
            </h2>
            <button
              @click="showAddModal = false"
              class="p-1 transition-colors text-slate-500 hover:text-white"
              :disabled="submitting"
            >
              <X :size="20" />
            </button>
          </div>

          <div v-if="formError" class="p-3 text-sm rounded-lg bg-red-500/10 text-red-400 border border-red-500/20">
            {{ formError }}
          </div>

          <form @submit.prevent="submitForm" class="space-y-4">
            <!-- Employee Selection -->
            <div>
              <label class="block text-sm font-medium mb-1.5 text-slate-400">Employee</label>
              <div class="relative">
                <select
                  v-model="addForm.employee"
                  class="input-dark appearance-none pr-10 cursor-pointer w-full"
                  :disabled="submitting || !!editingRecordId"
                >
                  <option v-for="emp in employeeList" :key="emp.name" :value="emp.name">
                    {{ emp.employee_name }}
                  </option>
                </select>
                <ChevronDown
                  :size="16"
                  class="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-500"
                />
              </div>
            </div>

            <!-- Date Selection -->
            <div>
              <label class="block text-sm font-medium mb-1.5 text-slate-400">Date</label>
              <input type="date" v-model="addForm.date" required class="input-dark w-full" :disabled="submitting || !!editingRecordId" />
            </div>

            <!-- Status Selection -->
            <div>
              <label class="block text-sm font-medium mb-1.5 text-slate-400">Status</label>
              <div class="relative">
                <select
                  v-model="addForm.status"
                  class="input-dark appearance-none pr-10 cursor-pointer w-full"
                  :disabled="submitting"
                >
                  <option v-for="status in statusOptions" :key="status" :value="status">
                    {{ status }}
                  </option>
                </select>
                <ChevronDown
                  :size="16"
                  class="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-500"
                />
              </div>
            </div>

            <!-- Clock In and Clock Out -->
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-sm font-medium mb-1.5 text-slate-400">Clock In</label>
                <input
                  type="time"
                  v-model="addForm.in_time"
                  class="input-dark w-full"
                  :disabled="submitting || (!!editingRecordId && hadInTime)"
                />
              </div>
              <div>
                <label class="block text-sm font-medium mb-1.5 text-slate-400">Clock Out</label>
                <input
                  type="time"
                  v-model="addForm.out_time"
                  class="input-dark w-full"
                  :disabled="submitting || (!!editingRecordId && hadOutTime)"
                />
              </div>
            </div>

            <!-- Action Buttons -->
            <div class="flex gap-3 pt-4">
              <button
                type="button"
                @click="showAddModal = false"
                class="flex-1 px-4 py-2 text-sm font-medium rounded-lg text-slate-300 hover:text-white bg-white/5 hover:bg-white/10 transition-colors"
                :disabled="submitting"
              >
                Cancel
              </button>
              <button
                type="submit"
                class="flex-1 btn-accent"
                :disabled="submitting"
              >
                {{ submitting ? "Submitting..." : "Submit" }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </transition>

    <!-- Request Attendance Modal (Create / Edit) -->
    <transition name="modal">
      <div
        v-if="showRequestModal"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-sm"
        style="background-color: var(--overlay-bg);"
        @click.self="showRequestModal = false"
      >
        <div class="modal-content glass-card w-full max-w-md p-6 space-y-5">
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold text-white">
              {{ editingRequestId ? "Edit Attendance Request" : "Request Attendance" }}
            </h2>
            <button
              @click="showRequestModal = false"
              class="p-1 transition-colors text-slate-500 hover:text-white"
              :disabled="requestSubmitting"
            >
              <X :size="20" />
            </button>
          </div>

          <div v-if="requestFormError" class="p-3 text-sm rounded-lg bg-red-500/10 text-red-400 border border-red-500/20">
            {{ requestFormError }}
          </div>

          <form @submit.prevent="submitRequestForm" class="space-y-4">
            <!-- From Date Selection -->
            <div>
              <label class="block text-sm font-medium mb-1.5 text-slate-400">From Date</label>
              <input
                type="date"
                v-model="requestForm.from_date"
                required
                class="input-dark w-full"
                :disabled="requestSubmitting"
              />
            </div>

            <!-- To Date Selection -->
            <div>
              <label class="block text-sm font-medium mb-1.5 text-slate-400">To Date</label>
              <input
                type="date"
                v-model="requestForm.to_date"
                required
                class="input-dark w-full"
                :disabled="requestSubmitting"
              />
            </div>



            <!-- Reason Explanation -->
            <div>
              <label class="block text-sm font-medium mb-1.5 text-slate-400">Reason Explanation</label>
              <textarea
                v-model="requestForm.explanation"
                rows="3"
                class="input-dark w-full py-2 px-3 bg-transparent border border-white/10 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-accent"
                placeholder="Explain the reason for this request..."
                :disabled="requestSubmitting"
              ></textarea>
            </div>

            <!-- Action Buttons -->
            <div class="flex gap-3 pt-4">
              <button
                type="button"
                @click="showRequestModal = false"
                class="flex-1 px-4 py-2 text-sm font-medium rounded-lg text-slate-300 hover:text-white bg-white/5 hover:bg-white/10 transition-colors"
                :disabled="requestSubmitting"
              >
                Cancel
              </button>
              <button
                type="submit"
                class="flex-1 btn-accent"
                :disabled="requestSubmitting"
              >
                {{ requestSubmitting ? "Submitting..." : "Submit" }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </transition>

    <!-- View Attendance Modal -->
    <transition name="modal">
      <div
        v-if="showViewModal"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-sm"
        style="background-color: var(--overlay-bg);"
        @click.self="showViewModal = false"
      >
        <div class="modal-content glass-card w-full max-w-lg p-6 space-y-6">
          <!-- Header -->
          <div class="flex items-center justify-between border-b border-white/[0.06] pb-4">
            <div>
              <h2 class="text-lg font-semibold text-white">
                Attendance Details
              </h2>
              <p class="text-xs text-slate-400 mt-1">
                {{ selectedRecord?.employee_name || selectedRecord?.employee }}
              </p>
            </div>
            <button
              @click="showViewModal = false"
              class="p-1 transition-colors text-slate-500 hover:text-white"
            >
              <X :size="20" />
            </button>
          </div>

          <!-- Details Grid -->
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span class="block text-xs text-slate-500 font-medium uppercase tracking-wider mb-0.5">Date</span>
              <span class="text-white font-medium">{{ selectedRecord ? formatDate(selectedRecord.date) : "" }}</span>
            </div>
            <div>
              <span class="block text-xs text-slate-500 font-medium uppercase tracking-wider mb-0.5">Status</span>
              <div>
                <span :class="statusBadge(selectedRecord?.status || '')" class="inline-block">{{ selectedRecord?.status }}</span>
              </div>
            </div>
            <div>
              <span class="block text-xs text-slate-500 font-medium uppercase tracking-wider mb-0.5">Clock In</span>
              <span class="text-slate-300 font-medium">{{ selectedRecord ? formatTime(selectedRecord.in_time) : "—" }}</span>
            </div>
            <div>
              <span class="block text-xs text-slate-500 font-medium uppercase tracking-wider mb-0.5">Clock Out</span>
              <span class="text-slate-300 font-medium">{{ selectedRecord ? formatTime(selectedRecord.out_time) : "—" }}</span>
            </div>
            <div>
              <span class="block text-xs text-slate-500 font-medium uppercase tracking-wider mb-0.5">Working Hours</span>
              <span class="font-semibold" :class="statusColor(selectedRecord?.status || '')">
                {{ selectedRecord && selectedRecord.working_hours > 0 ? selectedRecord.working_hours.toFixed(2) + " hours" : "—" }}
              </span>
            </div>
            <div>
              <span class="block text-xs text-slate-500 font-medium uppercase tracking-wider mb-0.5">Break Hours</span>
              <span class="text-slate-300 font-semibold">
                {{ selectedRecord && selectedRecord.break_hours && selectedRecord.break_hours > 0 ? selectedRecord.break_hours.toFixed(2) + " hours" : "—" }}
              </span>
            </div>
          </div>

          <!-- Break Logs Table Section -->
          <div class="border-t border-white/[0.06] pt-5">
            <h3 class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
              <Clock :size="14" /> Break Logs Breakdown
            </h3>

            <!-- Loading break logs -->
            <div v-if="loadingBreaks" class="flex items-center justify-center py-6">
              <div class="w-6 h-6 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
            </div>

            <div v-else>
              <div v-if="breakLogs.length" class="overflow-x-auto rounded-lg border border-white/[0.06] bg-white/[0.01]">
                <table class="w-full text-sm">
                  <thead>
                    <tr class="border-b border-white/[0.06] bg-white/[0.02]">
                      <th class="text-left text-xs font-medium text-slate-400 uppercase tracking-wider px-4 py-2.5">
                        Break In
                      </th>
                      <th class="text-left text-xs font-medium text-slate-400 uppercase tracking-wider px-4 py-2.5">
                        Break Out
                      </th>
                      <th class="text-right text-xs font-medium text-slate-400 uppercase tracking-wider px-4 py-2.5">
                        Duration
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="(log, idx) in breakLogs"
                      :key="idx"
                      class="border-b border-white/[0.03] last:border-0 hover:bg-white/[0.02] transition-colors"
                    >
                      <td class="px-4 py-2.5 text-slate-300 font-mono">
                        {{ formatTime(log.break_in) }}
                      </td>
                      <td class="px-4 py-2.5 text-slate-300 font-mono">
                        {{ formatTime(log.break_out) }}
                      </td>
                      <td class="px-4 py-2.5 text-right font-medium" :class="log.duration ? 'text-amber-400' : 'text-slate-500'">
                        {{ log.duration ? log.duration.toFixed(1) + " min" : "On Break" }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-else class="text-center py-6 border border-dashed border-white/[0.08] rounded-lg">
                <p class="text-slate-500 text-xs">No breaks recorded for this day</p>
              </div>
            </div>
          </div>

          <!-- Close button -->
          <div class="flex pt-2">
            <button
              type="button"
              @click="showViewModal = false"
              class="w-full px-4 py-2.5 text-sm font-medium rounded-lg text-slate-300 hover:text-white bg-white/5 hover:bg-white/10 border border-white/[0.08] transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Request Detail Modal -->
    <transition name="modal">
      <div
        v-if="showRequestDetailModal && selectedRequest"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-sm"
        style="background-color: var(--overlay-bg);"
        @click.self="showRequestDetailModal = false"
      >
        <div class="modal-content glass-card w-full max-w-lg p-6 space-y-6">
          <!-- Header -->
          <div class="flex items-center justify-between border-b border-white/[0.06] pb-4">
            <div>
              <h2 class="text-lg font-semibold text-white flex items-center gap-2">
                <FileText :size="20" class="text-teal-400" />
                Attendance Request Details
              </h2>
              <p class="text-xs text-slate-400 mt-1">
                {{ selectedRequest.employee_name }}
              </p>
            </div>
            <button
              @click="showRequestDetailModal = false"
              class="p-1 transition-colors text-slate-500 hover:text-white"
            >
              <X :size="20" />
            </button>
          </div>

          <!-- Details Grid -->
          <div class="space-y-5">
            <div class="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span class="block text-xs text-slate-500 font-medium uppercase tracking-wider mb-0.5">Reference ID</span>
                <span class="text-white font-medium font-mono text-xs">{{ selectedRequest.name }}</span>
              </div>
              <div>
                <span class="block text-xs text-slate-500 font-medium uppercase tracking-wider mb-0.5">Status</span>
                <span
                  class="inline-flex px-2.5 py-1 rounded-full text-xs font-medium border"
                  :class="requestStatusBadge(selectedRequest.status)"
                >
                  {{ selectedRequest.status }}
                </span>
              </div>
              <div>
                <span class="block text-xs text-slate-500 font-medium uppercase tracking-wider mb-0.5">Applied Date</span>
                <span class="text-white font-medium">{{ formatDate(selectedRequest.creation) }}</span>
              </div>
              <div>
                <span class="block text-xs text-slate-500 font-medium uppercase tracking-wider mb-0.5">Reason</span>
                <span class="text-white font-medium">{{ selectedRequest.reason }}</span>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span class="block text-xs text-slate-500 font-medium uppercase tracking-wider mb-0.5">From Date</span>
                <span class="text-white font-medium">{{ formatDate(selectedRequest.from_date) }}</span>
              </div>
              <div>
                <span class="block text-xs text-slate-500 font-medium uppercase tracking-wider mb-0.5">To Date</span>
                <span class="text-white font-medium">{{ formatDate(selectedRequest.to_date) }}</span>
              </div>
            </div>

            <div v-if="selectedRequest.explanation" class="bg-white/[0.03] p-4 rounded-xl border border-white/[0.06]">
              <p class="text-xs text-slate-500 uppercase mb-1 font-semibold">Explanation</p>
              <p class="text-slate-300 text-sm whitespace-pre-wrap">{{ selectedRequest.explanation }}</p>
            </div>

            <!-- Approve/Reject buttons for managers on Open requests -->
            <div v-if="canMark && selectedRequest.status === 'Open'" class="flex items-center gap-3 border-t border-white/[0.06] pt-5">
              <button
                @click="handleApproveReject(selectedRequest.name, 'Approve'); showRequestDetailModal = false;"
                :disabled="!!requestProcessing"
                class="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-medium rounded-lg shadow-lg active:scale-95 transition-all text-sm cursor-pointer"
              >
                <CheckCircle :size="16" />
                Approve
              </button>
              <button
                @click="handleApproveReject(selectedRequest.name, 'Reject'); showRequestDetailModal = false;"
                :disabled="!!requestProcessing"
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
              @click="showRequestDetailModal = false"
              class="w-full px-4 py-2.5 text-sm font-medium rounded-lg text-slate-300 hover:text-white bg-white/5 hover:bg-white/10 border border-white/[0.08] transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>

</template>
