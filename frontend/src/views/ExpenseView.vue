<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from "vue";
import { expensesApi, dashboardApi } from "../services/api";
import { useAuthStore } from "../stores/auth";
import {
  Receipt,
  Plus,
  Upload,
  X,
  IndianRupee,
  FileText,
  CheckCircle,
  XCircle,
  AlertCircle,
  Clock,
  Trash2,
  Edit,
  MoreVertical,
  LayoutGrid,
  List,
  ChevronDown,
} from "lucide-vue-next";

// Data types
interface ExpenseLine {
  expense_date: string;
  expense_type: string;
  amount: number;
  description: string;
}

interface Expense {
  name: string;
  employee: string;
  employee_name: string;
  total_claimed_amount: number;
  posting_date: string;
  approval_status: string;
  status: string;
  expense_approver?: string;
  payable_account?: string;
  remark?: string;
  company?: string;
  expenses: ExpenseLine[];
  proofs?: string[];
  proof?: string;
}

const authStore = useAuthStore();

const expenses = ref<Expense[]>([]);
const expenseTypes = ref<string[]>([]);
const loading = ref(true);
const showModal = ref(false);
const showDetailModal = ref(false);
const selectedDetail = ref<Expense | null>(null);
const viewMode = ref<"card" | "list">("list");

const employeeInfo = ref<any>(null);
const approvers = ref<any[]>([]);
const myApprovers = ref<any[]>([]);

const isSystemManager = computed(() => authStore.isSystemManager);
const expenseEmployees = ref<any[]>([]);
const selectedEmployee = ref<string>("");

// Approval Modal State
const showApproveModal = ref(false);
const approvingClaim = ref<Expense | null>(null);
const payableAccounts = ref<{ value: string; label: string }[]>([]);
const selectedPayableAccount = ref("");
const processingAction = ref(false);
const actionError = ref("");
const modalAction = ref<"Approve" | "Reject">("Approve");

// Form states
const isEditing = ref(false);
const editClaimName = ref("");
const activeActionMenu = ref("");

const form = ref({
  posting_date: new Date().toISOString().substring(0, 10),
  expense_approver: "",
  remark: "",
  expenses: [] as ExpenseLine[],
  proofs: [] as string[],
  employee: "",
  employee_name: "",
});

const submitting = ref(false);
const error = ref("");
const success = ref("");

// Upload
const fileInput = ref<HTMLInputElement | null>(null);

const todayVal = new Date();
const currentYear = todayVal.getFullYear();
const currentMonth = String(todayVal.getMonth() + 1).padStart(2, "0");
const lastDayOfMonth = String(new Date(currentYear, todayVal.getMonth() + 1, 0).getDate()).padStart(2, "0");

const filterStatus = ref("");
const filterFromDate = ref(`${currentYear}-${currentMonth}-01`);
const filterToDate = ref(`${currentYear}-${currentMonth}-${lastDayOfMonth}`);

const selectedPreset = ref("This Month");
const showDropdown = ref(false);

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

watch([filterStatus, filterFromDate, filterToDate, selectedEmployee], () => {
  loadData();
});

async function loadData() {
  loading.value = true;
  try {
    const fetchExpenses = selectedEmployee.value
      ? expensesApi.getTeamExpenses(
          filterStatus.value,
          filterFromDate.value,
          filterToDate.value,
          selectedEmployee.value === "all" ? undefined : selectedEmployee.value
        )
      : expensesApi.getMyExpenses(filterStatus.value, filterFromDate.value, filterToDate.value);

    const [expData, types] = await Promise.all([
      fetchExpenses,
      expensesApi.getTypes()
    ]);
    expenses.value = Array.isArray(expData) ? expData : [];
    expenseTypes.value = Array.isArray(types) ? types : [];
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
}

async function fetchEmployeeAndApprovers() {
  try {
    const emp = await dashboardApi.getEmployeeInfo();
    employeeInfo.value = emp;
    if (emp && emp.employee_id) {
      const apprData = await expensesApi.getApprovers(emp.employee_id);
      myApprovers.value = apprData?.department_approvers || [];
      approvers.value = [...myApprovers.value];
      // Set default approver if available
      if (!form.value.expense_approver && apprData?.expense_approver) {
        form.value.expense_approver = apprData.expense_approver;
      }
    }
  } catch (e) {
    console.error("Failed to load employee info / approvers:", e);
  }
}

async function fetchExpenseEmployees() {
  try {
    const data = await expensesApi.getExpenseApproverEmployees();
    expenseEmployees.value = Array.isArray(data) ? data : [];
    if (isSystemManager.value || expenseEmployees.value.length > 0) {
      selectedEmployee.value = "all";
    }
  } catch (e) {
    console.error("Failed to load expense employees:", e);
  }
}

async function openApproveModal(exp: Expense, action: "Approve" | "Reject") {
  approvingClaim.value = exp;
  modalAction.value = action;
  selectedPayableAccount.value = "";
  actionError.value = "";
  payableAccounts.value = [];
  showApproveModal.value = true;
  
  if (action === "Approve" && exp.company) {
    try {
      const accounts = await expensesApi.getPayableAccounts(exp.company);
      payableAccounts.value = Array.isArray(accounts) ? accounts : [];
      if (payableAccounts.value.length > 0) {
        selectedPayableAccount.value = payableAccounts.value[0].value;
      }
    } catch (e) {
      console.error("Failed to load payable accounts:", e);
    }
  }
}

async function submitProcess() {
  if (!approvingClaim.value) return;
  if (modalAction.value === "Approve" && !selectedPayableAccount.value) {
    actionError.value = "Please select a Payable Account.";
    return;
  }

  processingAction.value = true;
  actionError.value = "";
  try {
    const res = await expensesApi.process(
      approvingClaim.value.name,
      modalAction.value,
      modalAction.value === "Approve" ? selectedPayableAccount.value : undefined
    );
    if (res.success) {
      success.value = `Expense claim ${modalAction.value === "Approve" ? "approved" : "rejected"} successfully`;
      showApproveModal.value = false;
      approvingClaim.value = null;
      loadData();
    } else {
      actionError.value = res.error || "Action failed";
    }
  } catch (e: any) {
    actionError.value = e.message || "An error occurred during process";
  } finally {
    processingAction.value = false;
  }
}

const uploadingFile = ref(false);

async function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    uploadingFile.value = true;
    error.value = "";
    try {
      for (let i = 0; i < target.files.length; i++) {
        const file = target.files[i];
        const fileUrl = await uploadFile(file);
        form.value.proofs.push(fileUrl);
      }
    } catch (e: any) {
      error.value = "Failed to upload file: " + (e.message || e);
    } finally {
      uploadingFile.value = false;
      if (fileInput.value) fileInput.value.value = "";
    }
  }
}

async function uploadFile(file: File): Promise<string> {
  const formData = new FormData();
  formData.append("file", file, file.name);
  formData.append("is_private", "1");

  const res = await fetch("/api/method/upload_file", {
    method: "POST",
    headers: {
      "X-Frappe-CSRF-Token": (window as any).csrf_token || "",
    },
    body: formData,
  });

  const data = await res.json();
  if (data.message && data.message.file_url) {
    return data.message.file_url;
  }
  throw new Error(data.message || "Upload failed");
}

function openNewClaimModal() {
  isEditing.value = false;
  editClaimName.value = "";
  approvers.value = [...myApprovers.value];
  form.value = {
    posting_date: new Date().toISOString().substring(0, 10),
    expense_approver: approvers.value.length > 0 ? (employeeInfo.value?.expense_approver || approvers.value[0].name) : "",
    remark: "",
    expenses: [
      { expense_date: new Date().toISOString().substring(0, 10), expense_type: "", amount: 0, description: "" }
    ],
    proofs: [],
    employee: "",
    employee_name: "",
  };
  error.value = "";
  success.value = "";
  showModal.value = true;
}

async function handleEdit(exp: Expense) {
  activeActionMenu.value = "";
  isEditing.value = true;
  editClaimName.value = exp.name;
  
  const targetApprover = exp.expense_approver || "";

  form.value = {
    posting_date: exp.posting_date || new Date().toISOString().substring(0, 10),
    expense_approver: targetApprover,
    remark: exp.remark || "",
    expenses: exp.expenses && exp.expenses.length > 0
      ? exp.expenses.map((line) => ({
          expense_date: line.expense_date || exp.posting_date || new Date().toISOString().substring(0, 10),
          expense_type: line.expense_type || "",
          amount: line.amount || 0,
          description: line.description || "",
        }))
      : [{ expense_date: exp.posting_date || new Date().toISOString().substring(0, 10), expense_type: "", amount: 0, description: "" }],
    proofs: exp.proofs ? [...exp.proofs] : (exp.proof ? [exp.proof] : []),
    employee: exp.employee || "",
    employee_name: exp.employee_name || "",
  };

  if (exp.employee) {
    try {
      const apprData = await expensesApi.getApprovers(exp.employee);
      approvers.value = apprData?.department_approvers || [];
      // Re-assign targetApprover to model once options are loaded into dropdown
      form.value.expense_approver = targetApprover;
    } catch (e) {
      console.error("Failed to load approvers for employee:", exp.employee, e);
    }
  }
  
  error.value = "";
  success.value = "";
  showModal.value = true;
}

async function handleDelete(name: string) {
  activeActionMenu.value = "";
  if (!confirm("Are you sure you want to delete this expense claim?")) return;
  try {
    const res = await expensesApi.delete(name);
    if (res.success) {
      success.value = "Expense claim deleted successfully";
      loadData();
    } else {
      error.value = res.error || "Delete failed";
    }
  } catch (e: any) {
    error.value = e.message || "An error occurred";
  }
}

function openDetailModal(exp: Expense) {
  selectedDetail.value = exp;
  showDetailModal.value = true;
}

function addExpenseLine() {
  form.value.expenses.push({
    expense_date: form.value.posting_date,
    expense_type: "",
    amount: 0,
    description: "",
  });
}

function removeExpenseLine(idx: number) {
  form.value.expenses.splice(idx, 1);
  if (form.value.expenses.length === 0) {
    addExpenseLine();
  }
}

function toggleActionMenu(name: string) {
  activeActionMenu.value = activeActionMenu.value === name ? "" : name;
}

watch(showModal, (val) => {
  if (val) {
    document.body.classList.add("overflow-hidden");
  } else {
    if (!showDetailModal.value) {
      document.body.classList.remove("overflow-hidden");
    }
    isEditing.value = false;
    editClaimName.value = "";
  }
});

watch(showDetailModal, (val) => {
  if (val) {
    document.body.classList.add("overflow-hidden");
  } else {
    if (!showModal.value && !showApproveModal.value) {
      document.body.classList.remove("overflow-hidden");
    }
  }
});

watch(showApproveModal, (val) => {
  if (val) {
    document.body.classList.add("overflow-hidden");
  } else {
    if (!showModal.value && !showDetailModal.value) {
      document.body.classList.remove("overflow-hidden");
    }
  }
});

onUnmounted(() => {
  document.body.classList.remove("overflow-hidden");
});

const totalClaimedAmount = computed(() => {
  return form.value.expenses.reduce((sum, item) => sum + Number(item.amount || 0), 0);
});

async function submitExpense() {
  if (!form.value.expense_approver) {
    error.value = "Please select an expense approver";
    return;
  }
  if (form.value.expenses.length === 0) {
    error.value = "Please add at least one expense line";
    return;
  }
  for (const item of form.value.expenses) {
    if (!item.expense_type) {
      error.value = "Please select an expense type for all lines";
      return;
    }
    if (Number(item.amount || 0) <= 0) {
      error.value = "Amount must be greater than zero for all lines";
      return;
    }
  }

  submitting.value = true;
  error.value = "";

  try {
    const payload = {
      posting_date: form.value.posting_date,
      expense_approver: form.value.expense_approver,
      expenses: form.value.expenses,
      remark: form.value.remark,
      proofs: form.value.proofs,
    } as any;

    if (isEditing.value) {
      payload.name = editClaimName.value;
    }

    const res = await expensesApi.submit(payload);
    if (res.success) {
      success.value = isEditing.value ? "Expense updated successfully" : "Expense submitted successfully";
      showModal.value = false;
      isEditing.value = false;
      editClaimName.value = "";
      loadData();
    } else {
      error.value = res.error || "Submission failed";
    }
  } catch (e: any) {
    error.value = e.message || "Error occurred";
  } finally {
    submitting.value = false;
  }
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

onMounted(async () => {
  await fetchExpenseEmployees();
  loadData();
  fetchEmployeeAndApprovers();
  
  window.addEventListener("click", (e) => {
    const target = e.target as HTMLElement;
    if (!target.closest(".more-btn") && !target.closest(".dropdown-menu")) {
      activeActionMenu.value = "";
    }
    if (!target.closest(".date-picker-container")) {
      showDropdown.value = false;
    }
  });
});
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col md:flex-row md:items-end justify-between gap-6 animate-fade-in">
      <div>
        <h1 class="text-2xl sm:text-3xl font-bold text-white">Expenses</h1>
        <p class="text-sm text-slate-500 mt-1">Manage reimbursement claims</p>
      </div>
      <div class="flex items-center gap-3">
        <!-- View Toggle -->
        <div class="flex items-center bg-white/5 border border-white/10 rounded-xl p-1">
          <button
            @click="viewMode = 'list'"
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
            :class="viewMode === 'list' ? 'bg-gradient-to-r from-teal-500 to-emerald-500 text-white shadow-lg' : 'text-slate-400 hover:text-white'"
          >
            <List :size="14" />
            List
          </button>
          <button
            @click="viewMode = 'card'"
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
            :class="viewMode === 'card' ? 'bg-gradient-to-r from-teal-500 to-emerald-500 text-white shadow-lg' : 'text-slate-400 hover:text-white'"
          >
            <LayoutGrid :size="14" />
            Card
          </button>
        </div>
        <!-- New Claim Button -->
        <button
          @click="openNewClaimModal"
          class="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-teal-500 to-emerald-500 text-white rounded-xl shadow-lg shadow-teal-500/20 hover:shadow-teal-500/30 transition-all active:scale-95"
        >
          <Plus :size="18" />
          <span class="hidden sm:inline font-medium">New Claim</span>
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex flex-col sm:flex-row gap-4 p-4 bg-white/5 border border-white/10 rounded-2xl animate-fade-in relative z-20">
      <!-- Employee List Filter (visible if expense_approver/system manager) -->
      <div v-if="isSystemManager || expenseEmployees.length" class="flex-1">
        <label class="block text-[10px] font-semibold text-slate-400 uppercase mb-1.5 tracking-wider">Employee</label>
        <div class="relative w-full">
          <select v-model="selectedEmployee" class="input-dark appearance-none pr-10 text-xs py-2 px-3">
            <option value="all">All Employees</option>
            <option v-for="emp in expenseEmployees" :key="emp.name" :value="emp.name">
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
            <option value="Draft">Draft</option>
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
    </div>

    <!-- Alert -->
    <div
      v-if="success"
      class="p-4 rounded-xl bg-green-500/10 border border-green-500/20 text-green-400 flex items-center gap-2"
    >
      <CheckCircle :size="18" />
      {{ success }}
      <button @click="success = ''" class="ml-auto"><X :size="16" /></button>
    </div>

    <!-- List -->
    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="i in 3" :key="i" class="glass-card p-6 h-32 animate-pulse" />
    </div>

    <div
      v-else-if="expenses.length === 0"
      class="glass-card p-12 text-center text-slate-500 flex flex-col items-center"
    >
      <Receipt :size="48" class="mb-4 opacity-20" />
      <p>No expense claims found</p>
    </div>

    <!-- Card View -->
    <div v-else-if="viewMode === 'card'" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 animate-slide-up">
      <div
        v-for="exp in expenses"
        :key="exp.name"
        @click="openDetailModal(exp)"
        class="glass-card p-5 group hover:border-white/10 transition-colors cursor-pointer relative"
      >
        <div class="flex justify-between items-start mb-4">
          <div class="p-3 rounded-lg bg-indigo-500/10 text-indigo-400">
            <IndianRupee :size="20" />
          </div>
          <div class="flex items-center gap-2 relative">
            <span
              class="px-2.5 py-1 rounded-full text-xs font-medium border"
              :class="statusColor(exp.approval_status)"
            >
              {{ exp.approval_status }}
            </span>
            
            <div v-if="exp.approval_status === 'Draft'" class="relative inline-block text-left">
              <button
                @click.stop="toggleActionMenu(exp.name)"
                class="more-btn flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs text-slate-300 hover:text-white cursor-pointer transition-colors"
                title="More actions"
              >
                More
                <ChevronDown :size="12" />
              </button>
              
              <div
                v-if="activeActionMenu === exp.name"
                class="dropdown-menu absolute right-0 mt-1 z-30 w-32 rounded-lg shadow-xl overflow-hidden text-xs"
              >
                <!-- Approve / Reject for Manager (if team member's claim) -->
                <template v-if="exp.employee && exp.employee !== authStore.employee">
                  <button
                    @click.stop="openApproveModal(exp, 'Approve')"
                    class="dropdown-item w-full px-3 py-2 text-left flex items-center gap-1.5 text-emerald-400 hover:bg-emerald-500/10 font-medium cursor-pointer"
                  >
                    <CheckCircle :size="12" /> Approve
                  </button>
                  <button
                    @click.stop="openApproveModal(exp, 'Reject')"
                    class="dropdown-item dropdown-item-danger w-full px-3 py-2 text-left flex items-center gap-1.5 font-medium cursor-pointer"
                  >
                    <XCircle :size="12" /> Reject
                  </button>
                </template>

                <!-- Edit / Delete (Only available for own claims) -->
                <template v-else>
                  <button
                    @click.stop="handleEdit(exp)"
                    class="dropdown-item w-full px-3 py-2 text-left flex items-center gap-1.5 text-slate-300 hover:bg-white/5 cursor-pointer"
                  >
                    <Edit :size="12" /> Edit
                  </button>
                  <button
                    @click.stop="handleDelete(exp.name)"
                    class="dropdown-item dropdown-item-danger w-full px-3 py-2 text-left flex items-center gap-1.5 cursor-pointer"
                  >
                    <Trash2 :size="12" /> Delete
                  </button>
                </template>
              </div>
            </div>
          </div>
        </div>

        <div class="mb-4">
          <p class="text-2xl font-bold text-white">
            ₹{{ Number(exp.total_claimed_amount).toLocaleString() }}
          </p>
          <div class="flex flex-col gap-0.5 mt-1">
            <p class="text-xs text-slate-500">{{ exp.name }}</p>
            <p v-if="selectedEmployee" class="text-xs font-medium text-slate-400">{{ exp.employee_name || exp.employee }}</p>
          </div>
        </div>

        <div
          class="flex items-center justify-between text-xs text-slate-400 border-t border-white/5 pt-3"
        >
          <div class="flex items-center gap-1.5">
            <Clock :size="14" />
            {{ formatDate(exp.posting_date) }}
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="viewMode === 'list'" class="glass-card overflow-hidden animate-slide-up w-full">
      <div class="w-full overflow-x-auto">
        <table class="w-full min-w-max text-left text-sm border-collapse">
          <thead>
            <tr class="text-xs font-semibold text-slate-500 uppercase border-b border-white/5 bg-white/[0.02]">
              <th class="px-6 py-4">Reference</th>
              <th class="px-6 py-4">Employee</th>
              <th class="px-6 py-4">Amount</th>
              <th class="px-6 py-4 text-center">Status</th>
              <th class="px-6 py-4">Date</th>
              <th class="px-6 py-4 text-center">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-white/5">
            <tr
              v-for="exp in expenses"
              :key="exp.name"
              @click="openDetailModal(exp)"
              class="hover:bg-white/5 cursor-pointer transition-colors"
            >
              <td class="px-6 py-4 font-medium text-white truncate max-w-[200px]">{{ exp.name }}</td>
              <td class="px-6 py-4 text-slate-400 truncate max-w-[200px]">{{ exp.employee_name || exp.employee }}</td>
              <td class="px-6 py-4 font-bold text-white">₹{{ Number(exp.total_claimed_amount).toLocaleString() }}</td>
              <td class="px-6 py-4 text-center">
                <span class="inline-flex px-2.5 py-1 rounded-full text-xs font-medium border" :class="statusColor(exp.approval_status)">
                  {{ exp.approval_status }}
                </span>
              </td>
              <td class="px-6 py-4 text-xs text-slate-400">{{ formatDate(exp.posting_date) }}</td>
              <td class="px-6 py-4 text-center" @click.stop>
                <div v-if="exp.approval_status === 'Draft'" class="relative inline-block text-left">
                  <button
                    @click.stop="toggleActionMenu(exp.name)"
                    class="more-btn flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs text-slate-300 hover:text-white cursor-pointer transition-colors"
                    title="More actions"
                  >
                    More
                    <ChevronDown :size="12" />
                  </button>
                  
                  <div
                    v-if="activeActionMenu === exp.name"
                    class="dropdown-menu absolute right-0 mt-1 z-30 w-32 rounded-lg shadow-xl overflow-hidden text-xs"
                  >
                    <!-- Approve / Reject for Manager (if team member's claim) -->
                    <template v-if="exp.employee && exp.employee !== authStore.employee">
                      <button
                        @click.stop="openApproveModal(exp, 'Approve')"
                        class="dropdown-item w-full px-3 py-2 text-left flex items-center gap-1.5 text-emerald-400 hover:bg-emerald-500/10 font-medium cursor-pointer"
                      >
                        <CheckCircle :size="12" /> Approve
                      </button>
                      <button
                        @click.stop="openApproveModal(exp, 'Reject')"
                        class="dropdown-item dropdown-item-danger w-full px-3 py-2 text-left flex items-center gap-1.5 font-medium cursor-pointer"
                      >
                        <XCircle :size="12" /> Reject
                      </button>
                    </template>

                    <!-- Edit / Delete (Only available for own claims) -->
                    <template v-else>
                      <button
                        @click.stop="handleEdit(exp)"
                        class="dropdown-item w-full px-3 py-2 text-left flex items-center gap-1.5 text-slate-300 hover:bg-white/5 cursor-pointer"
                      >
                        <Edit :size="12" /> Edit
                      </button>
                      <button
                        @click.stop="handleDelete(exp.name)"
                        class="dropdown-item dropdown-item-danger w-full px-3 py-2 text-left flex items-center gap-1.5 cursor-pointer"
                      >
                        <Trash2 :size="12" /> Delete
                      </button>
                    </template>
                  </div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modal Form -->
    <div v-if="showModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 !mt-0">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showModal = false"></div>
      <div class="glass-card w-full max-w-4xl p-6 relative animate-scale-in max-h-[90vh] overflow-y-auto no-scrollbar">
        <button
          @click="showModal = false"
          class="absolute right-4 top-4 text-slate-500 hover:text-white"
        >
          <X :size="20" />
        </button>

        <h2 class="text-xl font-bold text-white mb-6 flex items-center gap-2">
          <Receipt class="text-teal-400" /> {{ isEditing ? 'Edit Expense Claim' : 'New Expense Claim' }}
        </h2>

        <form @submit.prevent="submitExpense" class="space-y-6">
          <!-- Error -->
          <div
            v-if="error"
            class="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2"
          >
            <AlertCircle :size="16" /> {{ error }}
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Employee Name -->
            <div>
              <label class="block text-xs font-medium text-slate-400 mb-1.5 uppercase">Employee Name <span class="text-red-500">*</span></label>
              <input
                type="text"
                disabled
                :value="isEditing ? form.employee_name : (employeeInfo?.employee_name || authStore.employeeName)"
                class="input-dark opacity-60 cursor-not-allowed"
              />
            </div>

            <!-- Posting Date -->
            <div>
              <label class="block text-xs font-medium text-slate-400 mb-1.5 uppercase">Posting Date <span class="text-red-500">*</span></label>
              <input
                v-model="form.posting_date"
                type="date"
                required
                class="input-dark"
              />
            </div>

            <!-- Expense Approver -->
            <div>
              <label class="block text-xs font-medium text-slate-400 mb-1.5 uppercase">Expense Approver <span class="text-red-500">*</span></label>
              <select
                v-model="form.expense_approver"
                required
                class="input-dark"
              >
                <option value="" disabled>Select Approver</option>
                <option v-for="appr in approvers" :key="appr.name" :value="appr.name">
                  {{ appr.full_name || appr.name }}
                </option>
              </select>
            </div>
          </div>

          <!-- Multi-Line Expense Details -->
          <div class="border-t border-white/10 pt-4">
            <h3 class="text-sm font-bold text-white mb-4 uppercase tracking-wider">Expense Items</h3>
            
            <div class="hidden md:grid grid-cols-12 gap-3 px-2 mb-2 text-slate-400 text-xs font-medium">
              <span class="col-span-2">Date <span class="text-red-500">*</span></span>
              <span class="col-span-3">Type <span class="text-red-500">*</span></span>
              <span class="col-span-2">Amount <span class="text-red-500">*</span></span>
              <span class="col-span-4">Description</span>
              <span class="col-span-1 text-center">Action</span>
            </div>

            <div class="space-y-3">
              <div v-for="(line, idx) in form.expenses" :key="idx" class="grid grid-cols-12 gap-3 items-center">
                <!-- Date -->
                <div class="col-span-12 md:col-span-2">
                  <input
                    v-model="line.expense_date"
                    type="date"
                    required
                    class="input-dark text-xs py-2 px-3"
                  />
                </div>
                <!-- Type -->
                <div class="col-span-12 md:col-span-3">
                  <select
                    v-model="line.expense_type"
                    required
                    class="input-dark text-xs py-2 px-3"
                  >
                    <option value="" disabled>Select Type</option>
                    <option v-for="t in expenseTypes" :key="t" :value="t">{{ t }}</option>
                  </select>
                </div>
                <!-- Amount -->
                <div class="col-span-12 md:col-span-2">
                  <input
                    v-model="line.amount"
                    type="number"
                    step="0.01"
                    required
                    placeholder="0.00"
                    class="input-dark text-xs py-2 px-3"
                  />
                </div>
                <!-- Description -->
                <div class="col-span-12 md:col-span-4">
                  <input
                    v-model="line.description"
                    type="text"
                    placeholder="Reason..."
                    class="input-dark text-xs py-2 px-3"
                  />
                </div>
                <!-- Delete -->
                <div class="col-span-12 md:col-span-1 flex justify-center">
                  <button
                    type="button"
                    @click="removeExpenseLine(idx)"
                    class="p-2 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors flex items-center justify-center"
                    title="Remove item"
                  >
                    <Trash2 :size="16" />
                  </button>
                </div>
              </div>
            </div>

            <button
              type="button"
              @click="addExpenseLine"
              class="mt-3 flex items-center gap-1.5 px-3 py-1.5 bg-white/5 border border-white/10 hover:bg-white/10 text-white rounded-lg text-xs font-medium transition-colors"
            >
              <Plus :size="14" /> Add Row
            </button>
          </div>

          <!-- Remark -->
          <div>
            <label class="block text-xs font-medium text-slate-400 mb-1.5 uppercase">Remark / Notes</label>
            <textarea
              v-model="form.remark"
              rows="2"
              placeholder="Describe the context of this claim..."
              class="input-dark resize-none"
            ></textarea>
          </div>

          <!-- Proofs/Attachments -->
          <div>
            <label class="block text-xs font-medium text-slate-400 mb-1.5 uppercase">Proofs / Attachments (Bill/Receipt)</label>
            
            <div v-if="form.proofs.length > 0" class="mb-4 space-y-2">
              <div v-for="(proofUrl, index) in form.proofs" :key="index" class="p-3 bg-white/5 border border-white/10 rounded-lg flex items-center justify-between text-xs">
                <div class="flex items-center gap-2 text-slate-300">
                  <FileText :size="16" class="text-teal-400" />
                  <a :href="proofUrl" target="_blank" class="hover:underline hover:text-white truncate max-w-[250px]">
                    Proof Attachment {{ index + 1 }}
                  </a>
                </div>
                <button
                  type="button"
                  @click="form.proofs.splice(index, 1)"
                  class="text-red-400 hover:text-red-350 text-xs font-medium"
                >
                  Remove
                </button>
              </div>
            </div>

            <div
              class="relative border border-dashed border-white/10 rounded-lg p-4 text-center hover:border-teal-500/30 transition-colors cursor-pointer"
              @click="fileInput?.click()"
            >
              <input
                ref="fileInput"
                type="file"
                class="hidden"
                accept="image/*,.pdf"
                multiple
                @change="handleFileSelect"
              />
              <Upload :size="20" class="mx-auto mb-1 text-slate-500" />
              <p class="text-xs text-slate-300">
                {{ uploadingFile ? "Uploading..." : "Click to upload proof receipt(s)" }}
              </p>
              <p class="text-[10px] text-slate-500 mt-0.5">Supports multiple image or PDF uploads</p>
            </div>
          </div>

          <!-- Total claimed display -->
          <div class="flex items-center justify-between border-t border-white/10 pt-4">
            <span class="text-sm text-slate-500">Total Claim Amount</span>
            <span class="text-xl font-bold text-white">₹{{ Number(totalClaimedAmount).toLocaleString() }}</span>
          </div>

          <button
            type="submit"
            :disabled="submitting"
            class="w-full mt-4 bg-gradient-to-r from-teal-500 to-emerald-500 hover:from-teal-400 hover:to-emerald-400 text-white font-medium py-2.5 rounded-lg shadow-lg flex items-center justify-center gap-2"
          >
            <span
              v-if="submitting"
              class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"
            ></span>
            <span v-else>{{ isEditing ? 'Update Claim' : 'Submit Claim' }}</span>
          </button>
        </form>
      </div>
    </div>

    <!-- Claim Details Modal -->
    <div v-if="showDetailModal && selectedDetail" class="fixed inset-0 z-50 flex items-center justify-center p-4 !mt-0">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showDetailModal = false"></div>
      <div class="glass-card w-full max-w-2xl p-6 relative animate-scale-in max-h-[90vh] overflow-y-auto no-scrollbar">
        <button
          @click="showDetailModal = false"
          class="absolute right-4 top-4 text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
        >
          <X :size="20" />
        </button>

        <h2 class="text-xl font-bold text-[var(--text-primary)] mb-6 flex items-center gap-2">
          <FileText class="text-[var(--accent)]" /> Claim Details
        </h2>

        <div class="space-y-6">
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p class="text-[var(--text-secondary)] text-xs font-semibold">Reference ID</p>
              <p class="text-[var(--text-primary)] font-medium mt-1">{{ selectedDetail.name }}</p>
            </div>
            <div>
              <p class="text-[var(--text-secondary)] text-xs font-semibold">Status</p>
              <span
                class="inline-block px-2.5 py-1 rounded-full text-xs font-semibold border mt-1"
                :class="statusColor(selectedDetail.approval_status)"
              >
                {{ selectedDetail.approval_status }}
              </span>
            </div>
            <div>
              <p class="text-[var(--text-secondary)] text-xs font-semibold">Posting Date</p>
              <p class="text-[var(--text-primary)] font-medium mt-1">{{ formatDate(selectedDetail.posting_date) }}</p>
            </div>
            <div>
              <p class="text-[var(--text-secondary)] text-xs font-semibold">Expense Approver</p>
              <p class="text-[var(--text-primary)] font-medium mt-1">{{ selectedDetail.expense_approver || '-' }}</p>
            </div>
            <div v-if="selectedDetail.payable_account">
              <p class="text-[var(--text-secondary)] text-xs font-semibold">Payable Account</p>
              <p class="text-[var(--text-primary)] font-medium mt-1">{{ selectedDetail.payable_account }}</p>
            </div>
          </div>

          <!-- Table of lines -->
          <div class="border border-[var(--border-color)] rounded-xl overflow-x-auto">
            <table class="w-full text-left border-collapse text-xs">
              <thead class="bg-[var(--surface-50)] border-b border-[var(--border-color)] text-[var(--text-secondary)] font-medium">
                <tr>
                  <th class="p-3">Date</th>
                  <th class="p-3">Type</th>
                  <th class="p-3">Amount</th>
                  <th class="p-3">Description</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-[var(--border-color)] text-[var(--text-secondary)]">
                <tr v-for="(line, idx) in selectedDetail.expenses" :key="idx" class="hover:bg-[var(--row-hover)]">
                  <td class="p-3 whitespace-nowrap">{{ formatDate(line.expense_date) }}</td>
                  <td class="p-3 whitespace-nowrap">{{ line.expense_type }}</td>
                  <td class="p-3 font-medium text-[var(--text-primary)]">₹{{ Number(line.amount).toLocaleString() }}</td>
                  <td class="p-3 text-[var(--text-secondary)]">{{ line.description || '-' }}</td>
                </tr>
                <tr v-if="!selectedDetail.expenses || selectedDetail.expenses.length === 0">
                  <td colspan="4" class="p-3 text-center text-[var(--text-tertiary)]">No lines found.</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="selectedDetail.remark" class="bg-[var(--surface-50)] p-4 rounded-xl border border-[var(--border-color)]">
            <p class="text-[var(--text-secondary)] text-xs uppercase mb-1 font-semibold">Remark / Notes</p>
            <p class="text-[var(--text-primary)] text-sm whitespace-pre-wrap">{{ selectedDetail.remark }}</p>
          </div>

          <div v-if="selectedDetail.proofs && selectedDetail.proofs.length > 0" class="bg-[var(--surface-50)] p-4 rounded-xl border border-[var(--border-color)] text-xs">
            <p class="text-[var(--text-secondary)] text-xs uppercase mb-2 font-semibold">Attached Proofs</p>
            <div class="space-y-2">
              <div v-for="(proofUrl, idx) in selectedDetail.proofs" :key="idx" class="flex items-center gap-2">
                <FileText :size="16" class="text-[var(--accent)]" />
                <a :href="proofUrl" target="_blank" class="text-[var(--accent)] hover:underline hover:text-[var(--accent-light)] font-medium truncate max-w-[400px]">
                  Proof Attachment {{ idx + 1 }}
                </a>
              </div>
            </div>
          </div>
          <div v-else-if="selectedDetail.proof" class="bg-[var(--surface-50)] p-4 rounded-xl border border-[var(--border-color)] text-xs">
            <p class="text-[var(--text-secondary)] text-xs uppercase mb-2 font-semibold">Attached Proof</p>
            <div class="flex items-center gap-2">
              <FileText :size="16" class="text-[var(--accent)]" />
              <a :href="selectedDetail.proof" target="_blank" class="text-[var(--accent)] hover:underline hover:text-[var(--accent-light)] font-medium">
                View Receipt / Bill
              </a>
            </div>
          </div>

          <div class="flex items-center justify-between border-t border-[var(--border-color)] pt-4">
            <span class="text-sm text-[var(--text-secondary)] font-semibold">Total Claim Amount</span>
            <span class="text-xl font-bold text-[var(--text-primary)]">₹{{ Number(selectedDetail.total_claimed_amount).toLocaleString() }}</span>
          </div>

          <!-- Actions at bottom of details modal -->
          <div v-if="selectedDetail.approval_status === 'Draft'" class="flex justify-end gap-3 border-t border-[var(--border-color)] pt-4">
            <!-- Approve / Reject (only for team members' claims) -->
            <template v-if="selectedDetail.employee && selectedDetail.employee !== authStore.employee">
              <button
                @click="openApproveModal(selectedDetail, 'Approve'); showDetailModal = false;"
                class="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-emerald-600 to-green-500 text-white rounded-xl text-xs font-semibold shadow-lg hover:shadow-green-500/20 transition-all cursor-pointer"
              >
                <CheckCircle :size="14" /> Approve
              </button>
              <button
                @click="openApproveModal(selectedDetail, 'Reject'); showDetailModal = false;"
                class="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-red-500 to-rose-500 text-white rounded-xl text-xs font-semibold shadow-lg transition-all cursor-pointer"
              >
                <XCircle :size="14" /> Reject
              </button>
            </template>

            <!-- Edit / Delete (Only available for own claims) -->
            <template v-else>
              <button
                @click="handleEdit(selectedDetail); showDetailModal = false;"
                class="flex items-center gap-1.5 px-4 py-2 bg-white/5 border border-white/10 hover:bg-white/10 text-white rounded-xl text-xs font-semibold transition-colors cursor-pointer"
              >
                <Edit :size="14" /> Edit Claim
              </button>
              <button
                @click="handleDelete(selectedDetail.name); showDetailModal = false;"
                class="flex items-center gap-1.5 px-4 py-2 bg-red-500/10 border border-red-500/20 hover:bg-red-500/20 text-red-400 rounded-xl text-xs font-semibold transition-colors cursor-pointer"
              >
                <Trash2 :size="14" /> Delete Claim
              </button>
            </template>
          </div>
        </div>
      </div>
    </div>

    <!-- Approval Confirmation Modal -->
    <div v-if="showApproveModal && approvingClaim" class="fixed inset-0 z-50 flex items-center justify-center p-4 !mt-0">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showApproveModal = false"></div>
      <div class="glass-card w-full max-w-md p-6 relative animate-scale-in">
        <button
          @click="showApproveModal = false"
          class="absolute right-4 top-4 text-slate-500 hover:text-white cursor-pointer"
        >
          <X :size="20" />
        </button>

        <h2 class="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <CheckCircle v-if="modalAction === 'Approve'" class="text-emerald-400" />
          <XCircle v-else class="text-red-400" />
          {{ modalAction === 'Approve' ? 'Approve Expense Claim' : 'Reject Expense Claim' }}
        </h2>

        <form @submit.prevent="submitProcess" class="space-y-4">
          <p class="text-xs text-slate-305 leading-relaxed">
            Are you sure you want to {{ modalAction.toLowerCase() }} the expense claim <strong>{{ approvingClaim.name }}</strong> for <strong>{{ approvingClaim.employee_name || approvingClaim.employee }}</strong> in the amount of <strong>₹{{ Number(approvingClaim.total_claimed_amount).toLocaleString() }}</strong>?
          </p>

          <!-- Error Alert -->
          <div
            v-if="actionError"
            class="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2"
          >
            <AlertCircle :size="16" /> {{ actionError }}
          </div>

          <!-- Payable Account Dropdown (only for Approve action) -->
          <div v-if="modalAction === 'Approve'">
            <label class="block text-xs font-semibold text-slate-400 uppercase mb-1.5 tracking-wider">Payable Account</label>
            <div class="relative w-full">
              <select v-model="selectedPayableAccount" required class="input-dark appearance-none pr-10 text-xs py-2 px-3">
                <option value="" disabled>Select Payable Account</option>
                <option v-for="acc in payableAccounts" :key="acc.value" :value="acc.value">
                  {{ acc.label || acc.value }}
                </option>
              </select>
              <ChevronDown class="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400" :size="14" />
            </div>
            <p class="text-[10px] text-slate-500 mt-1">Select the account from which this claim will be paid</p>
          </div>

          <div class="flex justify-end gap-3 border-t border-white/5 pt-4">
            <button
              type="button"
              @click="showApproveModal = false"
              class="px-4 py-2 bg-white/5 border border-white/10 hover:bg-white/10 text-white rounded-xl text-xs font-semibold transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="processingAction"
              class="flex items-center gap-1.5 px-4 py-2 text-white rounded-xl text-xs font-semibold shadow-lg transition-all cursor-pointer"
              :class="modalAction === 'Approve' ? 'bg-gradient-to-r from-teal-500 to-emerald-500 hover:from-teal-400 hover:to-emerald-400 hover:shadow-green-500/20' : 'bg-gradient-to-r from-red-500 to-rose-500 hover:from-red-400 hover:to-rose-400 hover:shadow-red-500/20'"
            >
              <span
                v-if="processingAction"
                class="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin"
              ></span>
              {{ modalAction === 'Approve' ? 'Approve' : 'Reject' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
