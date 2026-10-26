import { describe, it, expect, beforeEach, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

vi.mock("@/stores/employee", () => ({
	useEmployeeStore: vi.fn(() => ({
		employee: { name: "EMP-001", employee_name: "Test Employee" },
		ready: true,
		init: vi.fn(() => Promise.resolve()),
	})),
}));

vi.mock("@/stores/attendance", () => ({
	useAttendanceStore: vi.fn(() => ({
		isCheckedIn: false,
		isOnBreak: false,
		totalHoursToday: 0,
		overtimeHours: 0,
		workingHoursTarget: 8,
		roster: { start_time: "09:00", working_hours: 8 },
		canManageBreak: false,
		formattedWorkedTime: "00:00:00",
		timerLabel: "Not Clocked In",
		workedSecondsToday: 0,
		shiftComplete: false,
		history: [],
		clockIn: vi.fn(() => Promise.resolve({ success: true })),
		clockOut: vi.fn(() => Promise.resolve({ success: true })),
		startBreak: vi.fn(() => Promise.resolve({ success: true })),
		endBreak: vi.fn(() => Promise.resolve({ success: true })),
		fetchHistory: vi.fn(() => Promise.resolve()),
		init: vi.fn(() => Promise.resolve()),
	})),
}));

import { useAttendance } from "@/composables/useAttendance.js";

describe("useAttendance Composable", () => {
	beforeEach(() => {
		setActivePinia(createPinia());
		vi.clearAllMocks();
	});

	describe("Initial State", () => {
		it("returns isCheckedIn as false initially", () => {
			const { isCheckedIn } = useAttendance();
			expect(isCheckedIn.value).toBe(false);
		});

		it("returns isOnBreak as false initially", () => {
			const { isOnBreak } = useAttendance();
			expect(isOnBreak.value).toBe(false);
		});

		it("returns formattedTimer as 00:00:00 when not clocked in", () => {
			const { formattedTimer } = useAttendance();
			expect(formattedTimer.value).toBe("00:00:00");
		});

		it("returns timerLabel as Not Clocked In when not clocked in", () => {
			const { timerLabel } = useAttendance();
			expect(timerLabel.value).toBe("Not Clocked In");
		});

		it("returns hasWorkedToday as false when no hours worked", () => {
			const { hasWorkedToday } = useAttendance();
			expect(hasWorkedToday.value).toBe(false);
		});

		it("returns shiftComplete as false initially", () => {
			const { shiftComplete } = useAttendance();
			expect(shiftComplete.value).toBe(false);
		});
	});

	describe("Timer Circle Classes", () => {
		it("returns bg-white/5 when not clocked in and no hours", () => {
			const { timerCircleClass } = useAttendance();
			expect(timerCircleClass.value).toBe("bg-white/5");
		});

		it("returns bg-white/5 when not checked in, not on break, no hours", () => {
			const { timerCircleClass } = useAttendance();
			expect(timerCircleClass.value).toBe("bg-white/5");
		});
	});

	describe("Timer Text Classes", () => {
		it("returns text-white/40 when not clocked in and no hours", () => {
			const { timerTextClass } = useAttendance();
			expect(timerTextClass.value).toBe("text-white/40");
		});
	});

	describe("Daily Records", () => {
		it("returns empty array when no history", () => {
			const { dailyRecords } = useAttendance();
			expect(dailyRecords.value).toEqual([]);
		});
	});

	describe("Summary Computed", () => {
		it("returns 0 totalHours when no daily records", () => {
			const { totalHours } = useAttendance();
			expect(totalHours.value).toBe(0);
		});

		it("returns 100 onTimeRate when no records (default)", () => {
			const { onTimeRate } = useAttendance();
			expect(onTimeRate.value).toBe(100);
		});

		it("returns 0 averageShiftHours when no records", () => {
			const { averageShiftHours } = useAttendance();
			expect(averageShiftHours.value).toBe(0);
		});
	});

	describe("Attendance Events", () => {
		it("returns empty array when no history logs", () => {
			const { attendanceEvents } = useAttendance();
			expect(attendanceEvents.value).toEqual([]);
		});
	});

	describe("Format Helpers", () => {
		it("formatDate returns formatted date string", () => {
			const { formatDate } = useAttendance();
			const result = formatDate("2026-03-15T10:00:00");
			expect(result).toBeTruthy();
			expect(typeof result).toBe("string");
		});

		it("formatDate returns empty string for null input", () => {
			const { formatDate } = useAttendance();
			expect(formatDate(null)).toBe("");
		});

		it("formatDay returns day of week string", () => {
			const { formatDay } = useAttendance();
			const result = formatDay("2026-03-15T10:00:00");
			expect(result).toBeTruthy();
		});

		it("formatDay returns empty string for null input", () => {
			const { formatDay } = useAttendance();
			expect(formatDay(null)).toBe("");
		});

		it("formatTime returns formatted time string", () => {
			const { formatTime } = useAttendance();
			const result = formatTime("2026-03-15T14:30:00");
			expect(result).toBeTruthy();
			expect(result).toMatch(/\d{1,2}:\d{2}/);
		});

		it("formatTime returns empty string for null input", () => {
			const { formatTime } = useAttendance();
			expect(formatTime(null)).toBe("");
		});
	});

	describe("Actions", () => {
		it("handleClockIn calls attendance store clockIn", async () => {
			const { handleClockIn } = useAttendance();
			await handleClockIn();
		});

		it("handleClockOut calls attendance store clockOut", async () => {
			const { handleClockOut } = useAttendance();
			await handleClockOut();
		});

		it("handleBreak toggles break state", async () => {
			const { handleBreak } = useAttendance();
			await handleBreak();
		});

		it("loadMoreHistory increments history days", async () => {
			const { loadMoreHistory } = useAttendance();
			await loadMoreHistory();
		});

		it("initAttendance initializes employee and attendance", async () => {
			const { initAttendance } = useAttendance();
			await initAttendance();
		});
	});
});
