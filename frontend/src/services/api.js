// Caching helper — TTL: 1 hour
const CACHE_TTL_MS = 60 * 60 * 1000;

async function request(endpoint, options = {}) {
  const token = frappe?.csrf_token || document.cookie
    .match(/CSRFToken=([^;]+)/)?.[1];

  const headers = {
    "Content-Type": "application/json",
    Accept: "application/json",
    ...options.headers,
  };

  if (options.method && options.method !== "GET" && token) {
    headers["X-Frappe-CSRF-Token"] = token;
  }

  const res = await fetch(`/api/method/${endpoint}`, {
    ...options,
    headers,
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

function get(endpoint) {
  return request(endpoint, { method: "GET" });
}

function post(endpoint, body) {
  return request(endpoint, {
    method: "POST",
    body: body ? JSON.stringify(body) : undefined,
  });
}

/**
 * useCachedFetch — TTL: 1 hour
 * 1. Try cache (with expiry check)
 * 2. Fetch fresh
 * 3. Update cache
 */
export function useCachedFetch(key, fetcher, onData) {
  // 1. Try cache (with expiry check)
  const cached = localStorage.getItem(`cache_${key}`);
  if (cached) {
    try {
      const { data, timestamp } = JSON.parse(cached);
      const isExpired = Date.now() - timestamp > CACHE_TTL_MS;
      if (!isExpired) {
        onData(data);
      } else {
        localStorage.removeItem(`cache_${key}`);
      }
    } catch (e) {
      console.warn("Cache parse error", key);
      localStorage.removeItem(`cache_${key}`);
    }
  }

  // 2. Fetch fresh
  fetcher()
    .then((freshData) => {
      onData(freshData);
      // 3. Update cache
      localStorage.setItem(
        `cache_${key}`,
        JSON.stringify({ data: freshData, timestamp: Date.now() })
      );
    })
    .catch((e) => {
      console.error("Fetch failed", key, e);
      // If we had no cache, propagate error? Or just silent fail?
      // user wants "offline" behavior, so silent fail if we have cache is good.
      if (!cached) throw e;
    });
}

// ---------- Leave ----------
export const leaveApi = {
  getBalance: () => get("arijentek_core.api.attendance.get_leave_balance"),
  getApplications: () => get("arijentek_core.api.attendance.get_leave_applications"),
  getTypes: () => get("arijentek_core.api.leave.get_leave_types"),
};

// ---------- Holidays ----------
export const holidayApi = {
  getMonthHolidays: (from_date, to_date) => {
    const params = new URLSearchParams();
    if (from_date) params.set("from_date", from_date);
    if (to_date) params.set("to_date", to_date);
    const qs = params.toString();
    return get(`arijentek_core.api.attendance.get_holidays?${qs}`);
  },
};

// ---------- Attendance / Stats ----------
export const attendanceApi = {
  getTodayCheckin: () => get("arijentek_core.api.attendance.get_today_checkin_status"),
  punch: () => post("arijentek_core.api.attendance.punch"),
  getMonthStats: () => get("arijentek_core.api.attendance.get_monthly_attendance_stats"),
  getSummary: (employee) => get(`arijentek_core.api.attendance.get_attendance_summary?employee=${encodeURIComponent(employee)}`),
};

// ---------- Dashboard ----------
export const dashboardApi = {
  getData: () => get("arijentek_core.api.dashboard.get_employee_dashboard_data"),
  getEmployeeInfo: () => get("arijentek_core.api.attendance.get_current_employee"),
};

export const authApi = {
  changePassword: (oldPw, newPw) =>
    post("arijentek_core.api.settings.change_own_password", {
      current_password: oldPw,
      new_password: newPw,
    }),
};

export const rosterApi = {
  getWeeklyStats: (employeeId) =>
    get(`arijentek_core.api.roster.get_weekly_roster?employee_id=${encodeURIComponent(employeeId)}`),
};

export default {
  leaveApi,
  holidayApi,
  attendanceApi,
  dashboardApi,
  rosterApi,
  authApi,
  useCachedFetch,
};
