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
						<!-- Sentinel element for IntersectionObserver -->
						<tr ref="gridSentinelRef" class="h-1">
							<td :colspan="gridDayHeaders.length + 1" class="p-0 border-0"></td>
						</tr>
					</tbody>
				</table>
			</div>

			<!-- Safe Load More Controls & Status Indicator -->
			<div v-if="gridPager.state.hasMore" class="flex flex-col items-center justify-center p-3 border-t border-black/[0.06] dark:border-white/[0.07] gap-1.5">
				<button
					@click="gridPager.loadMore"
					:disabled="gridPager.state.loadingMore"
					class="btn-secondary !text-xs !py-1.5 !px-4 inline-flex items-center gap-1.5"
				>
					<span v-if="gridPager.state.loadingMore" class="material-symbols-outlined !text-[16px] animate-spin">progress_activity</span>
					<span v-else class="material-symbols-outlined !text-[16px]">expand_more</span>
					{{ gridPager.state.loadingMore ? 'Loading more employees…' : `Load more (${remainingEmployeesCount} remaining)` }}
				</button>
				<p class="text-[11px] text-[#5C6169] dark:text-white/50">
					Showing {{ gridPager.state.items.length }} of {{ gridPager.state.total }} employees
				</p>
			</div>
			<div v-else-if="gridPager.state.total > 50" class="py-2.5 px-4 text-center border-t border-black/[0.06] dark:border-white/[0.07] text-[11px] text-[#5C6169] dark:text-white/50">
				All {{ gridPager.state.total }} employees loaded.
			</div>
		</div>

		<!-- Unrecorded day summary (recorded cells open the shared ViewAttendance modal) -->
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
					<div v-if="canEditAttendance || showEmployeeFilter" class="modal-footer">
						<button @click="openEditDialog(detailCell)" class="btn-primary">Mark</button>
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
			:loading="isAttendanceLoading && !displayRows.length"
			:empty-text="listEmptyText"
			:show-pager="true"
			:total="totalRecords"
			:page="currentPage"
			:page-size="pageSize"
			:sort="{ key: sortBy, dir: sortDir }"
			@update:page="currentPage = $event"
			@update:page-size="pageSize = $event; currentPage = 1"
			@sort="toggleSort"
		>
			<template #cell-date="{ row }">
				{{ formatDate(row.date) }}
				<span class="block text-xs font-normal text-[#5C6169] dark:text-white/60">{{ formatDay(row.date) }}<span class="sm:hidden"> · {{ row.totalHours }}</span></span>
			</template>
			<template #cell-name="{ row }">
				<span class="block tabular-nums break-words leading-snug sm:truncate">{{ row.name }}</span>
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
					<ViewAttendance
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
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { createResource } from "frappe-ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useEmployeeStore } from "@/stores/employee";
import { useAttendanceStore } from "@/stores/attendance";
import ViewAttendance from "../../page_views/attendance/view_attendance.vue";

import CreateAttendance from "../../forms/attendance/create_attendance.vue";
import CreateBulkAttendance from "../../forms/attendance/create_bulk_attendance.vue";
import ActiveEmployeesList from "../../forms/attendance/active_employees_list.vue";

import SearchableDropdown from "@/components/SearchableDropdown.vue";
import DateRangePicker from "@/components/DateRangePicker.vue";
import { useInfiniteServerPager } from "@/composables/useInfiniteServerPager.js";

const emit = defineEmits(["request-attendance"]);

const queryClient = useQueryClient();
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

		await queryClient.invalidateQueries({ queryKey: ['attendance-records'] });
		if (showGridView.value) {
			await fetchGridData();
		}
	} catch (err) {
		notify(err.message || "Failed to delete attendance record.");
	}
}

async function onSaveSuccess() {
	await queryClient.invalidateQueries({ queryKey: ['attendance-records'] });
	if (showGridView.value) {
		await fetchGridData();
	}
}

const filterFromDate = ref("");
const filterToDate = ref("");
const selectedPreset = ref("All Time");

const { data: permissionsData } = useQuery({
	queryKey: ['attendance-permissions'],
	queryFn: async () => {
		const [mark, edit, del, manage, view] = await Promise.all([
			attendanceStore.checkCanMarkAttendance().catch(() => false),
			createResource({ url: "arijentek_core.api.attendance.can_user_edit", auto: false }).fetch().catch(() => false),
			createResource({ url: "arijentek_core.api.attendance.can_user_delete", auto: false }).fetch().catch(() => false),
			attendanceStore.checkCanManageAttendance().catch(() => false),
			attendanceStore.checkCanViewAttendance().catch(() => false),
		]);
		return { mark: !!mark, edit: !!edit, del: !!del, manage: !!manage, view: !!view };
	},
	staleTime: Infinity,
});

const canMark = computed(() => permissionsData.value?.mark ?? false);
const canEditAttendance = computed(() => permissionsData.value?.edit ?? false);
const canDeleteAttendance = computed(() => permissionsData.value?.del ?? false);
const canManage = computed(() => permissionsData.value?.manage ?? false);
const canView = computed(() => permissionsData.value?.view ?? false);

const showEmployeeFilter = computed(() => attendanceStore.employeeList.length > 0);
const selectedEmployee = ref("");

const showGridView = ref(false);

const _today = new Date();
const selectedMonth = ref(_today.getMonth() + 1);
const selectedYear = ref(_today.getFullYear());

// Grid infinite scroll pager
const gridSentinelRef = ref(null);

const gridPager = useInfiniteServerPager(
	async (page, pageSize) => {
		const empId = employeeStore.employee?.name;
		if (!empId && !showEmployeeFilter.value) return { items: [], total: 0, hasMore: false };
		const id = showEmployeeFilter.value ? selectedEmployee.value : empId;
		const params = new URLSearchParams({
			year: selectedYear.value,
			month: selectedMonth.value,
			page,
			page_size: pageSize,
		});
		if (id) params.append('employee_id', id);
		const res = await fetch(`/api/method/arijentek_core.api.attendance.get_attendance_grid?${params.toString()}`);
		const json = await res.json();
		const msg = json.message || {};
		return {
			items: msg.grid || [],
			total: msg.total !== undefined ? msg.total : (msg.grid || []).length,
			hasMore: msg.has_more ?? false,
		};
	},
	{ pageSize: 50, itemKey: 'employee' }
);

const gridLoading = computed(() => gridPager.state.loadingInitial);
const gridData = computed(() => gridPager.state.items);
const remainingEmployeesCount = computed(() => Math.max(0, gridPager.state.total - gridPager.state.items.length));

function fetchGridData() {
	return gridPager.resetAndFetch();
}

watch(
	[() => showGridView.value, gridSentinelRef, () => gridPager.state.hasMore],
	([isOpen, sentinel, hasMore]) => {
		if (isOpen && sentinel && hasMore) {
			gridPager.attachObserver(gridSentinelRef);
		} else if (!hasMore) {
			gridPager.cleanupObserver();
		}
	},
	{ flush: 'post' }
);
const gridDayHeaders = computed(() => {
	const m = selectedMonth.value;
	const y = selectedYear.value;
	const daysInMonth = new Date(y, m, 0).getDate();
	return Array.from({ length: daysInMonth }, (_, i) => String(i + 1));
});

const showCellDetail = ref(false);
const detailCell = ref({
	employee: "",
	employeeName: "",
	date: "",
	status: "",
	inTime: "",
	outTime: "",
	workingHoursFormatted: "",
});
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
	/* Recorded days open the same ViewAttendance modal the list rows use; only
	   unrecorded days (e.g. leave days with no attendance doc) fall back to the
	   summary popup, which exists for its Mark action. The grid API sends the
	   record id as `attendance_name`. */
	if (day.attendance_name) {
		viewAttendance(day.attendance_name);
		return;
	}
	detailCell.value = {
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

const currentPage = ref(1);
const pageSize = ref(10);

/* Sort state for the list. Date desc is the natural reading order (newest
   first); both live in the query key, so a header click refetches from the
   server rather than reshuffling the current page. */
const sortBy = ref('date'); // 'date' | 'name'
const sortDir = ref('desc'); // 'asc' | 'desc'

function toggleSort(col) {
	if (sortBy.value === col) {
		sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc';
	} else {
		sortBy.value = col;
		sortDir.value = 'asc';
	}
	currentPage.value = 1;
}

const orderParam = computed(() => `${sortBy.value === 'date' ? 'attendance_date' : 'name'} ${sortDir.value}`);

const canFilterEmployees = computed(() => canView.value || canManage.value || attendanceStore.employeeList.length > 0);

const targetEmpId = computed(() => {
	if (canFilterEmployees.value) {
		return selectedEmployee.value || "All";
	}
	return employeeStore.employee?.name || "";
});

const attendanceQueryKey = computed(() => [
	'attendance-records',
	targetEmpId.value,
	currentPage.value,
	pageSize.value,
	selectedPreset.value,
	filterFromDate.value,
	filterToDate.value,
	selectedMonth.value,
	selectedYear.value,
	filterStatus.value,
	orderParam.value,
]);

const {
	data: attendanceData,
	isLoading: isAttendanceLoading,
	refetch: refetchAttendance,
} = useQuery({
	queryKey: attendanceQueryKey,
	queryFn: async () => {
		const empId = employeeStore.employee?.name;
		const target = targetEmpId.value;
		if (!target && !empId) return { rows: [], total: 0 };

		const params = {
			override_employee_id: canFilterEmployees.value ? (selectedEmployee.value || "") : empId,
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
		if (currentPage.value) params.page = currentPage.value;
		if (pageSize.value) params.page_size = pageSize.value;
		params.order_by = orderParam.value;

		await attendanceStore.fetchHistory(target, params);
		return {
			rows: [...attendanceStore.history],
			total: attendanceStore.historyTotal,
		};
	},
	/* An admin/HR viewer may have no Employee record of their own — they see
	   everyone through the employee filter (canFilterEmployees), so the query
	   must not be gated on a personal employee id. */
	enabled: computed(() => Boolean((employeeStore.employee?.name || canFilterEmployees.value) && permissionsData.value !== undefined)),
	placeholderData: (previousData) => previousData,
});

const totalRecords = computed(() => attendanceData.value?.total || 0);

const hasActiveFilters = computed(() =>
	Boolean(selectedEmployee.value || filterStatus.value || (filterFromDate.value && filterToDate.value))
);
const listEmptyText = computed(() =>
	hasActiveFilters.value ? "No attendance records match these filters." : "No attendance records yet."
);

/* The display rows for the current page: transform the raw server records. */
const displayRows = computed(() => {
	const raw = attendanceData.value?.rows || [];
	return raw
		.filter((r) => r && !r._summary)
		.map(transformRecord)
		.filter(Boolean);
});

/* Column declarations for the list view (order = render order; `className`
   carries the responsive hiding). Date leads for scanning; the doctype name
   is the row's ID anchor (Claim/Application/Reference elsewhere). Date and
   ID are server-side sortable via the header buttons. */
const listColumns = [
	{ key: 'date', label: 'Date', className: 'whitespace-nowrap', sortable: true },
	{ key: 'name', label: 'ID', className: 'table-td-strong max-w-[180px] sm:max-w-none', sortable: true },
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
	currentPage.value = 1;
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
	if (empId && !attendanceStore.roster) {
		attendanceStore.fetchRoster(empId).catch(() => {});
	}
	if (attendanceStore.employeeList.length === 0) {
		attendanceStore.fetchEmployeeList().catch(() => {});
	}
	if (showGridView.value) {
		fetchGridData();
	}
});

onUnmounted(() => {
});
</script>
