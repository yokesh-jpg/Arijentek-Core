<template>
	<Teleport to="body">
		<div v-if="modelValue" class="modal-scrim" @click.self="close">
			<div class="modal-panel max-w-md" role="dialog" aria-modal="true" aria-labelledby="att-req-title">
				<header class="modal-header">
					<div class="min-w-0">
						<h3 id="att-req-title" class="modal-title">{{ isEditing ? 'Edit request' : 'Request attendance' }}</h3>
						<p class="text-[12px] text-[#5C6169] dark:text-white/55 mt-0.5">For a day worked away from the clock.</p>
					</div>
					<button type="button" @click="close" class="modal-close" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span></button>
				</header>

				<div class="modal-body">
					<div v-if="!isEditing">
						<label class="field-label">Employee</label>
						<SearchableDropdown
							v-if="showEmployeeFilter"
							v-model="requestEmployee"
							:options="attendanceStore.employeeList"
							labelKey="employee_name"
							valueKey="name"
							placeholder="Select employee"
						/>
						<p v-else class="field-static">{{ employeeStore.employee?.employee_name || '—' }}</p>
					</div>
					<div>
						<label class="field-label">Date</label>
						<DateField v-model="requestDate" />
					</div>
					<div>
						<label class="field-label">Explanation</label>
						<textarea v-model="requestExplanation" rows="3" class="field-input" placeholder="Where you were working and why"></textarea>
					</div>
				</div>

				<footer class="modal-footer justify-between">
					<p class="text-[12px] text-red-600 dark:text-red-400 min-w-0">{{ requestAttendanceError }}</p>
					<div class="flex items-center gap-2 shrink-0">
						<button type="button" class="btn-secondary" @click="close">Cancel</button>
						<button type="button" class="btn-primary" :disabled="requestingAttendance" @click="handleSaveAttendanceRequest">
							{{ requestingAttendance ? 'Saving…' : (isEditing ? 'Save changes' : 'Send request') }}
						</button>
					</div>
				</footer>
			</div>
		</div>
	</Teleport>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import SearchableDropdown from "@/components/SearchableDropdown.vue";
import { createResource } from "frappe-ui";
import { useEmployeeStore } from "@/stores/employee";
import { useAttendanceStore } from "@/stores/attendance";
import { getErrorMessage } from "@/utils";
import DateField from '../../../components/DateField.vue'

const props = defineProps({
	modelValue: Boolean,
	record: Object,
});

const emit = defineEmits(["update:modelValue", "save-success"]);

const employeeStore = useEmployeeStore();
const attendanceStore = useAttendanceStore();

const isEditing = ref(false);
const editRequestName = ref("");
const requestDate = ref("");
const requestExplanation = ref("");
const requestEmployee = ref("");
const requestingAttendance = ref(false);
const requestAttendanceError = ref("");

const showEmployeeFilter = computed(() => attendanceStore.employeeList.length > 1);

function close() {
	emit("update:modelValue", false);
}

function initForm() {
	requestAttendanceError.value = "";
	if (props.record) {
		isEditing.value = true;
		const req = props.record;
		editRequestName.value = req.name;
		requestDate.value = req.from_date;
		requestExplanation.value = req.explanation || "";
		requestEmployee.value = req.employee || "";
	} else {
		isEditing.value = false;
		editRequestName.value = "";
		requestDate.value = `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, "0")}-${String(new Date().getDate()).padStart(2, "0")}`;
		requestExplanation.value = "";
		requestEmployee.value = employeeStore.employee?.name || "";
	}
}

async function handleSaveAttendanceRequest() {
	requestAttendanceError.value = "";
	if (!requestDate.value) {
		requestAttendanceError.value = "Please select a date.";
		return;
	}
	if (!requestExplanation.value.trim()) {
		requestAttendanceError.value = "Please enter an explanation.";
		return;
	}

	requestingAttendance.value = true;
	try {
		if (isEditing.value) {
			const editResource = createResource({
				url: "arijentek_core.api.attendance.update_attendance_request",
				auto: false,
			});
			const res = await editResource.fetch({
				request_name: editRequestName.value,
				date: requestDate.value,
				explanation: requestExplanation.value,
			});

			if (editResource.error) {
				throw new Error(getErrorMessage(editResource.error, "Failed to update request."));
			}

			if (res && res.success === false) {
				requestAttendanceError.value = getErrorMessage(res.message || res, "Failed to update request.");
				return;
			}
		} else {
			const reqResource = createResource({
				url: "arijentek_core.api.attendance.create_attendance_request",
				auto: false,
			});
			const res = await reqResource.fetch({
				date: requestDate.value,
				explanation: requestExplanation.value,
				employee: requestEmployee.value,
			});

			if (reqResource.error) {
				throw new Error(getErrorMessage(reqResource.error, "Failed to submit attendance request."));
			}

			if (res && res.success === false) {
				requestAttendanceError.value = getErrorMessage(res.message || res, "Failed to submit attendance request.");
				return;
			}
		}

		emit("save-success");
		close();
	} catch (err) {
		requestAttendanceError.value = getErrorMessage(err, "Failed to save request.");
	} finally {
		requestingAttendance.value = false;
	}
}

watch(() => props.modelValue, (newVal) => {
	if (newVal) {
		initForm();
	}
});
</script>
