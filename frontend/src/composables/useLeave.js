/**
 * useLeave Composable
 *
 * Extracts leave management logic from LeaveView.vue
 * into a reusable composable for leave views.
 */
import { ref, computed } from "vue";
import { useLeaveStore } from "@/stores/leave";
import { useEmployeeStore } from "@/stores/employee";

export function useLeave() {
	const leaveStore = useLeaveStore();
	const employeeStore = useEmployeeStore();

	const showLeaveModal = ref(false);
	const activeFilter = ref("All");

	const leaveBalances = computed(() => leaveStore.leaveBalances);
	const leaveApplications = computed(() => leaveStore.leaveApplications);
	const leaveTypes = computed(() => leaveStore.leaveTypes);
	const totalLeaveBalance = computed(() => leaveStore.totalLeaveBalance);
	const pendingApplications = computed(() => leaveStore.pendingApplications);
	const approvedApplications = computed(() => leaveStore.approvedApplications);

	const filteredApplications = computed(() => {
		const apps = leaveApplications.value || [];
		if (activeFilter.value === "All") return apps;
		if (activeFilter.value === "Pending") return pendingApplications.value;
		if (activeFilter.value === "Approved") return approvedApplications.value;
		return apps;
	});

	const annualLeaveBalance = computed(() => {
		const annual = leaveBalances.value?.find(
			(b) =>
				b.leave_type?.toLowerCase().includes("annual") ||
				b.leave_type?.toLowerCase().includes("casual") ||
				b.leave_type?.toLowerCase().includes("privilege")
		);
		return annual?.balance || annual?.leaves || 0;
	});

	const sickLeaveBalance = computed(() => {
		const sick = leaveBalances.value?.find(
			(b) =>
				b.leave_type?.toLowerCase().includes("sick") ||
				b.leave_type?.toLowerCase().includes("medical")
		);
		return sick?.balance || sick?.leaves || 0;
	});

	const totalUsedDays = computed(() => {
		return (leaveApplications.value || [])
			.filter((a) => a.status === "Approved")
			.reduce((sum, a) => sum + (parseFloat(a.total_leave_days) || 0), 0);
	});

	const pendingCount = computed(() => pendingApplications.value?.length || 0);

	const leaveDatesForCalendar = computed(() => {
		return (leaveApplications.value || [])
			.filter((a) => a.status === "Approved")
			.flatMap((a) => {
				const dates = [];
				if (a.from_date) dates.push(a.from_date);
				if (a.to_date && a.to_date !== a.from_date) dates.push(a.to_date);
				return dates;
			});
	});

	function setFilter(filter) {
		activeFilter.value = filter;
	}

	async function initLeave() {
		await employeeStore.init();
		const employeeId = employeeStore.employee?.name;
		if (employeeId) {
			await leaveStore.init(employeeId);
		}
	}

	return {
		showLeaveModal,
		activeFilter,
		leaveBalances,
		leaveApplications,
		leaveTypes,
		totalLeaveBalance,
		pendingApplications,
		approvedApplications,
		filteredApplications,
		annualLeaveBalance,
		sickLeaveBalance,
		totalUsedDays,
		pendingCount,
		leaveDatesForCalendar,
		setFilter,
		initLeave,
	};
}
