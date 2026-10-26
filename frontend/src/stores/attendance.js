import { defineStore } from "pinia";
import { createResource } from "frappe-ui";
import { ref, computed } from "vue";

export const useAttendanceStore = defineStore("attendance", () => {
	const todayStatus = ref(null);
	const roster = ref(null);
	const history = ref([]);
	const historyTotal = ref(0);
	const loading = ref(false);
	const error = ref(null);
	const workedSecondsToday = ref(0);
	const employeeId = ref(null);
	let timerInterval = null;

	const employeeList = ref([]);
	const monthlyRoster = ref(null);

	// Today's check-in status
	const todayStatusResource = createResource({
		url: "arijentek_core.api.attendance.get_today_checkin_status",
		auto: false,
		onSuccess(data) {
			todayStatus.value = data;
		},
	});

	// Employee roster info
	const rosterResource = createResource({
		url: "arijentek_core.api.attendance.get_employee_roster",
		auto: false,
		onSuccess(data) {
			roster.value = data;
		},
	});

	// Clock in
	const clockInResource = createResource({
		url: "arijentek_core.api.attendance.clock_in",
		auto: false,
	});

	// Clock out
	const clockOutResource = createResource({
		url: "arijentek_core.api.attendance.clock_out",
		auto: false,
	});

	// Break start (creates an OUT record with break note)
	const breakStartResource = createResource({
		url: "arijentek_core.api.attendance.clock_out",
		auto: false,
	});

	// Break end (creates an IN record with break note)
	const breakEndResource = createResource({
		url: "arijentek_core.api.attendance.clock_in",
		auto: false,
	});

	// History
	const historyResource = createResource({
		url: "arijentek_core.api.attendance.get_attendance_history",
		auto: false,
		onSuccess(data) {
			// Paginated responses (page_size > 0) carry the page in `data.data`;
			// legacy responses carry every record in `data.records`.
			history.value = data?.data || data?.records || data || [];
			historyTotal.value = Number(data?.total) || history.value.length;
		},
	});

	// Employee list for marking attendance
	const employeeListResource = createResource({
		url: "arijentek_core.api.attendance.get_employee_list_for_attendance",
		auto: false,
		onSuccess(data) {
			employeeList.value = data || [];
		},
	});

	// Monthly roster
	const monthlyRosterResource = createResource({
		url: "arijentek_core.api.roster.get_monthly_roster",
		auto: false,
		onSuccess(data) {
			monthlyRoster.value = data;
		},
	});

	// Check if user can mark attendance (create permission)
	const canMarkAttendanceResource = createResource({
		url: "arijentek_core.api.attendance.can_mark_attendance",
		auto: false,
	});

	// Check if user can manage attendance (write permission — view other employees' data)
	const canManageAttendanceResource = createResource({
		url: "arijentek_core.api.attendance.can_manage_attendance",
		auto: false,
	});

	// Check if user can view attendance (read permission — gate employee filter)
	const canViewAttendanceResource = createResource({
		url: "arijentek_core.api.attendance.can_view_attendance",
		auto: false,
	});

	// Check if user can delete employee checkins (delete permission)
	const canDeleteCheckinResource = createResource({
		url: "arijentek_core.api.attendance.can_delete_checkin",
		auto: false,
	});

	// Mark attendance
	const markAttendanceResource = createResource({
		url: "arijentek_core.api.attendance.mark_attendance",
		auto: false,
	});

	// Computed
	const isCheckedIn = computed(() => {
		return todayStatus.value?.checked_in || false;
	});

	const isOnBreak = computed(() => {
		return todayStatus.value?.is_on_break || false;
	});

	const totalSecondsToday = computed(() => {
		if (typeof todayStatus.value?.total_seconds_today === "number") {
			return todayStatus.value.total_seconds_today;
		}
		return Math.round((todayStatus.value?.total_hours_today || 0) * 3600);
	});

	const totalHoursToday = computed(() => {
		return Number((workedSecondsToday.value / 3600).toFixed(2));
	});

	const overtimeHours = computed(() => {
		const overtime = workedSecondsToday.value / 3600 - workingHoursTarget.value;
		return Number(Math.max(0, overtime).toFixed(2));
	});

	const workingHoursTarget = computed(() => {
		return roster.value?.working_hours || todayStatus.value?.working_hours_target || 8;
	});

	const shiftComplete = computed(() => {
		return (
			workedSecondsToday.value >= workingHoursTarget.value * 3600 &&
			workedSecondsToday.value > 0
		);
	});

	const isDayCompleted = computed(() => {
		const data = todayStatus.value;
		if (!data) return false;

		// If there are shifts defined
		if (data.shifts && data.shifts.length > 0) {
			return data.shifts.every((s) => s.is_completed);
		}

		// Fallback for single/standard shift
		return (
			data.last_log_type === "OUT" &&
			!isOnBreak.value &&
			(data.logs || []).length >= 2 &&
			totalSecondsToday.value > 0
		);
	});

	const canManageBreak = computed(() => {
		return isCheckedIn.value || isOnBreak.value;
	});

	const timerLabel = computed(() => {
		if (isOnBreak.value) return "Break Paused";
		if (isCheckedIn.value) return "Shift Time";
		if (workedSecondsToday.value > 0) return "Today's Total";
		return "Not Clocked In";
	});

	const formattedWorkedTime = computed(() => {
		const totalSeconds = Math.floor(workedSecondsToday.value);
		const hours = Math.floor(totalSeconds / 3600);
		const minutes = Math.floor((totalSeconds % 3600) / 60);
		const seconds = totalSeconds % 60;
		return `${hours.toString().padStart(2, "0")}:${minutes
			.toString()
			.padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
	});

	function getErrorMessage(error) {
		if (!error) return "";
		if (typeof error === "string") return error;
		if (Array.isArray(error.messages)) return error.messages.join(" ");
		if (typeof error.messages === "string") return error.messages;
		return error.message || String(error);
	}

	function clearTimerTicker() {
		if (timerInterval) {
			clearInterval(timerInterval);
			timerInterval = null;
		}
	}

	function startTimerTicker() {
		clearTimerTicker();
		timerInterval = setInterval(() => {
			workedSecondsToday.value += 1;
		}, 1000);
	}

	function syncTimerFromStatus() {
		// Always clear timer first to prevent duplicates
		clearTimerTicker();

		// Sync worked seconds from backend data
		workedSecondsToday.value = totalSecondsToday.value;

		// Start timer only if checked in AND not on break
		if (isCheckedIn.value && !isOnBreak.value) {
			startTimerTicker();
		}
	}

	// Actions
	async function fetchTodayStatus(employeeId) {
		if (!employeeId) return;
		const result = await todayStatusResource.fetch({ employee_id: employeeId });
		syncTimerFromStatus();
		return result;
	}

	async function fetchRoster(employeeId) {
		if (!employeeId) return;
		return rosterResource.fetch({ employee_id: employeeId });
	}

	async function fetchHistory(employeeId, days = 30) {
		if (!employeeId) return;
		if (days && typeof days === "object") {
			await historyResource.fetch({ employee_id: employeeId, ...days });
		} else {
			await historyResource.fetch({ employee_id: employeeId, days });
		}
	}

	async function clockIn(employeeId, latitude = null, longitude = null, notes = null, shift = null) {
		if (loading.value) return { success: false, status: todayStatus.value };
		loading.value = true;
		error.value = null;
		try {
			const result = await clockInResource.fetch({
				latitude,
				longitude,
				notes,
				shift,
			});
			if (result && result.status) {
				todayStatus.value = result.status;
				syncTimerFromStatus();
				return result;
			} else if (result && result.success) {
				// Handle case where result has success but status might be named differently
				if (employeeId) {
					await fetchTodayStatus(employeeId);
				}
				return result;
			}
			return result;
		} catch (err) {
			const message = getErrorMessage(err);
			error.value = message;
			if (employeeId && message.includes("Already checked in")) {
				await fetchTodayStatus(employeeId);
				return { success: true, status: todayStatus.value, recovered: true };
			}
			throw err;
		} finally {
			loading.value = false;
		}
	}

	async function clockOut(employeeId, latitude = null, longitude = null, notes = null, shift = null) {
		if (loading.value) return { success: false, status: todayStatus.value };
		loading.value = true;
		error.value = null;
		try {
			const result = await clockOutResource.fetch({
				latitude,
				longitude,
				notes,
				shift,
			});
			if (result && result.status) {
				todayStatus.value = result.status;
				syncTimerFromStatus();
				return result;
			} else if (result && result.success) {
				// Handle case where result has success but status might be named differently
				if (employeeId) {
					await fetchTodayStatus(employeeId);
				}
				return result;
			}
			return result;
		} catch (err) {
			const message = getErrorMessage(err);
			error.value = message;
			if (
				employeeId &&
				(message.includes("No active check-in found") ||
					message.includes("Already checked out"))
			) {
				await fetchTodayStatus(employeeId);
				return { success: true, status: todayStatus.value, recovered: true };
			}
			throw err;
		} finally {
			loading.value = false;
		}
	}

	async function init(empId) {
		if (empId) {
			employeeId.value = empId;
			await Promise.all([fetchTodayStatus(empId), fetchRoster(empId)]);
		}
	}

	async function startBreak() {
		if (loading.value) return { success: false, status: todayStatus.value };
		loading.value = true;
		error.value = null;
		try {
			const shift = todayStatus.value?.active_shift_name;
			const result = await breakStartResource.fetch({
				notes: "Break Start",
				shift,
			});
			if (result && result.status) {
				todayStatus.value = result.status;
				syncTimerFromStatus();
			}
			return result;
		} catch (err) {
			error.value = getErrorMessage(err);
			throw err;
		} finally {
			loading.value = false;
		}
	}

	async function endBreak() {
		if (loading.value) return { success: false, status: todayStatus.value };
		loading.value = true;
		error.value = null;
		try {
			const shift = todayStatus.value?.active_shift_name;
			const result = await breakEndResource.fetch({
				notes: "Break End",
				shift,
			});
			if (result && result.status) {
				todayStatus.value = result.status;
				syncTimerFromStatus();
			}
			return result;
		} catch (err) {
			error.value = getErrorMessage(err);
			throw err;
		} finally {
			loading.value = false;
		}
	}

	async function fetchEmployeeList() {
		return employeeListResource.fetch();
	}

	async function fetchMonthlyRoster(employeeId, year, month) {
		if (employeeId) {
			return monthlyRosterResource.fetch({ employee_id: employeeId, year, month });
		}
	}

	async function checkCanMarkAttendance() {
		const result = await canMarkAttendanceResource.fetch();
		return result || false;
	}

	async function checkCanManageAttendance() {
		const result = await canManageAttendanceResource.fetch();
		return result || false;
	}

	async function checkCanViewAttendance() {
		const result = await canViewAttendanceResource.fetch();
		return result || false;
	}

	async function checkCanDeleteCheckin() {
		const result = await canDeleteCheckinResource.fetch();
		return result || false;
	}

	async function markAttendance(empId, date, status, inTime = null, outTime = null, lateEntry = null, earlyExit = null) {
		const params = { employee_id: empId, date, status };
		if (inTime) params.in_time = inTime;
		if (outTime) params.out_time = outTime;
		if (lateEntry !== null) params.late_entry = lateEntry;
		if (earlyExit !== null) params.early_exit = earlyExit;
		return markAttendanceResource.fetch(params);
	}

	const createAttendancePermissionResource = createResource({
		url: "arijentek_core.api.attendance.can_create_attendance",
		auto: false,
	});

	const readAttendancePermissionResource = createResource({
		url: "arijentek_core.api.attendance.can_read_attendance",
		auto: false,
	});

	const editAttendancePermissionResource = createResource({
		url: "arijentek_core.api.attendance.can_edit_attendance",
		auto: false,
	});

	const deleteAttendancePermissionResource = createResource({
		url: "arijentek_core.api.attendance.can_delete_attendance",
		auto: false,
	});

	const createEmployeeCheckinPermissionResource = createResource({
		url: "arijentek_core.api.attendance.can_create_employee_checkin",
		auto: false,
	});

	const readEmployeeCheckinPermissionResource = createResource({
		url: "arijentek_core.api.attendance.can_read_employee_checkin",
		auto: false,
	});

	const editEmployeeCheckinPermissionResource = createResource({
		url: "arijentek_core.api.attendance.can_edit_employee_checkin",
		auto: false,
	});

	const deleteEmployeeCheckinPermissionResource = createResource({
		url: "arijentek_core.api.attendance.can_delete_employee_checkin",
		auto: false,
	});

	const createAttendanceRequestPermissionResource = createResource({
		url: "arijentek_core.api.attendance.can_create_attendance_request",
		auto: false,
	});

	const readAttendanceRequestPermissionResource = createResource({
		url: "arijentek_core.api.attendance.can_read_attendance_request",
		auto: false,
	});

	const editAttendanceRequestPermissionResource = createResource({
		url: "arijentek_core.api.attendance.can_edit_attendance_request",
		auto: false,
	});

	const deleteAttendanceRequestPermissionResource = createResource({
		url: "arijentek_core.api.attendance.can_delete_attendance_request",
		auto: false,
	});

	const submitAttendanceRequestPermissionResource = createResource({
		url: "arijentek_core.api.attendance.can_submit_attendance_request",
		auto: false,
	});

	const createTimesheetPermissionResource = createResource({
		url: "arijentek_core.api.attendance.can_create_timesheet",
		auto: false,
	});

	const readTimesheetPermissionResource = createResource({
		url: "arijentek_core.api.attendance.can_read_timesheet",
		auto: false,
	});

	const editTimesheetPermissionResource = createResource({
		url: "arijentek_core.api.attendance.can_edit_timesheet",
		auto: false,
	});

	const deleteTimesheetPermissionResource = createResource({
		url: "arijentek_core.api.attendance.can_delete_timesheet",
		auto: false,
	});

	async function loadPermissions(consolidatedPerms = null) {
		let perms = consolidatedPerms;
		if (!perms) {
			try {
				const res = await fetch("/api/method/arijentek_core.api.dashboard.get_all_portal_permissions");
				const json = await res.json();
				perms = json.message?.attendance;
			} catch (err) {
				console.error("Failed to load attendance permissions:", err);
			}
		}
		if (perms) {
			createAttendancePermissionResource.data = perms.can_create_attendance;
			readAttendancePermissionResource.data = perms.can_read_attendance;
			editAttendancePermissionResource.data = perms.can_edit_attendance;
			deleteAttendancePermissionResource.data = perms.can_delete_attendance;
			createEmployeeCheckinPermissionResource.data = perms.can_create_employee_checkin;
			readEmployeeCheckinPermissionResource.data = perms.can_read_employee_checkin;
			editEmployeeCheckinPermissionResource.data = perms.can_edit_employee_checkin;
			deleteEmployeeCheckinPermissionResource.data = perms.can_delete_employee_checkin;
			createAttendanceRequestPermissionResource.data = perms.can_create_attendance_request;
			readAttendanceRequestPermissionResource.data = perms.can_read_attendance_request;
			editAttendanceRequestPermissionResource.data = perms.can_edit_attendance_request;
			deleteAttendanceRequestPermissionResource.data = perms.can_delete_attendance_request;
			submitAttendanceRequestPermissionResource.data = perms.can_submit_attendance_request;
			createTimesheetPermissionResource.data = perms.can_create_timesheet;
			readTimesheetPermissionResource.data = perms.can_read_timesheet;
			editTimesheetPermissionResource.data = perms.can_edit_timesheet;
			deleteTimesheetPermissionResource.data = perms.can_delete_timesheet;
		}
	}

	return {
		createAttendancePermissionResource,
		readAttendancePermissionResource,
		editAttendancePermissionResource,
		deleteAttendancePermissionResource,
		createEmployeeCheckinPermissionResource,
		readEmployeeCheckinPermissionResource,
		editEmployeeCheckinPermissionResource,
		deleteEmployeeCheckinPermissionResource,
		createAttendanceRequestPermissionResource,
		readAttendanceRequestPermissionResource,
		editAttendanceRequestPermissionResource,
		deleteAttendanceRequestPermissionResource,
		submitAttendanceRequestPermissionResource,
		createTimesheetPermissionResource,
		readTimesheetPermissionResource,
		editTimesheetPermissionResource,
		deleteTimesheetPermissionResource,
		todayStatus,
		roster,
		history,
		historyTotal,
		loading,
		error,
		workedSecondsToday,
		employeeId,
		isCheckedIn,
		isOnBreak,
		totalHoursToday,
		totalSecondsToday,
		overtimeHours,
		workingHoursTarget,
		shiftComplete,
		isDayCompleted,
		canManageBreak,
		timerLabel,
		formattedWorkedTime,
		employeeList,
		monthlyRoster,
		fetchTodayStatus,
		fetchRoster,
		fetchHistory,
		fetchEmployeeList,
		fetchMonthlyRoster,
		checkCanMarkAttendance,
		checkCanManageAttendance,
		checkCanViewAttendance,
		checkCanDeleteCheckin,
		markAttendance,
		clockIn,
		clockOut,
		startBreak,
		endBreak,
		init,
		syncTimerFromStatus,
		loadPermissions,
	};
});

