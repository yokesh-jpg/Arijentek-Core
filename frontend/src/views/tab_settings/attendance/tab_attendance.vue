<template>
	<div class="space-y-4 sm:space-y-5 tab-fill">
		<!-- ===== Header ===== -->
		<div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
			<div>
				<h2 class="section-title">Attendance records</h2>
				<p class="section-subtitle">Marked days, clock times and hours.</p>
			</div>
			<div class="flex items-center gap-2 flex-wrap">
				<button v-if="canMark" @click="showActiveEmployeesDialog = true" class="btn-secondary">
					<span class="material-symbols-outlined !text-[18px]">pending_actions</span>
					Active
				</button>
				<button v-if="canMark" @click="showBulkAttendanceDialog = true" class="btn-secondary">
					<span class="material-symbols-outlined !text-[18px]">group_add</span>
					Bulk
				</button>
				<button v-if="canMark || showEmployeeFilter" @click="openAddDialog" class="btn-primary">
					<span class="material-symbols-outlined !text-[18px]">add</span>
					Add attendance
				</button>
				<button v-else @click="openRequestDialog" class="btn-primary">
					<span class="material-symbols-outlined !text-[18px]">add</span>
					Request attendance
				</button>
			</div>
		</div>

		<!-- ===== Filters ===== -->
		<button
			@click="filtersOpen = !filtersOpen"
			class="btn-secondary lg:hidden w-full justify-between"
			:aria-expanded="filtersOpen"
		>
			<span class="inline-flex items-center gap-2">
				<span class="material-symbols-outlined !text-[18px]">tune</span>
				Filters
			</span>
			<span class="material-symbols-outlined !text-[18px] transition-transform" :class="{ 'rotate-180': filtersOpen }">expand_more</span>
		</button>

		<div class="glass-card !p-3" :class="filtersOpen ? '' : 'hidden lg:block'">
			<div class="flex flex-wrap items-center gap-2">
				<div v-if="showEmployeeFilter" class="flex-1 min-w-[180px]">
					<label class="sr-only">Employee</label>
					<SearchableDropdown
						v-model="selectedEmployee"
						:options="attendanceStore.employeeList"
						labelKey="employee_name"
						valueKey="name"
						placeholder="All employees"
						showAllOption
						allOptionLabel="All employees"
					/>
				</div>
				<div v-if="!showGridView" class="flex-1 min-w-[150px]">
					<label class="sr-only">Status</label>
					<SearchableDropdown
						v-model="filterStatus"
						:options="['Present', 'Absent', 'Half Day', 'On Leave']"
						placeholder="All statuses"
						showAllOption
						allOptionLabel="All statuses"
					/>
				</div>
				<div class="flex-1 min-w-[200px]">
					<label class="sr-only">Date range</label>
					<DateRangePicker v-model:fromDate="filterFromDate" v-model:toDate="filterToDate" v-model:preset="selectedPreset" />
				</div>
				<div class="seg-group shrink-0">
					<button @click="showGridView = false" class="seg-item" :class="{ 'seg-item-active': !showGridView }">
						<span class="material-symbols-outlined !text-[16px]">view_list</span>
						<span class="hidden sm:inline">List</span>
					</button>
					<button @click="showGridView = true; fetchGridData()" class="seg-item" :class="{ 'seg-item-active': showGridView }">
						<span class="material-symbols-outlined !text-[16px]">grid_view</span>
						<span class="hidden sm:inline">Grid</span>
					</button>
				</div>
			</div>
		</div>

		<!-- ===== Grid ===== -->
		<div v-if="showGridView" class="table-card">
			<!-- Legend first: the cells are unreadable without it, so it is part
			     of the table rather than a separate panel above it. -->
			<!-- The grid is keyed to a month, but nothing in the old filter bar
			     could change it — it was pinned to the current one forever. -->
			<div class="flex items-center justify-between gap-3 px-5 py-3 border-b border-black/[0.06] dark:border-white/[0.07]">
				<h2 class="text-[13px] font-medium text-[#17181B] dark:text-white">{{ gridMonthLabel }}</h2>
				<div class="flex items-center gap-1">
					<button @click="stepGridMonth(-1)" class="btn-icon-ghost" aria-label="Previous month">
						<span class="material-symbols-outlined !text-[18px]">chevron_left</span>
					</button>
					<button @click="stepGridMonth(1)" class="btn-icon-ghost" aria-label="Next month">
						<span class="material-symbols-outlined !text-[18px]">chevron_right</span>
					</button>
				</div>
			</div>

			<div class="flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-3 border-b border-black/[0.06] dark:border-white/[0.07]">
				<span v-for="l in gridLegend" :key="l.code" class="inline-flex items-center gap-1.5 text-xs text-[#5C6169] dark:text-white/65">
					<span class="w-5 h-5 grid place-items-center rounded-[6px] text-xs font-semibold" :class="l.cls">{{ l.code }}</span>
					{{ l.label }}
				</span>
			</div>

			<div v-if="gridLoading" class="empty-state">
				<span class="material-symbols-outlined !text-[28px] text-accent dark:text-accent-light animate-spin">progress_activity</span>
				<p class="empty-state-text">Loading grid…</p>
			</div>
			<div v-else-if="filteredGridData.length === 0" class="empty-state">
				<span class="material-symbols-outlined !text-[28px] text-[#C4C7CC] dark:text-white/25">event_busy</span>
				<p class="empty-state-text">No attendance for this period.</p>
			</div>

			<div v-else class="overflow-x-auto table-scroll">
				<table class="w-full border-collapse">
					<thead class="table-head">
						<tr>
							<th class="sticky left-0 z-20 table-th !py-3 bg-[#F7F7F9] dark:bg-[#1f1f23] border-r border-black/[0.06] dark:border-white/[0.07] w-[150px] min-w-[150px] max-w-[150px] shadow-[6px_0_12px_-8px_rgba(0,0,0,0.18)]">
								Employee
							</th>
							<th v-for="d in gridDayHeaders" :key="d" class="table-th !px-0 !text-center w-[30px] min-w-[30px]">
								{{ d }}
							</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="row in filteredGridData" :key="row.employee" class="group/row border-b border-black/[0.05] dark:border-white/[0.06] last:border-0">
							<td class="sticky left-0 z-10 px-3 py-1.5 border-r border-black/[0.06] dark:border-white/[0.07] bg-white dark:bg-[#1a1a1e] group-hover/row:bg-[#FAFAFC] dark:group-hover/row:bg-[#212126] w-[150px] max-w-[150px] shadow-[6px_0_12px_-8px_rgba(0,0,0,0.12)] transition-colors">
								<div class="flex items-center gap-2 min-w-0">
									<span class="avatar-chip !w-7 !h-7 !text-[12px]">{{ gridInitials(row.employee_name) }}</span>
									<span class="text-[13px] font-medium text-[#17181B] dark:text-white truncate" :title="row.employee_name">{{ row.employee_name }}</span>
								</div>
							</td>
							<td v-for="day in row.days" :key="day.date" class="px-0 py-1.5 text-center">
								<button
									v-if="day.status"
									@click="openCellDetail(day, row.employee, row.employee_name)"
									class="w-6 h-6 mx-auto grid place-items-center rounded-[6px] text-xs font-semibold transition-transform hover:scale-110"
									:class="getCellClasses(day.status)"
									:title="`${day.date} — ${day.status}`"
									:aria-label="`${row.employee_name}, ${day.date}, ${day.status}`"
								>
									{{ getStatusIcon(day.status) }}
								</button>
								<span v-else class="block w-6 h-6 mx-auto grid place-items-center text-[#D8DADE] dark:text-white/15 text-xs">·</span>
							</td>
						</tr>
					</tbody>
				</table>
			</div>
		</div>

		<!-- Day detail -->
		<Teleport to="body">
			<div v-if="showCellDetail" @click.self="showCellDetail = false" class="modal-scrim">
				<div class="modal-panel !max-w-sm">
					<div class="modal-header">
						<div>
							<h3 class="modal-title">{{ detailCell.employeeName }}</h3>
							<p class="text-xs text-[#5C6169] dark:text-white/60 mt-0.5">{{ detailCell.date }}</p>
						</div>
						<button @click="showCellDetail = false" class="modal-close" aria-label="Close">
							<span class="material-symbols-outlined !text-[20px]">close</span>
						</button>
					</div>
					<div class="modal-body space-y-3">
						<div class="flex items-center justify-between gap-3">
							<span class="text-[13px] text-[#5C6169] dark:text-white/65">Status</span>
							<span class="premium-tag" :class="getStatusClasses(detailCell.status)">{{ detailCell.status }}</span>
						</div>
						<div class="flex items-center justify-between gap-3">
							<span class="text-[13px] text-[#5C6169] dark:text-white/65">Clock in</span>
							<span class="text-[13px] font-medium text-[#17181B] dark:text-white tabular-nums">{{ detailCell.inTime || "—" }}</span>
						</div>
						<div class="flex items-center justify-between gap-3">
							<span class="text-[13px] text-[#5C6169] dark:text-white/65">Clock out</span>
							<span class="text-[13px] font-medium text-[#17181B] dark:text-white tabular-nums">{{ detailCell.outTime || "—" }}</span>
						</div>
						<div class="flex items-center justify-between gap-3">
							<span class="text-[13px] text-[#5C6169] dark:text-white/65">Hours</span>
							<span class="text-[13px] font-medium text-[#17181B] dark:text-white tabular-nums">{{ detailCell.workingHoursFormatted }}</span>
						</div>
					</div>
					<div v-if="detailCell.name || canEditAttendance || canDeleteAttendance || showEmployeeFilter" class="modal-footer">
						<button v-if="detailCell.name && canDeleteAttendance" @click="handleDelete(detailCell)" class="btn-secondary !text-red-600 dark:text-red-400 dark:!text-red-400 mr-auto">
							<span class="material-symbols-outlined !text-[18px]">delete</span>Delete
						</button>
						<button v-if="detailCell.name" @click="viewAttendance(detailCell.name)" class="btn-secondary">View</button>
						<button v-if="detailCell.name ? canEditAttendance : (canEditAttendance || showEmployeeFilter)" @click="openEditDialog(detailCell)" class="btn-primary">
							{{ detailCell.name ? 'Edit' : 'Mark' }}
						</button>
					</div>
				</div>
			</div>
		</Teleport>

		<!-- ===== List ===== -->
		<DataTable
			v-if="!showGridView"
			:columns="listColumns"
			:rows="displayRows"
			:actions="actionsForRecord"
			:row-key="'name'"
			:on-row-click="onRowClick"
			:loading="pager.state.loading"
			empty-text="No attendance records match these filters."
			:show-pager="true"
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
		>
			<template #cell-date="{ row }">
				{{ formatDate(row.date) }}
				<span class="block text-xs font-normal text-[#5C6169] dark:text-white/60">{{ formatDay(row.date) }}<span class="sm:hidden"> · {{ row.totalHours }}</span></span>
			</template>
			<template #cell-employeeName="{ row }">{{ row.employeeName || "—" }}</template>
			<template #cell-clockIn="{ row }">{{ row.clockIn ? formatTime(row.clockIn) : "—" }}</template>
			<template #cell-clockOut="{ row }">{{ row.clockOut ? formatTime(row.clockOut) : "—" }}</template>
			<template #cell-status="{ row }"><span class="premium-tag" :class="getStatusClasses(row.status)">{{ row.status }}</span></template>
		</DataTable>

		<!-- Attendance Details Modal -->
		<Teleport to="body">
			<div v-if="showAttendanceViewModal" class="fixed inset-0 z-[100] flex items-center justify-center bg-[#0B0B0E]/70 backdrop-blur-sm p-4 md:p-6">
				<div class="w-full max-w-md">
					<AttendancePageView 
						:id="selectedAttendanceViewId" 
						:isModal="true" 
						@close="showAttendanceViewModal = false"
						@edit="(record) => { showAttendanceViewModal = false; openEditDialog(record); }"
						@delete="(record) => { showAttendanceViewModal = false; handleDelete(record); }"
					/>
				</div>
			</div>
		</Teleport>

		<!-- Subcomponent Form Dialogs -->
		<CreateAttendance 
			v-model="showAddAttendanceDialog" 
			:record="selectedRecordToEdit" 
			@save-success="onSaveSuccess" 
		/>
		
		<CreateBulkAttendance 
			v-model="showBulkAttendanceDialog" 
			@save-success="onSaveSuccess" 
		/>
		
		<ActiveEmployeesList 
			v-model="showActiveEmployeesDialog" 
			@save-success="onSaveSuccess" 
		/>
	</div>
</template>

<script setup>
import { notify, ask } from '@/utils/feedback.js'
import DataTable from '@/components/DataTable.vue'
import { useServerPager } from '@/composables/useServerPager'
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { createResource } from "frappe-ui";
import { useEmployeeStore } from "@/stores/employee";
import { useAttendanceStore } from "@/stores/attendance";
import AttendancePageView from "../../page_views/AttendancePageView.vue";

import CreateAttendance from "../../forms/attendance/create_attendance.vue";
import CreateBulkAttendance from "../../forms/attendance/create_bulk_attendance.vue";
import ActiveEmployeesList from "../../forms/attendance/active_employees_list.vue";

import SearchableDropdown from "@/components/SearchableDropdown.vue";
import DateRangePicker from "@/components/DateRangePicker.vue";

const emit = defineEmits(["request-attendance"]);

const filtersOpen = ref(false);

const gridMonthLabel = computed(() =>
	new Date(selectedYear.value, selectedMonth.value - 1, 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
);

function stepGridMonth(delta) {
	const d = new Date(selectedYear.value, selectedMonth.value - 1 + delta, 1);
	selectedYear.value = d.getFullYear();
	selectedMonth.value = d.getMonth() + 1;
	fetchGridData();
}

const gridLegend = [
	{ code: 'P', label: 'Present', cls: 'bg-green-500/[0.14] text-green-700 dark:text-green-300' },
	{ code: 'A', label: 'Absent', cls: 'bg-red-500/[0.14] text-red-700 dark:text-red-300' },
	{ code: 'HD', label: 'Half day', cls: 'bg-amber-500/[0.16] text-amber-700 dark:text-amber-300' },
	{ code: 'L', label: 'On leave', cls: 'bg-violet-500/[0.14] text-violet-700 dark:text-violet-300' },
	{ code: '·', label: 'Not rostered', cls: 'bg-black/[0.04] dark:bg-white/[0.07] text-[#656A72] dark:text-white/55' },
];

function gridInitials(name) {
	return (name || '?').split(' ').filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join('');
}

const employeeStore = useEmployeeStore();
const attendanceStore = useAttendanceStore();

const showAddAttendanceDialog = ref(false);
const showBulkAttendanceDialog = ref(false);
const showActiveEmployeesDialog = ref(false);
const selectedRecordToEdit = ref(null);

function openAddDialog() {
	selectedRecordToEdit.value = null;
	showAddAttendanceDialog.value = true;
}

const showAttendanceViewModal = ref(false);
const selectedAttendanceViewId = ref("");

function openRequestDialog() {
	emit("request-attendance");
}

function viewAttendance(id) {
	if (id) {
		selectedAttendanceViewId.value = id;
		showAttendanceViewModal.value = true;
	}
}

function openEditDialog(record) {
	selectedRecordToEdit.value = record;
	showAddAttendanceDialog.value = true;
	showCellDetail.value = false;
}

async function handleDelete(record) {
	const attName = record.name || record.attendance_name || "";
	if (!attName) {
		notify("No attendance record exists for this day.");
		return;
	}

	if (!await ask("Are you sure you want to delete this attendance record?")) {
		return;
	}

	try {
		const deleteRes = createResource({
			url: "arijentek_core.api.attendance.delete_attendance",
			auto: false,
		});
		await deleteRes.fetch({
			attendance_name: attName,
		});

		showCellDetail.value = false;

		await pager.fetchPage();
		await fetchMonthlyRoster();
		if (showGridView.value) {
			await fetchGridData();
		}
	} catch (err) {
		notify(err.message || "Failed to delete attendance record.");
	}
}

async function onSaveSuccess() {
	await pager.fetchPage();
	await fetchMonthlyRoster();
	if (showGridView.value) {
		await fetchGridData();
	}
}

const filterFromDate = ref("");
const filterToDate = ref("");
const selectedPreset = ref("All Time");

const canMark = ref(false);
const canEditAttendance = ref(false);
const canDeleteAttendance = ref(false);
const canManage = ref(false);
const canView = ref(false);

const showEmployeeFilter = computed(() => attendanceStore.employeeList.length > 0);
const selectedEmployee = ref("");

const showGridView = ref(false);
const gridData = ref([]);
const gridDayHeaders = ref([]);
const gridLoading = ref(false);
const showCellDetail = ref(false);
const detailCell = ref({
	employeeName: "",
	date: "",
	status: "",
	inTime: "",
	outTime: "",
	workingHoursFormatted: "",
});

const _today = new Date();
const selectedMonth = ref(_today.getMonth() + 1);
const selectedYear = ref(_today.getFullYear());
const filterStatus = ref("");

const monthOptions = computed(() => {
	const opts = [];
	const now = new Date();
	for (let offset = -12; offset <= 2; offset++) {
		const d = new Date(now.getFullYear(), now.getMonth() + offset, 1);
		const m = d.getMonth() + 1;
		const y = d.getFullYear();
		opts.push({
			value: `${y}-${m}`,
			label: d.toLocaleDateString("en-US", { month: "long", year: "numeric" }),
			month: m,
			year: y,
		});
	}
	return opts;
});

const selectedMonthKey = computed({
	get: () => `${selectedYear.value}-${selectedMonth.value}`,
	set: (val) => {
		const [y, m] = val.split("-").map(Number);
		selectedYear.value = y;
		selectedMonth.value = m;
	},
});

const workingHoursTarget = computed(() => attendanceStore.workingHoursTarget);
const roster = computed(() => attendanceStore.roster);

/* One raw attendance record (from the server) -> the display row. The server
   already sorts by name/date, so this is a pure per-record transform (status
   derivation + hours formatting + employee name). */
function transformRecord(record) {
	if (!record || !record.date) return null;
	const dateStr = record.date;
	const date = new Date(dateStr + "T00:00:00");
	const dayOfWeek = date.getDay();
	const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;

	const clockIn = record.in_time || null;
	const clockOut = record.out_time || null;
	const totalHours = record.working_hours || 0;

	let status = record.status || "";

	if (!isWeekend && status === "") {
		if (clockIn) {
			const inTime = new Date(clockIn);
			const lateThreshold = new Date(date);
			const startTime = roster.value?.start_time ? roster.value.start_time.split(":") : [9, 0];
			lateThreshold.setHours(parseInt(startTime[0]), parseInt(startTime[1]), 0);

			if (totalHours >= workingHoursTarget.value) status = "On Time";
			else if (inTime > lateThreshold) status = "Slight Late";
			else status = "On Time";
		} else {
			const todayDate = new Date();
			todayDate.setHours(0, 0, 0, 0);
			if (date < todayDate) status = "Absent";
		}
	}

	if (isWeekend && !status) status = "Weekend";

	const formattedHours = totalHours > 0 ? `${Math.floor(totalHours)}h ${Math.round((totalHours % 1) * 60)}m` : "0h 0m";
	return { name: record.name, employee: record.employee, date: dateStr, clockIn, clockOut, totalHours: formattedHours, status, employeeName: record.employee_name || "" };
}

const filteredGridData = computed(() => {
	if (!filterStatus.value || filterStatus.value === "") return gridData.value;
	return gridData.value.filter((row) =>
		row.days.some((d) => d.status === filterStatus.value)
	);
});

function getStatusIcon(status) {
 	if (status === "Present" || status === "On Time") return "P";
 	if (status === "Absent") return "A";
 	if (status === "Half Day") return "HD";
 	if (status === "On Leave") return "L";
 	if (status === "Holiday" || status === "Weekend") return "H";
 	return "";
}

function getCellClasses(status) {
	if (status === "Present" || status === "On Time") return "bg-green-500/[0.14] text-green-700 dark:text-green-300";
	if (status === "Absent") return "bg-red-500/[0.14] text-red-700 dark:text-red-300";
	if (status === "Half Day") return "bg-amber-500/[0.16] text-amber-700 dark:text-amber-300";
	if (status === "On Leave") return "bg-violet-500/[0.14] text-violet-700 dark:text-violet-300";
	if (status === "Holiday" || status === "Weekend") return "bg-sky-500/[0.12] text-sky-700 dark:text-sky-300";
	return "bg-black/[0.04] dark:bg-white/[0.07] text-[#656A72] dark:text-white/55";
}

function formatGridHours(hours) {
	if (!hours || hours === 0) return "—";
	return `${Math.floor(hours)}h ${Math.round((hours % 1) * 60)}m`;
}

function openCellDetail(day, employeeId, employeeName) {
	detailCell.value = {
		name: day.name || "",
		employee: employeeId || "",
		employeeName,
		date: day.date,
		status: day.status,
		inTime: day.in_time ? new Date(day.in_time).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: true }) : "—",
		outTime: day.out_time ? new Date(day.out_time).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: true }) : "—",
		workingHoursFormatted: formatGridHours(day.working_hours),
	};
	showCellDetail.value = true;
}

function closeCellDetail() {
	showCellDetail.value = false;
}

async function fetchGridData() {
	const empId = employeeStore.employee?.name;
	if (!empId && !showEmployeeFilter.value) return;

	gridLoading.value = true;
	return new Promise((resolve) => {
		const gridRes = createResource({
			url: "arijentek_core.api.attendance.get_attendance_grid",
			makeParams: () => {
				const params = { year: selectedYear.value, month: selectedMonth.value };
				if (showEmployeeFilter.value) {
					if (selectedEmployee.value) params.employee_id = selectedEmployee.value;
				} else {
					params.employee_id = empId;
				}
				return params;
			},
			auto: false,
			onSuccess(data) {
				if (data && data.grid) {
					gridData.value = data.grid;
					const m = selectedMonth.value;
					const y = selectedYear.value;
					const daysInMonth = new Date(y, m, 0).getDate();
					gridDayHeaders.value = Array.from({ length: daysInMonth }, (_, i) => String(i + 1));
				} else {
					gridData.value = [];
				}
				gridLoading.value = false;
				resolve();
			},
			onError() {
				gridData.value = [];
				gridLoading.value = false;
				resolve();
			},
		});
		gridRes.fetch();
	});
}

function getStatusClasses(status) {
	// Returns a tag-* class so the chip matches every other status chip in the app.
	const s = status?.toLowerCase();
	if (s === "present" || s === "on time") return "tag-emerald";
	if (s === "absent") return "tag-red";
	if (s === "half day" || s === "slight late") return "tag-amber";
	if (s === "on leave") return "tag-neutral";
	return "tag-neutral";
}
function formatDate(dateStr) {
	const date = new Date(dateStr);
	return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}
function formatDay(dateStr) {
	return new Date(dateStr).toLocaleDateString("en-US", { weekday: "long" });
}
function formatTime(timeStr) {
	if (!timeStr) return '-';
	const d = new Date(timeStr);
	if (isNaN(d.getTime())) return '-';
	return d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: true });
}

async function handleCheckPermission() {
  try {
    canMark.value = await attendanceStore.checkCanMarkAttendance();
  } catch (e) {
    canMark.value = false;
  }
  
  try {
    const editRes = createResource({ url: "arijentek_core.api.attendance.can_user_edit", auto: false });
    const deleteRes = createResource({ url: "arijentek_core.api.attendance.can_user_delete", auto: false });
    canEditAttendance.value = await editRes.fetch();
    canDeleteAttendance.value = await deleteRes.fetch();
  } catch (e) {
    canEditAttendance.value = false;
    canDeleteAttendance.value = false;
  }
}

async function fetchMonthlyRoster() {
  const empId = employeeStore.employee?.name;
  const targetEmpId = showEmployeeFilter.value ? selectedEmployee.value : empId;
  if (targetEmpId) {
    await attendanceStore.fetchMonthlyRoster(targetEmpId, selectedYear.value, selectedMonth.value);
  }
}

/* Server-side fetch: `page`/`page_size` are passed to the API (LIMIT/OFFSET),
   and the store's `history`/`historyTotal` hold the current page + total.
   Returns { rows, total } for useServerPager. */
async function fetchMonthlyHistory(page, pageSize) {
  const empId = employeeStore.employee?.name;
  const targetEmpId = showEmployeeFilter.value ? (selectedEmployee.value || "All") : empId;
  if (targetEmpId) {
    const params = {
      override_employee_id: showEmployeeFilter.value ? (selectedEmployee.value || "") : empId,
    };
    const isAllTime = selectedPreset.value === "All Time";
    if (!isAllTime && filterFromDate.value && filterToDate.value) {
      params.start_date = filterFromDate.value;
      params.end_date = filterToDate.value;
    } else if (!isAllTime) {
      params.month = selectedMonth.value;
      params.year = selectedYear.value;
    }
    if (filterStatus.value && filterStatus.value !== "All") {
      params.status = filterStatus.value;
    }
    if (page) params.page = page;
    if (pageSize) params.page_size = pageSize;
    await attendanceStore.fetchHistory(targetEmpId, params);
    return { rows: attendanceStore.history, total: attendanceStore.historyTotal };
  }
  return { rows: [], total: 0 };
}

/* Server-side pager: one page at a time (LIMIT/OFFSET). Stale-while-revalidate
   keeps the previous page visible while the next loads; a stale fetch is dropped. */
const pager = useServerPager((page, size) => fetchMonthlyHistory(page, size), { size: 10 });

/* The display rows for the current page: transform the raw server records. */
const displayRows = computed(() =>
	pager.state.rows
		.filter((r) => r && !r._summary)
		.map(transformRecord)
		.filter(Boolean)
);

/* Column declarations for the list view (order = render order; `className`
   carries the responsive hiding). */
const listColumns = [
	{ key: 'date', label: 'Date', className: 'table-td-strong whitespace-nowrap' },
	{ key: 'employeeName', label: 'Employee', className: 'hidden md:table-cell' },
	{ key: 'clockIn', label: 'In', className: 'tabular-nums hidden sm:table-cell' },
	{ key: 'clockOut', label: 'Out', className: 'tabular-nums hidden sm:table-cell' },
	{ key: 'totalHours', label: 'Hours', className: 'tabular-nums whitespace-nowrap hidden sm:table-cell' },
	{ key: 'status', label: 'Status' },
];

/* Per-row actions, gated by permission. 2+ actions fold into the More dropdown
   (RowActions maxInline=1), so a row never shows delete one mis-click from edit. */
function actionsForRecord(row) {
	return [
		{ label: 'Edit', icon: 'edit', show: canEditAttendance.value, onClick: () => openEditDialog(row) },
		{ divider: true },
		{ label: 'Delete', icon: 'delete', danger: true, show: canDeleteAttendance.value, onClick: () => handleDelete(row) },
	];
}

function onRowClick(row) {
	viewAttendance(row.name);
}

watch(filterFromDate, (val) => {
	if (val) {
		const parts = val.split("-");
		if (parts.length >= 2) {
			const y = parseInt(parts[0], 10);
			const m = parseInt(parts[1], 10);
			if (!isNaN(y) && !isNaN(m)) {
				selectedYear.value = y;
				selectedMonth.value = m;
			}
		}
	}
});

watch([selectedEmployee, filterStatus, filterFromDate, filterToDate], () => {
	// Reset to page 1. The pager's own [page, size] watch re-fetches when the
	// page actually changes; if it is already 1, fetch directly so a filter
	// change on page 1 still refreshes.
	if (pager.state.page !== 1) {
		pager.state.page = 1;
	} else {
		pager.fetchPage();
	}
	if (showGridView.value) {
		fetchGridData();
	}
});

watch(showGridView, (val) => {
	if (val) {
		fetchGridData();
	}
});

onMounted(async () => {
	await employeeStore.init();
	const empId = employeeStore.employee?.name;
	if (empId) {
		await attendanceStore.init(empId);
	}
	await handleCheckPermission();
	try {
		canManage.value = await attendanceStore.checkCanManageAttendance();
	} catch (e) {
		canManage.value = false;
	}
	try {
		canView.value = await attendanceStore.checkCanViewAttendance();
	} catch (e) {
		canView.value = false;
	}
	await attendanceStore.fetchEmployeeList();
	await pager.fetchPage();
	await fetchMonthlyRoster();
	if (showGridView.value) {
		await fetchGridData();
	}
});

onUnmounted(() => {
});
</script>
