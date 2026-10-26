<template>
	<Dialog :options="{ size: 'md' }" v-model="show">
		<template #body>
			<div
			 class="modal-panel"
			>
				<!-- Custom Header -->
				<header class="modal-header">
					<div>
						<h3 class="modal-title">
							{{
								editId
									? "Edit Leave Policy Assignment"
									: "Add New Leave Policy Assignment"
							}}
						</h3>
						<p class="text-[12px] text-[#656A72] dark:text-white/60">
							{{ editId ? editId : "Fill in the assignment details below" }}
						</p>
					</div>
					<button
						@click="show = false"
					 class="btn-icon-ghost shrink-0"
					 aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span>
					</button>
				</header>

				<!-- Main Content -->
				<div class="p-6 overflow-visible min-h-[380px] flex flex-col gap-6">
					<!-- Employee link field -->
					<div class="flex flex-col gap-1.5">
						<label
							class="text-xs font-semibold text-[#5C6169] dark:text-white/65 "
							>Employee <span class="text-red-500 dark:text-red-400">*</span></label
						>
						<SearchableDropdown
							v-model="formData.employee"
							:options="leaveStore.employeeList"
							labelKey="employee_name"
							valueKey="name"
							placeholder="Select employee"
							:disabled="!!editId"
						/>
						<p v-if="errors.employee" class="field-error">
							{{ errors.employee }}
						</p>
					</div>

					<!-- Leave Policy link field -->
					<div class="flex flex-col gap-1.5">
						<label
							class="text-xs font-semibold text-[#5C6169] dark:text-white/65 "
							>Leave Policy <span class="text-red-500 dark:text-red-400">*</span></label
						>
						<div class="flex gap-2">
							<SearchableDropdown
								v-model="formData.leave_policy"
								:options="leaveStore.leavePolicies"
								labelKey="title"
								valueKey="name"
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
						<p v-if="errors.leave_policy" class="field-error">
							{{ errors.leave_policy }}
						</p>
					</div>

					<!-- Assign Based On select field -->
					<div class="flex flex-col gap-1.5">
						<label
							class="text-xs font-semibold text-[#5C6169] dark:text-white/65 "
							>Assign Based On <span class="text-red-500 dark:text-red-400">*</span></label
						>
						<SearchableDropdown
							v-model="formData.assignment_based_on"
							:options="assignmentBasisOptions"
							labelKey="label"
							valueKey="value"
							placeholder="Select assignment basis"
						/>
						<p v-if="errors.assignment_based_on" class="field-error">
							{{ errors.assignment_based_on }}
						</p>
					</div>

					<!-- Leave Period select field -->
					<div class="flex flex-col gap-1.5" v-if="formData.assignment_based_on === 'Leave Period'">
						<label
							class="text-xs font-semibold text-[#5C6169] dark:text-white/65 "
							>Leave Period <span class="text-red-500 dark:text-red-400">*</span></label
						>
						<div class="flex gap-2">
							<SearchableDropdown
								v-model="formData.leave_period"
								:options="activeLeavePeriods"
								labelKey="name"
								valueKey="name"
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
						<p v-if="errors.leave_period" class="field-error">
							{{ errors.leave_period }}
						</p>
					</div>
				</div>

				<!-- Actions -->
				<div
					class="flex flex-col px-6 py-4 border-t border-black/[0.07] dark:border-white/10 bg-white dark:bg-white/[0.06] mt-auto shrink-0"
				>
					<p v-if="submitError" class="text-[13px] text-red-600 dark:text-red-400 mb-3"
					>
						{{ submitError }}
					</p>
					<div class="flex justify-end gap-2">
						<button
						 class="btn-secondary"
							@click="show = false"
							:disabled="submitting"
						>
							Cancel
						</button>
						<button
						 class="btn-primary"
							@click="handleSave"
							:disabled="submitting"
						>
							<span
								v-if="submitting"
								class="material-symbols-outlined text-[18px] animate-spin"
								>progress_activity</span
							>
							{{ submitting ? "Saving..." : "Save Assignment" }}
						</button>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { Dialog, call } from "frappe-ui";
import { getErrorMessage } from "../../../utils.js";
import { useLeaveStore } from "../../../stores/leave";
import SearchableDropdown from "@/components/SearchableDropdown.vue";

const leaveStore = useLeaveStore();

const props = defineProps({
	modelValue: {
		type: Boolean,
		default: false,
	},
	editId: {
		type: String,
		default: "",
	},
});

const emit = defineEmits(["update:modelValue", "save", "create-leave-policy", "create-leave-period"]);

const show = computed({
	get: () => props.modelValue,
	set: (val) => emit("update:modelValue", val),
});

const getInitialFormData = () => ({
	employee: "",
	leave_policy: "",
	assignment_based_on: "Leave Period",
	leave_period: "",
});

const formData = ref(getInitialFormData());
const errors = ref({});
const submitError = ref("");
const submitting = ref(false);

const assignmentBasisOptions = [{ label: "Leave Period", value: "Leave Period" }];

const activeLeavePeriods = computed(() => {
	return leaveStore.leavePeriods.filter((lp) => lp.is_active);
});

onMounted(() => {
	leaveStore.fetchEmployeeList();
	leaveStore.fetchLeavePolicies();
	leaveStore.fetchLeavePeriods();
});

watch(show, async (newVal) => {
	if (newVal) {
		formData.value = getInitialFormData();
		errors.value = {};
		submitError.value = "";

		if (!leaveStore.employeeList.length) leaveStore.fetchEmployeeList();
		if (!leaveStore.leavePolicies.length) leaveStore.fetchLeavePolicies();
		if (!leaveStore.leavePeriods.length) leaveStore.fetchLeavePeriods();

		if (props.editId) {
			await fetchLeavePolicyAssignmentDetails();
		}
	}
});

const fetchLeavePolicyAssignmentDetails = async () => {
	try {
		const doc = await call("arijentek_core.api.leave.get_leave_policy_assignments", {
			name: props.editId,
		});
		if (doc) {
			formData.value = {
				name: doc.name,
				employee: doc.employee,
				leave_policy: doc.leave_policy,
				assignment_based_on: doc.assignment_based_on,
				leave_period: doc.leave_period || "",
			};
		}
	} catch (err) {
		submitError.value = getErrorMessage(err, "Failed to fetch assignment details");
	}
};

const validate = () => {
	errors.value = {};
	let isValid = true;

	if (!formData.value.employee) {
		errors.value.employee = "Employee is mandatory";
		isValid = false;
	}

	if (!formData.value.leave_policy) {
		errors.value.leave_policy = "Leave Policy is mandatory";
		isValid = false;
	}

	if (!formData.value.assignment_based_on) {
		errors.value.assignment_based_on = "Assignment Basis is mandatory";
		isValid = false;
	}

	if (formData.value.assignment_based_on === "Leave Period" && !formData.value.leave_period) {
		errors.value.leave_period = "Leave Period is mandatory";
		isValid = false;
	}

	return isValid;
};

const handleSave = async () => {
	submitError.value = "";
	if (validate()) {
		submitting.value = true;
		try {
			const res = await call("arijentek_core.api.leave.save_leave_policy_assignment", {
				assignment_data: formData.value,
			});
			if (res && res.success === false) {
				submitError.value = getErrorMessage(
					res.error || res.message,
					"Failed to save leave policy assignment"
				);
			} else {
				emit("save", formData.value);
				show.value = false;
			}
		} catch (err) {
			submitError.value = getErrorMessage(err, "Failed to save leave policy assignment");
		} finally {
			submitting.value = false;
		}
	}
};
</script>
