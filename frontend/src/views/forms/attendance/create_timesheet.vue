<template>
	<Dialog :options="{ size: '6xl' }" v-model="show">
		<template #body>
			<div class="modal-panel">
				<header class="modal-header">
					<div>
						<h3 class="modal-title">{{ isEdit ? 'Edit timesheet' : 'Add new timesheet' }}</h3>
						<p class="text-[12px] text-[#656A72] dark:text-white/60">{{ isEdit ? 'Update details for ' + editId : 'Fill in the details below' }}</p>
					</div>
					<button @click="show = false" class="btn-icon-ghost shrink-0" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span>
					</button>
				</header>

				<div class="flex-1 px-5 py-5 overflow-y-auto flex flex-col gap-5">
					<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
						<!-- Employee Selection / Label -->
						<div class="flex flex-col gap-1.5">
							<label class="field-label">Employee <span class="text-red-500 dark:text-red-400">*</span></label>
							<div v-if="showEmployeeSelection">
								<SearchableDropdown
									v-model="formData.employee"
									:options="attendanceStore.employeeList"
									labelKey="employee_name"
									valueKey="name"
									placeholder="Select employee"
								/>
							</div>
							<div v-else class="px-3 py-2 w-full bg-black/[0.04] dark:bg-black/30 border border-black/[0.07] dark:border-white/10 rounded-[12px] text-sm text-[#17181B] dark:text-white/80 font-medium h-[38px] flex items-center">
								{{ currentEmployeeName || 'Loading...' }}
							</div>
							<p v-if="errors.employee" class="field-error">{{ errors.employee }}</p>
						</div>

						<!-- Start Date -->
						<div class="flex flex-col gap-1.5">
							<label class="field-label">Start date <span class="text-red-500 dark:text-red-400">*</span></label>
							<DateField v-model="formData.start_date" />
							<p v-if="errors.start_date" class="field-error">{{ errors.start_date }}</p>
						</div>
					</div>

					<!-- Time Logs Grid Header -->
					<div class="border-t border-black/[0.07] dark:border-white/10 pt-6">
						<h4 class="text-sm font-semibold text-[#17181B] dark:text-white mb-4">
							Time Sheet Details
						</h4>
						<div class="hidden md:grid grid-cols-12 gap-4 px-2 mb-2">
							<span class="text-xs font-semibold text-[#656A72] dark:text-white/65 col-span-2">Activity Type <span class="text-red-500 dark:text-red-400">*</span></span>
							<span class="text-xs font-semibold text-[#656A72] dark:text-white/65 col-span-3">From Time <span class="text-red-500 dark:text-red-400">*</span></span>
							<span class="text-xs font-semibold text-[#656A72] dark:text-white/65 col-span-3">To Time <span class="text-red-500 dark:text-red-400">*</span></span>
							<span class="text-xs font-semibold text-[#656A72] dark:text-white/65 col-span-1">Hours</span>
							<span class="text-xs font-semibold text-[#656A72] dark:text-white/65 col-span-2">Description</span>
							<span class="text-xs font-semibold text-[#656A72] dark:text-white/65 col-span-1 text-center">Action</span>
						</div>

						<!-- Time Log Lines List -->
						<div class="space-y-3">
							<div v-for="(line, index) in formData.time_logs" :key="index" class="grid grid-cols-12 gap-4 items-center">
								<!-- Activity Type -->
								<div class="col-span-12 md:col-span-2">
									<SearchableDropdown
										v-model="line.activity_type"
										:options="activityTypes"
										labelKey="name"
										valueKey="name"
										placeholder="Select activity"
									/>
								</div>
								<!-- From Time -->
								<div class="col-span-12 md:col-span-3">
									<DateTimeField v-model="line.from_time" @change="calculateHours(index)" />
								</div>
								<!-- To Time -->
								<div class="col-span-12 md:col-span-3">
									<DateTimeField v-model="line.to_time" @change="calculateHours(index)" />
								</div>
								<!-- Hours -->
								<div class="col-span-12 md:col-span-1">
									<input type="number" step="0.01" v-model="line.hours" @input="calculateToTime(index)" placeholder="0.0" class="field-input" />
								</div>
								<!-- Description -->
								<div class="col-span-12 md:col-span-2">
									<input type="text" v-model="line.description" placeholder="Notes..." class="field-input" />
								</div>
								<!-- Action -->
								<div class="col-span-12 md:col-span-1 flex justify-center">
									<button type="button" @click="removeTimeLogLine(index)" class="w-8 h-8 rounded-full hover:bg-red-50 dark:hover:bg-red-950/20 flex items-center justify-center text-red-500 dark:text-red-400 transition-all">
										<span class="material-symbols-outlined text-sm">delete</span>
									</button>
								</div>
							</div>
						</div>

						<!-- Add Line Button -->
						<button type="button" @click="addTimeLogLine" class="btn-secondary mt-4">
							<span class="material-symbols-outlined text-sm">add</span>
							Add Row
						</button>
					</div>
					
					<!-- Total Hours Display -->
					<div class="flex items-center justify-between border-t border-black/[0.07] dark:border-white/10 pt-6">
						<span class="text-xs font-semibold text-[#656A72] dark:text-white/55 ">Total Timesheet Hours</span>
						<span class="text-xl font-semibold text-[#17181B] dark:text-white tracking-tight">{{ totalTimesheetHours.toFixed(2) }} hrs</span>
					</div>
				</div>

				<div class="px-5 py-4 border-t border-black/[0.06] dark:border-white/[0.08] shrink-0">
					<p v-if="submitError" class="text-[13px] text-red-600 dark:text-red-400 mb-3">{{ submitError }}</p>
					<div class="flex justify-end gap-2">
						<button
						 class="btn-secondary"
							@click="show = false"
							:disabled="submitting"
						>
							Cancel
						</button>
						<!-- Save as Draft Button -->
						<button
							class="btn-secondary"
							@click="handleSave(false)"
							:disabled="submitting"
						>
							<span v-if="submitting" class="material-symbols-outlined text-[18px] animate-spin">progress_activity</span>
							<span v-else class="material-symbols-outlined text-[18px]">drafts</span>
							Save Draft
						</button>
						<!-- Submit Button -->
						<button
							class="btn-primary"
							@click="handleSave(true)"
							:disabled="submitting"
						>
							<span v-if="submitting" class="material-symbols-outlined text-[18px] animate-spin">progress_activity</span>
							<span v-else class="material-symbols-outlined text-[18px]">send</span>
							Submit Timesheet
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
import { useEmployeeStore } from "../../../stores/employee";
import { useAttendanceStore } from "../../../stores/attendance";
import SearchableDropdown from "../../../components/SearchableDropdown.vue";
import DateField from '../../../components/DateField.vue'
import DateTimeField from '../../../components/DateTimeField.vue'

const props = defineProps({
	modelValue: { type: Boolean, default: false },
	record: { type: Object, default: null }
});

const emit = defineEmits(["update:modelValue", "save-success"]);

const employeeStore = useEmployeeStore();
const attendanceStore = useAttendanceStore();

const show = computed({
	get: () => props.modelValue,
	set: (val) => emit("update:modelValue", val)
});

const isEdit = computed(() => !!props.record);
const editId = computed(() => props.record?.name || "");

const canManageTimesheets = ref(false);

const showEmployeeSelection = computed(() => {
	if (isEdit.value) return false;
	return canManageTimesheets.value || !employeeStore.employee;
});

const currentEmployeeName = computed(() => {
	if (isEdit.value && props.record) {
		return props.record.employee_name || props.record.employee || employeeStore.employee?.employee_name || "";
	}
	return employeeStore.employee?.employee_name || "";
});

const activityTypes = ref([]);
const errors = ref({});
const submitError = ref("");
const submitting = ref(false);

function getCurrentDatetimeLocal() {
	const now = new Date();
	const offset = now.getTimezoneOffset();
	const localDate = new Date(now.getTime() - offset * 60 * 1000);
	return localDate.toISOString().slice(0, 16);
}

const getInitialFormData = () => ({
	name: "",
	employee: "",
	start_date: new Date().toISOString().substring(0, 10),
	time_logs: [
		{ activity_type: "", from_time: getCurrentDatetimeLocal(), to_time: "", hours: 0, description: "" }
	]
});

const formData = ref(getInitialFormData());

const totalTimesheetHours = computed(() => {
	return formData.value.time_logs.reduce((sum, item) => sum + parseFloat(item.hours || 0), 0);
});

// Watch employee to ensure formData.employee is set even if loaded late
watch(() => employeeStore.employee, (newEmp) => {
	if (newEmp && !formData.value.employee && !isEdit.value) {
		formData.value.employee = newEmp.name || "";
	}
}, { immediate: true });

onMounted(async () => {
	await employeeStore.init();
	
	try {
		const res = await call("arijentek_core.api.attendance.can_manage_timesheets");
		canManageTimesheets.value = !!res;
	} catch (e) {
		console.error("Failed to check if user can manage timesheets:", e);
		canManageTimesheets.value = false;
	}

	try {
		await attendanceStore.fetchEmployeeList();
	} catch (e) {
		console.error("Failed to fetch employee list:", e);
	}

	try {
		const types = await call("arijentek_core.api.attendance.get_activity_type");
		activityTypes.value = types || [];
	} catch (e) {
		console.error("Failed to load activity types:", e);
	}
});


// Format Datetime for datetime-local input (YYYY-MM-DDTHH:mm)
function formatDatetimeLocal(dtStr) {
	if (!dtStr) return "";
	const date = new Date(dtStr);
	if (isNaN(date.getTime())) return dtStr;
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, "0");
	const day = String(date.getDate()).padStart(2, "0");
	const hours = String(date.getHours()).padStart(2, "0");
	const minutes = String(date.getMinutes()).padStart(2, "0");
	return `${year}-${month}-${day}T${hours}:${minutes}`;
}

watch(show, async (newVal) => {
	if (newVal) {
		formData.value = getInitialFormData();
		errors.value = {};
		submitError.value = "";
		
		if (isEdit.value && props.record) {
			try {
				// Fetch full Timesheet doc details from ERPNext via custom API
				const timesheetDoc = await call("arijentek_core.api.attendance.get_timesheet_list_details", {
					name: props.record.name
				});
				
				if (timesheetDoc) {
					formData.value = {
						name: timesheetDoc.name,
						employee: timesheetDoc.employee,
						start_date: timesheetDoc.start_date || new Date().toISOString().substring(0, 10),
						time_logs: timesheetDoc.time_logs?.map(log => ({
							activity_type: log.activity_type,
							from_time: formatDatetimeLocal(log.from_time),
							to_time: formatDatetimeLocal(log.to_time),
							hours: log.hours || 0,
							description: log.description || "",
							completed: log.completed || 0
						})) || [{ activity_type: "", from_time: "", to_time: "", hours: 0, description: "" }]
					};
				}
			} catch (e) {
				console.error("Failed to load timesheet details:", e);
				submitError.value = getErrorMessage(e, "Failed to load timesheet details");
			}
		} else {
			formData.value.employee = employeeStore.employee?.name || "";
		}
	}
});

function addTimeLogLine() {
	formData.value.time_logs.push({
		activity_type: "",
		from_time: "",
		to_time: "",
		hours: 0,
		description: ""
	});
}

function removeTimeLogLine(idx) {
	formData.value.time_logs.splice(idx, 1);
	if (formData.value.time_logs.length === 0) {
		addTimeLogLine();
	}
}

function calculateHours(index) {
	const line = formData.value.time_logs[index];
	if (line.from_time && line.to_time) {
		const from = new Date(line.from_time);
		const to = new Date(line.to_time);
		if (to >= from) {
			const diffMs = to - from;
			line.hours = parseFloat((diffMs / 3600000).toFixed(2));
		} else {
			line.hours = 0;
		}
	}
}

function calculateToTime(index) {
	const line = formData.value.time_logs[index];
	if (line.from_time && line.hours !== undefined && line.hours !== null) {
		const from = new Date(line.from_time);
		const hrs = parseFloat(line.hours) || 0;
		const toMs = from.getTime() + (hrs * 3600000);
		const toDate = new Date(toMs);
		line.to_time = formatDatetimeLocal(toDate);
	}
}

function validate() {
	errors.value = {};
	let isValid = true;
	if (!formData.value.employee) {
		errors.value.employee = "Employee is required";
		isValid = false;
	}
	if (!formData.value.start_date) {
		errors.value.start_date = "Start Date is required";
		isValid = false;
	}
	if (formData.value.time_logs.length === 0) {
		submitError.value = "Please add at least one time log line.";
		return false;
	}
	for (const item of formData.value.time_logs) {
		if (!item.activity_type) {
			submitError.value = "Please select an Activity Type for all lines.";
			return false;
		}
		if (!item.from_time || !item.to_time) {
			submitError.value = "Please fill in From Time and To Time for all lines.";
			return false;
		}
		if (parseFloat(item.hours || 0) <= 0) {
			submitError.value = "Hours must be greater than zero for all lines.";
			return false;
		}
	}
	return isValid;
}

async function handleSave(submit = false) {
	submitError.value = "";
	if (validate()) {
		submitting.value = true;
		try {
			const payload = {
				employee: formData.value.employee,
				start_date: formData.value.start_date,
				time_logs: formData.value.time_logs,
				name: formData.value.name || undefined,
				submit: submit ? 1 : 0
			};
			const response = await call("arijentek_core.api.attendance.save_timesheet", payload);
			
			const docName = (typeof response === "object" && response?.name) ? response.name : response;
			const formattedResult = {
				name: docName,
				employee: formData.value.employee,
				employee_name: currentEmployeeName.value,
				start_date: formData.value.start_date,
				end_date: formData.value.start_date, // dummy end date is start date
				total_hours: totalTimesheetHours.value,
				status: submit ? "Submitted" : "Draft"
			};
			
			emit("save-success", formattedResult);
			show.value = false;
		} catch (err) {
			submitError.value = getErrorMessage(err, "Failed to save timesheet");
		} finally {
			submitting.value = false;
		}
	}
}
</script>

<style scoped>
</style>
