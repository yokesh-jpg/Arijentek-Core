<template>
	<div :class="isModal ? 'modal-panel' : 'h-full flex flex-col'">
		<!-- Header -->
		<header class="flex items-start justify-between gap-3 px-5 py-4 border-b border-black/[0.07] dark:border-white/10 shrink-0">
			<div class="flex items-start gap-3 min-w-0">
				<button v-if="!isModal" @click="goBack" class="btn-icon-ghost shrink-0 -ml-1" aria-label="Back">
					<span class="material-symbols-outlined !text-[18px]">arrow_back</span>
				</button>
				<div class="min-w-0">
					<h2 class="modal-title truncate">Shift assignment details</h2>
					<p v-if="details?.employee_name" class="text-[13px] text-[#5C6169] dark:text-white/65 truncate">{{ details.employee_name }}</p>
					<p class="text-[12px] text-[#656A72] dark:text-white/55 truncate tabular-nums">{{ assignmentId }}</p>
				</div>
			</div>
			<div class="flex items-center gap-1 shrink-0">
				<!-- One date of a multi-day shift or the whole entry: three choices,
				     so they sit behind More; a single day is just Edit and Delete. -->
				<RowActions v-if="details" :actions="[
					{ label: 'Edit', icon: 'edit', show: !!details.can_edit, onClick: () => emit('edit', details) },
					{ divider: true },
					{ label: 'Delete ' + formatDate(details.date) + ' only', icon: 'event_busy', danger: true, show: !!details.can_delete && details.start_date !== details.end_date, onClick: () => handleDelete(details.date) },
					{ label: 'Delete whole entry', icon: 'delete', danger: true, show: !!details.can_delete && details.start_date !== details.end_date, onClick: () => handleDelete(null) },
					{ label: 'Delete', icon: 'delete', danger: true, show: !!details.can_delete && details.start_date === details.end_date, onClick: () => handleDelete(null) },
				]" />
				<button v-if="isModal" @click="goBack" class="btn-icon-ghost" aria-label="Close">
					<span class="material-symbols-outlined !text-[18px]">close</span>
				</button>
			</div>
		</header>

		<!-- Main Content -->
		<main class="flex-1 overflow-y-auto px-6 py-5">
			<div>
				<!-- Loading State -->
				<div v-if="loading" class="flex flex-col items-center justify-center py-16 gap-3">
					<span class="w-5 h-5 rounded-full border-2 border-black/10 dark:border-white/15 border-t-accent animate-spin"></span>
					<span class="text-[13px] text-[#5C6169] dark:text-white/65">Loading details…</span>
				</div>

				<!-- Error State -->
				<div v-else-if="error" class="empty-state">
					<span class="material-symbols-outlined !text-[28px] text-red-600 dark:text-red-400">error</span>
					<p class="empty-state-text">Could not load this record</p>
					<p class="text-[12px] text-[#656A72] dark:text-white/55">{{ error }}</p>
					<button @click="fetchDetails" class="btn-secondary !h-9 mt-3">Try again</button>
				</div>

				<!-- Details Card -->
				<div v-else-if="details" class="space-y-6">
					<div class="pb-5 border-b border-black/[0.06] dark:border-white/[0.08]">
						<div class="flex items-center gap-3.5">
							<span class="avatar-chip !w-11 !h-11 !text-[14px] shrink-0 font-semibold">{{ initials(details.employee_name) }}</span>
							<div class="min-w-0 flex-1">
								<p class="text-[15px] font-semibold text-[#17181B] dark:text-white leading-snug truncate">{{ details.employee_name }}</p>
								<div class="flex items-center gap-2 mt-0.5 text-[12px] text-[#5C6169] dark:text-white/55">
									<span class="tabular-nums font-mono">{{ details.employee }}</span>
									<span v-if="details.department">•</span>
									<span v-if="details.department" class="truncate">{{ details.department }}</span>
								</div>
							</div>
							<span class="premium-tag shrink-0" :class="(details.status || 'Active') === 'Active' ? 'tag-emerald' : 'tag-neutral'">
								{{ details.status || 'Active' }}
							</span>
						</div>
					</div>

					<div class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-5">
						<div class="space-y-1">
							<p class="status-label">Shift assignment ID</p>
							<div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 font-mono">{{ details.assignment_id }}</div>
						</div>
						
						<div class="space-y-1">
							<p class="status-label">Shift type</p>
							<div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 flex items-center gap-1.5 flex-wrap">
								<span class="material-symbols-outlined text-[16px] text-accent dark:text-accent-light">schedule</span>
								<span>{{ details.shift_type }}</span>
								<span v-if="details.start_time || details.end_time" class="text-xs font-normal text-[#5C6169] dark:text-white/60 tabular-nums">
									({{ formatTime(details.start_time) }} – {{ formatTime(details.end_time) }})
								</span>
							</div>
						</div>
						
						<div class="space-y-1">
							<p class="status-label">Date</p>
							<div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 flex items-center gap-1.5">
								<span class="material-symbols-outlined text-[16px] text-[#656A72] dark:text-white/60">calendar_today</span>
								{{ formatDate(details.date) }}
							</div>
						</div>

						<div class="space-y-1">
							<p class="status-label">Assignment period</p>
							<div class="text-[13px] font-medium text-[#17181B] dark:text-white mt-1 flex items-center gap-1.5 tabular-nums">
								<span class="material-symbols-outlined text-[16px] text-[#656A72] dark:text-white/60">date_range</span>
								<span>{{ formatDate(details.start_date) }}</span>
								<template v-if="details.end_date && details.end_date !== details.start_date">
									<span class="text-xs text-[#656A72] dark:text-white/50">to</span>
									<span>{{ formatDate(details.end_date) }}</span>
								</template>
								<template v-else-if="!details.end_date">
									<span class="text-xs text-[#656A72] dark:text-white/50">(ongoing)</span>
								</template>
							</div>
						</div>

						<div v-if="details.shift_location" class="space-y-1">
							<p class="status-label">Shift location</p>
							<div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 flex items-center gap-1.5">
								<span class="material-symbols-outlined text-[16px] text-[#656A72] dark:text-white/60">location_on</span>
								{{ details.shift_location }}
							</div>
						</div>
						
						<div class="space-y-1">
							<p class="status-label">Attendance status</p>
							<div>
								<span class="premium-tag" :class="getStatusBadgeClass(details.attendance_status)">
									{{ details.attendance_status }}
								</span>
							</div>
						</div>

						<div class="space-y-1">
							<p class="status-label">Attendance ID</p>
							<div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">
								<button v-if="details.attendance_id" @click="openAttendance(details.attendance_id)" class="text-accent dark:text-accent-light hover:underline cursor-pointer transition-colors inline-flex items-center gap-1">
									<span>{{ details.attendance_id }}</span>
									<span class="material-symbols-outlined !text-[15px]">open_in_new</span>
								</button>
								<span v-else class="text-[#656A72] dark:text-white/60 italic font-medium text-xs">No Attendance</span>
							</div>
						</div>
					</div>
				</div>

				<!-- Fallback if not loading, no error, but no details -->
				<div v-else class="empty-state">
					<span class="material-symbols-outlined !text-[28px] text-[#C4C7CC] dark:text-white/25">search_off</span>
					<p class="empty-state-text">No record found</p>
					<p class="text-[12px] text-[#656A72] dark:text-white/55">{{ assignmentId }}</p>
				</div>
			</div>
		</main>

		<!-- Attendance Details Modal -->
		<Teleport to="body">
			<div v-if="showAttendanceModal" @click.self="showAttendanceModal = false" class="fixed inset-0 z-[110] flex items-center justify-center bg-[#0B0B0E]/70 backdrop-blur-sm p-4 md:p-6">
				<div class="w-full max-w-md" @click.stop>
					<AttendancePageView :id="selectedAttendanceId" :isModal="true" @close="showAttendanceModal = false" />
				</div>
			</div>
		</Teleport>

		<footer v-if="isModal" class="px-5 py-4 border-t border-black/[0.07] dark:border-white/10 shrink-0">
			<button class="btn-secondary w-full" @click="goBack">Close</button>
		</footer>
	</div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { call } from 'frappe-ui';
import AttendancePageView from './AttendancePageView.vue';
import RowActions from '@/components/RowActions.vue';
import { useRosterStore } from '@/stores/roster';
import { notify, ask } from '@/utils/feedback.js';

const props = defineProps({
	id: {
		type: String,
		default: ''
	},
	isModal: {
		type: Boolean,
		default: false
	},
	selectedDate: {
		type: String,
		default: ''
	}
});

const emit = defineEmits(['close', 'edit', 'delete']);

const route = useRoute();
const router = useRouter();
const rosterStore = useRosterStore();

const assignmentId = ref(props.id || route.params.id);
const loading = ref(true);
const error = ref('');
const details = ref(null);

const showAttendanceModal = ref(false);
const selectedAttendanceId = ref('');

function initials(name) {
	return (name || '?')
		.split(' ')
		.filter(Boolean)
		.slice(0, 2)
		.map((w) => w[0].toUpperCase())
		.join('');
}

function formatTime(timeStr) {
	if (!timeStr || timeStr === 'None') return '';
	const parts = timeStr.split(':');
	return parts.length >= 2 ? `${parts[0]}:${parts[1]}` : timeStr;
}

function formatDate(dateStr) {
	if (!dateStr) return '—';
	const d = new Date(dateStr.includes('T') ? dateStr : `${dateStr}T00:00:00`);
	if (isNaN(d.getTime())) return '—';
	return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

function getStatusBadgeClass(status) {
	switch (status) {
		case 'Present': return 'tag-emerald';
		case 'Absent': return 'tag-red';
		case 'Half Day': return 'tag-amber';
		case 'On Leave': return 'tag-accent';
		default: return 'tag-neutral';
	}
}

async function handleDelete(deleteDate) {
	if (props.isModal) {
		emit('delete', { 
			assignment_id: details.value?.assignment_id || assignmentId.value, 
			delete_date: deleteDate 
		});
	} else {
		if (!await ask('Are you sure you want to delete this shift assignment?')) return;
		try {
			const res = await rosterStore.deleteRoster(details.value?.assignment_id || assignmentId.value, deleteDate);
			if (res && res.success === false) {
				notify(res.message || 'Failed to delete shift assignment.');
				return;
			}
			notify('Shift assignment deleted');
			router.push({ name: 'roster' });
		} catch {
			notify('Failed to delete shift assignment.');
		}
	}
}

function openAttendance(id) {
	selectedAttendanceId.value = id;
	showAttendanceModal.value = true;
}

function goBack() {
	if (props.isModal) {
		emit('close');
	} else if (window.history.length > 2) {
		router.back();
	} else {
		router.push({ name: 'roster' });
	}
}

watch(() => props.id, (newVal) => {
	if (newVal) {
		assignmentId.value = newVal;
		fetchDetails();
	}
});

watch(() => props.selectedDate, () => {
	if (assignmentId.value) {
		fetchDetails();
	}
});

async function fetchDetails() {
	if (!assignmentId.value) {
		loading.value = false;
		error.value = 'No assignment ID provided';
		return;
	}
	
	loading.value = true;
	error.value = '';
	
	try {
		const data = await call('arijentek_core.api.roster.get_shift_assignment_details', { 
			assignment_id: assignmentId.value,
			date: props.selectedDate || undefined
		});
		
		if (!data || data.error) {
			throw new Error((data && data.message) || 'Entry is not available or has been deleted.');
		}
		
		details.value = data;
	} catch (err) {
		error.value = err.message || 'An error occurred while fetching details';
	} finally {
		loading.value = false;
	}
}

onMounted(() => {
	fetchDetails();
});
</script>
