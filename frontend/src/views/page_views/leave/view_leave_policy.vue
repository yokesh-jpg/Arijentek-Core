<template>
	<Dialog :options="{ size: '2xl' }" v-model="show">
		<template #body>
			<div class="modal-panel">
				<!-- Header -->
				<header class="modal-header">
					<div>
						<h3 class="modal-title truncate">Leave policy details</h3>
						<p class="text-[12px] text-[#656A72] dark:text-white/60 truncate tabular-nums">{{ details?.name || leavePolicyId }}</p>
					</div>
					<div class="flex items-center gap-2 relative">
						<!-- More Actions Dropdown -->
						<RowActions v-if="details && (leaveStore.canEditLeavePolicy || leaveStore.canDeleteLeavePolicy)" :actions="[
								{ label: 'Edit', icon: 'edit', show: !!(leaveStore.canEditLeavePolicy), onClick: () => { show = false; emit('edit', details.name) } },
								{ divider: true },
								{ label: 'Delete', icon: 'delete', danger: true, show: !!(leaveStore.canDeleteLeavePolicy), onClick: () => { show = false; emit('delete', details.name) } },
							]" />

						<!-- Close Button -->
						<button @click="show = false" class="btn-icon-ghost shrink-0" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span></button>
					</div>
				</header>

				<!-- Loading State -->
				<div v-if="loading" class="flex flex-col items-center justify-center py-24 bg-white dark:bg-surface-1">
					<span class="material-symbols-outlined text-4xl animate-spin text-accent dark:text-accent-light mb-4">progress_activity</span>
					<p class="text-sm font-medium text-[#5C6169] dark:text-white/65">Loading leave policy details...</p>
				</div>

				<!-- Error State -->
				<div v-else-if="error" class="empty-state">
						<span class="material-symbols-outlined !text-[28px] text-red-600 dark:text-red-400">error</span>
						<p class="empty-state-text">Could not load this record</p>
						<p class="text-[12px] text-[#656A72] dark:text-white/55">{{ error }}</p>
					</div>

				<!-- Content -->
				<div v-else-if="details" class="p-6 overflow-y-auto min-h-[40vh] flex flex-col gap-6">
					
					<div class="grid grid-cols-1 gap-6">
						<!-- Title Info -->
						<div class="flex flex-col gap-1.5">
							<p class="status-label">Title</p>
							<div class="flex items-center gap-2 p-3 bg-white dark:bg-black/20 border border-black/[0.07] dark:border-white/5 rounded-[12px]">
								<span class="material-symbols-outlined text-[#656A72] dark:text-white/60 text-lg">policy</span>
								<p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.title }}</p>
							</div>
						</div>
					</div>

					<div class="flex flex-col gap-2 border border-black/[0.07] dark:border-white/10 rounded-[12px] p-4 bg-white dark:bg-black/10">
						<h3 class="text-sm font-semibold text-[#17181B] dark:text-white/80 mb-2">Leave Allocations</h3>
						<div class="overflow-visible">
							<table class="w-full text-left border-collapse min-w-[400px]">
								<thead>
									<tr>
										<th class="table-th">Leave type</th>
										<th class="!text-right table-th">Annual allocation</th>
									</tr>
								</thead>
								<tbody>
									<tr v-for="(row, index) in details.leave_policy_details" :key="index" class="border-b last:border-0 border-black/[0.05] dark:border-white/[0.06]">
										<td class="table-td">
											<p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ row.leave_type }}</p>
										</td>
										<td class="!text-right table-td">
											<p class="text-sm font-medium text-[#17181B] dark:text-white">{{ row.annual_allocation }}</p>
										</td>
									</tr>
									<tr v-if="!details.leave_policy_details || !details.leave_policy_details.length">
										<td colspan="2" class="px-4 py-6 text-center text-sm text-[#5C6169] dark:text-white/65 font-medium">
											No leave allocations added to this policy.
										</td>
									</tr>
								</tbody>
							</table>
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
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { Dialog, call } from 'frappe-ui';
import { getErrorMessage } from '../../../utils.js';
import { useLeaveStore } from '../../../stores/leave';
import RowActions from '@/components/RowActions.vue';

const leaveStore = useLeaveStore();

const props = defineProps({
	modelValue: {
		type: Boolean,
		required: true
	},
	leavePolicyId: {
		type: String,
		required: true
	}
});

const emit = defineEmits(['update:modelValue', 'edit', 'delete']);

const show = computed({
	get: () => props.modelValue,
	set: (val) => emit('update:modelValue', val)
});

const details = ref(null);
const loading = ref(false);
const error = ref('');
const activeDetailActionMenu = ref(false);

const fetchDetails = async () => {
	if (!props.leavePolicyId) return;
	
	loading.value = true;
	error.value = '';
	try {
		const res = await call('arijentek_core.api.leave.get_leave_policy', { name: props.leavePolicyId });
		details.value = res;
	} catch (err) {
		error.value = getErrorMessage(err, 'Failed to fetch Leave Policy details');
	} finally {
		loading.value = false;
	}
};

watch(() => props.modelValue, (newVal) => {
	if (newVal) {
		fetchDetails();
		activeDetailActionMenu.value = false;
	}
});

watch(() => props.leavePolicyId, () => {
	if (show.value) {
		fetchDetails();
	}
});

// Close dropdown when clicking outside
const closeDropdown = (e) => {
	if (!e.target.closest('.dropdown-menu') && !e.target.closest('.more_vert')) {
		activeDetailActionMenu.value = false;
	}
};

onMounted(() => {
	document.addEventListener('click', closeDropdown);
});

onUnmounted(() => {
	document.removeEventListener('click', closeDropdown);
});
</script>
