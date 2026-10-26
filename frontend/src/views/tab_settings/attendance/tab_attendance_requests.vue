<template>
	<div class="space-y-4 sm:space-y-5 tab-fill">
		<div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
			<div>
				<h2 class="section-title">Attendance requests</h2>
				<p class="section-subtitle">Work-from-home, on-duty and missed-punch corrections.</p>
			</div>
			<button @click="openRequestDialog" class="btn-primary">
				<span class="material-symbols-outlined !text-[18px]">add</span>
				New request
			</button>
		</div>

		<!-- Server-side list: one page at a time (LIMIT/OFFSET) via DataTable. -->
		<DataTable
			:columns="listColumns"
			:rows="pager.state.rows"
			:actions="actionsForReq"
			:row-key="'name'"
			:loading="pager.state.loading"
			empty-text="No attendance requests match these filters."
			:show-pager="true"
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
		>
			<template #cell-name="{ row }">
				<span class="block tabular-nums break-words leading-snug sm:truncate">{{ row.name }}</span>
				<span class="block sm:hidden text-xs font-normal text-[#5C6169] dark:text-white/60 leading-snug">
					{{ row.employee_name }} · {{ formatDate(row.from_date) }}
				</span>
			</template>
			<template #cell-employeeName="{ row }">
				<span class="truncate">{{ row.employee_name }}</span>
			</template>
			<template #cell-reason="{ row }">
				<span class="block truncate">{{ row.reason || '—' }}</span>
				<span v-if="row.explanation" class="block text-xs text-[#656A72] dark:text-white/55 truncate" :title="row.explanation">{{ row.explanation }}</span>
			</template>
			<template #cell-date="{ row }">
				{{ formatDate(row.from_date) }}
				<span v-if="row.to_date && row.to_date !== row.from_date"> – {{ formatDate(row.to_date) }}</span>
				<span v-if="row.half_day" class="block text-xs text-[#656A72] dark:text-white/55">Half day</span>
			</template>
			<template #cell-status="{ row }">
				<span class="premium-tag" :class="getRequestStatusClasses(row.docstatus)">{{ getRequestStatusLabel(row.docstatus) }}</span>
			</template>
		</DataTable>

		<CreateAttendanceRequest
			v-model="showRequestAttendanceDialog"
			:record="selectedRequestToEdit"
			@save-success="pager.fetchPage()"
			@close-dialog="emit('close-dialog')"
		/>
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
import { useAuthStore } from "@/stores/auth";
import { getErrorMessage } from "@/utils";
import CreateAttendanceRequest from "../../forms/attendance/create_attendance_request.vue";

const props = defineProps({
	openDialogOnMount: {
		type: Boolean,
		default: false,
	},
});

const emit = defineEmits(["close-dialog"]);

const employeeStore = useEmployeeStore();
const attendanceStore = useAttendanceStore();
const authStore = useAuthStore();

const requestsEmployee = ref("");
const requestsStatus = ref("");

const showRequestAttendanceDialog = ref(false);
const selectedRequestToEdit = ref(null);

const sessionUser = computed(() => authStore.user?.user || authStore.user?.email || authStore.user?.name || "");
const canSubmitRequest = computed(() => attendanceStore.submitAttendanceRequestPermissionResource?.data === true);

const filterFromDate = ref("");
const filterToDate = ref("");
const selectedPreset = ref("All Time");

const requestsListResource = createResource({
	url: "arijentek_core.api.attendance.get_attendance_requests",
	auto: false,
});

/* Server-side fetch: `page`/`page_size` are passed to the API (LIMIT/OFFSET),
   and the response holds the current page + total. Returns { rows, total }
   for useServerPager. Handles both the paginated dict (page_size > 0) and
   the legacy list (page_size = 0) responses. */
async function fetchRequests(page, size) {
	const params = {
		page: page,
		page_size: size,
		employee_id: requestsEmployee.value || null,
		status: requestsStatus.value || null,
		start_date: filterFromDate.value || null,
		end_date: filterToDate.value || null,
	};
	try {
		await requestsListResource.fetch(params);
		const res = requestsListResource.data;
		const rows = Array.isArray(res) ? res : (res?.data || []);
		const total = Array.isArray(res) ? res.length : Number(res?.total || 0);
		return { rows, total };
	} catch (e) {
		console.error("Attendance requests fetch failed:", e);
		return { rows: [], total: 0 };
	}
}

/* Server-side pager: one page at a time (LIMIT/OFFSET). Stale-while-revalidate
   keeps the previous page visible while the next loads; a stale fetch is dropped. */
const pager = useServerPager((page, size) => fetchRequests(page, size), { size: 10 });

/* Column declarations for the list (order = render order; `className`
   carries the responsive hiding). */
const listColumns = [
	{ key: "name", label: "Request", className: "table-td-strong max-w-[180px] sm:max-w-none" },
	{ key: "employeeName", label: "Employee", className: "hidden sm:table-cell" },
	{ key: "reason", label: "Reason", className: "hidden md:table-cell max-w-[280px]" },
	{ key: "date", label: "Date", className: "tabular-nums whitespace-nowrap hidden sm:table-cell" },
	{ key: "status", label: "Status" },
];

/* Per-row actions, gated by permission. The gate mirrors the old template:
   rows are only actionable for the owner's own drafts or for a user with
   submit permission. */
function actionsForReq(req) {
	const gate = (req.docstatus === 0 && req.owner === sessionUser.value) || canSubmitRequest.value;
	return [
		{ label: 'Approve', icon: 'check_circle', show: gate && req.docstatus === 0 && canSubmitRequest.value, onClick: () => handleApproveRequest(req.name) },
		{ label: 'Reject', icon: 'cancel', show: gate && req.docstatus === 0 && canSubmitRequest.value, onClick: () => handleRejectRequest(req.name) },
		{ label: 'Edit', icon: 'edit', show: req.docstatus === 0 && (req.owner === sessionUser.value || canSubmitRequest.value), onClick: () => openEditRequestDialog(req) },
		{ divider: true, show: gate },
		{ label: 'Delete', icon: 'delete', danger: true, show: gate, onClick: () => handleDeleteRequest(req.name) },
	];
}

function openRequestDialog() {
	selectedRequestToEdit.value = null;
	showRequestAttendanceDialog.value = true;
}

const showEmployeeFilter = computed(() => attendanceStore.employeeList.length > 0);

function openEditRequestDialog(req) {
	selectedRequestToEdit.value = req;
	showRequestAttendanceDialog.value = true;
}

async function handleDeleteRequest(name) {
	if (!await ask("Are you sure you want to delete this request?")) return;

	try {
		const deleteResource = createResource({
			url: "arijentek_core.api.attendance.delete_attendance_request",
			auto: false,
		});
		const res = await deleteResource.fetch({ request_name: name });

		if (res && res.success === false) {
			notify(res.message);
			return;
		}

		if (deleteResource.error) {
			throw new Error(getErrorMessage(deleteResource.error) || "Failed to delete request.");
		}
		await pager.fetchPage();
	} catch (err) {
		notify(getErrorMessage(err) || "Failed to delete request.");
	}
}

async function handleApproveRequest(name) {
	if (!await ask("Are you sure you want to approve this request?")) return;

	try {
		const approveResource = createResource({
			url: "arijentek_core.api.attendance.approve_attendance_request",
			auto: false,
		});
		await approveResource.fetch({ request_name: name });

		if (approveResource.error) {
			throw new Error(getErrorMessage(approveResource.error) || "Failed to approve request.");
		}
		await pager.fetchPage();
	} catch (err) {
		notify(getErrorMessage(err) || "Failed to approve request.");
	}
}

async function handleRejectRequest(name) {
	if (!await ask("Are you sure you want to reject this request?")) return;

	try {
		const rejectResource = createResource({
			url: "arijentek_core.api.attendance.reject_attendance_request",
			auto: false,
		});
		await rejectResource.fetch({ request_name: name });

		if (rejectResource.error) {
			throw new Error(getErrorMessage(rejectResource.error) || "Failed to reject request.");
		}
		await pager.fetchPage();
	} catch (err) {
		notify(getErrorMessage(err) || "Failed to reject request.");
	}
}

function getRequestStatusLabel(docstatus) {
	if (docstatus === 0) return "Draft";
	if (docstatus === 1) return "Approved";
	if (docstatus === 2) return "Rejected";
	return "Unknown";
}

function getRequestStatusClasses(docstatus) {
	if (docstatus === 0) return "tag-amber";
	if (docstatus === 1) return "tag-emerald";
	if (docstatus === 2) return "tag-red";
	return "tag-neutral";
}

function formatDate(dateStr) {
	const date = new Date(dateStr);
	return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

watch([requestsEmployee, requestsStatus, filterFromDate, filterToDate], () => {
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
	await pager.fetchPage();

	if (props.openDialogOnMount) {
		openRequestDialog();
		emit("close-dialog");
	}
});
</script>
