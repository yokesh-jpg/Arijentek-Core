<template>
	<Teleport to="body">
	<div v-if="modelValue" class="modal-scrim" @click.self="close">
		<div class="modal-panel max-w-7xl min-h-[75vh] relative" role="dialog" aria-modal="true" aria-labelledby="bulk-att-title">
			<div class="modal-header">
				<div class="flex flex-wrap items-center gap-x-4 gap-y-2 min-w-0">
					<h3 id="bulk-att-title" class="modal-title">Bulk attendance</h3>
					<div class="seg-group">
						<button
							type="button"
							@click="setSelectionMode('single')"
							class="seg-item !h-7 !px-3 !text-[12px]"
							:class="{ 'seg-item-active': selectionMode === 'single' }"
						>
							Single date
						</button>
						<button
							type="button"
							@click="setSelectionMode('range')"
							class="seg-item !h-7 !px-3 !text-[12px]"
							:class="{ 'seg-item-active': selectionMode === 'range' }"
						>
							Date range
						</button>
					</div>
				</div>
				<button type="button" @click="close" class="modal-close" aria-label="Close">
					<span class="material-symbols-outlined !text-[18px]">close</span>
				</button>
			</div>

			<div class="modal-body !space-y-5">
				<div class="grid grid-cols-1 md:grid-cols-4 gap-4">
					<div>
						<label class="field-label">
							{{ selectionMode === 'Range' ? 'Date range (max 31 days)' : 'Date' }}
						</label>
						<div v-if="selectionMode === 'single'">
							<DateField v-model="bulkForm.date" />
						</div>
						<div v-else>
							<DateRangePicker
								v-model:fromDate="bulkForm.fromDate"
								v-model:toDate="bulkForm.toDate"
								v-model:preset="bulkForm.datePreset"
								@change="onDateRangeChange"
							/>
							<div v-if="rangeDayCount > 31" class="text-[12px] font-medium text-red-500 dark:text-red-400 mt-1">
								Range cannot exceed 31 days (Selected: {{ rangeDayCount }} days)
							</div>
						</div>
					</div>
					<div>
						<label class="field-label">Status</label>
						<SearchableDropdown
							v-model="bulkForm.status"
							:options="statusOptions"
							labelKey="label"
							valueKey="value"
							placeholder="Select status"
						/>
					</div>
					<div>
						<label class="field-label">Shift</label>
						<SearchableDropdown
							v-model="bulkForm.shift"
							:options="bulkOptions.shifts"
							placeholder="Select shift"
							:showAllOption="true"
							allOptionLabel="None"
						/>
					</div>
					<div class="flex flex-col justify-end pb-2 gap-2">
						<label class="flex items-center gap-2 text-[13px] text-[#17181B] dark:text-white cursor-pointer select-none">
							<input type="checkbox" v-model="bulkForm.late_entry" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40" /> Late entry
						</label>
						<label class="flex items-center gap-2 text-[13px] text-[#17181B] dark:text-white cursor-pointer select-none">
							<input type="checkbox" v-model="bulkForm.early_exit" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40" /> Early exit
						</label>
						<label class="flex items-center gap-2 text-[13px] text-[#17181B] dark:text-white cursor-pointer select-none">
							<input type="checkbox" v-model="bulkForm.avoid_holidays" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40" /> Avoid holidays
						</label>
					</div>
				</div>

				<div class="modal-section grid grid-cols-1 sm:grid-cols-2 gap-4">
					<div class="relative">
						<label class="field-label">Filter department</label>
						<SearchableDropdown
							v-model="bulkFilters.department"
							:options="bulkOptions.departments"
							placeholder="Search or select department"
							:showAllOption="true"
							allOptionLabel="All departments"
						/>
					</div>
					<div class="relative">
						<label class="field-label">Filter designation</label>
						<SearchableDropdown
							v-model="bulkFilters.designation"
							:options="bulkOptions.designations"
							placeholder="Search or select designation"
							:showAllOption="true"
							allOptionLabel="All designations"
						/>
					</div>
				</div>

				<div v-if="loadingBulkFilters || loadingBulkEmployees" class="empty-state">
					<span class="w-6 h-6 rounded-full border-2 border-accent/25 border-t-accent animate-spin"></span>
					<p class="empty-state-text">Loading employees…</p>
				</div>
				<div v-else-if="bulkEmployeeList.length === 0" class="empty-state">
					<span class="material-symbols-outlined">group_off</span>
					<p class="empty-state-title">No employees found</p>
					<p class="empty-state-text">Try a different department or designation.</p>
				</div>
				<div v-else class="table-card !rounded-[12px] overflow-x-auto max-h-[55vh] overflow-y-auto">
					<table class="w-full text-left relative">
						<thead class="table-head sticky top-0 z-10">
							<tr>
								<th class="table-th text-center w-12">
									<input type="checkbox" @change="toggleAllBulkEmployees" :checked="selectedBulkEmployees.length === bulkEmployeeList.length && bulkEmployeeList.length > 0" class="w-4 h-4 rounded accent-accent cursor-pointer" />
								</th>
								<th class="table-th ">Employee</th>
								<th class="table-th ">Department</th>
								<th class="table-th ">Designation</th>
								<th class="table-th w-48">Status</th>
								<th class="table-th w-48">Shift</th>
								<th class="table-th text-right">Already marked</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="emp in bulkEmployeeList" :key="emp.name" class="table-row">
								<td class="px-4 py-3 text-center">
									<input type="checkbox" :value="emp.name" v-model="selectedBulkEmployees" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40" />
								</td>
								<td class="table-td-strong">{{ emp.employee_name }}</td>
								<td class="table-td">{{ emp.department || '—' }}</td>
								<td class="table-td">{{ emp.designation || '—' }}</td>
								<td class="px-4 py-2">
									<SearchableDropdown
										v-model="emp.status"
										:options="statusOptions"
										labelKey="label"
										valueKey="value"
										placeholder="Select status"
										@change="emp.is_status_dirty = true"
									/>
								</td>
								<td class="px-4 py-2">
									<SearchableDropdown
										v-model="emp.shift"
										:options="bulkOptions.shifts"
										placeholder="Select shift"
										:showAllOption="true"
										allOptionLabel="None"
										@change="emp.is_shift_dirty = true"
									/>
								</td>
								<td class="px-4 py-3 text-right">
									<span v-if="emp.attendance_status" class="premium-tag tag-neutral">
										{{ emp.attendance_status }}
									</span>
									<span v-else class="text-[13px] text-[#656A72] dark:text-white/55">—</span>
								</td>
							</tr>
						</tbody>
					</table>
				</div>
			</div>

			<div class="modal-footer !flex-col !items-stretch gap-3">
				<p v-if="bulkErrorMessage" class="text-[12px] font-medium text-red-600 dark:text-red-400">{{ bulkErrorMessage }}</p>
				<div class="flex items-center justify-between w-full gap-3">
					<div class="text-[12px] text-[#5C6169] dark:text-white/60 tabular-nums">{{ selectedBulkEmployees.length }} selected</div>
					<div class="flex items-center gap-2">
						<button @click="close" class="btn-secondary">
							Cancel
						</button>
						<button
							@click="submitBulkAttendance"
							:disabled="submittingBulkAttendance || selectedBulkEmployees.length === 0 || (selectionMode === 'range' && rangeDayCount > 31)"
							class="btn-primary"
						>
							<span v-if="submittingBulkAttendance" class="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></span>
							{{ submittingBulkAttendance ? 'Saving…' : 'Mark attendance' }}
						</button>
					</div>
				</div>
			</div>

			<!-- Existing Attendance Confirmation Modal -->
			<div v-if="showConfirmModal" class="absolute inset-0 z-50 flex items-center justify-center bg-black/60 rounded-[20px] p-4">
				<div role="alertdialog" aria-modal="true" class="bg-white dark:bg-surface-2 rounded-2xl shadow-2xl max-w-md w-full p-6 border-t-4 border-accent">
					<h4 class="text-xl font-semibold text-[#17181B] dark:text-white mb-2">Update existing attendance?</h4>
					<p class="text-base text-[#5C6169] dark:text-white/60 mb-2">
						Attendance records already exist for
						<span class="font-semibold text-[#17181B] dark:text-white">{{ existingEmployeesWithAttendanceCount }}</span>
						selected employee(s) within the chosen date range. Proceeding will update these existing attendance records.
					</p>
					<p class="text-[13px] text-[#5C6169] dark:text-white/60 mb-6">
						Do you want to proceed and update the existing attendance entries?
					</p>
					<div class="flex gap-3">
						<button
							type="button"
							@click="showConfirmModal = false"
							class="flex-1 py-3.5 rounded-xl border-2 border-black/[0.12] dark:border-white/[0.08] text-[#2D3138] dark:text-white/80 font-semibold text-base hover:bg-black/[0.03] dark:hover:bg-surface-3 transition"
						>
							Cancel
						</button>
						<button
							type="button"
							@click="confirmAndSubmit"
							class="flex-1 py-3.5 rounded-xl bg-accent hover:bg-accent-hover text-white font-semibold text-base transition"
						>
							Update
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
	</Teleport>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import SearchableDropdown from "@/components/SearchableDropdown.vue";
import DateRangePicker from "@/components/DateRangePicker.vue";
import { createResource } from "frappe-ui";
import { getErrorMessage } from "@/utils";
import DateField from '../../../components/DateField.vue'

const props = defineProps({
	modelValue: Boolean,
});

const emit = defineEmits(["update:modelValue", "save-success"]);

const bulkErrorMessage = ref("");
const selectionMode = ref("single"); // 'single' | 'range'

const getTodayDateString = () => {
	const d = new Date();
	const y = d.getFullYear();
	const m = String(d.getMonth() + 1).padStart(2, "0");
	const day = String(d.getDate()).padStart(2, "0");
	return `${y}-${m}-${day}`;
};

const bulkFilters = ref({ department: "", designation: "" });
const bulkForm = ref({
	date: getTodayDateString(),
	fromDate: getTodayDateString(),
	toDate: getTodayDateString(),
	datePreset: "Today",
	shift: "",
	status: "Present",
	late_entry: false,
	early_exit: false,
	avoid_holidays: true,
});

const statusOptions = [
	{ label: "Present", value: "Present" },
	{ label: "Absent", value: "Absent" },
	{ label: "Half Day", value: "Half Day" },
	{ label: "On Leave", value: "On Leave" },
];
const bulkEmployeeList = ref([]);
const selectedBulkEmployees = ref([]);

const bulkOptions = ref({ departments: [], designations: [], shifts: [] });
const loadingBulkFilters = ref(false);
const loadingBulkEmployees = ref(false);
const submittingBulkAttendance = ref(false);
const showConfirmModal = ref(false);

const rangeDayCount = computed(() => {
	if (selectionMode.value !== "range" || !bulkForm.value.fromDate || !bulkForm.value.toDate) {
		return 1;
	}
	const start = new Date(bulkForm.value.fromDate);
	const end = new Date(bulkForm.value.toDate);
	if (isNaN(start.getTime()) || isNaN(end.getTime())) return 0;
	const diffTime = end.getTime() - start.getTime();
	return Math.floor(diffTime / (1000 * 3600 * 24)) + 1;
});

const existingEmployeesWithAttendanceCount = computed(() => {
	return bulkEmployeeList.value.filter(
		emp => selectedBulkEmployees.value.includes(emp.name) && (emp.attendance_status || emp.existing_count > 0)
	).length;
});

const getBulkFiltersResource = createResource({
	url: "arijentek_core.api.attendance.get_bulk_attendance_filters",
	auto: false,
});

const getBulkEmployeesResource = createResource({
	url: "arijentek_core.api.attendance.get_employees_for_bulk_attendance",
	auto: false,
});

const markBulkAttendanceResource = createResource({
	url: "arijentek_core.api.attendance.mark_bulk_attendance",
	auto: false,
});

function close() {
	showConfirmModal.value = false;
	emit("update:modelValue", false);
}

function setSelectionMode(mode) {
	selectionMode.value = mode;
	fetchBulkEmployees();
}

function onDateRangeChange() {
	if (selectionMode.value === "range") {
		fetchBulkEmployees();
	}
}

async function openBulkAttendance() {
	const today = getTodayDateString();
	selectionMode.value = "single";
	bulkForm.value.date = today;
	bulkForm.value.fromDate = today;
	bulkForm.value.toDate = today;
	bulkForm.value.datePreset = "Today";
	bulkForm.value.shift = "";
	bulkForm.value.status = "Present";
	bulkForm.value.late_entry = false;
	bulkForm.value.early_exit = false;
	bulkForm.value.avoid_holidays = true;
	bulkFilters.value.department = "";
	bulkFilters.value.designation = "";
	bulkEmployeeList.value = [];
	selectedBulkEmployees.value = [];
	bulkErrorMessage.value = "";
	showConfirmModal.value = false;

	if (bulkOptions.value.departments.length === 0) {
		loadingBulkFilters.value = true;
		try {
			const res = await getBulkFiltersResource.fetch();
			if (res) {
				bulkOptions.value = res;
			}
		} catch (err) {
			console.error("Failed to load bulk filters", err);
		} finally {
			loadingBulkFilters.value = false;
		}
	}
	await fetchBulkEmployees();
}

async function fetchBulkEmployees() {
	bulkErrorMessage.value = "";
	if (selectionMode.value === "single" && !bulkForm.value.date) return;
	if (selectionMode.value === "range" && (!bulkForm.value.fromDate || !bulkForm.value.toDate)) return;

	if (selectionMode.value === "range" && rangeDayCount.value > 31) {
		bulkErrorMessage.value = "Date range cannot exceed 31 days.";
		return;
	}

	loadingBulkEmployees.value = true;
	try {
		const params = {
			department: bulkFilters.value.department || null,
			designation: bulkFilters.value.designation || null,
		};
		if (selectionMode.value === "range") {
			params.from_date = bulkForm.value.fromDate;
			params.to_date = bulkForm.value.toDate;
		} else {
			params.date = bulkForm.value.date;
		}

		const res = await getBulkEmployeesResource.fetch(params);
		if (res) {
			bulkEmployeeList.value = res.map(emp => ({
				...emp,
				status: bulkForm.value.status,
				shift: bulkForm.value.shift,
				is_status_dirty: false,
				is_shift_dirty: false
			}));
			selectedBulkEmployees.value = [];
		}
	} catch (err) {
		console.error("Failed to load employees for bulk attendance", err);
	} finally {
		loadingBulkEmployees.value = false;
	}
}

function toggleAllBulkEmployees(e) {
	if (e.target.checked) {
		selectedBulkEmployees.value = bulkEmployeeList.value.map(emp => emp.name);
	} else {
		selectedBulkEmployees.value = [];
	}
}

async function submitBulkAttendance() {
	bulkErrorMessage.value = "";

	if (selectedBulkEmployees.value.length === 0) {
		bulkErrorMessage.value = "Please select at least one employee.";
		return;
	}

	if (selectionMode.value === "single" && !bulkForm.value.date) {
		bulkErrorMessage.value = "Please fill date.";
		return;
	}

	if (selectionMode.value === "range") {
		if (!bulkForm.value.fromDate || !bulkForm.value.toDate) {
			bulkErrorMessage.value = "Please fill date range.";
			return;
		}
		if (rangeDayCount.value > 31) {
			bulkErrorMessage.value = "Date range cannot exceed 31 days.";
			return;
		}
	}

	if (!bulkForm.value.shift) {
		bulkErrorMessage.value = "Shift is mandatory.";
		return;
	}

	const selectedEmployeesData = bulkEmployeeList.value.filter(emp => selectedBulkEmployees.value.includes(emp.name));
	if (selectedEmployeesData.some(emp => !emp.status)) {
		bulkErrorMessage.value = "All selected employees must have a status.";
		return;
	}

	const onLeaveEmployees = bulkEmployeeList.value.filter(
		emp => selectedBulkEmployees.value.includes(emp.name) && emp.attendance_status === "On Leave"
	);

	if (onLeaveEmployees.length > 0) {
		const names = onLeaveEmployees.map(e => e.employee_name).join(", ");
		bulkErrorMessage.value = `Cannot update attendance because ${names} is already on leave. Please delete the leave application and the attendance entry first.`;
		return;
	}

	// Check if any selected employee already has attendance entries
	if (existingEmployeesWithAttendanceCount.value > 0) {
		showConfirmModal.value = true;
		return;
	}

	await executeBulkAttendanceSubmit();
}

async function confirmAndSubmit() {
	showConfirmModal.value = false;
	await executeBulkAttendanceSubmit();
}

async function executeBulkAttendanceSubmit() {
	const payload = selectedBulkEmployees.value.map(empId => {
		const emp = bulkEmployeeList.value.find(e => e.name === empId);
		return {
			employee: empId,
			from_date: selectionMode.value === "range" ? bulkForm.value.fromDate : bulkForm.value.date,
			to_date: selectionMode.value === "range" ? bulkForm.value.toDate : bulkForm.value.date,
			status: emp.status,
			shift: emp.shift || null,
			late_entry: bulkForm.value.late_entry ? 1 : 0,
			early_exit: bulkForm.value.early_exit ? 1 : 0,
			avoid_holidays: bulkForm.value.avoid_holidays ? 1 : 0,
		};
	});

	submittingBulkAttendance.value = true;
	try {
		await markBulkAttendanceResource.fetch({
			data: JSON.stringify(payload),
		});
		emit("save-success");
		close();
	} catch (err) {
		bulkErrorMessage.value = "Failed to submit bulk attendance: " + getErrorMessage(err);
	} finally {
		submittingBulkAttendance.value = false;
	}
}

watch(
	() => bulkForm.value.status,
	(newStatus) => {
		bulkEmployeeList.value.forEach(emp => {
			if (!emp.is_status_dirty) {
				emp.status = newStatus;
			}
		});
	}
);

watch(
	() => bulkForm.value.shift,
	(newShift) => {
		bulkEmployeeList.value.forEach(emp => {
			if (!emp.is_shift_dirty) {
				emp.shift = newShift;
			}
		});
	}
);

watch(
	() => [bulkFilters.value.department, bulkFilters.value.designation, bulkForm.value.date],
	() => {
		if (props.modelValue && selectionMode.value === "single") {
			fetchBulkEmployees();
		}
	}
);

watch(
	() => props.modelValue,
	newVal => {
		if (newVal) {
			openBulkAttendance();
		}
	}
);
</script>
