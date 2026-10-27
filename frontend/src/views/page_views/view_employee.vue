<template>
	<Dialog :options="{ size: '3xl' }" v-model="show">
		<template #body>
			<div class="modal-panel">
				<header class="modal-header">
					<div class="min-w-0">
						<h3 class="modal-title truncate">Employee details</h3>
						<p v-if="details?.employee_name" class="text-[13px] text-[#5C6169] dark:text-white/65 truncate">{{ details.employee_name }}</p>
						<p class="text-[12px] text-[#656A72] dark:text-white/55 truncate tabular-nums">{{ employeeId }}</p>
					</div>
					<div class="flex items-center gap-1 shrink-0">
						<button v-if="details && canEditThisEmployee" @click="emit('edit', { name: details.name }); show = false" class="btn-icon-ghost" aria-label="Edit" title="Edit">
							<span class="material-symbols-outlined !text-[18px]">edit</span>
						</button>
						<button v-if="details && teamStore.deleteEmployeePermissionResource?.data" @click="emit('delete', { name: details.name }); show = false" class="btn-danger-ghost" aria-label="Delete" title="Delete">
							<span class="material-symbols-outlined !text-[18px]">delete</span>
						</button>
						<button @click="show = false" class="btn-icon-ghost" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span></button>
					</div>
				</header>

				<div class="flex-1 overflow-y-auto px-6 py-5">
					<div v-if="loading" class="flex flex-col items-center justify-center py-16 gap-3">
						<span class="w-5 h-5 rounded-full border-2 border-black/10 dark:border-white/15 border-t-accent animate-spin"></span>
						<span class="text-[13px] text-[#5C6169] dark:text-white/65">Loading details…</span>
					</div>

					<div v-else-if="error" class="empty-state">
						<span class="material-symbols-outlined !text-[28px] text-red-600 dark:text-red-400">error</span>
						<p class="empty-state-text">Could not load this record</p>
						<p class="text-[12px] text-[#656A72] dark:text-white/55">{{ error }}</p>
						<button @click="fetchDetails" class="btn-secondary !h-9 mt-1">Try again</button>
					</div>

					<template v-else-if="details">
						<!-- Who: photo, role, status. -->
						<div class="flex items-center gap-4">
							<span class="avatar-chip !w-14 !h-14 !text-[18px] overflow-hidden shrink-0">
								<img v-if="details.image" :src="details.image" class="w-full h-full object-cover" alt="" />
								<template v-else>{{ details.employee_name ? details.employee_name.charAt(0).toUpperCase() : '?' }}</template>
							</span>
							<div class="min-w-0 flex-1">
								<p class="text-[14px] font-semibold text-[#17181B] dark:text-white truncate">{{ details.employee_name }}</p>
								<p class="text-[13px] text-[#5C6169] dark:text-white/65 truncate">{{ details.designation || 'No designation' }} · {{ details.department || 'No department' }}</p>
							</div>
							<span class="premium-tag shrink-0" :class="getStatusBadgeClass(details.status)">{{ details.status }}</span>
						</div>

						<!-- Personal -->
						<div class="mt-6 pt-5 border-t border-black/[0.07] dark:border-white/10">
							<p class="status-label flex items-center gap-1.5 mb-3"><span class="material-symbols-outlined !text-[16px]">person</span>Personal</p>
							<div class="grid grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-5">
								<div><p class="status-label">Employee ID</p><p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 tabular-nums">{{ details.name }}</p></div>
								<div><p class="status-label">Employee number</p><p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 tabular-nums">{{ details.employee_number || '—' }}</p></div>
								<div><p class="status-label">Gender</p><p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.gender || '—' }}</p></div>
								<div><p class="status-label">Salutation</p><p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.salutation || '—' }}</p></div>
								<div><p class="status-label">Date of birth</p><p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ formatDate(details.date_of_birth) || '—' }}</p></div>
								<div><p class="status-label">Date of joining</p><p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ formatDate(details.date_of_joining) || '—' }}</p></div>
							</div>
						</div>

						<!-- Contact -->
						<div class="mt-6 pt-5 border-t border-black/[0.07] dark:border-white/10">
							<p class="status-label flex items-center gap-1.5 mb-3"><span class="material-symbols-outlined !text-[16px]">call</span>Contact</p>
							<div class="grid grid-cols-1 md:grid-cols-3 gap-x-6 gap-y-5">
								<div class="min-w-0"><p class="status-label">Company email</p><p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 truncate">{{ details.company_email || '—' }}</p></div>
								<div class="min-w-0"><p class="status-label">Personal email</p><p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 truncate">{{ details.personal_email || '—' }}</p></div>
								<div><p class="status-label">Phone</p><p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 tabular-nums">{{ details.cell_number || '—' }}</p></div>
								<div class="md:col-span-3"><p class="status-label">Current address</p><p class="text-[13px] text-[#17181B] dark:text-white/90 leading-relaxed whitespace-pre-wrap mt-1">{{ details.current_address || 'Not provided' }}</p></div>
								<div class="md:col-span-3"><p class="status-label">Permanent address</p><p class="text-[13px] text-[#17181B] dark:text-white/90 leading-relaxed whitespace-pre-wrap mt-1">{{ details.permanent_address || 'Not provided' }}</p></div>
							</div>
						</div>

						<!-- Work -->
						<div class="mt-6 pt-5 border-t border-black/[0.07] dark:border-white/10">
							<p class="status-label flex items-center gap-1.5 mb-3"><span class="material-symbols-outlined !text-[16px]">work</span>Work</p>
							<div class="grid grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-5">
								<div><p class="status-label">Department</p><p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.department || '—' }}</p></div>
								<div><p class="status-label">Designation</p><p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.designation || '—' }}</p></div>
								<div><p class="status-label">Grade</p><p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.grade || '—' }}</p></div>
								<div><p class="status-label">Employment type</p><p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.employment_type || '—' }}</p></div>
								<div><p class="status-label">Branch</p><p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.branch || '—' }}</p></div>
								<div class="min-w-0">
									<p class="status-label">User account</p>
									<p class="text-[14px] font-semibold mt-1 truncate" :class="details.user_id ? 'text-[#17181B] dark:text-white' : 'text-[#656A72] dark:text-white/55'">{{ details.user_id || 'Not linked' }}</p>
								</div>
							</div>
						</div>

						<!-- Approvers. Three tinted cards in three colours said nothing the
						     captions do not; they read as ordinary fields now. -->
						<div class="mt-6 pt-5 border-t border-black/[0.07] dark:border-white/10">
							<p class="status-label flex items-center gap-1.5 mb-3"><span class="material-symbols-outlined !text-[16px]">verified_user</span>Approvers</p>
							<div class="grid grid-cols-1 md:grid-cols-3 gap-x-6 gap-y-5">
								<div><p class="status-label">Reports to</p><p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.reports_to_name || 'None' }}</p></div>
								<div><p class="status-label">Shift approver</p><p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.shift_approver_name || 'None' }}</p></div>
								<div><p class="status-label">Expense approver</p><p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.expense_approver_name || 'None' }}</p></div>
							</div>
						</div>

						<!-- Emergency contact -->
						<div class="mt-6 pt-5 border-t border-black/[0.07] dark:border-white/10">
							<p class="status-label flex items-center gap-1.5 mb-3"><span class="material-symbols-outlined !text-[16px]">emergency</span>Emergency contact</p>
							<div class="grid grid-cols-1 md:grid-cols-3 gap-x-6 gap-y-5">
								<div><p class="status-label">Name</p><p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.person_to_be_contacted || 'Not provided' }}</p></div>
								<div><p class="status-label">Phone</p><p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 tabular-nums">{{ details.emergency_phone_number || 'Not provided' }}</p></div>
								<div><p class="status-label">Relation</p><p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.relation || 'Not provided' }}</p></div>
							</div>
						</div>
					</template>
				</div>

				<footer class="px-5 py-4 border-t border-black/[0.07] dark:border-white/10 shrink-0">
					<button class="btn-secondary w-full" @click="show = false">Close</button>
				</footer>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue';
import { Dialog, createResource } from 'frappe-ui';
import { useTeamStore } from '../../stores/team.js';
import { useEmployeeStore } from '../../stores/employee.js';
import { useAuthStore } from '../../stores/auth.js';

const teamStore = useTeamStore();
const employeeStore = useEmployeeStore();
const authStore = useAuthStore();

const props = defineProps({
	modelValue: Boolean,
	employeeId: String
});

const emit = defineEmits(['update:modelValue', 'edit', 'delete']);

const show = computed({
	get: () => props.modelValue,
	set: (val) => emit('update:modelValue', val)
});

const loading = ref(true);
const error = ref('');
const details = ref(null);

const canEditThisEmployee = computed(() => {
	if (teamStore.editEmployeePermissionResource?.data) return true;
	const currentEmpId = employeeStore.employee?.name;
	const currentUserId = authStore.user?.user || authStore.user?.email;
	if (details.value && ((currentEmpId && details.value.name === currentEmpId) || (currentUserId && details.value.user_id && details.value.user_id === currentUserId))) {
		return true;
	}
	return false;
});

watch(() => show.value, (newVal) => {
	if (newVal && props.employeeId) {
		fetchDetails();
	} else {
		details.value = null;
	}
});

function formatDate(dateStr) {
	if (!dateStr) return '';
	const d = new Date(dateStr);
	return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

function getStatusBadgeClass(status) {
	switch (status) {
		case 'Active': return 'tag-emerald';
		case 'Inactive': return 'tag-neutral';
		case 'Suspended': return 'tag-red';
		case 'Left': return 'tag-amber';
		default: return 'tag-neutral';
	}
}

async function fetchDetails() {
	if (!props.employeeId) return;
	
	loading.value = true;
	error.value = '';
	
	try {
		const res = createResource({
			url: 'arijentek_core.api.teams_permissons.get_employee_list',
			auto: false
		});
		
		const data = await res.fetch({ employee_id: props.employeeId });
		if (res.error) {
			throw new Error(res.error.message || 'Failed to fetch details');
		}
		
		details.value = data;
	} catch (err) {
		error.value = err.message || 'An error occurred while fetching details';
	} finally {
		loading.value = false;
	}
}
</script>
