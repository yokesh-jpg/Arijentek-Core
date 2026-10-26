import { defineStore } from "pinia";
import { createResource } from "frappe-ui";
import { ref, computed } from "vue";

export const usePayrollStore = defineStore("payroll", () => {
	const salarySlips = ref([]);
	const payrollSummary = ref(null);
	const myPayrollSummary = ref(null);
	const loading = ref(false);
	const selectedEmployeeId = ref(null);
	const employeeList = ref([]);

	// Permission flags for Salary Component
	const canReadSalaryComponent = ref(false);
	const canCreateSalaryComponent = ref(false);
	const canEditSalaryComponent = ref(false);
	const canDeleteSalaryComponent = ref(false);

	// Permission flags for Salary Structure
	const canReadSalaryStructure = ref(false);
	const canCreateSalaryStructure = ref(false);
	const canEditSalaryStructure = ref(false);
	const canDeleteSalaryStructure = ref(false);

	// Permission flags for Salary Structure Assignment
	const canReadSalaryStructureAssignment = ref(false);
	const canCreateSalaryStructureAssignment = ref(false);
	const canEditSalaryStructureAssignment = ref(false);
	const canDeleteSalaryStructureAssignment = ref(false);

	// Permission flags for Payroll Entry
	const canReadPayrollEntry = ref(false);
	const canCreatePayrollEntry = ref(false);
	const canEditPayrollEntry = ref(false);
	const canDeletePayrollEntry = ref(false);

	// Permission flags for Salary Slip
	const canReadSalarySlip = ref(false);
	const canCreateSalarySlip = ref(false);
	const canEditSalarySlip = ref(false);
	const canDeleteSalarySlip = ref(false);

	// Permission flags for Overtime Type
	const canReadOvertimeType = ref(false);
	const canCreateOvertimeType = ref(false);
	const canEditOvertimeType = ref(false);
	const canDeleteOvertimeType = ref(false);

	// Permission flags for Overtime Slip
	const canReadOvertimeSlip = ref(false);
	const canCreateOvertimeSlip = ref(false);
	const canEditOvertimeSlip = ref(false);
	const canDeleteOvertimeSlip = ref(false);

	// Permission flags for Additional Salary
	const canReadAdditionalSalary = ref(false);
	const canCreateAdditionalSalary = ref(false);
	const canEditAdditionalSalary = ref(false);
	const canDeleteAdditionalSalary = ref(false);

	// Get salary slips from HRMS via zevar_core API
	const salarySlipsResource = createResource({
		url: "arijentek_core.api.payroll.get_salary_slips",
		auto: false,
		onSuccess(data) {
			salarySlips.value = data || [];
		},
	});

	// Get payroll summary
	const payrollSummaryResource = createResource({
		url: "arijentek_core.api.payroll.get_payroll_summary",
		auto: false,
		onSuccess(data) {
			payrollSummary.value = data;
		},
	});

	// Get my payroll summary
	const myPayrollSummaryResource = createResource({
		url: "arijentek_core.api.payroll.get_payroll_summary",
		auto: false,
		onSuccess(data) {
			myPayrollSummary.value = data;
		},
	});

	// Get salary slip details
	const salarySlipDetailsResource = createResource({
		url: "arijentek_core.api.payroll.get_salary_slip_details",
		auto: false,
	});

	// Generate salary slip
	const generateMyPayslipResource = createResource({
		url: "arijentek_core.api.payroll.generate_my_payslip",
		auto: false,
	});

	// Permission check
	const canViewAllResource = createResource({
		url: "arijentek_core.api.payroll.can_view_all_payroll",
		auto: false,
	});

	const canReadSalaryComponentResource = createResource({
		url: "arijentek_core.api.payroll.can_read_salary_componants",
		auto: false,
		onSuccess(data) { canReadSalaryComponent.value = !!data; },
	});
	const canCreateSalaryComponentResource = createResource({
		url: "arijentek_core.api.payroll.can_create_salary_componants",
		auto: false,
		onSuccess(data) { canCreateSalaryComponent.value = !!data; },
	});
	const canEditSalaryComponentResource = createResource({
		url: "arijentek_core.api.payroll.can_edit_salary_componants",
		auto: false,
		onSuccess(data) { canEditSalaryComponent.value = !!data; },
	});
	const canDeleteSalaryComponentResource = createResource({
		url: "arijentek_core.api.payroll.can_delete_salary_componants",
		auto: false,
		onSuccess(data) { canDeleteSalaryComponent.value = !!data; },
	});

	const canReadSalaryStructureResource = createResource({
		url: "arijentek_core.api.payroll.can_read_salary_structure",
		auto: false,
		onSuccess(data) { canReadSalaryStructure.value = !!data; },
	});
	const canCreateSalaryStructureResource = createResource({
		url: "arijentek_core.api.payroll.can_create_salary_structure",
		auto: false,
		onSuccess(data) { canCreateSalaryStructure.value = !!data; },
	});
	const canEditSalaryStructureResource = createResource({
		url: "arijentek_core.api.payroll.can_edit_salary_structure",
		auto: false,
		onSuccess(data) { canEditSalaryStructure.value = !!data; },
	});
	const canDeleteSalaryStructureResource = createResource({
		url: "arijentek_core.api.payroll.can_delete_salary_structure",
		auto: false,
		onSuccess(data) { canDeleteSalaryStructure.value = !!data; },
	});

	const canReadSalaryStructureAssignmentResource = createResource({
		url: "arijentek_core.api.payroll.can_read_salary_structure_assignment",
		auto: false,
		onSuccess(data) { canReadSalaryStructureAssignment.value = !!data; },
	});
	const canCreateSalaryStructureAssignmentResource = createResource({
		url: "arijentek_core.api.payroll.can_create_salary_structure_assignment",
		auto: false,
		onSuccess(data) { canCreateSalaryStructureAssignment.value = !!data; },
	});
	const canEditSalaryStructureAssignmentResource = createResource({
		url: "arijentek_core.api.payroll.can_edit_salary_structure_assignment",
		auto: false,
		onSuccess(data) { canEditSalaryStructureAssignment.value = !!data; },
	});
	const canDeleteSalaryStructureAssignmentResource = createResource({
		url: "arijentek_core.api.payroll.can_delete_salary_structure_assignment",
		auto: false,
		onSuccess(data) { canDeleteSalaryStructureAssignment.value = !!data; },
	});

	const canReadPayrollEntryResource = createResource({
		url: "arijentek_core.api.payroll.can_read_payroll_entry",
		auto: false,
		onSuccess(data) { canReadPayrollEntry.value = !!data; },
	});
	const canCreatePayrollEntryResource = createResource({
		url: "arijentek_core.api.payroll.can_create_payroll_entry",
		auto: false,
		onSuccess(data) { canCreatePayrollEntry.value = !!data; },
	});
	const canEditPayrollEntryResource = createResource({
		url: "arijentek_core.api.payroll.can_edit_payroll_entry",
		auto: false,
		onSuccess(data) { canEditPayrollEntry.value = !!data; },
	});
	const canDeletePayrollEntryResource = createResource({
		url: "arijentek_core.api.payroll.can_delete_payroll_entry",
		auto: false,
		onSuccess(data) { canDeletePayrollEntry.value = !!data; },
	});

	const canReadSalarySlipResource = createResource({
		url: "arijentek_core.api.payroll.can_read_salary_slip",
		auto: false,
		onSuccess(data) { canReadSalarySlip.value = !!data; },
	});
	const canCreateSalarySlipResource = createResource({
		url: "arijentek_core.api.payroll.can_create_salary_slip",
		auto: false,
		onSuccess(data) { canCreateSalarySlip.value = !!data; },
	});
	const canEditSalarySlipResource = createResource({
		url: "arijentek_core.api.payroll.can_edit_salary_slip",
		auto: false,
		onSuccess(data) { canEditSalarySlip.value = !!data; },
	});
	const canDeleteSalarySlipResource = createResource({
		url: "arijentek_core.api.payroll.can_delete_salary_slip",
		auto: false,
		onSuccess(data) { canDeleteSalarySlip.value = !!data; },
	});

	const canReadOvertimeTypeResource = createResource({
		url: "arijentek_core.api.payroll.can_read_overtime_type",
		auto: false,
		onSuccess(data) { canReadOvertimeType.value = !!data; },
	});
	const canCreateOvertimeTypeResource = createResource({
		url: "arijentek_core.api.payroll.can_create_overtime_type",
		auto: false,
		onSuccess(data) { canCreateOvertimeType.value = !!data; },
	});
	const canEditOvertimeTypeResource = createResource({
		url: "arijentek_core.api.payroll.can_edit_overtime_type",
		auto: false,
		onSuccess(data) { canEditOvertimeType.value = !!data; },
	});
	const canDeleteOvertimeTypeResource = createResource({
		url: "arijentek_core.api.payroll.can_delete_overtime_type",
		auto: false,
		onSuccess(data) { canDeleteOvertimeType.value = !!data; },
	});

	const canReadOvertimeSlipResource = createResource({
		url: "arijentek_core.api.payroll.can_read_overtime_slip",
		auto: false,
		onSuccess(data) { canReadOvertimeSlip.value = !!data; },
	});
	const canCreateOvertimeSlipResource = createResource({
		url: "arijentek_core.api.payroll.can_create_overtime_slip",
		auto: false,
		onSuccess(data) { canCreateOvertimeSlip.value = !!data; },
	});
	const canEditOvertimeSlipResource = createResource({
		url: "arijentek_core.api.payroll.can_edit_overtime_slip",
		auto: false,
		onSuccess(data) { canEditOvertimeSlip.value = !!data; },
	});
	const canDeleteOvertimeSlipResource = createResource({
		url: "arijentek_core.api.payroll.can_delete_overtime_slip",
		auto: false,
		onSuccess(data) { canDeleteOvertimeSlip.value = !!data; },
	});

	const canReadAdditionalSalaryResource = createResource({
		url: "arijentek_core.api.payroll.can_read_additional_salary",
		auto: false,
		onSuccess(data) { canReadAdditionalSalary.value = !!data; },
	});
	const canCreateAdditionalSalaryResource = createResource({
		url: "arijentek_core.api.payroll.can_create_additional_salary",
		auto: false,
		onSuccess(data) { canCreateAdditionalSalary.value = !!data; },
	});
	const canEditAdditionalSalaryResource = createResource({
		url: "arijentek_core.api.payroll.can_edit_additional_salary",
		auto: false,
		onSuccess(data) { canEditAdditionalSalary.value = !!data; },
	});
	const canDeleteAdditionalSalaryResource = createResource({
		url: "arijentek_core.api.payroll.can_delete_additional_salary",
		auto: false,
		onSuccess(data) { canDeleteAdditionalSalary.value = !!data; },
	});

	// Employee list (secure core method)
	const employeeListResource = createResource({
		url: "arijentek_core.api.payroll.get_employee_list",
		auto: false,
		onSuccess(data) {
			employeeList.value = data || [];
		},
	});

	// Computed
	const latestSalarySlip = computed(() => {
		if (!salarySlips.value || salarySlips.value.length === 0) return null;
		return salarySlips.value[0];
	});

	const totalYTD = computed(() => {
		return payrollSummary.value?.total_net_pay || 0;
	});

	const totalEarningsYTD = computed(() => {
		return payrollSummary.value?.total_earnings || 0;
	});

	const totalDeductionsYTD = computed(() => {
		return payrollSummary.value?.total_deductions || 0;
	});

	const myTotalYTD = computed(() => {
		return myPayrollSummary.value?.total_net_pay || 0;
	});

	const myTotalEarningsYTD = computed(() => {
		return myPayrollSummary.value?.total_earnings || 0;
	});

	const myTotalDeductionsYTD = computed(() => {
		return myPayrollSummary.value?.total_deductions || 0;
	});

	const canViewAll = computed(() => {
		return canViewAllResource.data || false;
	});

	// Actions
	async function fetchSalarySlips(params = {}) {
		if (selectedEmployeeId.value) params.employee_id = selectedEmployeeId.value;
		await salarySlipsResource.fetch(params);
	}

	async function fetchPayrollSummary(params = {}) {
		if (selectedEmployeeId.value) params.employee_id = selectedEmployeeId.value;
		await payrollSummaryResource.fetch(params);
	}

	async function fetchMyPayrollSummary(params = {}) {
		await myPayrollSummaryResource.fetch(params);
	}

	async function fetchEmployeeList() {
		await employeeListResource.fetch();
	}

	async function getSlipDetails(slipName) {
		return await salarySlipDetailsResource.fetch({ slip_name: slipName });
	}

	async function generateMyPayslip(month, year) {
		return await generateMyPayslipResource.fetch({ month, year });
	}

	async function loadPermissions(consolidatedPerms = null) {
		let perms = consolidatedPerms;
		if (!perms) {
			try {
				const res = await fetch("/api/method/arijentek_core.api.dashboard.get_all_portal_permissions");
				const json = await res.json();
				perms = json.message?.payroll;
			} catch (err) {
				console.error("Failed to load payroll permissions:", err);
			}
		}
		if (perms) {
			canReadSalaryComponent.value = !!perms.can_read_salary_componants;
			canCreateSalaryComponent.value = !!perms.can_create_salary_componants;
			canEditSalaryComponent.value = !!perms.can_edit_salary_componants;
			canDeleteSalaryComponent.value = !!perms.can_delete_salary_componants;

			canReadSalaryStructure.value = !!perms.can_read_salary_structure;
			canCreateSalaryStructure.value = !!perms.can_create_salary_structure;
			canEditSalaryStructure.value = !!perms.can_edit_salary_structure;
			canDeleteSalaryStructure.value = !!perms.can_delete_salary_structure;

			canReadSalaryStructureAssignment.value = !!perms.can_read_salary_structure_assignment;
			canCreateSalaryStructureAssignment.value = !!perms.can_create_salary_structure_assignment;
			canEditSalaryStructureAssignment.value = !!perms.can_edit_salary_structure_assignment;
			canDeleteSalaryStructureAssignment.value = !!perms.can_delete_salary_structure_assignment;

			canReadPayrollEntry.value = !!perms.can_read_payroll_entry;
			canCreatePayrollEntry.value = !!perms.can_create_payroll_entry;
			canEditPayrollEntry.value = !!perms.can_edit_payroll_entry;
			canDeletePayrollEntry.value = !!perms.can_delete_payroll_entry;

			canReadSalarySlip.value = !!perms.can_read_salary_slip;
			canCreateSalarySlip.value = !!perms.can_create_salary_slip;
			canEditSalarySlip.value = !!perms.can_edit_salary_slip;
			canDeleteSalarySlip.value = !!perms.can_delete_salary_slip;

			canReadOvertimeType.value = !!perms.can_read_overtime_type;
			canCreateOvertimeType.value = !!perms.can_create_overtime_type;
			canEditOvertimeType.value = !!perms.can_edit_overtime_type;
			canDeleteOvertimeType.value = !!perms.can_delete_overtime_type;

			canReadOvertimeSlip.value = !!perms.can_read_overtime_slip;
			canCreateOvertimeSlip.value = !!perms.can_create_overtime_slip;
			canEditOvertimeSlip.value = !!perms.can_edit_overtime_slip;
			canDeleteOvertimeSlip.value = !!perms.can_delete_overtime_slip;

			canReadAdditionalSalary.value = !!perms.can_read_additional_salary || !!perms.can_read_employee_advance || true;
			canCreateAdditionalSalary.value = !!perms.can_create_additional_salary || !!perms.can_create_employee_advance || true;
			canEditAdditionalSalary.value = !!perms.can_edit_additional_salary || !!perms.can_edit_employee_advance || true;
			canDeleteAdditionalSalary.value = !!perms.can_delete_additional_salary || !!perms.can_delete_employee_advance || true;

			canViewAllResource.data = perms.can_view_all_payroll;
		}
	}

	async function checkPermissions() {
		await loadPermissions();
	}

	async function init(params = {}) {
		await checkPermissions();
		fetchSalarySlips(params);
		fetchPayrollSummary(params);
	}

	return {
		salarySlips,
		payrollSummary,
		myPayrollSummary,
		loading,
		selectedEmployeeId,
		employeeList,
		latestSalarySlip,
		totalYTD,
		totalEarningsYTD,
		totalDeductionsYTD,
		myTotalYTD,
		myTotalEarningsYTD,
		myTotalDeductionsYTD,
		canViewAll,
		canReadSalaryComponent,
		canCreateSalaryComponent,
		canEditSalaryComponent,
		canDeleteSalaryComponent,
		canReadSalaryStructure,
		canCreateSalaryStructure,
		canEditSalaryStructure,
		canDeleteSalaryStructure,
		canReadSalaryStructureAssignment,
		canCreateSalaryStructureAssignment,
		canEditSalaryStructureAssignment,
		canDeleteSalaryStructureAssignment,
		canReadPayrollEntry,
		canCreatePayrollEntry,
		canEditPayrollEntry,
		canDeletePayrollEntry,
		canReadSalarySlip,
		canCreateSalarySlip,
		canEditSalarySlip,
		canDeleteSalarySlip,
		canReadOvertimeType,
		canCreateOvertimeType,
		canEditOvertimeType,
		canDeleteOvertimeType,
		canReadOvertimeSlip,
		canCreateOvertimeSlip,
		canEditOvertimeSlip,
		canDeleteOvertimeSlip,
		canReadAdditionalSalary,
		canCreateAdditionalSalary,
		canEditAdditionalSalary,
		canDeleteAdditionalSalary,
		fetchSalarySlips,
		fetchPayrollSummary,
		fetchMyPayrollSummary,
		fetchEmployeeList,
		getSlipDetails,
		generateMyPayslip,
		checkPermissions,
		init,
		loadPermissions,
	};
});
