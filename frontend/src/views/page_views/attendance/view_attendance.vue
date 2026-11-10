<template>
	<div :class="isModal ? 'modal-panel' : 'h-full flex flex-col'">
		<!-- Header. In a dialog the panel supplies the frame, so this is just a
		     title row; as a page it also carries the back button. -->
		<header class="flex items-start justify-between gap-3 px-5 py-4 border-b border-black/[0.07] dark:border-white/10 shrink-0">
			<div class="flex items-start gap-3 min-w-0">
				<button v-if="!isModal" @click="goBack" class="btn-icon-ghost shrink-0 -ml-1" aria-label="Back">
					<span class="material-symbols-outlined !text-[18px]">arrow_back</span>
				</button>
				<div class="min-w-0">
					<h2 class="modal-title truncate">Attendance details</h2>
					<p v-if="details?.employee_name" class="text-[13px] text-[#5C6169] dark:text-white/65 truncate">
						{{ details.employee_name }}
					</p>
					<!-- The record id is what you quote when chasing a correction, so it
					     stays visible even before the record resolves. -->
					<p class="text-[12px] text-[#656A72] dark:text-white/55 truncate tabular-nums">
						{{ details?.attendance_id || attendanceId }}
					</p>
				</div>
			</div>
			<div class="flex items-center gap-1 shrink-0">
				<button v-if="details?.can_edit" @click="emit('edit', { name: details.attendance_id })" class="btn-icon-ghost" aria-label="Edit">
					<span class="material-symbols-outlined !text-[18px]">edit</span>
				</button>
				<button v-if="details?.can_delete" @click="emit('delete', { name: details.attendance_id })" class="btn-icon-ghost hover:!text-red-600 dark:text-red-400" aria-label="Delete">
					<span class="material-symbols-outlined !text-[18px]">delete</span>
				</button>
				<button @click="goBack" class="btn-icon-ghost" aria-label="Close">
					<span class="material-symbols-outlined !text-[18px]">close</span>
				</button>
			</div>
		</header>

		<!-- Body -->
		<div class="flex-1 overflow-y-auto px-6 py-5">
			<div v-if="loading" class="flex flex-col items-center justify-center py-16 gap-3">
				<span class="material-symbols-outlined !text-[28px] text-accent dark:text-accent-light animate-spin">progress_activity</span>
				<span class="text-[13px] text-[#5C6169] dark:text-white/65">Loading details…</span>
			</div>

			<div v-else-if="error" class="inset-panel text-center">
				<span class="material-symbols-outlined !text-[24px] text-red-500 dark:text-red-400">error</span>
				<p class="text-[13px] font-semibold text-[#17181B] dark:text-white mt-1">Could not load this record</p>
				<p class="text-[13px] text-[#5C6169] dark:text-white/65 mt-0.5">{{ error }}</p>
				<button @click="fetchDetails" class="btn-secondary !h-9 mt-3 mx-auto">Try again</button>
			</div>

			<div v-else-if="!details" class="inset-panel text-center">
				<span class="material-symbols-outlined !text-[24px] text-[#656A72] dark:text-white/60">search_off</span>
				<p class="text-[13px] font-semibold text-[#17181B] dark:text-white mt-1">No record found</p>
				<p class="text-[13px] text-[#5C6169] dark:text-white/65 mt-0.5">{{ attendanceId }}</p>
			</div>

			<template v-else>
				<!-- Facts, two to a row. -->
				<div class="grid grid-cols-2 gap-x-6 gap-y-5">
					<div>
						<p class="status-label">Date</p>
						<p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ formatDate(details.date) }}</p>
					</div>
					<div>
						<p class="status-label">Status</p>
						<span class="premium-tag mt-1" :class="statusTag(details.status)">
							{{ details.status }}
						</span>
					</div>
					<div>
						<p class="status-label">Clock in</p>
						<p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 tabular-nums">{{ formatTime(details.in_time) }}</p>
					</div>
					<div>
						<p class="status-label">Clock out</p>
						<p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 tabular-nums">{{ formatTime(details.out_time) }}</p>
					</div>
					<div>
						<p class="status-label">Working hours</p>
						<p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 tabular-nums">{{ formatHours(details.working_hours) }}</p>
					</div>
					<div>
						<p class="status-label">Break hours</p>
						<p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 tabular-nums">{{ formatHours(details.break_hours) }}</p>
					</div>
					<div v-if="details.shift">
						<p class="status-label">Shift</p>
						<p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.shift }}</p>
					</div>
					<div v-if="details.late_entry || details.early_exit">
						<p class="status-label">Exceptions</p>
						<div class="flex flex-wrap gap-1.5 mt-1">
							<span v-if="details.late_entry" class="tag-amber inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold">Late entry</span>
							<span v-if="details.early_exit" class="tag-amber inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold">Early exit</span>
						</div>
					</div>
				</div>

				<!-- Break logs -->
				<div v-if="details.break_logs?.length" class="mt-6 pt-5 border-t border-black/[0.07] dark:border-white/10">
					<p class="status-label flex items-center gap-1.5 mb-2.5">
						<span class="material-symbols-outlined !text-[16px]">schedule</span>
						Break logs breakdown
					</p>
					<div class="table-card !rounded-[12px]">
						<table class="w-full">
							<thead>
								<tr class="border-b border-black/[0.07] dark:border-white/10">
									<th class="table-th">Break in</th>
									<th class="table-th">Break out</th>
									<th class="table-th !text-right">Duration</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="(log, idx) in details.break_logs" :key="idx" class="border-b last:border-0 border-black/[0.05] dark:border-white/[0.06]">
									<td class="table-td tabular-nums">{{ formatTime(log.break_in) }}</td>
									<td class="table-td tabular-nums">{{ formatTime(log.break_out) }}</td>
									<td class="table-td !text-right">
										<span v-if="log.is_ongoing" class="inline-flex items-center gap-1.5 text-accent dark:text-accent-light font-medium">
											<span class="w-1.5 h-1.5 rounded-full bg-accent animate-pulse"></span>
											{{ log.duration }}
										</span>
										<span v-else>{{ log.duration }}</span>
									</td>
								</tr>
							</tbody>
						</table>
					</div>
				</div>
			</template>
		</div>

		<footer class="px-5 py-4 border-t border-black/[0.07] dark:border-white/10 shrink-0">
			<button class="btn-secondary w-full" @click="goBack">Close</button>
		</footer>
	</div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { createResource } from 'frappe-ui'

const props = defineProps({
	id: { type: String, default: '' },
	isModal: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'edit', 'delete'])

const router = useRouter()

const attendanceId = ref(props.id)
const loading = ref(true)
const error = ref('')
const details = ref(null)

function goBack() {
	if (props.isModal) emit('close')
	else if (window.history.length > 2) router.back()
	else router.push({ name: 'attendance' })
}

watch(
	() => props.id,
	(newVal) => {
		if (newVal) {
			attendanceId.value = newVal
			fetchDetails()
		}
	},
)

function formatDate(dateStr) {
	if (!dateStr) return '—'
	/* Parsed as local midnight: a bare 'YYYY-MM-DD' is read as UTC, which names
	   the previous day east of UTC. */
	const d = new Date(dateStr + 'T00:00:00')
	if (isNaN(d.getTime())) return '—'
	return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
}

function formatTime(timeStr) {
	if (!timeStr) return '—'
	const d = new Date(String(timeStr).replace(' ', 'T'))
	if (isNaN(d.getTime())) return '—'
	return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true })
}

/* A worked day of zero hours is '—', not '0.00 hrs' — the absent rows read as
   missing data, which is what they are. */
function formatHours(h) {
	return h ? h.toFixed(2) + ' hrs' : '—'
}

function statusTag(status) {
	switch (status) {
		case 'Present':
			return 'tag-emerald'
		case 'Absent':
			return 'tag-red'
		case 'Half Day':
			return 'tag-amber'
		default:
			return 'tag-neutral'
	}
}

async function fetchDetails() {
	if (!attendanceId.value) return
	loading.value = true
	error.value = ''
	try {
		const res = createResource({ url: 'arijentek_core.api.attendance.get_attendance_details', auto: false })
		const data = await res.fetch({ attendance_id: attendanceId.value })
		if (res.error) throw new Error(res.error.message || 'Failed to fetch details')
		details.value = data || null
	} catch (err) {
		error.value = err.message || 'An error occurred while fetching details'
	} finally {
		loading.value = false
	}
}

onMounted(fetchDetails)
</script>
