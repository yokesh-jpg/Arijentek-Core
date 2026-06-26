import { useAuthStore } from "../stores/auth";

const BASE = "/api/method";

async function request<T = any>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const auth = useAuthStore();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };

  const token = auth.csrfToken || (window as any).csrf_token;
  if (token && options.method && options.method !== "GET") {
    headers["X-Frappe-CSRF-Token"] = token;
  }

  const res = await fetch(`${BASE}/${endpoint}`, {
    ...options,
    headers: { ...headers, ...((options.headers as Record<string, string>) || {}) },
    credentials: "include",
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    let msg = "Request failed";
    if (err._server_messages) {
      try {
        const msgs = JSON.parse(err._server_messages);
        msg = JSON.parse(msgs[0]).message || msg;
      } catch {
        /* ignore */
      }
    } else if (err.exception) {
      msg = err.exception;
    }
    throw new Error(msg);
  }

  const data = await res.json();
  return data.message !== undefined ? data.message : data;
}

function get<T = any>(endpoint: string) {
  return request<T>(endpoint, { method: "GET" });
}

function post<T = any>(endpoint: string, body?: any) {
  return request<T>(endpoint, {
    method: "POST",
    body: body ? JSON.stringify(body) : undefined,
  });
}

// Caching helper — TTL: 1 hour
const CACHE_TTL_MS = 60 * 60 * 1000; // 1 hour

export async function useCachedFetch<T>(
  key: string,
  fetcher: () => Promise<T>,
  onData: (data: T) => void,
) {
  // 1. Try cache (with expiry check)
  const cached = localStorage.getItem(`cache_${key}`);
  if (cached) {
    try {
      const { data, timestamp } = JSON.parse(cached);
      const isExpired = Date.now() - timestamp > CACHE_TTL_MS;
      if (!isExpired) {
        onData(data);
      } else {
        // Remove stale cache
        localStorage.removeItem(`cache_${key}`);
      }
    } catch (e) {
      console.warn("Cache parse error", key);
      localStorage.removeItem(`cache_${key}`);
    }
  }

  // 2. Fetch fresh
  try {
    const freshData = await fetcher();
    onData(freshData);
    // 3. Update cache
    localStorage.setItem(
      `cache_${key}`,
      JSON.stringify({
        data: freshData,
        timestamp: Date.now(),
      }),
    );
  } catch (e) {
    console.error("Fetch failed", key, e);
    // If we had no cache, propagate error? Or just silent fail?
    // user wants "offline" behavior, so silent fail if we have cache is good.
    if (!cached) throw e;
  }
}

// ---------- Dashboard ----------
export const dashboardApi = {
  getData: () => get("arijentek_core.api.get_dashboard_data"),
  getEmployeeInfo: () => get("arijentek_core.api.get_employee_info"),
  getReportingInfo: (employee?: string) =>
    get(`arijentek_core.api.get_reporting_info${employee ? `?employee=${encodeURIComponent(employee)}` : ""}`),
};

// ---------- Attendance / Clock ----------
export const attendanceApi = {
  punch: (timestamp?: string) => post("arijentek_core.api.punch", { timestamp }),
  getTodayCheckin: () => get("arijentek_core.api.get_today_checkin"),
  getStatus: () => get("arijentek_core.api.v1.attendance.get_status"),
  getSummary: () => get("arijentek_core.api.get_attendance_summary"),
  getRecords: (month?: number, year?: number, employee_id?: string) => {
    const params: string[] = [];
    if (month && year) params.push(`month=${month}`, `year=${year}`);
    if (employee_id) params.push(`employee_id=${encodeURIComponent(employee_id)}`);
    const qs = params.length ? `?${params.join("&")}` : "";
    return get(`arijentek_core.api.get_attendance_records${qs}`);
  },

  getShiftApproverEmployees: () => get("arijentek_core.get_shift_approver_employees"),
  canMarkAttendance: () => get("arijentek_core.can_mark_attendance"),
  getAttendanceStatusList: () => get("arijentek_core.api.v1.attendance.get_attendance_status"),
  submitManualAttendance: (data: {
    employee: string;
    date: string;
    status: string;
    in_time?: string;
    out_time?: string;
    id?: string;
  }) => post("arijentek_core.api.v1.attendance.manual_attendance", data),
  deleteAttendance: (name: string) => post("arijentek_core.api.v1.attendance.delete_attendance", { name }),
  createRequest: (data: {
    from_date: string;
    to_date: string;
    reason: string;
    explanation?: string;
  }) => post("arijentek_core.api.v1.attendance.create_attendance_request", data),
  getMyRequests: (status?: string, from_date?: string, to_date?: string) => {
    const params: string[] = [];
    if (status) params.push(`status=${encodeURIComponent(status)}`);
    if (from_date) params.push(`from_date=${encodeURIComponent(from_date)}`);
    if (to_date) params.push(`to_date=${encodeURIComponent(to_date)}`);
    const qs = params.length ? `?${params.join("&")}` : "";
    return get(`arijentek_core.api.v1.attendance.get_my_attendance_requests${qs}`);
  },
  updateRequest: (data: {
    name: string;
    from_date?: string;
    to_date?: string;
    reason?: string;
    explanation?: string;
  }) => post("arijentek_core.api.v1.attendance.update_attendance_request", data),
  deleteRequest: (name: string) =>
    post("arijentek_core.api.v1.attendance.delete_attendance_request", { name }),

  startBreak: () => post("arijentek_core.api.start_break"),
  endBreak: () => post("arijentek_core.api.end_break"),
  getBreakStatus: () => get("arijentek_core.api.get_break_status"),
  getAttendanceBreaks: (employee?: string, date?: string) => {
    const params: string[] = [];
    if (employee) params.push(`employee=${encodeURIComponent(employee)}`);
    if (date) params.push(`date=${encodeURIComponent(date)}`);
    const qs = params.length ? `?${params.join("&")}` : "";
    return get(`arijentek_core.api.get_attendance_breaks${qs}`);
  },
  // Roster
  getRoster: (month?: number, year?: number, employee?: string) => {
    const params: string[] = [];
    if (month && year) params.push(`month=${month}`, `year=${year}`);
    if (employee) params.push(`employee=${encodeURIComponent(employee)}`);
    const qs = params.length ? `?${params.join("&")}` : "";

    return get(`arijentek_core.api.get_roster_data${qs}`);
  },
};

// ---------- Leave ----------
export const leaveApi = {
  getTypes: (employee?: string) =>
    get(`arijentek_core.api.get_leave_types${employee ? `?employee=${encodeURIComponent(employee)}` : ""}`),
  getBalance: (employee?: string) =>
    get(`arijentek_core.api.get_leave_balance${employee ? `?employee=${encodeURIComponent(employee)}` : ""}`),
  getApplications: (employee?: string, status?: string, from_date?: string, to_date?: string) => {
    const params: string[] = [];
    if (employee) params.push(`employee=${encodeURIComponent(employee)}`);
    if (status) params.push(`status=${encodeURIComponent(status)}`);
    if (from_date) params.push(`from_date=${encodeURIComponent(from_date)}`);
    if (to_date) params.push(`to_date=${encodeURIComponent(to_date)}`);
    const qs = params.length ? `?${params.join("&")}` : "";
    return get(`arijentek_core.api.get_leave_applications${qs}`);
  },
  getHolidays: (from_date?: string, to_date?: string, exclude_weekly_off?: boolean, employee?: string) => {
    const params: string[] = [];
    if (from_date && to_date) {
      params.push(`from_date=${from_date}`, `to_date=${to_date}`);
    }
    if (exclude_weekly_off) {
      params.push("exclude_weekly_off=1");
    }
    if (employee) {
      params.push(`employee=${encodeURIComponent(employee)}`);
    }
    const qs = params.length ? `?${params.join("&")}` : "";
    return get(`arijentek_core.api.get_holidays${qs}`);
  },
  apply: (data: {
    leave_type: string;
    from_date: string;
    to_date: string;
    half_day?: number;
    reason?: string;
    name?: string;
  }) => post("arijentek_core.api.apply_leave", data),
  cancel: (leave_application: string) =>
    post("arijentek_core.api.cancel_leave", { leave_application }),
  delete: (leave_application: string) =>
    post("arijentek_core.api.delete_leave", { leave_application }),
  deleteApprovedRejected: (leave_application: string) =>
    post("arijentek_core.api.delete_approved_rejected_leave", { leave_application }),
};

// ---------- Payroll ----------
export const payrollApi = {
  getSlips: () => get("arijentek_core.api.get_salary_slips"),
  getDownloadUrl: (name: string) =>
    `/api/method/arijentek_core.api.download_payslip?name=${encodeURIComponent(name)}`,
  generatePayroll: (month?: number, year?: number) =>
    post("arijentek_core.api.generate_payroll", { month, year }),
  getSlipDetails: (name: string) =>
    get(`arijentek_core.api.get_payslip_details?name=${encodeURIComponent(name)}`),
  getPreview: (month?: number, year?: number) =>
    get(
      `arijentek_core.api.get_payroll_preview${month && year ? `?month=${month}&year=${year}` : ""}`,
    ),
  getDashboard: () => get("arijentek_core.api.get_payroll_dashboard"),
  generateMyPayslip: (month?: number, year?: number) =>
    post("arijentek_core.api.generate_my_payslip", { month, year }),
  deletePayslip: (name: string) => post("arijentek_core.api.delete_my_payslip", { name }),
  canDeleteSalarySlip: () => get<boolean>("arijentek_core.api.can_delete_salary_slip"),
};

export const managerApi = {
  getTeamLeaves: (status?: string, from_date?: string, to_date?: string, employee?: string) => {
    const params: string[] = [];
    if (status) params.push(`status=${encodeURIComponent(status)}`);
    if (from_date) params.push(`from_date=${encodeURIComponent(from_date)}`);
    if (to_date) params.push(`to_date=${encodeURIComponent(to_date)}`);
    if (employee) params.push(`employee=${encodeURIComponent(employee)}`);
    const qs = params.length ? `?${params.join("&")}` : "";
    return get(`arijentek_core.api.get_team_leaves${qs}`);
  },
  getLeaveApproverEmployees: () => get("arijentek_core.get_leave_approver_employees"),
  processLeave: (application: string, status: "Approved" | "Rejected") =>
    post("arijentek_core.api.process_leave", { leave_application: application, status }),
  getPendingLeaveCount: () => get("arijentek_core.api.notifications.get_pending_leave_count"),
  getPendingCounts: () => get("arijentek_core.api.notifications.get_team_pending_counts"),
  getTeamAttendanceRequests: (status?: string, from_date?: string, to_date?: string, employee?: string) => {
    const params: string[] = [];
    if (status) params.push(`status=${encodeURIComponent(status)}`);
    if (from_date) params.push(`from_date=${encodeURIComponent(from_date)}`);
    if (to_date) params.push(`to_date=${encodeURIComponent(to_date)}`);
    if (employee) params.push(`employee=${encodeURIComponent(employee)}`);
    const qs = params.length ? `?${params.join("&")}` : "";
    return get(`arijentek_core.api.v1.attendance.get_team_attendance_requests${qs}`);
  },
  processAttendanceRequest: (name: string, action: "Approve" | "Reject") =>
    post("arijentek_core.api.v1.attendance.process_attendance_request", { name, action }),
};

export const authApi = {
  changePassword: (oldPw: string, newPw: string) =>
    post("arijentek_core.api.auth.change_password", { old_password: oldPw, new_password: newPw }),
};

export const expensesApi = {
  getTypes: () => get("arijentek_core.api.expenses.get_expense_types"),
  getMyExpenses: (status?: string, fromDate?: string, toDate?: string) => {
    const params: string[] = [];
    if (status) params.push(`status=${encodeURIComponent(status)}`);
    if (fromDate) params.push(`from_date=${encodeURIComponent(fromDate)}`);
    if (toDate) params.push(`to_date=${encodeURIComponent(toDate)}`);
    const qs = params.length ? `?${params.join("&")}` : "";
    return get(`arijentek_core.api.expenses.get_my_expenses${qs}`);
  },
  submit: (data: any) => post("arijentek_core.api.expenses.submit_expense_claim", data),
  getApprovers: (employee: string) => get(`arijentek_core.api.expenses.get_expense_approvers?employee=${encodeURIComponent(employee)}`),
  getCompanyDefaults: (company: string) => get(`arijentek_core.api.expenses.get_company_defaults?company=${encodeURIComponent(company)}`),
  delete: (name: string) => post("arijentek_core.api.expenses.delete_expense_claim", { name }),
  // Manager
  getTeamExpenses: (status?: string, fromDate?: string, toDate?: string, employee?: string) => {
    const params: string[] = [];
    if (status) params.push(`status=${encodeURIComponent(status)}`);
    if (fromDate) params.push(`from_date=${encodeURIComponent(fromDate)}`);
    if (toDate) params.push(`to_date=${encodeURIComponent(toDate)}`);
    if (employee) params.push(`employee=${encodeURIComponent(employee)}`);
    const qs = params.length ? `?${params.join("&")}` : "";
    return get(`arijentek_core.api.expenses.get_team_expenses${qs}`);
  },
  getExpenseApproverEmployees: () => get("arijentek_core.get_expense_approver_employees"),
  getPayableAccounts: (company: string) => get(`arijentek_core.api.expenses.get_payable_accounts?company=${encodeURIComponent(company)}`),
  process: (name: string, action: "Approve" | "Reject", payable_account?: string) =>
    post("arijentek_core.api.expenses.process_expense", { name, action, payable_account }),
};
