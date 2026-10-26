<template>
	<Dialog :options="{ size: '7xl', title: 'BulkLeaveDialog' }" v-model="show">
		<template #body>
			<div class="modal-panel">
				<!-- Custom Header -->
				<header class="modal-header">
					<div>
						<h3 class="modal-title">
							Bulk leave policy assignment
						</h3>
						<p class="text-[12px] text-[#656A72] dark:text-white/60">
							Assign leave policies to multiple employees
						</p>
					</div>
					<button @click="show = false" class="btn-icon-ghost shrink-0" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span>
					</button>
				</header>

				<!-- Main Content -->
				<div class="p-6 overflow-y-hidden flex-1 flex flex-col md:flex-row gap-6">
					
					<!-- Left Side: Config and Filters -->
					<div class="flex flex-col gap-6 w-full md:w-1/3 shrink-0 overflow-y-auto pb-4 pr-2">
						<!-- Config Section -->
						<div class="flex flex-col gap-4 bg-black/[0.02] dark:bg-white/[0.04] p-4 rounded-[12px] border border-black/[0.07] dark:border-white/10">
							<div>
								<label class="field-label">Leave period <span class="text-red-500 dark:text-red-400">*</span></label>
								<div class="flex gap-2">
									<SearchableDropdown
										v-model="bulkForm.leave_period"
										:options="activeLeavePeriods"
										label-key="name"
										value-key="name"
										placeholder="Select leave period"
										class="flex-1"
									/>
									<button
										v-if="leaveStore.canCreateLeavePeriod"
										@click="emit('create-leave-period')"
										class="btn-icon-ghost shrink-0"
										aria-label="Create new leave period"
										type="button"
									>
										<span class="material-symbols-outlined !text-[18px]">add</span>
									</button>
								</div>
							</div>
							<div>
								<label class="field-label">Leave policy <span class="text-red-500 dark:text-red-400">*</span></label>
								<div class="flex gap-2">
									<SearchableDropdown
										v-model="bulkForm.leave_policy"
										:options="formattedLeavePolicies"
										label-key="_display_label"
										value-key="name"
										placeholder="Select leave policy"
										class="flex-1"
									/>
									<button
										v-if="leaveStore.canCreateLeavePolicy"
										@click="emit('create-leave-policy')"
										class="btn-icon-ghost shrink-0"
										aria-label="Create new leave policy"
										type="button"
									>
										<span class="material-symbols-outlined !text-[18px]">add</span>
									</button>
								</div>
							</div>
						</div>

						<!-- Filters Section -->
						<div class="flex flex-col gap-4">
							<div class="relative">
								<label class="field-label">Search employee</label>
								<input type="text" v-model="employeeSearchQuery" placeholder="Name or ID..." class="field-input">
							</div>
							<div class="relative">
								<label class="field-label">Filter department</label>
								<SearchableDropdown
									v-model="bulkFilters.department"
									:options="filterData.departments"
									placeholder="Department..."
									show-all-option
									all-option-label="All departments"
								/>
							</div>
							<div class="relative">
								<label class="field-label">Filter designation</label>
								<SearchableDropdown
									v-model="bulkFilters.designation"
									:options="filterData.designations"
									placeholder="Designation..."
									show-all-option
									all-option-label="All designations"
								/>
							</div>
							<div class="relative">
								<label class="field-label">Filter branch</label>
								<SearchableDropdown
									v-model="bulkFilters.branch"
									:options="filterData.branches"
									placeholder="Branch..."
									show-all-option
									all-option-label="All Branches"
								/>
							</div>
							<div class="relative">
								<label class="field-label">Employment type</label>
								<SearchableDropdown
									v-model="bulkFilters.employment_type"
									:options="filterData.employmentTypes"
									placeholder="Employment Type..."
									show-all-option
									all-option-label="All Employment Types"
								/>
							</div>
						</div>
					</div>
					
					<!-- Right Side: Employee Table -->
					<div class="flex-1 flex flex-col overflow-hidden">
						<div v-if="loadingEmployees" class="flex justify-center py-10 text-[#656A72] dark:text-white/55 text-sm font-semibold">
							Loading Employees...
						</div>
						<div v-else-if="!bulkForm.leave_period" class="flex justify-center py-10 text-[#656A72] dark:text-white/55 text-sm font-semibold">
							Please select a Leave Period first.
						</div>
						<div v-else-if="filteredEmployeeList.length === 0" class="flex justify-center py-10 text-[#656A72] dark:text-white/55 text-sm font-semibold">
							No employees found matching the current filters.
						</div>
						<div v-else class="overflow-x-auto border border-black/[0.07] dark:border-white/10 rounded-[12px] flex-1 overflow-y-auto h-full">
							<table class="w-full text-left relative">
								<thead class="sticky top-0 border-b border-black/[0.07] dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.06] backdrop-blur z-10 shadow-sm">
									<tr>
										<th class="px-4 py-3 text-center w-12">
											<input type="checkbox" @change="toggleAllEmployees" :checked="selectedEmployees.length === filteredEmployeeList.length && filteredEmployeeList.length > 0" class="rounded border-black/[0.09] text-accent dark:text-accent-light focus:ring-accent/20 h-4 w-4 bg-white dark:bg-white/[0.06] border cursor-pointer" />
										</th>
										<th class="table-th">Employee</th>
										<th class="table-th">Department</th>
										<th class="table-th">Designation</th>
										<th class="table-th">Branch</th>
									</tr>
								</thead>
								<tbody class="divide-y divide-black/[0.05] dark:divide-white/[0.06]">
									<tr v-for="emp in filteredEmployeeList" :key="emp.name" class="hover:bg-black/[0.03] dark:hover:bg-white/[0.06] transition-colors">
										<td class="px-4 py-3 text-center">
											<input type="checkbox" :value="emp.name" v-model="selectedEmployees" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40" />
										</td>
										<td class="px-4 py-3 text-sm font-semibold text-[#17181B] dark:text-white">{{ emp.employee_name }}</td>
										<td class="px-4 py-3 text-xs text-[#5C6169] dark:text-white/65">{{ emp.department || '-' }}</td>
										<td class="px-4 py-3 text-xs text-[#5C6169] dark:text-white/65">{{ emp.designation || '-' }}</td>
										<td class="px-4 py-3 text-xs text-[#5C6169] dark:text-white/65">{{ emp.branch || '-' }}</td>
									</tr>
								</tbody>
							</table>
						</div>
					</div>

				</div>

				<!-- Actions -->
				<div class="px-5 py-4 border-t border-black/[0.06] dark:border-white/[0.08] shrink-0">
					<div v-if="submitError" class="p-3 mb-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-[12px] flex items-start gap-3">
						<span class="material-symbols-outlined text-red-500 dark:text-red-400 shrink-0">error</span>
						<p class="text-sm font-medium text-red-800 dark:text-red-200" v-html="submitError"></p>
					</div>
					
					<div class="flex items-center justify-between w-full">
						<div class="text-xs font-semibold text-[#5C6169] dark:text-white/65">{{ selectedEmployees.length }} selected</div>
						<div class="flex items-center gap-3">
							<button @click="show = false" :disabled="submitting" class="btn-secondary">
								Cancel
							</button>
							<button @click="handleSave" :disabled="submitting || selectedEmployees.length === 0 || !bulkForm.leave_policy" class="btn-primary">
								<span v-if="submitting" class="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></span>
								Assign Policies
							</button>
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { Dialog, call } from "frappe-ui";
import { useLeaveStore } from "../../../stores/leave";
import { getErrorMessage } from "../../../utils";
import SearchableDropdown from "../../../components/SearchableDropdown.vue";

const leaveStore = useLeaveStore();

const props = defineProps({
	modelValue: {
		type: Boolean,
		default: false,
	},
});

const emit = defineEmits(["update:modelValue", "save", "create-leave-policy", "create-leave-period"]);

const show = computed({
	get: () => props.modelValue,
	set: (val) => emit("update:modelValue", val),
});

const bulkForm = ref({
	leave_period: "",
	leave_policy: "",
	assignment_based_on: "Leave Period"
});

const bulkFilters = ref({
	department: "",
	designation: "",
	branch: "",
	employment_type: ""
});

const employeeSearchQuery = ref("");

const formattedLeavePolicies = computed(() => {
	return leaveStore.leavePolicies.map(p => ({
		...p,
		_display_label: p.title || p.name
	}));
});

const activeLeavePeriods = computed(() => {
	return leaveStore.leavePeriods.filter((lp) => lp.is_active);
});

const filterData = ref({
	departments: [],
	designations: [],
	branches: [],
	employmentTypes: []
});

const employeeList = ref([]);

const filteredEmployeeList = computed(() => {
	if (!employeeSearchQuery.value) return employeeList.value;
	const query = employeeSearchQuery.value.toLowerCase();
	return employeeList.value.filter(emp => {
		const nameMatch = emp.employee_name && emp.employee_name.toLowerCase().includes(query);
		const idMatch = emp.name && emp.name.toLowerCase().includes(query);
		return nameMatch || idMatch;
	});
});

const selectedEmployees = ref([]);
const loadingEmployees = ref(false);
const submitting = ref(false);
const submitError = ref("");

async function fetchFilterData() {
	try {
		const [deptRes, desigRes, branchRes, empTypeRes] = await Promise.all([
			call("arijentek_core.api.teams_permissons.get_departments"),
			call("arijentek_core.api.teams_permissons.get_designations"),
			call("arijentek_core.api.teams_permissons.get_branches"),
			call("arijentek_core.api.teams_permissons.get_employment_types")
		]);
		filterData.value.departments = deptRes || [];
		filterData.value.designations = desigRes || [];
		filterData.value.branches = branchRes || [];
		filterData.value.employmentTypes = empTypeRes || [];
	} catch (e) {
		console.error("Failed to load filter data", e);
	}
}

async function fetchEmployees() {
	if (!bulkForm.value.leave_period) return;
	loadingEmployees.value = true;
	try {
		const res = await call("arijentek_core.api.leave.get_employee_list_for_leave", {
			department: bulkFilters.value.department || "",
			designation: bulkFilters.value.designation || "",
			branch: bulkFilters.value.branch || "",
			employment_type: bulkFilters.value.employment_type || "",
			leave_period: bulkForm.value.leave_period,
			exclude_has_leave_policy_for_period: true
		});
		employeeList.value = res || [];
		selectedEmployees.value = []; // reset selection
	} catch (err) {
		console.error("Failed to fetch employees", err);
	} finally {
		loadingEmployees.value = false;
	}
}

watch(bulkFilters, () => {
	fetchEmployees();
}, { deep: true });

watch(() => bulkForm.value.leave_period, () => {
	fetchEmployees();
});

watch(show, (newVal) => {
	if (newVal) {
		submitError.value = "";
		selectedEmployees.value = [];
		if (filterData.value.departments.length === 0) {
			fetchFilterData();
		}
		if (!leaveStore.leavePolicies.length) {
			leaveStore.fetchLeavePolicies();
		}
		if (!leaveStore.leavePeriods.length) {
			leaveStore.fetchLeavePeriods();
		}
		fetchEmployees();
	}
});

function toggleAllEmployees(e) {
	if (e.target.checked) {
		selectedEmployees.value = filteredEmployeeList.value.map(emp => emp.name);
	} else {
		selectedEmployees.value = [];
	}
}

const handleSave = async () => {
	if (submitting.value) return;
	submitError.value = "";
	if (selectedEmployees.value.length === 0) return;
	
	submitting.value = true;
	try {
		const res = await call("arijentek_core.api.leave.bulk_save_leave_policy_assignment", {
			employees: JSON.stringify(selectedEmployees.value),
			leave_policy: bulkForm.value.leave_policy,
			assignment_based_on: bulkForm.value.assignment_based_on,
			leave_period: bulkForm.value.leave_period
		});
		
		if (res && res.success === false) {
			submitError.value = res.error || "Failed to bulk assign leave policies";
		} else {
			emit("save");
			show.value = false;
		}
	} catch (err) {
		submitError.value = getErrorMessage(err, "Failed to save leave policy assignments");
	} finally {
		submitting.value = false;
	}
};
</script>

<style>
/* Push the dialog to the right so it doesn't hide behind the fixed left navbar */
@media (min-width: 1024px) {
	[data-dialog="BulkLeaveDialog"] > div {
		padding-left: 17rem !important; /* Clear the sidebar */
	}
}
</style>
