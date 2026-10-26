<template>
	<div class="space-y-4 sm:space-y-5 tab-fill">
		<div>
			<h2 class="section-title">Check-ins</h2>
			<p class="section-subtitle">Raw punches from the terminals, newest first.</p>
		</div>

		<div class="glass-card !p-3">
			<div class="flex flex-wrap items-center gap-2">
				<div v-if="showEmployeeFilter" class="flex-1 min-w-[180px]">
					<label class="sr-only">Employee</label>
					<SearchableDropdown
						v-model="selectedCheckinsEmployee"
						:options="attendanceStore.employeeList"
						labelKey="employee_name"
						valueKey="name"
						placeholder="All employees"
						showAllOption
						allOptionLabel="All employees"
					/>
				</div>
				<div class="flex-1 min-w-[200px]">
					<label class="sr-only">Date range</label>
					<DateRangePicker v-model:fromDate="filterFromDate" v-model:toDate="filterToDate" v-model:preset="selectedPreset" />
				</div>
			</div>
		</div>

		<!-- Server-side list: one page at a time (LIMIT/OFFSET) via DataTable. -->
		<DataTable
			:columns="listColumns"
			:rows="pager.state.rows"
			:actions="actionsForLog"
			:row-key="'name'"
			:loading="pager.state.loading"
			empty-text="No check-ins for this period."
			:show-pager="true"
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
		>
			<template #cell-time="{ row }">
				<span class="block whitespace-nowrap">{{ formatDateTime(row.time) }}</span>
				<span class="block text-xs font-normal text-[#5C6169] dark:text-white/60">
					{{ formatDay(row.time) }}<span class="md:hidden"> · {{ row.employee_name || row.employee }}</span>
				</span>
			</template>
			<template #cell-employeeName="{ row }">{{ row.employee_name || row.employee || "—" }}</template>
			<template #cell-logType="{ row }">
				<!-- IN and OUT are opposites, so they get opposite colours
				     rather than two shades of the same one. -->
				<span class="premium-tag inline-flex items-center gap-1" :class="row.log_type === 'IN' ? 'tag-emerald' : 'tag-neutral'">
					<span class="material-symbols-outlined !text-[14px]">{{ row.log_type === 'IN' ? 'login' : 'logout' }}</span>
					{{ row.log_type }}
				</span>
			</template>
			<template #cell-device_id="{ row }">
				<span class="block truncate max-w-[200px]" :title="row.device_id">{{ row.device_id || "—" }}</span>
			</template>
			<template #cell-shift="{ row }">{{ row.shift || "—" }}</template>
		</DataTable>
	</div>
</template>

<script setup>
import DataTable from '@/components/DataTable.vue'
import { useServerPager } from '@/composables/useServerPager.js'
import { notify, ask } from '@/utils/feedback.js'
import { ref, computed, onMounted, watch } from "vue";
import { createResource } from "frappe-ui";
import { useEmployeeStore } from "@/stores/employee";
import { useAttendanceStore } from "@/stores/attendance";
import SearchableDropdown from "@/components/SearchableDropdown.vue";
import DateRangePicker from "@/components/DateRangePicker.vue";

const employeeStore = useEmployeeStore();
const attendanceStore = useAttendanceStore();

const selectedCheckinsEmployee = ref("");
const canDeleteCheckin = ref(false);

const filterFromDate = ref("");
const filterToDate = ref("");
const selectedPreset = ref("All Time");

const checkinsResource = createResource({
	url: "arijentek_core.api.attendance.get_employee_checkins",
	auto: false,
});

/* Server-side fetch: `page`/`page_size` are passed to the API (LIMIT/OFFSET),
   and the response holds the current page + total. Returns { rows, total }
   for useServerPager. Handles both the paginated dict (page_size > 0) and
   the legacy list (page_size = 0) responses. */
async function fetchCheckins(page, size) {
	const params = { page: page, page_size: size };
	if (showEmployeeFilter.value) {
		params.override_employee_id = selectedCheckinsEmployee.value || "";
	} else {
		const empId = employeeStore.employee?.name;
		if (!empId) {
			return { rows: [], total: 0 };
		}
		params.employee_id = empId;
	}
	if (selectedPreset.value !== "All Time" && filterFromDate.value && filterToDate.value) {
		params.start_date = filterFromDate.value;
		params.end_date = filterToDate.value;
	}
	try {
		await checkinsResource.fetch(params);
		const res = checkinsResource.data;
		const rows = Array.isArray(res) ? res : (res?.data || []);
		const total = Array.isArray(res) ? res.length : Number(res?.total || 0);
		return { rows, total };
	} catch (e) {
		console.error("Checkins fetch failed:", e);
		return { rows: [], total: 0 };
	}
}

/* Server-side pager: one page at a time (LIMIT/OFFSET). Stale-while-revalidate
   keeps the previous page visible while the next loads; a stale fetch is dropped. */
const pager = useServerPager((page, size) => fetchCheckins(page, size), { size: 10 });

/* Column declarations for the list (order = render order; `className`
   carries the responsive hiding). */
const listColumns = [
	{ key: "time", label: "When", className: "table-td-strong whitespace-nowrap" },
	{ key: "employeeName", label: "Employee", className: "hidden md:table-cell" },
	{ key: "logType", label: "Type" },
	{ key: "device_id", label: "Device", className: "hidden lg:table-cell" },
	{ key: "shift", label: "Shift", className: "hidden sm:table-cell" },
];

/* Per-row actions, gated by permission. */
function actionsForLog(row) {
	return [
		{ label: 'Delete check-in', icon: 'delete', danger: true, show: canDeleteCheckin.value, onClick: () => handleDeleteCheckin(row) },
	];
}

const showEmployeeFilter = computed(() => attendanceStore.employeeList.length > 0);

function formatDateTime(timeStr) {
	if (!timeStr) return "—";
	const d = new Date(timeStr);
	return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) +
		" " +
		d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: true });
}

function formatDay(dateStr) {
	return new Date(dateStr).toLocaleDateString("en-US", { weekday: "long" });
}

async function handleDeleteCheckin(log) {
	const logName = log.name || "";
	if (!logName) {
		notify("No check-in record exists.");
		return;
	}

	if (!await ask("This will affect your shift hour calculation. Are you sure you want to delete?")) {
		return;
	}

	try {
		const deleteRes = createResource({
			url: "arijentek_core.api.attendance.delete_employee_checkin",
			auto: false,
		});
		await deleteRes.fetch({
			checkin_name: logName,
		});
		await pager.fetchPage();
	} catch (err) {
		notify(err.message || "Failed to delete check-in record.");
	}
}

watch([filterFromDate, filterToDate, selectedCheckinsEmployee], () => {
	// Reset to page 1. The pager's own [page, size] watch re-fetches when the
	// page actually changes; if it is already 1, fetch directly so a filter
	// change on page 1 still refreshes.
	if (pager.state.page !== 1) {
		pager.state.page = 1;
	} else {
		pager.fetchPage();
	}
});

onMounted(async () => {
	await employeeStore.init();
	await attendanceStore.fetchEmployeeList();
	try {
		canDeleteCheckin.value = await attendanceStore.checkCanDeleteCheckin();
	} catch (e) {
		canDeleteCheckin.value = false;
	}
	await pager.fetchPage();
});
</script>
