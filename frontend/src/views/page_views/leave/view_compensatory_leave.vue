<template>
	<Dialog :options="{ size: '3xl' }" v-model="show">
		<template #body>
			<div class="modal-panel">
				<!-- Header -->
				<header class="modal-header">
					<div>
						<h3 class="modal-title truncate">Compensatory leave details</h3>
						<p class="text-[12px] text-[#656A72] dark:text-white/60 truncate tabular-nums">{{ details?.name || compLeaveId }}</p>
					</div>
					<div class="flex items-center gap-2 relative">
						<!-- More Actions Dropdown -->
						<RowActions v-if="details && hasActions" :actions="[
								{ label: 'Approve', icon: 'check_circle', show: !!(details.docstatus === 0 && canApprove), onClick: () => { handleApprove(details.name) } },
								{ label: 'Reject', icon: 'cancel', show: !!(details.docstatus === 0 && details.status !== 'Rejected' && canApprove), onClick: () => { handleReject(details.name) } },
								{ label: 'Edit', icon: 'edit', show: !!(details.docstatus === 0), onClick: () => { show = false; emit('edit', details) } },
								{ divider: true },
								{ label: 'Delete', icon: 'delete', danger: true, onClick: () => { show = false; emit('delete', details) } },
							]" />

						<button @click="show = false" class="btn-icon-ghost shrink-0" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span></button>
					</div>
				</header>

				<!-- Main Content -->
				<div class="flex-1 overflow-y-auto px-6 py-5" @click="activeDetailActionMenu = false">
					<div v-if="loading" class="flex flex-col items-center justify-center py-16 gap-3">
						<span class="w-5 h-5 rounded-full border-2 border-black/10 dark:border-white/15 border-t-accent animate-spin"></span>
						<span class="text-[13px] text-[#5C6169] dark:text-white/65">Loading details…</span>
					</div>

					<div v-else-if="error" class="empty-state">
						<span class="material-symbols-outlined !text-[28px] text-red-600 dark:text-red-400">error</span>
						<p class="empty-state-text">Could not load this record</p>
						<p class="text-[12px] text-[#656A72] dark:text-white/55">{{ error }}</p>
					</div>

					<div v-else-if="details">
						<div class="pb-5">
							<div class="flex items-center gap-4">
								<span class="avatar-chip !w-11 !h-11 !text-[14px]">{{ details.employee_name ? details.employee_name.charAt(0).toUpperCase() : '?' }}</span>
								<div>
									<p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.employee_name }}</p>
									<p class="text-xs font-medium text-[#5C6169] dark:text-white/65">{{ details.employee }}</p>
									<p v-if="details.department" class="text-xs font-medium text-[#656A72] dark:text-white/55 mt-0.5">{{ details.department }}</p>
								</div>
								<div class="ml-auto flex flex-col items-end gap-2">
									<span class="premium-tag" :class="getStatusStyle(details.docstatus, details.status)">
										{{ getStatusLabel(details.docstatus, details.status) }}
									</span>
								</div>
							</div>
						</div>
						<div class="pt-5 grid grid-cols-2 sm:grid-cols-4 gap-x-6 gap-y-5">
							<div>
								<p class="status-label">Leave type</p>
								<p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.leave_type }}</p>
							</div>
							<div>
								<p class="status-label">Half day</p>
								<p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.half_day ? 'Yes' : 'No' }}</p>
							</div>
							<div class="col-span-2">
								<p class="status-label">Work period</p>
								<p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ formatDate(details.work_from_date) }} - {{ formatDate(details.work_end_date) }}</p>
							</div>
						</div>
						<div v-if="details.half_day && details.half_day_date" class="px-6 pb-4">
							<div class="grid grid-cols-2 sm:grid-cols-4 gap-6">
								<div>
									<p class="status-label">Half day date</p>
									<p class="text-[14px] font-semibold text-amber-800 dark:text-amber-300 mt-1">{{ formatDate(details.half_day_date) }}</p>
								</div>
							</div>
						</div>
						<div v-if="details.leave_allocation" class="px-6 pb-4">
							<div class="grid grid-cols-2 sm:grid-cols-4 gap-6">
								<div class="col-span-2">
									<p class="status-label">Leave allocation</p>
									<p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.leave_allocation }}</p>
								</div>
							</div>
						</div>
						<div class="modal-section">
							<p class="status-label">Reason</p>
							<div class="text-[13px] text-[#17181B] dark:text-white/90 leading-relaxed whitespace-pre-wrap mt-1">
								{{ details.reason || 'No reason provided.' }}
							</div>
						</div>
					</div>
				</div>
				<footer class="px-5 py-4 border-t border-black/[0.07] dark:border-white/10 shrink-0">
					<button class="btn-secondary w-full" @click="show = false">Close</button>
				</footer>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { notify, ask } from '@/utils/feedback.js'
import { ref, watch, computed } from "vue";
import { Dialog, createResource } from "frappe-ui";
import { useLeaveStore } from "@/stores/leave";
import RowActions from '@/components/RowActions.vue';

const props = defineProps({
	modelValue: {
		type: Boolean,
		default: false,
	},
	compLeaveId: {
		type: String,
		default: null,
	},
	canApprove: {
		type: Boolean,
		default: false,
	},
});

const emit = defineEmits(["update:modelValue", "edit", "delete", "status-updated"]);

const show = ref(props.modelValue);
const leaveStore = useLeaveStore();
const details = ref(null);
const loading = ref(false);
const error = ref("");
const activeDetailActionMenu = ref(false);

const hasActions = computed(() => {
	if (!details.value) return false;
	const d = details.value;
	// Edit: draft only
	if (d.docstatus === 0) return true;
	// Delete: draft, or submitted/cancelled with submit perm
	// Delete is always offered, the same as on the list row.
	return true;
	// Approve/Reject: draft + canApprove
	if (d.docstatus === 0 && props.canApprove) return true;
	return false;
});

watch(
	() => props.modelValue,
	(newVal) => {
		show.value = newVal;
		if (newVal && props.compLeaveId) {
			fetchDetails(props.compLeaveId);
		}
	}
);

watch(show, (newVal) => {
	emit("update:modelValue", newVal);
});

async function fetchDetails(id) {
	loading.value = true;
	error.value = "";
	details.value = null;

	const res = createResource({
		url: "arijentek_core.api.leave.get_compensatory_leave_requests",
		auto: false,
	});

	try {
		const data = await res.fetch({ name: id });
		if (data) {
			details.value = data;
		} else {
			error.value = "Compensatory leave request not found.";
		}
	} catch (err) {
		error.value = err?.messages?.[0] || "Failed to load compensatory leave details";
	} finally {
		loading.value = false;
	}
}

async function handleApprove(name) {
	activeDetailActionMenu.value = false;
	if (!await ask("Are you sure you want to approve this compensatory leave request?")) return;

	const approveResource = createResource({
		url: "arijentek_core.api.leave.approve_compensatory_leave_request",
		auto: false,
	});

	try {
		const res = await approveResource.fetch({ name });
		if (res && res.success === false) {
			notify(res.error || "Failed to approve request");
		} else {
			emit("status-updated", { name, action: "approved" });
			show.value = false;
		}
	} catch (err) {
		notify(err.message || "Failed to approve request");
	}
}

async function handleReject(name) {
	activeDetailActionMenu.value = false;
	if (!await ask("Are you sure you want to reject this compensatory leave request?")) return;

	const rejectResource = createResource({
		url: "arijentek_core.api.leave.reject_compensatory_leave_request",
		auto: false,
	});

	try {
		const res = await rejectResource.fetch({ name });
		if (res && res.success === false) {
			notify(res.error || "Failed to reject request");
		} else {
			emit("status-updated", { name, action: "rejected" });
			show.value = false;
		}
	} catch (err) {
		notify(err.message || "Failed to reject request");
	}
}

function formatDate(dateStr) {
	if (!dateStr) return "";
	return new Date(dateStr).toLocaleDateString("en-US", {
		month: "short",
		day: "numeric",
		year: "numeric",
	});
}

function getStatusStyle(docstatus, status) {
	if (status === "Rejected") return "tag-red";
	if (docstatus === 0) return "tag-amber";
	if (docstatus === 1) return "tag-emerald";
	if (docstatus === 2) return "bg-black/[0.04] text-[#17181B] dark:bg-white/[0.06] dark:text-white/85";
	return "bg-black/[0.04] text-[#17181B] dark:bg-white/[0.06] dark:text-white/85";
}

function getStatusLabel(docstatus, status) {
	if (status === "Rejected") return "Rejected";
	if (docstatus === 0) return "Draft";
	if (docstatus === 1) return "Approved";
	if (docstatus === 2) return "Cancelled";
	return "Unknown";
}
</script>
