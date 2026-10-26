import { describe, it, expect, beforeEach, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

vi.mock("@/stores/employee", () => ({
	useEmployeeStore: vi.fn(() => ({
		employee: { name: "EMP-001", employee_name: "Test Employee" },
		ready: true,
		init: vi.fn(() => Promise.resolve()),
	})),
}));

vi.mock("@/stores/leave", () => ({
	useLeaveStore: vi.fn(() => ({
		leaveBalances: [
			{ leave_type: "Annual Leave", balance: 12, leaves: 12 },
			{ leave_type: "Sick Leave", balance: 5, leaves: 5 },
		],
		leaveApplications: [
			{
				name: "LEV-001",
				leave_type: "Annual Leave",
				status: "Approved",
				total_leave_days: 2,
				from_date: "2026-03-10",
				to_date: "2026-03-11",
			},
			{
				name: "LEV-002",
				leave_type: "Sick Leave",
				status: "Pending",
				total_leave_days: 1,
				from_date: "2026-04-01",
				to_date: "2026-04-01",
			},
			{
				name: "LEV-003",
				leave_type: "Annual Leave",
				status: "Approved",
				total_leave_days: 3,
				from_date: "2026-05-01",
				to_date: "2026-05-03",
			},
			{
				name: "LEV-004",
				leave_type: "Casual Leave",
				status: "Open",
				total_leave_days: 1,
				from_date: "2026-04-15",
				to_date: "2026-04-15",
			},
		],
		leaveTypes: ["Annual Leave", "Sick Leave", "Casual Leave"],
		totalLeaveBalance: 17,
		pendingApplications: [
			{ name: "LEV-002", status: "Pending" },
			{ name: "LEV-004", status: "Open" },
		],
		approvedApplications: [
			{ name: "LEV-001", status: "Approved" },
			{ name: "LEV-003", status: "Approved" },
		],
		init: vi.fn(() => Promise.resolve()),
	})),
}));

import { useLeave } from "@/composables/useLeave.js";

describe("useLeave Composable", () => {
	beforeEach(() => {
		setActivePinia(createPinia());
		vi.clearAllMocks();
	});

	describe("Initial State", () => {
		it("showLeaveModal defaults to false", () => {
			const { showLeaveModal } = useLeave();
			expect(showLeaveModal.value).toBe(false);
		});

		it("activeFilter defaults to All", () => {
			const { activeFilter } = useLeave();
			expect(activeFilter.value).toBe("All");
		});
	});

	describe("Leave Balances", () => {
		it("returns leave balances from store", () => {
			const { leaveBalances } = useLeave();
			expect(leaveBalances.value).toHaveLength(2);
		});

		it("calculates annual leave balance", () => {
			const { annualLeaveBalance } = useLeave();
			expect(annualLeaveBalance.value).toBe(12);
		});

		it("calculates sick leave balance", () => {
			const { sickLeaveBalance } = useLeave();
			expect(sickLeaveBalance.value).toBe(5);
		});

		it("returns total leave balance from store", () => {
			const { totalLeaveBalance } = useLeave();
			expect(totalLeaveBalance.value).toBe(17);
		});
	});

	describe("Leave Applications", () => {
		it("returns all applications from store", () => {
			const { leaveApplications } = useLeave();
			expect(leaveApplications.value).toHaveLength(4);
		});

		it("returns pending applications", () => {
			const { pendingApplications } = useLeave();
			expect(pendingApplications.value).toHaveLength(2);
		});

		it("returns approved applications", () => {
			const { approvedApplications } = useLeave();
			expect(approvedApplications.value).toHaveLength(2);
		});
	});

	describe("Filtered Applications", () => {
		it("returns all applications when filter is All", () => {
			const { filteredApplications } = useLeave();
			expect(filteredApplications.value).toHaveLength(4);
		});

		it("returns pending applications when filter is Pending", () => {
			const { filteredApplications, setFilter } = useLeave();
			setFilter("Pending");
			expect(filteredApplications.value).toHaveLength(2);
		});

		it("returns approved applications when filter is Approved", () => {
			const { filteredApplications, setFilter } = useLeave();
			setFilter("Approved");
			expect(filteredApplications.value).toHaveLength(2);
		});
	});

	describe("Total Used Days", () => {
		it("sums approved leave days", () => {
			const { totalUsedDays } = useLeave();
			expect(totalUsedDays.value).toBe(5);
		});
	});

	describe("Pending Count", () => {
		it("counts pending applications", () => {
			const { pendingCount } = useLeave();
			expect(pendingCount.value).toBe(2);
		});
	});

	describe("Leave Dates for Calendar", () => {
		it("extracts dates from approved leaves", () => {
			const { leaveDatesForCalendar } = useLeave();
			expect(leaveDatesForCalendar.value.length).toBeGreaterThan(0);
		});

		it("includes from_date of approved leaves", () => {
			const { leaveDatesForCalendar } = useLeave();
			expect(leaveDatesForCalendar.value).toContain("2026-03-10");
		});

		it("includes to_date when different from from_date", () => {
			const { leaveDatesForCalendar } = useLeave();
			expect(leaveDatesForCalendar.value).toContain("2026-03-11");
		});
	});

	describe("setFilter", () => {
		it("updates the active filter", () => {
			const { activeFilter, setFilter } = useLeave();
			setFilter("Approved");
			expect(activeFilter.value).toBe("Approved");
		});

		it("can switch filters", () => {
			const { activeFilter, setFilter } = useLeave();
			setFilter("Pending");
			expect(activeFilter.value).toBe("Pending");
			setFilter("All");
			expect(activeFilter.value).toBe("All");
		});
	});

	describe("initLeave", () => {
		it("calls init without error", async () => {
			const { initLeave } = useLeave();
			await expect(initLeave()).resolves.toBeUndefined();
		});
	});

	describe("Leave Types", () => {
		it("returns leave types from store", () => {
			const { leaveTypes } = useLeave();
			expect(leaveTypes.value).toHaveLength(3);
			expect(leaveTypes.value).toContain("Annual Leave");
		});
	});
});
