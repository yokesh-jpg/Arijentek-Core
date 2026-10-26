<template>
	<div class="modal-scrim" @click="$emit('close')">
		<div class="modal-panel max-w-lg" @click.stop>
			<!-- Header. The id is what you quote when chasing a task, so it sits
			     under the title rather than in a chip beside it. -->
			<header class="modal-header">
				<div class="min-w-0">
					<h3 class="modal-title">Task details</h3>
					<p class="text-[12px] text-[#656A72] dark:text-white/60 truncate tabular-nums">{{ todoId }}</p>
				</div>
				<button @click="$emit('close')" class="btn-icon-ghost shrink-0" aria-label="Close">
					<span class="material-symbols-outlined !text-[18px]">close</span>
				</button>
			</header>

			<div class="flex-1 overflow-y-auto px-6 py-5">
				<div v-if="loading" class="flex flex-col items-center justify-center py-16 gap-3">
					<span class="material-symbols-outlined !text-[28px] text-accent dark:text-accent-light animate-spin">progress_activity</span>
					<span class="text-[13px] text-[#5C6169] dark:text-white/65">Loading task…</span>
				</div>

				<div v-else-if="!taskData" class="empty-state">
					<span class="material-symbols-outlined !text-[28px] text-[#C4C7CC] dark:text-white/25">error</span>
					<p class="empty-state-text">Could not load this task.</p>
				</div>

				<template v-else>
					<!-- The task's own words lead. A "Description" label above them
					     only restates what the sentence already is. -->
					<p class="text-[14px] font-semibold text-[#17181B] dark:text-white leading-relaxed whitespace-pre-wrap break-words">
						{{ taskData.description || 'Untitled task' }}
					</p>

					<div class="flex flex-wrap items-center gap-2 mt-3">
						<span class="premium-tag" :class="priorityTag(taskData.priority)">{{ taskData.priority }} priority</span>
						<span class="premium-tag" :class="statusTag(taskData.status)">{{ taskData.status }}</span>
					</div>

					<!-- Facts read as plain fields on the panel. A tinted card here
					     would be a second surface inside the dialog. -->
					<div class="mt-6 pt-5 border-t border-black/[0.07] dark:border-white/10 grid grid-cols-2 gap-x-6 gap-y-5">
						<div>
							<p class="status-label">Assigned to</p>
							<div class="flex items-center gap-2 mt-1">
								<span v-if="assignee" class="avatar-chip !w-7 !h-7 !text-[12px]">{{ initials(assignee) }}</span>
								<span class="text-[14px] font-semibold" :class="assignee ? 'text-[#17181B] dark:text-white' : 'text-[#656A72] dark:text-white/60'">
									{{ assignee || 'Unassigned' }}
								</span>
							</div>
						</div>
						<div>
							<p class="status-label">Created by</p>
							<p class="text-[14px] font-semibold mt-1" :class="creator ? 'text-[#17181B] dark:text-white' : 'text-[#656A72] dark:text-white/60'">
								{{ creator || '—' }}
							</p>
						</div>
						<div>
							<p class="status-label">Due date</p>
							<p class="text-[14px] font-semibold mt-1 tabular-nums" :class="taskData.date ? 'text-[#17181B] dark:text-white' : 'text-[#656A72] dark:text-white/60'">
								{{ formatTodoDate(taskData.date) || 'No date set' }}
							</p>
						</div>
						<div v-if="taskData.reference_type && taskData.reference_name">
							<p class="status-label">Reference</p>
							<p class="text-[14px] font-semibold text-accent dark:text-accent-light mt-1 break-words">
								{{ taskData.reference_type }}: {{ taskData.reference_name }}
							</p>
						</div>
					</div>

					<div v-if="attachments.length" class="mt-6 pt-5 border-t border-black/[0.07] dark:border-white/10">
						<p class="status-label">Attachments</p>
						<div class="space-y-2 mt-1">
							<a
								v-for="file in attachments"
								:key="file.name"
								:href="file.file_url"
								target="_blank"
								rel="noopener"
								class="flex items-center gap-3 px-3 py-2.5 rounded-[12px] border border-black/[0.07] dark:border-white/10 hover:bg-black/[0.03] dark:hover:bg-white/[0.06] transition-colors"
							>
								<span class="material-symbols-outlined !text-[18px] text-[#656A72] dark:text-white/60 shrink-0">attachment</span>
								<span class="text-[13px] font-medium text-[#17181B] dark:text-white truncate" :title="file.file_name">{{ file.file_name }}</span>
								<span class="material-symbols-outlined !text-[16px] text-[#656A72] dark:text-white/60 ml-auto shrink-0">open_in_new</span>
							</a>
						</div>
					</div>
				</template>
			</div>

			<footer v-if="!loading && taskData" class="modal-footer justify-end">
				<button class="btn-secondary" @click="$emit('close')">Close</button>
				<button class="btn-primary" @click="$emit('edit', taskData)">Edit task</button>
			</footer>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useTasksStore } from '@/stores/tasks'
import { call } from 'frappe-ui'

const props = defineProps({
	todoId: {
		type: String,
		required: true,
	},
})

const emit = defineEmits(['close', 'edit'])

const tasksStore = useTasksStore()
const taskData = ref(null)
const loading = ref(true)
const attachments = ref([])

const assignee = computed(() => taskData.value?.allocated_to_name || taskData.value?.allocated_to || '')
const creator = computed(() => taskData.value?.assigned_by_name || taskData.value?.assigned_by || '')

function initials(name) {
	return String(name)
		.split(/[\s@._-]+/)
		.filter(Boolean)
		.slice(0, 2)
		.map((p) => p[0].toUpperCase())
		.join('')
}

onMounted(async () => {
	loading.value = true
	try {
		taskData.value = await tasksStore.fetchTodoDetail(props.todoId)

		try {
			const files = await call('frappe.client.get_list', {
				doctype: 'File',
				filters: {
					attached_to_doctype: 'ToDo',
					attached_to_name: props.todoId,
				},
				fields: ['name', 'file_name', 'file_url'],
			})
			attachments.value = files || []
		} catch (fileErr) {
			console.error('Failed to fetch attachments', fileErr)
			attachments.value = []
		}
	} catch (e) {
		console.error('Failed to fetch task details:', e)
	} finally {
		loading.value = false
	}
})

function formatTodoDate(dateStr) {
	if (!dateStr) return ''
	/* Parsed as local midnight: a bare 'YYYY-MM-DD' is read as UTC, which names
	   the previous day east of UTC. */
	const d = new Date(dateStr + 'T00:00:00')
	if (isNaN(d.getTime())) return ''
	return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

/* These were red-750 / amber-750 / emerald-850 / gray-150, none of which are
   real steps in the ramp - Tailwind emits no CSS for them, so the badges were
   rendering unstyled. The shared tag classes carry the right pairs. */
function priorityTag(priority) {
	if (priority === 'High') return 'tag-red'
	if (priority === 'Medium') return 'tag-amber'
	return 'tag-neutral'
}

function statusTag(status) {
	if (status === 'Open') return 'tag-emerald'
	if (status === 'Cancelled') return 'tag-red'
	return 'tag-neutral'
}
</script>
