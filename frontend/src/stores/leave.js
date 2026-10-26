import { defineStore } from "pinia";
import { createResource } from "frappe-ui";
import { ref, computed } from "vue";

export const useLeaveStore = defineStore("leave", () => {
	const leaveBalances = ref([]);
	const leaveApplications = ref([]);
	const leaveTypes = ref([]);
	const loading = ref(false);
	const employeeId = ref(null);
	const isApprover = ref(false);
	const isGlobalApprover = ref(false);
	const preventSelfApproval = ref(false);
	const approvedEmployeeList = ref([]);
	const employeeList = ref([]);
	const allLeaveTypesList = ref([]);
	const leavePolicies = ref([]);
	const leaveAllocations = ref([]);
	const leavePeriods = ref([]);
	const leavePolicyAssignments = ref([]);
	const countries = ref([]);
	const subdivisionsByCountry = ref({});
	const holidayLists = ref([]);

	// Permission flags
	const canRead = ref(false);
	const canCreate = ref(false);
	const canEdit = ref(false);
	const canDelete = ref(false);
	const canSubmit = ref(false);

	// Permission flags for Compensatory Leave
	const canReadCompLeave = ref(false);
	const canCreateCompLeave = ref(false);
	const canEditCompLeave = ref(false);
	const canDeleteCompLeave = ref(false);
	const canSubmitCompLeave = ref(false);

	// Permission flags for Leave Types
	const canReadLeaveTypes = ref(false);
	const canCreateLeaveTypes = ref(false);
	const canEditLeaveTypes = ref(false);
	const canDeleteLeaveTypes = ref(false);

	// Permission flags for Leave Policy
	const canReadLeavePolicy = ref(false);
	const canCreateLeavePolicy = ref(false);
	const canEditLeavePolicy = ref(false);
	const canDeleteLeavePolicy = ref(false);

	// Permission flags for Leave Allocation
	const canReadLeaveAllocation = ref(false);
	const canCreateLeaveAllocation = ref(false);
	const canEditLeaveAllocation = ref(false);
	const canDeleteLeaveAllocation = ref(false);

	// Permission flags for Leave Period
	const canReadLeavePeriod = ref(false);
	const canCreateLeavePeriod = ref(false);
	const canEditLeavePeriod = ref(false);
	const canDeleteLeavePeriod = ref(false);

	// Permission flags for Leave Policy Assignment
	const canReadLeavePolicyAssignment = ref(false);
	const canCreateLeavePolicyAssignment = ref(false);
	const canEditLeavePolicyAssignment = ref(false);
	const canDeleteLeavePolicyAssignment = ref(false);

	// Permission flags for Holiday List
	const canReadHolidayList = ref(false);
	const canCreateHolidayList = ref(false);
	const canEditHolidayList = ref(false);
	const canDeleteHolidayList = ref(false);

	// Permission flags for Holiday List Assignment
	const canReadHolidayListAssignment = ref(false);
	const canCreateHolidayListAssignment = ref(false);
	const canEditHolidayListAssignment = ref(false);
	const canDeleteHolidayListAssignment = ref(false);

	// Get supported countries
	const countriesResource = createResource({
		url: "arijentek_core.api.leave.get_supported_countries",
		auto: false,
		onSuccess(data) {
			if (data && data.countries) {
				countries.value = data.countries;
				subdivisionsByCountry.value = data.subdivisions_by_country;
			}
		},
		onError(err) {
			console.error('Failed to fetch countries:', err);
		}
	});

	// Get leave balance map from HRMS
	const leaveBalanceResource = createResource({
		url: "arijentek_core.api.leave.get_employee_leave_balance_map",
		auto: false,
		onSuccess(data) {
			if (data) {
				leaveBalances.value = Object.entries(data).map(([key, value]) => ({
					leave_type: key,
					...value,
				}));
			} else {
				leaveBalances.value = [];
			}
		},
	});

	// Get leave applications from HRMS
	const leaveApplicationsResource = createResource({
		url: "hrms.api.get_leave_applications",
		auto: false,
		onSuccess(data) {
			leaveApplications.value = data || [];
		},
	});

	const leaveApplicationsForAllResource = createResource({
		url: "arijentek_core.api.leave.get_leave_applications_for_all",
		auto: false,
		onSuccess(data) {
			leaveApplications.value = data || [];
		},
	});

	// Get leave types from HRMS
	const leaveTypesResource = createResource({
		url: "hrms.api.get_leave_types",
		auto: false,
		onSuccess(data) {
			if (data && Array.isArray(data)) {
				leaveTypes.value = data.map((name) => ({
					name: name,
					leave_type_name: name,
				}));
			} else {
				leaveTypes.value = [];
			}
		},

	});

	// Check if current user is a leave approver
	const approverCheckResource = createResource({
		url: "arijentek_core.api.leave.is_user_leave_approver",
		auto: false,
		onSuccess(data) {
			if (data && data.is_approver) {
				isApprover.value = true;
				isGlobalApprover.value = !!data.is_global_approver;
				preventSelfApproval.value = !!data.prevent_self_leave_approval;
				approvedEmployeeList.value = data.employees || [];
			} else {
				isApprover.value = false;
				isGlobalApprover.value = false;
				preventSelfApproval.value = false;
				approvedEmployeeList.value = [];
			}
		},
		onError(err) {
			console.error("Approver check failed:", err);
			isApprover.value = false;
			isGlobalApprover.value = false;
			preventSelfApproval.value = false;
			approvedEmployeeList.value = [];
		},
	});

	// Permission resources
	const canReadResource = createResource({
		url: "arijentek_core.api.leave.can_read_leave_application",
		auto: true,
		onSuccess(data) { canRead.value = !!data; },
	});
	const canCreateResource = createResource({
		url: "arijentek_core.api.leave.can_create_leave_application",
		auto: true,
		onSuccess(data) { canCreate.value = !!data; },
	});
	const canEditResource = createResource({
		url: "arijentek_core.api.leave.can_edit_leave_application",
		auto: true,
		onSuccess(data) { canEdit.value = !!data; },
	});
	const canDeleteResource = createResource({
		url: "arijentek_core.api.leave.can_delete_leave_application",
		auto: true,
		onSuccess(data) { canDelete.value = !!data; },
	});
	const canSubmitResource = createResource({
		url: "arijentek_core.api.leave.can_submit_leave_application",
		auto: true,
		onSuccess(data) { canSubmit.value = !!data; },
	});

	const canReadCompResource = createResource({
		url: "arijentek_core.api.leave.can_read_compensatory_leave_request",
		auto: true,
		onSuccess(data) { canReadCompLeave.value = !!data; },
	});
	const canCreateCompResource = createResource({
		url: "arijentek_core.api.leave.can_create_compensatory_leave_request",
		auto: true,
		onSuccess(data) { canCreateCompLeave.value = !!data; },
	});
	const canEditCompResource = createResource({
		url: "arijentek_core.api.leave.can_edit_compensatory_leave_request",
		auto: true,
		onSuccess(data) { canEditCompLeave.value = !!data; },
	});
	const canDeleteCompResource = createResource({
		url: "arijentek_core.api.leave.can_delete_compensatory_leave_request",
		auto: true,
		onSuccess(data) { canDeleteCompLeave.value = !!data; },
	});
	const canSubmitCompResource = createResource({
		url: "arijentek_core.api.leave.can_submit_compensatory_leave_request",
		auto: true,
		onSuccess(data) { canSubmitCompLeave.value = !!data; },
	});

	const canReadLeaveTypesResource = createResource({
		url: "arijentek_core.api.leave.can_read_leave_types",
		auto: true,
		onSuccess(data) { canReadLeaveTypes.value = !!data; },
	});
	const canCreateLeaveTypesResource = createResource({
		url: "arijentek_core.api.leave.can_create_leave_types",
		auto: true,
		onSuccess(data) { canCreateLeaveTypes.value = !!data; },
	});
	const canEditLeaveTypesResource = createResource({
		url: "arijentek_core.api.leave.can_edit_leave_types",
		auto: true,
		onSuccess(data) { canEditLeaveTypes.value = !!data; },
	});
	const canDeleteLeaveTypesResource = createResource({
		url: "arijentek_core.api.leave.can_delete_leave_types",
		auto: true,
		onSuccess(data) { canDeleteLeaveTypes.value = !!data; },
	});

	const canReadLeavePolicyResource = createResource({
		url: "arijentek_core.api.leave.can_read_leave_policy",
		auto: true,
		onSuccess(data) { canReadLeavePolicy.value = !!data; },
	});
	const canCreateLeavePolicyResource = createResource({
		url: "arijentek_core.api.leave.can_create_leave_policy",
		auto: true,
		onSuccess(data) { canCreateLeavePolicy.value = !!data; },
	});
	const canEditLeavePolicyResource = createResource({
		url: "arijentek_core.api.leave.can_edit_leave_policy",
		auto: true,
		onSuccess(data) { canEditLeavePolicy.value = !!data; },
	});
	const canDeleteLeavePolicyResource = createResource({
		url: "arijentek_core.api.leave.can_delete_leave_policy",
		auto: true,
		onSuccess(data) { canDeleteLeavePolicy.value = !!data; },
	});

	const canReadLeaveAllocationResource = createResource({
		url: "arijentek_core.api.leave.can_read_leave_allocation",
		auto: true,
		onSuccess(data) { canReadLeaveAllocation.value = !!data; },
	});
	const canCreateLeaveAllocationResource = createResource({
		url: "arijentek_core.api.leave.can_create_leave_allocation",
		auto: true,
		onSuccess(data) { canCreateLeaveAllocation.value = !!data; },
	});
	const canEditLeaveAllocationResource = createResource({
		url: "arijentek_core.api.leave.can_edit_leave_allocation",
		auto: true,
		onSuccess(data) { canEditLeaveAllocation.value = !!data; },
	});
	const canDeleteLeaveAllocationResource = createResource({
		url: "arijentek_core.api.leave.can_delete_leave_allocation",
		auto: true,
		onSuccess(data) { canDeleteLeaveAllocation.value = !!data; },
	});

	const canReadLeavePeriodResource = createResource({
		url: "arijentek_core.api.leave.can_read_leave_period",
		auto: true,
		onSuccess(data) { canReadLeavePeriod.value = !!data; },
	});
	const canCreateLeavePeriodResource = createResource({
		url: "arijentek_core.api.leave.can_create_leave_period",
		auto: true,
		onSuccess(data) { canCreateLeavePeriod.value = !!data; },
	});
	const canEditLeavePeriodResource = createResource({
		url: "arijentek_core.api.leave.can_edit_leave_period",
		auto: true,
		onSuccess(data) { canEditLeavePeriod.value = !!data; },
	});
	const canDeleteLeavePeriodResource = createResource({
		url: "arijentek_core.api.leave.can_delete_leave_period",
		auto: true,
		onSuccess(data) { canDeleteLeavePeriod.value = !!data; },
	});

	const canReadLeavePolicyAssignmentResource = createResource({
		url: "arijentek_core.api.leave.can_read_leave_policy_assignment",
		auto: true,
		onSuccess(data) { canReadLeavePolicyAssignment.value = !!data; },
	});
	const canCreateLeavePolicyAssignmentResource = createResource({
		url: "arijentek_core.api.leave.can_create_leave_policy_assignment",
		auto: true,
		onSuccess(data) { canCreateLeavePolicyAssignment.value = !!data; },
	});
	const canEditLeavePolicyAssignmentResource = createResource({
		url: "arijentek_core.api.leave.can_edit_leave_policy_assignment",
		auto: true,
		onSuccess(data) { canEditLeavePolicyAssignment.value = !!data; },
	});
	const canDeleteLeavePolicyAssignmentResource = createResource({
		url: "arijentek_core.api.leave.can_delete_leave_policy_assignment",
		auto: true,
		onSuccess(data) { canDeleteLeavePolicyAssignment.value = !!data; },
	});

	const canReadHolidayListResource = createResource({
		url: "arijentek_core.api.leave.can_read_holiday_list",
		auto: true,
		onSuccess(data) { canReadHolidayList.value = !!data; },
	});
	const canCreateHolidayListResource = createResource({
		url: "arijentek_core.api.leave.can_create_holiday_list",
		auto: true,
		onSuccess(data) { canCreateHolidayList.value = !!data; },
	});
	const canEditHolidayListResource = createResource({
		url: "arijentek_core.api.leave.can_edit_holiday_list",
		auto: true,
		onSuccess(data) { canEditHolidayList.value = !!data; },
	});
	const canDeleteHolidayListResource = createResource({
		url: "arijentek_core.api.leave.can_delete_holiday_list",
		auto: true,
		onSuccess(data) { canDeleteHolidayList.value = !!data; },
	});

	const canReadHolidayListAssignmentResource = createResource({
		url: "arijentek_core.api.leave.can_read_holiday_list_assignment",
		auto: true,
		onSuccess(data) { canReadHolidayListAssignment.value = !!data; },
	});
	const canCreateHolidayListAssignmentResource = createResource({
		url: "arijentek_core.api.leave.can_create_holiday_list_assignment",
		auto: true,
		onSuccess(data) { canCreateHolidayListAssignment.value = !!data; },
	});
	const canEditHolidayListAssignmentResource = createResource({
		url: "arijentek_core.api.leave.can_edit_holiday_list_assignment",
		auto: true,
		onSuccess(data) { canEditHolidayListAssignment.value = !!data; },
	});
	const canDeleteHolidayListAssignmentResource = createResource({
		url: "arijentek_core.api.leave.can_delete_holiday_list_assignment",
		auto: true,
		onSuccess(data) { canDeleteHolidayListAssignment.value = !!data; },
	});

	const leavePolicyAssignmentsResource = createResource({
		url: "arijentek_core.api.leave.get_leave_policy_assignments",
		auto: true,
		onSuccess(data) { leavePolicyAssignments.value = data || []; },
	});

	const employeeListResource = createResource({
		url: "arijentek_core.api.leave.get_employee_list_for_leave",
		auto: false,
		onSuccess(data) {
			employeeList.value = data || [];
		},
	});

	const allLeaveTypesListResource = createResource({
		url: "arijentek_core.api.leave.get_leave_types",
		auto: false,
		onSuccess(data) {
			allLeaveTypesList.value = data || [];
		},
	});

	const leavePoliciesResource = createResource({
		url: "arijentek_core.api.leave.get_leave_policy",
		auto: false,
		onSuccess(data) {
			leavePolicies.value = data || [];
		},
	});

	const leaveAllocationsResource = createResource({
		url: "arijentek_core.api.leave.get_leave_allocations",
		auto: false,
		onSuccess(data) {
			leaveAllocations.value = data || [];
		},
	});

	const leavePeriodsResource = createResource({
		url: "arijentek_core.api.leave.get_leave_periods",
		auto: false,
		onSuccess(data) {
			leavePeriods.value = data || [];
		},
	});

	const holidayListsResource = createResource({
		url: "arijentek_core.api.leave.get_holiday_list",
		auto: false,
		onSuccess(data) {
			holidayLists.value = data || [];
		},
	});

	// Computed
	const totalLeaveBalance = computed(() => {
		return leaveBalances.value.reduce((sum, lb) => sum + (lb.balance_leaves || 0), 0);
	});

	const pendingApplications = computed(() => {
		return leaveApplications.value.filter(
			(app) => app.status === "Open" || app.status === "Pending"
		);
	});

	const approvedApplications = computed(() => {
		return leaveApplications.value.filter((app) => app.status === "Approved");
	});

	// Actions
	async function fetchCountries() {
		await countriesResource.fetch();
	}

	async function fetchLeaveBalances(emp_id = null) {
		const targetEmployee = emp_id === null ? employeeId.value : emp_id;
		const params = {};
		if (targetEmployee) {
			params.employee = targetEmployee;
		}
		await leaveBalanceResource.fetch(params);
	}

	async function fetchLeaveApplications(emp_id = null, for_approval = false, approver_id = null) {
		const targetEmployee = emp_id === null ? employeeId.value : emp_id;
		const params = {};
		if (targetEmployee) {
			params.employee = targetEmployee;
		}
		if (for_approval) {
			params.for_approval = true;
			if (approver_id) {
				params.approver_id = approver_id;
			}
		}
		await leaveApplicationsResource.fetch(params);
	}

	async function fetchLeaveApplicationsForAll() {
		await leaveApplicationsForAllResource.fetch();
	}

	async function fetchLeaveTypes(emp_id = null) {
		const targetEmployee = emp_id || employeeId.value;
		if (!targetEmployee) return;
		const today = new Date().toISOString().split("T")[0];
		await leaveTypesResource.fetch({ employee: targetEmployee, date: today });
	}

	async function fetchEmployeeList() {
		return employeeListResource.fetch();
	}

	async function fetchAllLeaveTypes() {
		await allLeaveTypesListResource.fetch();
	}

	async function fetchLeavePolicies(search_text = "") {
		const params = {};
		if (search_text) {
			params.search_text = search_text;
		}
		await leavePoliciesResource.fetch(params);
	}

	async function fetchLeaveAllocations(search_text = "") {
		const params = {};
		if (search_text) {
			params.search_text = search_text;
		}
		await leaveAllocationsResource.fetch(params);
	}

	async function fetchLeavePeriods(search_text = "") {
		const params = {};
		if (search_text) {
			params.search_text = search_text;
		}
		await leavePeriodsResource.fetch(params);
	}

	async function fetchLeavePolicyAssignments(search_text = "") {
		const params = {};
		if (search_text) {
			params.search_text = search_text;
		}
		await leavePolicyAssignmentsResource.fetch(params);
	}

	async function fetchHolidayLists(search_text = "") {
		const params = {};
		if (search_text) {
			params.search_text = search_text;
		}
		await holidayListsResource.fetch(params);
	}

	async function checkApproverStatus() {
		await approverCheckResource.fetch();
	}

	function init(empId) {
		employeeId.value = empId;
		fetchLeaveBalances();
		fetchLeaveApplications();
		fetchLeaveTypes();
		checkApproverStatus();
	}

	function canApproveLeave(appEmployee) {
		if (!isApprover.value) return false;
		if (isGlobalApprover.value) return true;
		if (!approvedEmployeeList.value.some(e => e.name === appEmployee)) return false;
		if (preventSelfApproval.value && employeeId.value === appEmployee) return false;
		return true;
	}

	function canEditLeaveApplication(app) {
		return app.status === 'Open';
	}

	function canDeleteLeaveApplication(app) {
		return app.status === 'Open';
	}

	function canApproveOrRejectLeaveApplication(app) {
		return app.status === 'Open' && (canApproveLeave(app.employee) || canSubmit.value);
	}

	function canDeleteApprovedRejectedLeaveApplication(app) {
		return (app.status === 'Approved' || app.status === 'Rejected') && (canApproveLeave(app.employee) || canSubmit.value);
	}

	return {
		leaveBalances,
		leaveApplications,
		leaveTypes,
		loading,
		isApprover,
		isGlobalApprover,
		preventSelfApproval,
		approvedEmployeeList,
		canRead,
		canCreate,
		canEdit,
		canDelete,
		canSubmit,
		canReadCompLeave,
		canCreateCompLeave,
		canEditCompLeave,
		canDeleteCompLeave,
		canSubmitCompLeave,
		canReadLeaveTypes,
		canCreateLeaveTypes,
		canEditLeaveTypes,
		canDeleteLeaveTypes,
		canReadLeavePolicy,
		canCreateLeavePolicy,
		canEditLeavePolicy,
		canDeleteLeavePolicy,
		canReadLeaveAllocation,
		canCreateLeaveAllocation,
		canEditLeaveAllocation,
		canDeleteLeaveAllocation,
		canReadLeavePeriod,
		canCreateLeavePeriod,
		canEditLeavePeriod,
		canDeleteLeavePeriod,
		canReadLeavePolicyAssignment,
		canCreateLeavePolicyAssignment,
		canEditLeavePolicyAssignment,
		canDeleteLeavePolicyAssignment,
		canReadHolidayList,
		canCreateHolidayList,
		canEditHolidayList,
		canDeleteHolidayList,
		canReadHolidayListAssignment,
		canCreateHolidayListAssignment,
		canEditHolidayListAssignment,
		canDeleteHolidayListAssignment,
		totalLeaveBalance,
		pendingApplications,
		approvedApplications,
		employeeList,
		allLeaveTypesList,
		leavePolicies,
		leaveAllocations,
		leavePeriods,
		leavePolicyAssignments,
		countries,
		subdivisionsByCountry,
		holidayLists,
		fetchLeaveBalances,
		fetchLeaveApplications,
		fetchLeaveApplicationsForAll,
		fetchLeaveTypes,
		fetchEmployeeList,
		fetchAllLeaveTypes,
		fetchLeavePolicies,
		fetchLeaveAllocations,
		fetchLeavePeriods,
		fetchLeavePolicyAssignments,
		fetchCountries,
		fetchHolidayLists,
		checkApproverStatus,
		init,
		canApproveLeave,
		canEditLeaveApplication,
		canDeleteLeaveApplication,
		canApproveOrRejectLeaveApplication,
		canDeleteApprovedRejectedLeaveApplication,
	};
});

