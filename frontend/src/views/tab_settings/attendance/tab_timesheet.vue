<template>
	<div class="space-y-4 sm:space-y-5 tab-fill">
		<div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
			<div>
				<h2 class="section-title">Timesheets</h2>
				<p class="section-subtitle">Weekly hours submitted for approval.</p>
			</div>
			<button v-if="canCreateTimesheet" @click="openAddDialog" class="btn-primary">
				<span class="material-symbols-outlined !text-[18px]">add</span>
				New timesheet
			</button>
		</div>

		<div class="glass-card !p-3">
			<div class="flex flex-wrap items-center gap-2">
				<div class="relative flex-[2] min-w-[220px]">
						<span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/55 pointer-events-none">search</span>
						<input v-model="searchText" type="text" placeholder="Timesheet ID, e.g. TS-2026-00042" aria-label="Search" class="field-input !pl-9" />
					</div>
				<div v-if="canManageTimesheets" class="flex-1 min-w-[180px]">
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
				<!-- Include Void Option -->
				<label class="flex items-center gap-2 text-xs font-medium text-[#5C6169] dark:text-white/70 cursor-pointer px-2 py-1 select-none">
					<input type="checkbox" v-model="includeVoid" class="w-4 h-4 rounded text-accent dark:text-accent-light bg-black/[0.03] dark:bg-white/[0.05] border-black/[0.1] dark:border-white/[0.1] focus:ring-2 focus:ring-accent/30 cursor-pointer" />
					<span>Include Void</span>
				</label>
			</div>
		</div>

		<!-- Server-side list: one page at a time (LIMIT/OFFSET) via DataTable. -->
		<DataTable
			:columns="listColumns"
			:rows="pager.state.rows"
			:actions="actionsForRecord"
			:row-key="'name'"
			:loading="pager.state.loading"
			empty-text="No timesheets yet."
			:show-pager="true"
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			:on-row-click="(row) => openViewDialog(row.name)"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
		>
			<template #cell-period="{ row }">
				<span class="block whitespace-normal sm:whitespace-nowrap">{{ formatDate(row.start_date) }} – {{ formatDate(row.end_date) }}</span>
				<span class="block text-xs font-normal text-[#5C6A72] dark:text-white/60">
					<span class="sm:hidden">{{ formatHours(row.total_hours) }} · </span>{{ row.name }}<span class="md:hidden"> · {{ row.employee_name || row.employee }}</span>
				</span>
			</template>
			<template #cell-employee="{ row }">
				{{ row.employee_name || row.employee || "—" }}
			</template>
			<template #cell-hours="{ row }">
				{{ formatHours(row.total_hours) }}
			</template>
			<template #cell-status="{ row }">
				<span class="premium-tag" :class="getStatusClasses(row.status)">{{ row.status }}</span>
			</template>
		</DataTable>

		<CreateTimesheet v-model="showAddTimesheetDialog" :record="selectedRecordToEdit" @save-success="onSaveSuccess" />

		<div v-if="showViewModal" class="modal-scrim" @click="showViewModal = false">
			<div class="relative w-full max-w-4xl" @click.stop>
				<ViewTimesheet v-if="selectedViewId" :id="selectedViewId" @close="showViewModal = false" @refresh="onViewRefresh" @edit="onViewEdit" />
			</div>
		</div>
	</div>
</template>

<script setup>
import DataTable from '@/components/DataTable.vue'
import { useServerPager } from '@/composables/useServerPager.js'
import { notify, ask } from '@/utils/feedback.js'
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { call } from "frappe-ui";
import { useAttendanceStore } from "@/stores/attendance";
import CreateTimesheet from "../../forms/attendance/create_timesheet.vue";
import ViewTimesheet from "../../page_views/attendance/view_timesheet.vue";
import SearchableDropdown from "@/components/SearchableDropdown.vue";
import { getErrorMessage } from "@/utils";

const attendanceStore = useAttendanceStore();

const searchText = ref("");
const includeVoid = ref(false);
const showAddTimesheetDialog = ref(false);
const selectedRecordToEdit = ref(null);

const canManageTimesheets = ref(false);
const selectedEmployee = ref("");

const showViewModal = ref(false);
const selectedViewId = ref("");

// Permissions computed properties loaded from the attendance store
const canCreateTimesheet = computed(() => attendanceStore.createTimesheetPermissionResource.data ?? true);
const canReadTimesheet = computed(() => attendanceStore.readTimesheetPermissionResource.data ?? true);
const canEditTimesheet = computed(() => attendanceStore.editTimesheetPermissionResource.data ?? true);
const canDeleteTimesheet = computed(() => attendanceStore.deleteTimesheetPermissionResource.data ?? true);

/* Server-side fetch: `page`/`page_size` are passed to the API (LIMIT/OFFSET),
   and the response holds the current page + total. Returns { rows, total }
   for useServerPager. Handles both the paginated dict (page_size > 0) and
   the legacy list (page_size = 0) responses. */
async function fetchTimesheets(page, size) {
	const params = {
		page: page,
		page_size: size,
		search_text: searchText.value || "",
		employee: selectedEmployee.value || "",
		include_void: includeVoid.value,
	};
	try {
		const res = await call("arijentek_core.api.attendance.get_time_sheet_list", params);
		const rows = Array.isArray(res) ? res : (res?.data || []);
		const total = Array.isArray(res) ? res.length : Number(res?.total || 0);
		return { rows, total };
	} catch (e) {
		console.error("Timesheet fetch failed:", e);
		return { rows: [], total: 0 };
	}
}

/* Server-side pager: one page at a time (LIMIT/OFFSET). Stale-while-revalidate
   keeps the previous page visible while the next loads; a stale fetch is dropped. */
const pager = useServerPager((page, size) => fetchTimesheets(page, size), { size: 10 });

/* Column declarations for the list (order = render order; `className`
   carries the responsive hiding). */
const listColumns = [
	{ key: "period", label: "Period", className: "table-td-strong" },
	{ key: "employee", label: "Employee", className: "hidden md:table-cell" },
	{ key: "hours", label: "Hours", className: "tabular-nums whitespace-nowrap hidden sm:table-cell" },
	{ key: "status", label: "Status" },
];

/* Per-row actions, gated by permission. The gate mirrors the old template:
   rows are only editable when not cancelled. */
function actionsForRecord(record) {
	return [
		{ label: "Edit", icon: "edit", show: !!(canEditTimesheet.value && record.status !== "Cancelled"), onClick: () => openEditDialog(record) },
		{ divider: true },
		{ label: "Delete", icon: "delete", danger: true, show: canDeleteTimesheet.value, onClick: () => handleDelete(record) },
	];
}

function openAddDialog() {
	selectedRecordToEdit.value = null;
	showAddTimesheetDialog.value = true;
}

function openEditDialog(record) {
	selectedRecordToEdit.value = record;
	showAddTimesheetDialog.value = true;
}

async function handleDelete(record) {
	if (!await ask(`Are you sure you want to delete timesheet ${record.name}?`)) {
		return;
	}
	try {
		const res = await call("arijentek_core.api.attendance.delete_timesheet", {
			name: record.name
		});
		if (res && res.success === false) {
			notify(res.error || 'Failed to delete timesheet');
			return;
		}
		await pager.fetchPage();
	} catch (e) {
		console.error("Failed to delete timesheet:", e);
		notify(getErrorMessage(e, "Failed to delete timesheet"));
	}
}

function openViewDialog(id) {
	selectedViewId.value = id;
	showViewModal.value = true;
}

function onViewRefresh() {
	pager.fetchPage();
}

function onViewEdit(record) {
	openEditDialog(record);
}

function onSaveSuccess(savedRecord) {
	pager.fetchPage();
}

function formatDate(dateStr) {
	if (!dateStr) return "-";
	const date = new Date(dateStr);
	return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

const floatPrecision = ref(2);

function formatHours(hours) {
	if (hours === undefined || hours === null) return `0.${'0'.repeat(floatPrecision.value)}h`;

	let hrsNum = 0;
	if (typeof hours === "string") {
		hrsNum = parseFloat(hours.replace("h", "").trim()) || 0;
	} else {
		hrsNum = hours;
	}
	return `${hrsNum.toFixed(floatPrecision.value)}h`;
}

function getStatusClasses(status) {
	// Same semantic chips as every other status in the app; "emerald" resolves
	// to the brand accent in this palette, so it could not mean success here.
	const s = status?.toLowerCase() || "";
	if (s === "submitted") return "tag-emerald";
	if (s === "draft") return "tag-amber";
	if (s === "cancelled") return "tag-red";
	return "tag-neutral";
}

// Filter changes reset to page 1. The pager's own [page, size] watch re-fetches
// when the page actually changes; if it is already 1, fetch directly so a filter
// change on page 1 still refreshes.
watch([searchText, selectedEmployee, includeVoid], () => {
	if (pager.state.page !== 1) {
		pager.state.page = 1;
	} else {
		pager.fetchPage();
	}
});

onMounted(async () => {
	try {
		const precision = await call("arijentek_core.api.attendance.get_float_precision");
		floatPrecision.value = parseInt(precision) || 2;
	} catch (e) {
		console.error("Failed to fetch float precision:", e);
	}

	try {
		const res = await call("arijentek_core.api.attendance.can_manage_timesheets");
		canManageTimesheets.value = !!res;
	} catch (e) {
		console.error("Failed to check timesheet manager permission:", e);
	}

	if (canManageTimesheets.value) {
		try {
			await attendanceStore.fetchEmployeeList();
		} catch (e) {
			console.error("Failed to load employee list:", e);
		}
	}

	// Fetch permissions
	await Promise.allSettled([
		attendanceStore.createTimesheetPermissionResource.fetch(),
		attendanceStore.readTimesheetPermissionResource.fetch(),
		attendanceStore.editTimesheetPermissionResource.fetch(),
		attendanceStore.deleteTimesheetPermissionResource.fetch(),
	]);

	// Fetch Timesheets
	if (canReadTimesheet.value) {
		await pager.fetchPage();
	}
});

onUnmounted(() => {
});
</script>

<style scoped>
thead th:first-child {
	border-top-left-radius: 0.75rem;
}
thead th:last-child {
	border-top-right-radius: 0.75rem;
}
</style>