<template>
	<Teleport to="body">
		<div v-if="modelValue" class="modal-scrim" @click.self="close">
			<div class="modal-panel max-w-md" role="dialog" aria-modal="true" aria-labelledby="att-form-title">
				<header class="modal-header">
					<div class="min-w-0">
						<h3 id="att-form-title" class="modal-title">{{ isEditing ? 'Edit attendance' : 'Add attendance' }}</h3>
						<p class="text-[12px] text-[#5C6169] dark:text-white/55 mt-0.5 truncate">{{ isEditing ? editAttendanceName : 'Mark a day and its clock times.' }}</p>
					</div>
					<button type="button" @click="close" class="modal-close" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span></button>
				</header>

				<div class="modal-body">
					<div>
						<label class="field-label">Employee</label>
						<SearchableDropdown
							v-if="showEmployeeFilter"
							v-model="addAttendanceEmployee"
							:options="attendanceStore.employeeList"
							labelKey="employee_name"
							valueKey="name"
							placeholder="Select employee"
							:disabled="isEditing"
						/>
						<p v-else class="field-static">{{ employeeStore.employee?.employee_name || '—' }}</p>
					</div>
					<div>
						<label class="field-label">Date</label>
						<DateField v-model="addAttendanceDate" :disabled="isEditing" />
					</div>
					<div>
						<label class="field-label">Status</label>
						<SearchableDropdown
							v-model="addAttendanceStatus"
							:options="statusOptions"
							labelKey="label"
							valueKey="value"
							placeholder="Select status"
						/>
					</div>
					<div class="grid grid-cols-2 gap-4">
						<div>
							<label class="field-label">Clock in</label>
							<TimeField v-model="addAttendanceInTime" />
						</div>
						<div>
							<label class="field-label">Clock out</label>
							<TimeField v-model="addAttendanceOutTime" />
						</div>
					</div>
					<div class="flex items-center gap-6">
						<label class="flex items-center gap-2 text-[13px] text-[#17181B] dark:text-white cursor-pointer select-none">
							<input v-model="addAttendanceLateEntry" type="checkbox" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40" />
							Late entry
						</label>
						<label class="flex items-center gap-2 text-[13px] text-[#17181B] dark:text-white cursor-pointer select-none">
							<input v-model="addAttendanceEarlyExit" type="checkbox" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40" />
							Early exit
						</label>
					</div>
				</div>

				<footer class="modal-footer justify-between">
					<p class="text-[12px] text-red-600 dark:text-red-400 min-w-0">{{ addAttendanceError }}</p>
					<div class="flex items-center gap-2 shrink-0">
						<button type="button" class="btn-secondary" @click="close">Cancel</button>
						<button type="button" class="btn-primary" :disabled="addingAttendance" @click="handleSaveAttendance">
							{{ addingAttendance ? 'Saving…' : (isEditing ? 'Save changes' : 'Save') }}
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
import TimeField from '../../../components/TimeField.vue'

const props = defineProps({
	modelValue: Boolean,
	record: Object,
});

const emit = defineEmits(["update:modelValue", "save-success"]);

const employeeStore = useEmployeeStore();
const attendanceStore = useAttendanceStore();

const isEditing = ref(false);
const editAttendanceName = ref("");
const addAttendanceEmployee = ref("");
const addAttendanceDate = ref("");
const addAttendanceStatus = ref("Present");
const addAttendanceInTime = ref("");
const addAttendanceOutTime = ref("");
const hasExistingInTime = ref(false);

const statusOptions = [
	{ label: "Present", value: "Present" },
	{ label: "Absent", value: "Absent" },
	{ label: "Half Day", value: "Half Day" },
];
const hasExistingOutTime = ref(false);
const addAttendanceLateEntry = ref(false);
const addAttendanceEarlyExit = ref(false);
const addAttendanceError = ref("");
const addingAttendance = ref(false);

const showEmployeeFilter = computed(() => attendanceStore.employeeList.length > 1);

const getAttendanceResource = createResource({
	url: "frappe.client.get",
	auto: false,
});

function extractTime(dtStr) {
	if (!dtStr) return "";
	const parts = dtStr.split(/[ T]/);
	if (parts.length > 1) {
		return parts[1].substring(0, 5); // get HH:MM
	}
	return "";
}

function close() {
	emit("update:modelValue", false);
}

async function initForm() {
	addAttendanceError.value = "";
	if (props.record) {
		isEditing.value = true;
		const record = props.record;
		const attId = record.name || record.attendance_name || "";
		editAttendanceName.value = attId;
		addingAttendance.value = true;
		try {
			const res = await getAttendanceResource.fetch({
				doctype: "Attendance",
				name: attId
			});
			if (res && res.name) {
				addAttendanceEmployee.value = res.employee || "";
				addAttendanceDate.value = res.attendance_date || "";
				addAttendanceStatus.value = res.status || "Present";
				addAttendanceInTime.value = res.in_time ? extractTime(res.in_time) : "";
				addAttendanceOutTime.value = res.out_time ? extractTime(res.out_time) : "";
				hasExistingInTime.value = !!res.in_time;
				hasExistingOutTime.value = !!res.out_time;
				addAttendanceLateEntry.value = !!res.late_entry;
				addAttendanceEarlyExit.value = !!res.early_exit;
			} else {
				addAttendanceEmployee.value = record.employee || record.employee_id || "";
				addAttendanceDate.value = record.date || "";
				addAttendanceStatus.value = record.status || "Present";
				addAttendanceInTime.value = record.clockIn ? extractTime(record.clockIn) : "";
				addAttendanceOutTime.value = record.clockOut ? extractTime(record.clockOut) : "";
				hasExistingInTime.value = !!record.clockIn;
				hasExistingOutTime.value = !!record.clockOut;
				addAttendanceLateEntry.value = !!record.late_entry;
				addAttendanceEarlyExit.value = !!record.early_exit;
			}
		} catch (err) {
			console.error("Failed to fetch attendance details:", err);
			addAttendanceEmployee.value = record.employee || record.employee_id || "";
			addAttendanceDate.value = record.date || "";
			addAttendanceStatus.value = record.status || "Present";
			addAttendanceInTime.value = record.clockIn ? extractTime(record.clockIn) : "";
			addAttendanceOutTime.value = record.clockOut ? extractTime(record.clockOut) : "";
			hasExistingInTime.value = !!record.clockIn;
			hasExistingOutTime.value = !!record.clockOut;
			addAttendanceLateEntry.value = !!record.late_entry;
			addAttendanceEarlyExit.value = !!record.early_exit;
		} finally {
			addingAttendance.value = false;
		}
	} else {
		isEditing.value = false;
		hasExistingInTime.value = false;
		hasExistingOutTime.value = false;
		addAttendanceLateEntry.value = false;
		addAttendanceEarlyExit.value = false;
		editAttendanceName.value = "";
		addAttendanceEmployee.value = showEmployeeFilter.value ? "" : (employeeStore.employee?.name || "");
		addAttendanceDate.value = `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, "0")}-${String(new Date().getDate()).padStart(2, "0")}`;
		addAttendanceStatus.value = "Present";
		addAttendanceInTime.value = "";
		addAttendanceOutTime.value = "";
		addAttendanceError.value = "";
	}
}

const hrSettingsResource = createResource({
	url: "frappe.client.get_value",
	auto: true,
	makeParams() {
		return {
			doctype: "HR Settings",
			fieldname: "timesheet_with_clockin",
		};
	},
});

const isTimesheetAutomationEnabled = computed(() => {
	return hrSettingsResource.data?.timesheet_with_clockin == 1;
});

async function handleSaveAttendance() {
	addAttendanceError.value = "";
	const empId = addAttendanceEmployee.value;
	if (!empId) {
		addAttendanceError.value = "Please select an employee.";
		return;
	}
	if (!addAttendanceDate.value) {
		addAttendanceError.value = "Please select a date.";
		return;
	}

	if (isTimesheetAutomationEnabled.value) {
		if (!addAttendanceInTime.value) {
			addAttendanceError.value = "Clock In time is mandatory when Timesheet Automation is enabled.";
			return;
		}
		if (!addAttendanceOutTime.value) {
			addAttendanceError.value = "Clock Out time is mandatory when Timesheet Automation is enabled.";
			return;
		}
	}

	addingAttendance.value = true;
	try {
		if (isEditing.value) {
			if (editAttendanceName.value) {
				const updateRes = createResource({
					url: "arijentek_core.api.attendance.update_attendance",
					auto: false,
				});
				const res = await updateRes.fetch({
					attendance_name: editAttendanceName.value,
					status: addAttendanceStatus.value,
					in_time: addAttendanceInTime.value || null,
					out_time: addAttendanceOutTime.value || null,
					late_entry: addAttendanceLateEntry.value ? 1 : 0,
					early_exit: addAttendanceEarlyExit.value ? 1 : 0,
				});
				if (updateRes.error) {
					throw new Error(getErrorMessage(updateRes.error) || "Failed to update attendance.");
				}
				if (res && res.success === false) {
					throw new Error(res.message || "Failed to update attendance.");
				}
			} else {
				throw new Error("No attendance record ID specified.");
			}
		} else {
			try {
				const res = await attendanceStore.markAttendance(
					empId,
					addAttendanceDate.value,
					addAttendanceStatus.value,
					addAttendanceInTime.value || null,
					addAttendanceOutTime.value || null,
					addAttendanceLateEntry.value ? 1 : 0,
					addAttendanceEarlyExit.value ? 1 : 0
				);
				if (res && res.success === false) {
					throw new Error(res.message || "Failed to mark attendance.");
				}
			} catch (err) {
				throw new Error(getErrorMessage(err) || "Failed to mark attendance.");
			}
		}

		emit("save-success");
		close();
	} catch (err) {
		addAttendanceError.value = getErrorMessage(err) || "Failed to save attendance.";
	} finally {
		addingAttendance.value = false;
	}
}

watch(() => props.modelValue, (newVal) => {
	if (newVal) {
		initForm();
	}
});
</script>
