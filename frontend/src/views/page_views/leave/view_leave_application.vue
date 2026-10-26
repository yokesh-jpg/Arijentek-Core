<template>
	<Dialog :options="{ size: '3xl' }" v-model="show">
		<template #body>
			<div class="modal-panel">
				<!-- Header -->
				<header class="modal-header">
					<div>
						<h3 class="modal-title truncate">Leave application details</h3>
						<p class="text-[12px] text-[#656A72] dark:text-white/60 truncate tabular-nums">{{ details?.name || leaveApplicationId }}</p>
					</div>
					<div class="flex items-center gap-2 relative">
						<!-- More Actions Dropdown -->
						<RowActions v-if="details && (leaveStore.canEditLeaveApplication(details) || leaveStore.canDeleteLeaveApplication(details) || leaveStore.canApproveOrRejectLeaveApplication(details) || leaveStore.canDeleteApprovedRejectedLeaveApplication(details))" :actions="[
								{ label: 'Approve', icon: 'check_circle', show: !!(leaveStore.canApproveOrRejectLeaveApplication(details)), onClick: () => { handleUpdateStatus(details.name, 'Approved') } },
								{ label: 'Reject', icon: 'cancel', show: !!(leaveStore.canApproveOrRejectLeaveApplication(details)), onClick: () => { handleUpdateStatus(details.name, 'Rejected') } },
								{ label: 'Edit', icon: 'edit', show: !!(leaveStore.canEditLeaveApplication(details)), onClick: () => { show = false; emit('edit', details) } },
								{ divider: true },
								{ label: 'Delete', icon: 'delete', danger: true, show: !!(leaveStore.canDeleteLeaveApplication(details)), onClick: () => { show = false; emit('delete', details) } },
								{ label: 'Delete', icon: 'delete_forever', danger: true, show: !!(leaveStore.canDeleteApprovedRejectedLeaveApplication(details)), onClick: () => { show = false; emit('delete-approved-rejected', details) } },
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
								</div>
								<div class="ml-auto flex flex-col items-end gap-2">
									<span class="premium-tag" :class="getStatusStyle(details.status)">
										{{ details.status }}
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
								<p class="status-label">Total days</p>
								<p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.total_leave_days || 1 }}</p>
							</div>
							<div class="col-span-2">
								<p class="status-label">Duration</p>
								<p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ formatDate(details.from_date) }} - {{ formatDate(details.to_date) }}</p>
							</div>
						</div>
						<div class="modal-section">
							<p class="status-label">Reason for leave</p>
							<div class="text-[13px] text-[#17181B] dark:text-white/90 leading-relaxed whitespace-pre-wrap mt-1">
								{{ details.description || 'No reason provided.' }}
							</div>
						</div>
						
						<!-- Attachments Section -->
						<div v-if="attachments.length > 0" class="modal-section">
							<p class="status-label">Attachments</p>
							<div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
								<a v-for="file in attachments" :key="file.name" :href="file.file_url" target="_blank" class="flex items-center gap-3 p-3 bg-black/[0.02] dark:bg-white/[0.04] border border-black/[0.07] dark:border-white/10 rounded-[12px] hover:bg-white dark:hover:bg-white/[0.08] hover:border-accent/30 transition-all group shadow-sm">
									<div class="w-10 h-10 rounded-[12px] bg-green-500/[0.1] dark:bg-green-500/15 text-green-700 dark:text-green-300 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
										<span class="material-symbols-outlined">attachment</span>
									</div>
									<div class="overflow-hidden">
										<p class="text-[13px] font-medium text-[#17181B] dark:text-white truncate" :title="file.file_name">{{ file.file_name }}</p>
										<p class="text-xs text-[#5C6169] dark:text-white/65 mt-0.5">Click to view</p>
									</div>
								</a>
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
import { Dialog, createResource, call } from "frappe-ui";
import { useLeaveStore } from "@/stores/leave";
import { useEmployeeStore } from "@/stores/employee";
import RowActions from '@/components/RowActions.vue';

const props = defineProps({
	modelValue: {
		type: Boolean,
		default: false,
	},
	leaveApplicationId: {
		type: String,
		default: null,
	},
});

const emit = defineEmits(["update:modelValue", "edit", "delete", "status-updated", "delete-approved-rejected"]);

const show = ref(props.modelValue);
const leaveStore = useLeaveStore();
const employeeStore = useEmployeeStore();
const details = ref(null);
const loading = ref(false);
const error = ref("");
const activeDetailActionMenu = ref(false);
const attachments = ref([]);

watch(
	() => props.modelValue,
	(newVal) => {
		show.value = newVal;
		if (newVal && props.leaveApplicationId) {
			get_leave_appication_details(props.leaveApplicationId);
		}
	}
);

watch(show, (newVal) => {
	emit("update:modelValue", newVal);
});

async function get_leave_appication_details(id) {
	loading.value = true;
	error.value = "";
	details.value = null;

	const res = createResource({
		url: "arijentek_core.api.leave.get_leave_application",
		auto: false,
	});

	try {
		const data = await res.fetch({ name: id });
		if (data) {
			details.value = data;
			
			// Fetch attachments
			try {
				const files = await call('frappe.client.get_list', {
					doctype: 'File',
					filters: {
						attached_to_doctype: 'Leave Application',
						attached_to_name: id
					},
					fields: ['name', 'file_name', 'file_url']
				});
				attachments.value = files || [];
			} catch (fileErr) {
				console.error("Failed to fetch attachments", fileErr);
				attachments.value = [];
			}
		} else {
			error.value = "Leave application not found.";
			attachments.value = [];
		}
	} catch (err) {
		error.value = err?.messages?.[0] || "Failed to load leave application details";
	} finally {
		loading.value = false;
	}
}

async function handleUpdateStatus(name, status) {
	activeDetailActionMenu.value = false;
	if (!await ask(`Are you sure you want to mark this application as ${status}?`)) return;

	try {
		const res = await call("arijentek_core.api.leave.update_leave_status", { name, status });
		if (res && res.success === false) {
			notify(res.error || "Failed to update status");
		} else {
			notify(`Leave application marked as ${status}`, "success");
			emit("status-updated", { name, status });
			show.value = false;
		}
	} catch (err) {
		notify(err.message || "Failed to update status");
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

function getStatusStyle(status) {
	switch (status) {
		case "Open":
			return "tag-amber";
		case "Approved":
			return "tag-emerald";
		case "Rejected":
			return "tag-red";
		default:
			return "bg-black/[0.04] text-[#17181B] dark:bg-white/[0.06] dark:text-white/85";
	}
}
</script>
