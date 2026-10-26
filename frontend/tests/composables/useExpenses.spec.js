import { describe, it, expect, beforeEach, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

vi.mock("@/stores/employee", () => ({
	useEmployeeStore: vi.fn(() => ({
		employee: { name: "EMP-001", employee_name: "Test Employee" },
		ready: true,
		init: vi.fn(() => Promise.resolve()),
	})),
}));

vi.mock("@/stores/expense", () => ({
	useExpenseStore: vi.fn(() => ({
		expenseClaims: [],
		expenseTypes: [],
		loading: false,
		init: vi.fn(() => Promise.resolve()),
	})),
}));

import { useExpenses } from "@/composables/useExpenses.js";

describe("useExpenses Composable", () => {
	beforeEach(() => {
		setActivePinia(createPinia());
		vi.clearAllMocks();
	});

	describe("Initial State", () => {
		it("showClaimModal defaults to false", () => {
			const { showClaimModal } = useExpenses();
			expect(showClaimModal.value).toBe(false);
		});

		it("activeFilter defaults to All", () => {
			const { activeFilter } = useExpenses();
			expect(activeFilter.value).toBe("All");
		});

		it("stats defaults to zeros", () => {
			const { stats } = useExpenses();
			expect(stats.value).toEqual({
				total_reimbursed: 0,
				pending_amount: 0,
				pending_count: 0,
			});
		});
	});

	describe("Filtered Claims", () => {
		it("returns all claims when filter is All", () => {
			const { filteredClaims, activeFilter } = useExpenses();
			expect(activeFilter.value).toBe("All");
			expect(filteredClaims.value.length).toBeGreaterThan(0);
		});

		it("filters claims by status", () => {
			const { filteredClaims, setFilter } = useExpenses();
			setFilter("Approved");
			expect(filteredClaims.value.every((c) => c.status === "Approved")).toBe(true);
		});

		it("returns pending claims when filter is Pending", () => {
			const { filteredClaims, setFilter } = useExpenses();
			setFilter("Pending");
			expect(filteredClaims.value.every((c) => c.status === "Pending")).toBe(true);
		});

		it("returns draft claims when filter is Draft", () => {
			const { filteredClaims, setFilter } = useExpenses();
			setFilter("Draft");
			expect(filteredClaims.value.every((c) => c.status === "Draft")).toBe(true);
		});

		it("returns rejected claims when filter is Rejected", () => {
			const { filteredClaims, setFilter } = useExpenses();
			setFilter("Rejected");
			expect(filteredClaims.value.every((c) => c.status === "Rejected")).toBe(true);
		});

		it("returns empty for non-existent status filter", () => {
			const { filteredClaims, setFilter } = useExpenses();
			setFilter("NonExistent");
			expect(filteredClaims.value).toEqual([]);
		});
	});

	describe("setFilter", () => {
		it("updates the active filter", () => {
			const { activeFilter, setFilter } = useExpenses();
			setFilter("Approved");
			expect(activeFilter.value).toBe("Approved");
		});

		it("can switch filters multiple times", () => {
			const { activeFilter, setFilter } = useExpenses();
			setFilter("Approved");
			expect(activeFilter.value).toBe("Approved");
			setFilter("Pending");
			expect(activeFilter.value).toBe("Pending");
			setFilter("All");
			expect(activeFilter.value).toBe("All");
		});
	});

	describe("getTypeIcon", () => {
		it("returns correct icon for Travel", () => {
			const { getTypeIcon } = useExpenses();
			expect(getTypeIcon("Travel")).toBe("directions_car");
		});

		it("returns correct icon for Food & Dining", () => {
			const { getTypeIcon } = useExpenses();
			expect(getTypeIcon("Food & Dining")).toBe("restaurant");
		});

		it("returns correct icon for Office Supplies", () => {
			const { getTypeIcon } = useExpenses();
			expect(getTypeIcon("Office Supplies")).toBe("inventory_2");
		});

		it("returns correct icon for Communication", () => {
			const { getTypeIcon } = useExpenses();
			expect(getTypeIcon("Communication")).toBe("settings_cell");
		});

		it("returns correct icon for Other", () => {
			const { getTypeIcon } = useExpenses();
			expect(getTypeIcon("Other")).toBe("payments");
		});

		it("returns receipt_long for unknown type", () => {
			const { getTypeIcon } = useExpenses();
			expect(getTypeIcon("UnknownType")).toBe("receipt_long");
		});
	});

	describe("getTypeColor", () => {
		it("returns correct color class for Travel", () => {
			const { getTypeColor } = useExpenses();
			expect(getTypeColor("Travel")).toBe("text-blue-400");
		});

		it("returns correct color class for Food & Dining", () => {
			const { getTypeColor } = useExpenses();
			expect(getTypeColor("Food & Dining")).toBe("text-orange-400");
		});

		it("returns correct color class for Office Supplies", () => {
			const { getTypeColor } = useExpenses();
			expect(getTypeColor("Office Supplies")).toBe("text-purple-400");
		});

		it("returns correct color class for Communication", () => {
			const { getTypeColor } = useExpenses();
			expect(getTypeColor("Communication")).toBe("text-green-400");
		});

		it("returns default color class for unknown type", () => {
			const { getTypeColor } = useExpenses();
			expect(getTypeColor("UnknownType")).toBe("text-gray-400");
		});
	});

	describe("formatCurrency", () => {
		it("formats amount in INR", () => {
			const { formatCurrency } = useExpenses();
			const result = formatCurrency(5400);
			expect(result).toContain("5,400");
		});

		it("formats zero amount", () => {
			const { formatCurrency } = useExpenses();
			const result = formatCurrency(0);
			expect(result).toBeTruthy();
		});

		it("formats large amounts with commas", () => {
			const { formatCurrency } = useExpenses();
			const result = formatCurrency(100000);
			expect(result).toContain("1,00,000");
		});
	});

	describe("initExpenses", () => {
		it("calls init without error", async () => {
			const { initExpenses } = useExpenses();
			await expect(initExpenses()).resolves.toBeUndefined();
		});
	});

	describe("Mock Claims Data", () => {
		it("has 4 mock claims", () => {
			const { filteredClaims } = useExpenses();
			expect(filteredClaims.value).toHaveLength(4);
		});

		it("mock claims have required fields", () => {
			const { filteredClaims } = useExpenses();
			filteredClaims.value.forEach((claim) => {
				expect(claim).toHaveProperty("name");
				expect(claim).toHaveProperty("expense_type");
				expect(claim).toHaveProperty("posting_date");
				expect(claim).toHaveProperty("total_claimed_amount");
				expect(claim).toHaveProperty("status");
			});
		});
	});
});
