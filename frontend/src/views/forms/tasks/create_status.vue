<template>
	<div class="modal-scrim">
		<div class="modal-panel max-w-[480px]">
			<div class="modal-header">
				<h3 class="modal-title">Manage statuses</h3>
				<button @click="$emit('close')" class="modal-close" aria-label="Close">
					<span class="material-symbols-outlined !text-[20px]">close</span>
				</button>
			</div>

			<div class="modal-body">
				<div>
					<label class="field-label">Add a status</label>
					<div class="flex gap-2">
						<input
							v-model="newStatusName"
							type="text"
							placeholder="e.g. In progress"
							class="field-input flex-1"
							@keyup.enter="handleAddStatus"
						/>
						<button
							@click="handleAddStatus"
							:disabled="!newStatusName.trim() || loading"
							class="btn-primary shrink-0"
						>
							<span class="material-symbols-outlined !text-[18px]">add</span>
							Add
						</button>
					</div>
					<p v-if="error" class="field-error">{{ error }}</p>
				</div>

				<div>
					<div class="flex items-center justify-between mb-1.5">
						<p class="field-label !mb-0">Existing statuses</p>
						<span class="text-[11px] text-[#656A72] dark:text-white/50">Drag to reorder</span>
					</div>

					<div v-if="tasksStore.taskStatusList.loading" class="py-6 text-center text-[13px] text-[#656A72] dark:text-white/60">
						Loading…
					</div>
					<div
						v-else-if="!tasksStore.taskStatusList.data?.length"
						class="grid place-items-center py-6 rounded-[12px] border border-dashed border-black/[0.10] dark:border-white/[0.14] text-[13px] text-[#656A72] dark:text-white/60"
					>
						No statuses yet
					</div>
					<ul v-else ref="statusListEl" class="divide-y divide-black/[0.06] dark:divide-white/[0.07]">
						<li
							v-for="status in tasksStore.taskStatusList.data"
							:key="status"
							:data-id="status"
							class="status-sortable-item flex items-center gap-2 px-2 py-2.5 group rounded-[10px] transition-colors select-none hover:bg-black/[0.03] dark:hover:bg-white/[0.04] cursor-grab active:cursor-grabbing border border-transparent"
						>
							<span
								class="drag-handle material-symbols-outlined !text-[18px] text-[#C4C7CC] group-hover:text-accent dark:text-white/35 dark:group-hover:text-accent shrink-0 p-0.5 rounded transition-colors"
								title="Drag to reorder"
							>
								drag_indicator
							</span>
							<span class="text-[13px] font-medium text-gray-900 dark:text-white flex-1 truncate pointer-events-none">
								{{ status }}
							</span>

							<button
								type="button"
								@click.stop="handleEditStatus(status)"
								class="btn-icon-ghost !h-7 !w-7"
								title="Rename"
							>
								<span class="material-symbols-outlined !text-[16px]">edit</span>
							</button>
							<button
								type="button"
								@click.stop="handleDeleteStatus(status)"
								class="btn-danger-ghost !h-7 !w-7"
								title="Delete"
							>
								<span class="material-symbols-outlined !text-[16px]">delete</span>
							</button>
						</li>
					</ul>
				</div>
			</div>

			<!-- Rename dialog, stacked above this one -->
			<div v-if="editingStatus.show" class="modal-scrim !z-[60]">
				<div class="modal-panel max-w-[360px]">
					<div class="modal-header">
						<h4 class="modal-title">Rename status</h4>
						<button @click="editingStatus.show = false" class="modal-close" aria-label="Close">
							<span class="material-symbols-outlined !text-[20px]">close</span>
						</button>
					</div>
					<div class="modal-body">
						<input
							v-model="editingStatus.new"
							type="text"
							placeholder="Status name"
							class="field-input"
							@keyup.enter="saveEditStatus"
						/>
					</div>
					<div class="modal-footer">
						<button @click="editingStatus.show = false" class="btn-secondary flex-1">Cancel</button>
						<button
							@click="saveEditStatus"
							:disabled="!editingStatus.new.trim()"
							class="btn-primary flex-1"
						>
							Save
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ask } from '@/utils/feedback.js';
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import { useTasksStore } from '@/stores/tasks';
import { createResource } from 'frappe-ui';
import { getErrorMessage } from '@/utils';
import Sortable from 'sortablejs';

const emit = defineEmits(['close']);
const tasksStore = useTasksStore();

const newStatusName = ref('');
const loading = ref(false);
const error = ref('');
const statusListEl = ref(null);
let sortableInstance = null;

const addStatusResource = createResource({
	url: 'arijentek_core.api.tasks.add_task_status',
	auto: false,
});

const editStatusResource = createResource({
	url: 'arijentek_core.api.tasks.edit_task_status',
	auto: false,
});

const deleteStatusResource = createResource({
	url: 'arijentek_core.api.tasks.delete_task_status',
	auto: false,
});

const reorderStatusResource = createResource({
	url: 'arijentek_core.api.tasks.reorder_task_status',
	auto: false,
});

function initSortable() {
	if (sortableInstance) {
		sortableInstance.destroy();
		sortableInstance = null;
	}
	if (!statusListEl.value) return;

	sortableInstance = new Sortable(statusListEl.value, {
		animation: 180,
		filter: 'button, input',
		preventOnFilter: false,
		ghostClass: '!opacity-30',
		chosenClass: '!bg-accent/[0.08]',
		dragClass: '!shadow-md',
		onEnd: async (evt) => {
			const { oldIndex, newIndex, item, from } = evt;
			if (oldIndex === newIndex || oldIndex == null || newIndex == null) return;

			// Restore DOM node back to original index so Vue virtual DOM can reconcile with keys without collision
			const targetChild = from.children[oldIndex > newIndex ? oldIndex + 1 : oldIndex];
			from.insertBefore(item, targetChild || null);

			// Reorder items in reactive state
			const list = [...tasksStore.taskStatusList.data];
			const [movedItem] = list.splice(oldIndex, 1);
			list.splice(newIndex, 0, movedItem);

			// Optimistic UI update
			tasksStore.taskStatusList.data = list;

			try {
				await reorderStatusResource.fetch({ new_order: JSON.stringify(list) });
				await tasksStore.taskStatusList.fetch();
			} catch (e) {
				error.value = getErrorMessage(e, 'Failed to reorder statuses');
				await tasksStore.taskStatusList.fetch(); // Revert on failure
			}
		},
	});
}

watch(
	() => tasksStore.taskStatusList.data,
	async () => {
		await nextTick();
		initSortable();
	},
	{ deep: true }
);

onMounted(async () => {
	await nextTick();
	initSortable();
});

onBeforeUnmount(() => {
	if (sortableInstance) {
		sortableInstance.destroy();
		sortableInstance = null;
	}
});

async function handleAddStatus() {
	if (!newStatusName.value.trim()) return;
	error.value = '';
	loading.value = true;

	try {
		await addStatusResource.fetch({ status_name: newStatusName.value });
		await tasksStore.taskStatusList.fetch();
		newStatusName.value = '';
	} catch (e) {
		error.value = getErrorMessage(e, 'Failed to add status');
	} finally {
		loading.value = false;
	}
}

const editingStatus = ref({ show: false, old: '', new: '' });

function handleEditStatus(status) {
	editingStatus.value = { show: true, old: status, new: status };
}

async function saveEditStatus() {
	if (!editingStatus.value.new.trim() || editingStatus.value.new.trim() === editingStatus.value.old) {
		editingStatus.value.show = false;
		return;
	}
	error.value = '';
	try {
		await editStatusResource.fetch({
			old_status: editingStatus.value.old,
			new_status: editingStatus.value.new.trim(),
		});
		editingStatus.value.show = false;
		await tasksStore.taskStatusList.fetch();
	} catch (e) {
		error.value = getErrorMessage(e, 'Failed to edit status');
	}
}

async function handleDeleteStatus(status) {
	if (await ask(`Are you sure you want to delete the status "${status}"?`)) {
		error.value = '';
		try {
			await deleteStatusResource.fetch({ status_name: status });
			await tasksStore.taskStatusList.fetch();
		} catch (e) {
			error.value = getErrorMessage(e, 'Failed to delete status');
		}
	}
}
</script>
