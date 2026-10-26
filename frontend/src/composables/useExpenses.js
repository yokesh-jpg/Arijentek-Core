/**
 * useExpenses Composable
 *
 * Extracts expense claim logic from ExpenseView.vue
 * into a reusable composable for expense views.
 */
import { ref, computed } from "vue";
import { useExpenseStore } from "@/stores/expense";
import { useEmployeeStore } from "@/stores/employee";

export function useExpenses() {
	const expenseStore = useExpenseStore();
	const employeeStore = useEmployeeStore();

	const showClaimModal = ref(false);
	const activeFilter = ref("All");

	const stats = ref({
		total_reimbursed: 0,
		pending_amount: 0,
		pending_count: 0,
	});

	const mockClaims = [
		{
			name: "EXP-2024-001",
			expense_type: "Travel",
			posting_date: "2024-03-10",
			total_claimed_amount: 5400,
			status: "Approved",
			description: "Client meeting in South Mumbai - Taxi and tolls",
		},
		{
			name: "EXP-2024-002",
			expense_type: "Food & Dining",
			posting_date: "2024-03-11",
			total_claimed_amount: 1250,
			status: "Pending",
			description: "Team lunch for project kickoff",
		},
		{
			name: "EXP-2024-003",
			expense_type: "Office Supplies",
			posting_date: "2024-03-12",
			total_claimed_amount: 850,
			status: "Draft",
			description: "Printer ink and paper reams",
		},
		{
			name: "EXP-2024-004",
			expense_type: "Communication",
			posting_date: "2024-03-05",
			total_claimed_amount: 1999,
			status: "Rejected",
			description: "Monthly broadband bill - personal usage",
		},
	];

	const filteredClaims = computed(() => {
		const claims =
			expenseStore.expenseClaims.length > 0 ? expenseStore.expenseClaims : mockClaims;
		if (activeFilter.value === "All") return claims;
		return claims.filter((c) => c.status === activeFilter.value);
	});

	function getTypeIcon(type) {
		const icons = {
			Travel: "directions_car",
			"Food & Dining": "restaurant",
			"Office Supplies": "inventory_2",
			Communication: "settings_cell",
			Other: "payments",
		};
		return icons[type] || "receipt_long";
	}

	function getTypeColor(type) {
		const colors = {
			Travel: "text-blue-400",
			"Food & Dining": "text-orange-400",
			"Office Supplies": "text-purple-400",
			Communication: "text-green-400",
			Other: "text-gray-400",
		};
		return colors[type] || "text-gray-400";
	}

	function formatCurrency(amount) {
		return new Intl.NumberFormat("en-IN", {
			style: "currency",
			currency: "INR",
			maximumFractionDigits: 0,
		}).format(amount);
	}

	function setFilter(filter) {
		activeFilter.value = filter;
	}

	async function initExpenses() {
		await employeeStore.init();
		const employeeId = employeeStore.employee?.name;
		if (employeeId) {
			await expenseStore.init(employeeId);
		}
	}

	return {
		showClaimModal,
		activeFilter,
		stats,
		filteredClaims,
		getTypeIcon,
		getTypeColor,
		formatCurrency,
		setFilter,
		initExpenses,
	};
}
