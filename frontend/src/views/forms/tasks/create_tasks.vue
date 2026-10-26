<template>
	<div class="modal-scrim">
		<div class="modal-panel max-w-[440px]">
			<div class="modal-header">
				<h3 class="modal-title">{{ isEditing ? 'Edit task' : 'Add task' }}</h3>
				<button @click="$emit('close')" class="modal-close" aria-label="Close">
					<span class="material-symbols-outlined !text-[20px]">close</span>
				</button>
			</div>

			<div class="modal-body text-left">
				<div>
					<label class="field-label">Assigned to</label>
					<div v-if="tasksStore.permissions?.can_allocate" class="relative">
						<SearchableDropdown
							v-model="form.assignedTo"
							:options="allocatableUsers || []"
							labelKey="full_name"
							valueKey="name"
							placeholder="Select user"
						/>
					</div>
					<div v-else class="field-static">
						{{ metadata?.current_user?.full_name || 'Loading…' }}
					</div>
				</div>

				<div v-if="isEditing">
					<label class="field-label">Status</label>
					<div class="relative">
						<SearchableDropdown
							v-model="form.status"
							:options="taskStatusOptions"
							labelKey="label"
							valueKey="value"
							placeholder="Select status"
						/>
					</div>
				</div>

				<div>
					<label class="field-label">Priority</label>
					<div class="relative">
						<SearchableDropdown
							v-model="form.priority"
							:options="priorityOptions"
							labelKey="label"
							valueKey="value"
							placeholder="Select priority"
						/>
					</div>
				</div>

				<div>
					<label class="field-label">Allocated date</label>
					<div class="field-static">{{ formattedTodayDate }}</div>
				</div>

				<div>
					<label class="field-label">Due date <span class="text-red-600 dark:text-red-400">*</span></label>
					<DateField v-model="form.dueDate" />
				</div>

				<div>
					<label class="field-label">Description <span class="text-red-600 dark:text-red-400">*</span></label>
					<textarea
						v-model="form.description"
						placeholder="What needs doing?"
						rows="3"
						class="field-input"
					></textarea>
				</div>

				<div class="pt-4 border-t border-black/[0.06] dark:border-white/[0.08]">
					<div class="flex items-center justify-between gap-3 mb-3">
						<span class="field-label !mb-0">Attachments</span>
						<button
							type="button"
							@click="$refs.fileInput.click()"
							class="h-8 px-3 inline-flex items-center gap-1.5 rounded-[12px] text-xs font-medium text-accent dark:text-accent-light hover:bg-accent/[0.08] transition-colors"
						>
							<span class="material-symbols-outlined !text-[16px]">attach_file</span>
							Add files
						</button>
						<input type="file" multiple class="hidden" ref="fileInput" @change="onFilesSelected" />
					</div>

					<div v-if="attachments.length > 0" class="flex flex-col gap-2">
						<div
							v-for="(file, index) in attachments"
							:key="index"
							class="flex items-center justify-between gap-2 px-3 py-2.5 rounded-[12px] bg-black/[0.03] dark:bg-white/[0.06]"
						>
							<div class="flex items-center gap-2.5 min-w-0">
								<span class="material-symbols-outlined !text-[18px] text-[#656A72] dark:text-white/60 shrink-0"
									>description</span
								>
								<span class="text-[13px] text-gray-900 dark:text-white truncate">{{
									file.file_name || file.name
								}}</span>
							</div>
							<div class="flex items-center gap-1.5 shrink-0">
								<span v-if="file.isExisting" class="text-xs text-[#656A72] dark:text-white/60">Saved</span>
								<button
									type="button"
									@click="removeAttachment(index)"
									class="btn-danger-ghost !w-8 !h-8"
									title="Remove attachment"
								>
									<span class="material-symbols-outlined !text-[16px]">delete</span>
								</button>
							</div>
						</div>
					</div>
					<div
						v-else
						class="grid place-items-center py-5 rounded-[12px] border border-dashed border-black/[0.10] dark:border-white/[0.14]"
					>
						<p class="text-xs text-[#656A72] dark:text-white/60">No attachments yet</p>
					</div>
				</div>

				<p v-if="error" class="field-error">{{ error }}</p>
			</div>

			<div class="modal-footer">
				<button @click="handleSave" :disabled="loading" class="btn-primary flex-1">
					<span class="material-symbols-outlined !text-[18px]">{{
						isEditing ? 'save' : 'add'
					}}</span>
					{{ isEditing ? 'Save changes' : 'Add task' }}
				</button>
				<button @click="$emit('close')" class="btn-secondary flex-1">Cancel</button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { notify, ask } from '@/utils/feedback.js'
import { ref, computed, watch, onMounted } from 'vue';
import SearchableDropdown from '@/components/SearchableDropdown.vue';
import { useTasksStore } from '@/stores/tasks';
import { call } from 'frappe-ui';
import { getErrorMessage } from '@/utils.js';
import DateField from '../../../components/DateField.vue'

const props = defineProps({
	isEditing: {
		type: Boolean,
		default: false,
	},
	todoToEdit: {
		type: Object,
		default: null,
	},
	metadata: {
		type: Object,
		required: true,
	},
	allocatableUsers: {
		type: Array,
		default: () => [],
	},
	loading: {
		type: Boolean,
		default: false,
	},
});

const emit = defineEmits(['close', 'save']);

const tasksStore = useTasksStore();

const taskStatusOptions = computed(() => {
	if (!tasksStore.taskStatusList.data) return [];
	return tasksStore.taskStatusList.data.map(status => ({ label: status, value: status }));
});

const priorityOptions = computed(() => {
	if (!props.metadata?.priorities) return [];
	return props.metadata.priorities.map(prio => ({ label: prio, value: prio }));
});

const form = ref({
	id: null,
	assignedTo: '',
	priority: 'Medium',
	dueDate: '',
	description: '',
	status: 'Open',
});

const error = ref('');
const fileInput = ref(null);
const attachments = ref([]);

const formattedTodayDate = computed(() => {
	if (props.isEditing && props.todoToEdit && props.todoToEdit.creation_date) {
		const d = new Date(props.todoToEdit.creation_date + 'T00:00:00');
		return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
	}
	if (props.metadata?.today) {
		const d = new Date(props.metadata.today + 'T00:00:00');
		return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
	}
	const d = new Date();
	return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
});

onMounted(async () => {
	if (props.isEditing && props.todoToEdit) {
		form.value.id = props.todoToEdit.id;
		form.value.assignedTo = props.todoToEdit.allocated_to || '';
		form.value.priority = props.todoToEdit.priority || 'Medium';
		form.value.dueDate = props.todoToEdit.date || '';
		form.value.description = props.todoToEdit.description || '';
		form.value.status = props.todoToEdit.status || 'Open';
		
		// fetch existing attachments
		try {
			const files = await call('frappe.client.get_list', {
				doctype: 'File',
				filters: {
					attached_to_doctype: 'ToDo',
					attached_to_name: props.todoToEdit.id
				},
				fields: ['name', 'file_name', 'file_url']
			});
			if (files && files.length > 0) {
				files.forEach(f => {
					f.isExisting = true;
					attachments.value.push(f);
				});
			}
		} catch(e) {
			console.error("Failed to fetch attachments", e);
		}
	} else {
		form.value.priority = props.metadata?.priorities?.[1] || 'Medium';
		form.value.assignedTo = props.metadata?.current_user?.name || '';
		// The board's per-column + passes the column through as todoToEdit.status
		// without isEditing, so a task created from 'Cancelled' lands there.
		form.value.status = props.todoToEdit?.status || 'Open';
	}
});

const onFilesSelected = (e) => {
	const files = Array.from(e.target.files);
	files.forEach(f => {
		attachments.value.push(f);
	});
	e.target.value = '';
};

const removeAttachment = async (index) => {
	const file = attachments.value[index];
	if (file.isExisting) {
		if (await ask('Are you sure you want to delete this attachment? It will be removed immediately.')) {
			try {
				await call('frappe.client.delete', { doctype: 'File', name: file.name });
				attachments.value.splice(index, 1);
			} catch (err) {
				notify(getErrorMessage(err, 'Failed to delete file'));
			}
		}
	} else {
		attachments.value.splice(index, 1);
	}
};

function handleSave() {
	error.value = '';

	if (!form.value.description.trim()) {
		error.value = 'Task Description is required.';
		return;
	}
	if (!form.value.dueDate) {
		error.value = 'Due Date is required.';
		return;
	}

	let allocatedDateObj = new Date();
	if (props.isEditing && props.todoToEdit && props.todoToEdit.creation_date) {
		allocatedDateObj = new Date(props.todoToEdit.creation_date + 'T00:00:00');
	} else if (props.metadata?.today) {
		allocatedDateObj = new Date(props.metadata.today + 'T00:00:00');
	}
	allocatedDateObj.setHours(0, 0, 0, 0);

	const selectedDue = new Date(form.value.dueDate + 'T00:00:00');
	selectedDue.setHours(0, 0, 0, 0);

	if (selectedDue < allocatedDateObj) {
		error.value = 'Due Date cannot be before the Allocated Date.';
		return;
	}

	emit('save', { ...form.value, attachments: attachments.value });
}
</script>
