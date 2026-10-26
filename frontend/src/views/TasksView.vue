<template>
	<div class="h-full flex flex-col gap-4 sm:gap-5">
		<!-- ===== Header ===== -->
		<div class="flex flex-wrap items-start justify-between gap-3">
			<div class="min-w-0">
				<h1 class="page-title">Tasks</h1>
				<p class="page-subtitle">
					{{ openCount }} open · {{ filteredTodos.length }} shown
				</p>
			</div>

			<div class="flex items-center gap-2 shrink-0">
				<button
					v-if="tasksStore.permissions?.can_allocate"
					@click="showAddStatusDialog = true"
					class="btn-secondary"
				>
					<span class="material-symbols-outlined !text-[18px]">tune</span>
					<span class="hidden sm:inline">Manage statuses</span>
				</button>
				<button
					@click="openAddTaskDialog"
					class="btn-primary"
				>
					<span class="material-symbols-outlined !text-[18px]">add</span>
					Add task
				</button>
			</div>
		</div>

		<!-- ===== Toolbar =====
		     View switcher, search and every filter on one line, the way the
		     reference groups them. Filters stay visible rather than hiding
		     behind a popover: there are five of them and a hidden filter is a
		     filter people forget is on. -->
		<div class="glass-card !p-3 flex flex-wrap items-center gap-2 shrink-0 relative z-20">
			<div
				class="flex items-center gap-1 p-1 rounded-full bg-black/[0.04] dark:bg-white/[0.06] shrink-0"
			>
				<button
					v-for="v in viewOptions"
					:key="v.value"
					@click="viewMode = v.value"
					class="h-8 px-3 inline-flex items-center gap-1.5 rounded-[12px] text-[13px] font-medium transition-colors"
					:class="viewMode === v.value ? 'bg-white dark:bg-white/[0.14] text-[#17181B] dark:text-white shadow-[0_1px_2px_rgba(11,11,12,.08)]' : 'text-[#5C6169] dark:text-white/65 hover:text-[#17181B] dark:hover:text-white'"
				>
					<span class="material-symbols-outlined !text-[18px]">{{ v.icon }}</span>
					<span class="hidden sm:inline">{{ v.label }}</span>
				</button>
			</div>

			<div class="relative flex-1 min-w-[180px]">
				<span
					class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/60"
					>search</span
				>
				<input
					v-model="searchQuery"
					type="search"
					placeholder="Search tasks…"
					class="w-full h-10 pl-10 pr-3 rounded-[12px] text-[13px] bg-black/[0.03] dark:bg-white/[0.06] border border-transparent focus:border-accent/30 focus:bg-white dark:focus:bg-white/[0.09] outline-none transition-colors placeholder:text-[#656A72] dark:text-white/60"
				/>
			</div>

			<!-- Filters button: phone only. Five dropdowns stacked full width ate
			     the screen before a single task was visible. -->
			<button
				@click="filtersOpen = true"
				class="btn-secondary lg:hidden shrink-0"
			>
				<span class="material-symbols-outlined !text-[18px]">filter_list</span>
				Filters
				<span
					v-if="activeFilterCount"
					class="min-w-[18px] h-[18px] px-1 grid place-items-center rounded-[12px] bg-accent text-white text-xs font-semibold tabular-nums"
					>{{ activeFilterCount }}</span
				>
			</button>

			<Teleport to="body" :disabled="!isMobile">
				<div
					v-if="isMobile && filtersOpen"
					class="fixed inset-0 bg-[#0B0B0E]/70 backdrop-blur-sm z-[80]"
					@click="filtersOpen = false"
				></div>

				<div
					:class="!isMobile ? 'contents' : filtersOpen ? 'fixed inset-x-0 bottom-0 z-[81] flex flex-col gap-3 rounded-t-[22px] bg-white dark:bg-surface-1 border-t border-black/[0.08] dark:border-white/10 p-4 pb-[calc(1rem+env(safe-area-inset-bottom,0px))] max-h-[80vh] overflow-y-auto' : 'hidden'"
				>
					<div v-if="isMobile" class="flex items-center justify-between gap-3">
						<h2 class="text-base font-semibold text-[#17181B] dark:text-white">Filters</h2>
						<button
							@click="filtersOpen = false"
							class="w-9 h-9 grid place-items-center rounded-full text-[#5C6169] dark:text-white/65"
							aria-label="Close filters"
						>
							<span class="material-symbols-outlined !text-[20px]">close</span>
						</button>
					</div>

			<!-- Status only filters the list: on the board the column IS the status. -->
			<div v-if="viewMode === 'list'" class="w-full shrink-0 lg:w-40">
				<SearchableDropdown
					v-model="selectedStatusFilter"
					:options="statusOptions"
					labelKey="label"
					valueKey="value"
					:showAllOption="true"
					allOptionLabel="All statuses"
					placeholder="Status"
				/>
			</div>

			<div class="w-full shrink-0 lg:w-40">
				<SearchableDropdown
					v-model="selectedPriorityFilter"
					:options="priorityOptions"
					labelKey="label"
					valueKey="value"
					:showAllOption="true"
					allOptionLabel="All priorities"
					placeholder="Priority"
				/>
			</div>

			<div class="w-full shrink-0 relative z-30 lg:w-auto">
				<DateRangePicker
					v-model:preset="datePreset"
					v-model:fromDate="dateFrom"
					v-model:toDate="dateTo"
					:inline="isMobile"
				/>
			</div>

			<div v-if="tasksStore.permissions?.can_allocate" class="w-full shrink-0 lg:w-44">
				<SearchableDropdown
					v-model="selectedUserFilter"
					:options="tasksStore.allocatableUsersList.data || []"
					labelKey="full_name"
					valueKey="name"
					:showAllOption="true"
					allOptionLabel="All users"
					placeholder="Assignee"
				/>
			</div>

			<button
				v-if="hasActiveFilters && !isMobile"
				@click="clearFilters"
				class="btn-ghost !text-accent dark:!text-accent-light hover:!bg-accent/[0.08] shrink-0"
			>
				<span class="material-symbols-outlined !text-[18px]">close</span>
				Clear
			</button>

					<div v-if="isMobile" class="flex gap-2 mt-2">
						<button
							v-if="hasActiveFilters"
							@click="clearFilters"
							class="btn-secondary flex-1"
						>
							Clear all
						</button>
						<button
							@click="filtersOpen = false"
							class="btn-primary flex-1"
						>
							Show {{ filteredTodos.length }} tasks
						</button>
					</div>
				</div>
			</Teleport>
		</div>

		<!-- Status strip: phone only. Three columns side by side at 375px meant a
		     sideways scroll that clipped every card; this picks one and gives it
		     the full width. -->
		<div
			v-if="viewMode === 'card'"
			class="lg:hidden flex items-center gap-2 overflow-x-auto no-scrollbar shrink-0 -mx-4 px-4"
		>
			<button
				v-for="status in visibleStatuses"
				:key="status"
				@click="activeStatus = status"
				class="h-9 px-3.5 shrink-0 inline-flex items-center gap-2 rounded-[12px] border text-[13px] font-medium transition-colors"
				:class="activeStatus === status ? 'bg-accent border-accent text-white' : 'border-black/[0.08] dark:border-white/[0.12] text-[#17181B] dark:text-white'"
			>
				<span
					class="w-1.5 h-1.5 rounded-full"
					:class="activeStatus === status ? 'bg-white/70' : getStatusBulletColor(status)"
				></span>
				{{ status }}
				<span
					class="tabular-nums"
					:class="activeStatus === status ? 'text-white/85' : 'text-[#5C6169] dark:text-white/60'"
					>{{ getTodosByStatus(status).length }}</span
				>
			</button>
		</div>

		<!-- ===== Board ===== -->
		<div class="flex-1 min-h-0">
			<div
				v-if="viewMode === 'card'"
				ref="kanbanContainer"
				@wheel="handleKanbanWheel"
				@mousedown="handlePanStart"
				@mousemove="handlePanMove"
				@mouseup="handlePanEnd"
				@mouseleave="handlePanEnd"
				class="flex gap-4 h-full overflow-y-hidden pb-2 no-scrollbar overflow-x-hidden lg:overflow-x-auto"
				:class="{ 'select-none cursor-grabbing': isPanning }"
			>
				<!-- flex-1 with a floor: three statuses spread across the board
				     instead of huddling at the left, and a longer status list hits
				     the min-width and scrolls horizontally instead. -->
				<section
					v-for="status in columnsToRender"
					:key="status"
					class="flex-1 flex flex-col min-h-0 rounded-[16px] border transition-colors lg:min-w-[280px] lg:max-w-[420px]"
					:class="dragOverStatus === status ? 'border-accent/50 bg-accent/[0.05]' : 'border-black/[0.06] dark:border-white/[0.07] bg-black/[0.02] dark:bg-white/[0.03]'"
					@dragover.prevent="onDragOver($event, status)"
					@dragleave="onDragLeave($event, status)"
					@drop="onDrop($event, status)"
				>
					<!-- Column header: state dot, name, count, add -->
					<header class="hidden lg:flex items-center gap-2 px-3 py-3 shrink-0">
						<span
							class="w-2 h-2 rounded-full shrink-0"
							:class="getStatusBulletColor(status)"
						></span>
						<h2
							class="text-[13px] font-semibold text-[#17181B] dark:text-white truncate"
						>
							{{ status }}
						</h2>
						<span
							class="text-xs font-medium text-[#5C6169] dark:text-white/60 tabular-nums"
							>{{ getTodosByStatus(status).length }}</span
						>
						<button
							@click="openAddTaskInStatus(status)"
							class="ml-auto w-7 h-7 shrink-0 grid place-items-center rounded-full text-[#5C6169] dark:text-white/65 hover:bg-black/[0.06] dark:hover:bg-white/[0.10] hover:text-accent transition-colors"
							:title="'Add task to ' + status"
							:aria-label="'Add task to ' + status"
						>
							<span class="material-symbols-outlined !text-[18px]">add</span>
						</button>
					</header>

					<button
						@click="openAddTaskInStatus(status)"
						class="lg:hidden mx-2.5 mt-2.5 h-10 shrink-0 flex items-center justify-center gap-1.5 rounded-[12px] border border-dashed border-black/15 dark:border-white/20 text-[13px] font-medium text-[#5C6169] dark:text-white/65"
					>
						<span class="material-symbols-outlined !text-[18px]">add</span>
						Add to {{ status }}
					</button>

					<div
						data-column-scroller
						class="flex-1 min-h-0 overflow-y-auto column-scroll px-2.5 pb-2.5 space-y-2.5"
					>
						<article
							v-for="todo in getTodosByStatus(status)"
							:key="todo.id"
							:draggable="true"
							@dragstart="onDragStart($event, todo, 'todo')"
							@dragend="onDragEnd"
							@click="openViewTaskDialog(todo.id)"
							class="task-card rounded-[16px] bg-white dark:bg-surface-2 border border-black/[0.06] dark:border-white/[0.08] p-3.5 cursor-pointer active:cursor-grabbing hover:border-accent/35 hover:shadow-[0_8px_24px_-14px_rgba(51,40,123,.35)] transition-all"
							:class="[ draggedItem?.id === todo.id ? 'opacity-50' : '', todo.status === 'Closed' || todo.status === 'Cancelled' ? 'opacity-70' : '', ]"
						>
							<!-- Chips first, the way the reference cards open -->
							<div class="flex items-start gap-2 mb-2.5">
								<div class="flex flex-wrap items-center gap-1.5 min-w-0">
									<span class="premium-tag" :class="getPriorityTagClass(todo.priority)">{{
										todo.priority || 'Normal'
									}}</span>
									<span
										v-if="todo.date"
										class="premium-tag"
										:class="isTodoOverdueOrDueToday(todo) ? 'tag-red' : 'tag-neutral'"
										>{{ dueLabel(todo) }}</span
									>
								</div>

								<div class="relative ml-auto shrink-0">
									<button
										@click.stop="toggleTodoMenu(todo, $event)"
										class="row-actions-btn"
										:class="menuTodo?.name === todo.name && 'row-actions-btn-open'"
										aria-haspopup="menu"
										:aria-expanded="menuTodo?.name === todo.name"
									>
										<span>More</span>
										<span class="material-symbols-outlined !text-[16px] transition-transform" :class="menuTodo?.name === todo.name && 'rotate-180'">expand_more</span>
									</button>

								</div>
							</div>

							<p
								class="text-[13px] font-medium text-[#17181B] dark:text-white leading-snug line-clamp-3"
							>
								{{ todo.description }}
							</p>

							<footer
								class="flex items-center gap-2 mt-3 pt-3 border-t border-black/[0.06] dark:border-white/[0.07]"
							>
								<!-- An em dash in an accent disc read as a person whose initials
								     are "—". Unassigned gets a neutral outline and a person icon. -->
								<span
									v-if="assigneeName(todo)"
									class="w-6 h-6 shrink-0 rounded-full bg-accent/10 text-accent dark:text-accent-light grid place-items-center text-xs font-semibold"
									:title="assigneeName(todo)"
									>{{ assigneeInitials(todo) }}</span
								>
								<span
									v-else
									class="w-6 h-6 shrink-0 rounded-full border border-dashed border-black/20 dark:border-white/25 text-[#656A72] dark:text-white/55 grid place-items-center"
									title="Unassigned"
								>
									<span class="material-symbols-outlined !text-[14px]">person</span>
								</span>
								<span
									class="text-xs text-[#5C6169] dark:text-white/65 truncate min-w-0 flex-1"
									>{{ assigneeName(todo) || 'Unassigned' }}</span
								>
								<span
									class="text-xs font-mono text-[#656A72] dark:text-white/55 shrink-0"
									>{{ todo.id }}</span
								>
							</footer>
						</article>

						<!-- Empty column: the drop target has to look like one -->
						<div
							v-if="getTodosByStatus(status).length === 0"
							class="h-32 rounded-[16px] border-2 border-dashed border-black/[0.09] dark:border-white/[0.12] grid place-content-center text-center px-4"
						>
							<span
								class="material-symbols-outlined !text-[24px] text-[#C4C7CC] dark:text-white/25 mx-auto"
								>task_alt</span
							>
							<p class="text-xs text-[#656A72] dark:text-white/55 mt-1.5">
								Drop a task here
							</p>
						</div>
					</div>
				</section>
			</div>

			<!-- ===== List ===== -->
			<div v-else class="h-full flex flex-col min-h-0">
				<div
					v-if="filteredTodos.length === 0"
					class="glass-card flex-1 grid place-content-center text-center px-6"
				>
					<span
						class="material-symbols-outlined !text-[32px] text-[#C4C7CC] dark:text-white/25 mx-auto"
						>inventory_2</span
					>
					<h3 class="text-base font-semibold text-[#17181B] dark:text-white mt-3">
						No tasks found
					</h3>
					<p class="text-[13px] text-[#5C6169] dark:text-white/65 mt-1 max-w-sm">
						Nothing matches these filters. Try a different search or clear them.
					</p>
					<button
						@click="clearFilters"
						class="btn-primary mt-4 mx-auto"
					>
						Clear filters
					</button>
				</div>

				<div v-else class="table-card flex-1 flex flex-col min-h-0">
					<div class="overflow-auto flex-1 custom-scrollbar">
						<table class="w-full text-left">
							<thead
								class="sticky top-0 z-10 bg-white/95 dark:bg-surface-1/95 backdrop-blur-sm"
							>
								<tr
									class="text-xs font-medium text-[#5C6169] dark:text-white/65 border-b border-black/[0.07] dark:border-white/[0.08]"
								>
									<th class="px-4 py-3 font-medium">Task</th>
									<th class="px-4 py-3 font-medium">Description</th>
									<th class="px-4 py-3 font-medium">Priority</th>
									<th class="px-4 py-3 font-medium">Status</th>
									<th class="px-4 py-3 font-medium">Assigned to</th>
									<th class="px-4 py-3 font-medium">Due</th>
									<th class="px-4 py-3 font-medium text-right">Actions</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-black/[0.05] dark:divide-white/[0.06]">
								<tr
									v-for="todo in pg.rows"
									:key="todo.id"
									@click="openViewTaskDialog(todo.id)"
									class="cursor-pointer hover:bg-black/[0.02] dark:hover:bg-white/[0.04] transition-colors"
								>
									<td
										class="px-4 py-3 text-xs font-mono text-[#5C6169] dark:text-white/65 whitespace-nowrap"
									>
										{{ todo.id }}
									</td>
									<td class="px-4 py-3">
										<div
											class="text-[13px] text-[#17181B] dark:text-white line-clamp-1 max-w-[320px]"
											:title="todo.description"
										>
											{{ todo.description }}
										</div>
									</td>
									<td class="px-4 py-3 whitespace-nowrap">
										<span class="premium-tag" :class="getPriorityTagClass(todo.priority)">{{
											todo.priority || 'Normal'
										}}</span>
									</td>
									<td class="px-4 py-3 whitespace-nowrap">
										<span class="premium-tag" :class="getStatusBadgeClass(todo.status)">{{
											todo.status
										}}</span>
									</td>
									<td
										class="px-4 py-3 text-[13px] text-[#5C6169] dark:text-white/65 whitespace-nowrap"
									>
										{{ assigneeName(todo) || '—' }}
									</td>
									<td
										class="px-4 py-3 text-[13px] whitespace-nowrap tabular-nums"
										:class="isTodoOverdueOrDueToday(todo) ? 'text-[#DC2626] dark:text-red-400 font-medium' : 'text-[#5C6169] dark:text-white/65'"
									>
										{{ formatTodoDate(todo.date) || '—' }}
									</td>
									<td class="px-4 py-3 text-right whitespace-nowrap">
										<div class="relative inline-block">
											<button
										@click.stop="toggleTodoMenu(todo, $event)"
										class="row-actions-btn"
										:class="menuTodo?.name === todo.name && 'row-actions-btn-open'"
										aria-haspopup="menu"
										:aria-expanded="menuTodo?.name === todo.name"
									>
										<span>More</span>
										<span class="material-symbols-outlined !text-[16px] transition-transform" :class="menuTodo?.name === todo.name && 'rotate-180'">expand_more</span>
									</button>

										</div>
									</td>
								</tr>
							</tbody>
						</table>
					</div>
					<TablePager v-if="pg.total > 0" v-model:page="pg.page" v-model:page-size="pg.size" :total="pg.total" />
				</div>
			</div>
		</div>

		<!-- ===== Task actions menu =====
		     One menu for both views, teleported to the body. Inline inside a
		     column it was clipped by that column's own overflow — the menu could
		     only ever draw as far as the card's edge. Positioned from the
		     button's rect and flipped up when it would run past the viewport. -->
		<Teleport to="body">
			<div
				v-if="menuTodo"
				class="fixed inset-0 z-[70]"
				@click="closeTodoMenu"
				@contextmenu.prevent="closeTodoMenu"
			></div>
			<div
				v-if="menuTodo"
				class="fixed w-44 rounded-[12px] bg-white dark:bg-surface-2 border border-black/[0.08] dark:border-white/10 shadow-[0_20px_50px_-20px_rgba(0,0,0,.35)] py-1.5 z-[71]"
				:style="{ top: menuPos.top + 'px', left: menuPos.left + 'px' }"
			>
				<button
					@click.stop="openEditTaskDialog(menuTodo)"
					class="w-full text-left px-3 py-2 text-[13px] text-[#17181B] dark:text-white hover:bg-black/[0.04] dark:hover:bg-white/[0.06] flex items-center gap-2.5"
				>
					<span class="material-symbols-outlined !text-[18px]">edit</span>Edit
				</button>
				<button
					@click.stop="handleDeleteTodo(menuTodo.id)"
					class="w-full text-left px-3 py-2 text-[13px] text-red-600 dark:text-red-400 hover:bg-red-500/[0.07] flex items-center gap-2.5"
				>
					<span class="material-symbols-outlined !text-[18px]">delete</span>Delete
				</button>

				<div class="h-px my-1.5 bg-black/[0.07] dark:bg-white/[0.08]"></div>

				<button
					v-for="st in visibleStatuses"
					:key="st"
					v-show="st !== menuTodo.status"
					@click.stop="handleUpdateStatus(menuTodo.id, st)"
					class="w-full text-left px-3 py-2 text-[13px] text-[#17181B] dark:text-white hover:bg-black/[0.04] dark:hover:bg-white/[0.06] flex items-center gap-2.5"
				>
					<span class="material-symbols-outlined !text-[18px]">{{
						st === 'Closed' ? 'check_circle' : st === 'Cancelled' ? 'cancel' : 'play_arrow'
					}}</span>
					Move to {{ st }}
				</button>
			</div>
		</Teleport>

		<!-- Add/Edit Task Dialog -->
		<CreateTasks
			v-if="showAddTaskDialog"
			:isEditing="isEditing"
			:todoToEdit="currentTodoToEdit"
			:metadata="metadata"
			:allocatableUsers="tasksStore.allocatableUsersList.data"
			:loading="tasksStore.loading"
			@close="showAddTaskDialog = false"
			@save="handleSaveTaskFromForm"
		/>

		<!-- Manage Statuses Dialog -->
		<CreateStatus v-if="showAddStatusDialog" @close="showAddStatusDialog = false" />

		<!-- View Task Dialog -->
		<ViewTask
			v-if="showViewTaskDialog"
			:todoId="currentTodoToViewId"
			@close="showViewTaskDialog = false"
			@edit="handleEditFromView"
		/>
	</div>
</template>

<script setup>
import TablePager from '@/components/TablePager.vue'
import { usePager } from '@/composables/usePager.js'
import { notify, ask } from '@/utils/feedback.js'
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { createResource } from "frappe-ui";
import { useTasksStore } from "@/stores/tasks";
import SearchableDropdown from "@/components/SearchableDropdown.vue";
import CreateTasks from "@/views/forms/tasks/create_tasks.vue";
import CreateStatus from "@/views/forms/tasks/create_status.vue";
import ViewTask from "@/views/page_views/task/view_tasks.vue";
import DateRangePicker from "@/components/DateRangePicker.vue";
import { getErrorMessage } from "@/utils";

const tasksStore = useTasksStore();

const draggedItem = ref(null);
const draggedType = ref(null);
const dragOverStatus = ref(null);
const viewMode = ref("card");
const kanbanContainer = ref(null);

// Panning state
const isPanning = ref(false);
let startX = 0;
let scrollLeft = 0;

// Administrative User Filter
const selectedUserFilter = ref("");

// General Filters
const searchQuery = ref("");
const selectedPriorityFilter = ref("");
const selectedStatusFilter = ref("");
const datePreset = ref("All Time");
const dateFrom = ref("");
const dateTo = ref("");

// Dialog states
const showAddTaskDialog = ref(false);
const showAddStatusDialog = ref(false);
const showViewTaskDialog = ref(false);
const currentTodoToViewId = ref(null);
const isEditing = ref(false);
const currentTodoToEdit = ref(null);

// Card actions menu state
const activeTodoMenuId = ref(null);
const menuTodo = ref(null);
const menuPos = ref({ top: 0, left: 0 });

const metadata = ref({
	can_assign_to_others: false,
	priorities: ["Low", "Medium", "High"],
	statuses: ["Open", "Closed", "Cancelled"],
	users: [],
	current_user: null,
	today: new Date().toISOString().split("T")[0]
});

const metadataResource = createResource({
	url: "arijentek_core.api.tasks.get_todo_creation_metadata",
	auto: true,
	onSuccess(data) {
		if (data) {
			metadata.value = data;
		}
	}
});

const visibleStatuses = computed(() => {
	return tasksStore.taskStatusList.data || metadata.value.statuses || [];
});

const viewOptions = [
	{ value: "card", label: "Board", icon: "view_kanban" },
	{ value: "list", label: "List", icon: "format_list_bulleted" },
];

/* Phone layout is driven by a media query rather than a width ref, so it
   matches the `lg:` breakpoint the classes use and updates on rotation. */
const MOBILE_QUERY = "(max-width: 1023.98px)";
const isMobile = ref(false);
let mq = null;
function onMediaChange(e) {
	isMobile.value = e.matches;
	if (!e.matches) filtersOpen.value = false;
}

const filtersOpen = ref(false);

/* One column at a time on a phone. */
const activeStatus = ref(null);
const columnsToRender = computed(() => {
	if (!isMobile.value) return visibleStatuses.value;
	const list = visibleStatuses.value;
	if (!list.length) return [];
	return [list.includes(activeStatus.value) ? activeStatus.value : list[0]];
});
watch(
	visibleStatuses,
	(list) => {
		if (list.length && !list.includes(activeStatus.value)) activeStatus.value = list[0];
	},
	{ immediate: true }
);

const activeFilterCount = computed(
	() =>
		[
			searchQuery.value,
			selectedPriorityFilter.value,
			viewMode.value === "list" ? selectedStatusFilter.value : "",
			dateFrom.value,
			selectedUserFilter.value,
		].filter(Boolean).length
);

const openCount = computed(() => (tasksStore.todos || []).filter((t) => t.status === "Open").length);

const hasActiveFilters = computed(
	() =>
		Boolean(searchQuery.value) ||
		Boolean(selectedPriorityFilter.value) ||
		Boolean(selectedStatusFilter.value) ||
		Boolean(dateFrom.value) ||
		Boolean(dateTo.value)
);

function assigneeName(todo) {
	return todo.allocated_to_name || todo.allocated_to || "";
}

function assigneeInitials(todo) {
	const name = assigneeName(todo);
	if (!name) return "—";
	return name
		.split(/[\s@._]+/)
		.filter(Boolean)
		.map((n) => n[0])
		.join("")
		.substring(0, 2)
		.toUpperCase();
}

/* The card shows one due chip, so it says how near the date is rather than
   repeating the date the list view already prints in full. */
function dueLabel(todo) {
	if (!todo.date) return "";
	const due = new Date(todo.date + "T00:00:00");
	const today = new Date();
	today.setHours(0, 0, 0, 0);
	const days = Math.round((due - today) / 86400000);
	if (days < 0) return `Overdue ${Math.abs(days)}d`;
	if (days === 0) return "Due today";
	if (days === 1) return "Due tomorrow";
	if (days <= 7) return `Due in ${days}d`;
	return formatTodoDate(todo.date);
}

/* The "+" in a column header opens the form already pointed at that column,
   so adding to In Progress does not mean creating in Open then dragging. */
function openAddTaskInStatus(status) {
	isEditing.value = false;
	currentTodoToEdit.value = { status };
	showAddTaskDialog.value = true;
}

const priorityOptions = computed(() => {
	return (metadata.value.priorities || []).map(p => ({ label: p, value: p }));
});

const statusOptions = computed(() => {
	return visibleStatuses.value.map(s => ({ label: s, value: s }));
});

const filteredTodos = computed(() => {
	let list = tasksStore.todos || [];

	if (searchQuery.value) {
		const q = searchQuery.value.toLowerCase();
		list = list.filter(t => 
			(t.id && t.id.toLowerCase().includes(q)) || 
			(t.description && t.description.toLowerCase().includes(q))
		);
	}

	if (selectedPriorityFilter.value) {
		list = list.filter(t => t.priority === selectedPriorityFilter.value);
	}

	// Status filter only applies explicitly in list view
	if (selectedStatusFilter.value && viewMode.value === 'list') {
		list = list.filter(t => t.status === selectedStatusFilter.value);
	}

	if (dateFrom.value && dateTo.value) {
		list = list.filter(t => {
			if (!t.date) return false;
			return t.date >= dateFrom.value && t.date <= dateTo.value;
		});
	}

	return list;
});

function clearFilters() {
	searchQuery.value = "";
	selectedPriorityFilter.value = "";
	selectedStatusFilter.value = "";
	datePreset.value = "All Time";
	dateFrom.value = "";
	dateTo.value = "";
}

function openAddTaskDialog() {
	isEditing.value = false;
	currentTodoToEdit.value = null;
	showAddTaskDialog.value = true;
}

function openViewTaskDialog(todoId) {
	currentTodoToViewId.value = todoId;
	showViewTaskDialog.value = true;
}

function handleEditFromView(todoData) {
	showViewTaskDialog.value = false;
	currentTodoToEdit.value = todoData;
	isEditing.value = true;
	showAddTaskDialog.value = true;
}

function openEditTaskDialog(todo) {
	isEditing.value = true;
	closeTodoMenu(); // Close menu on click edit
	
	// Temporarily set the partial todo to show something quickly (optional)
	currentTodoToEdit.value = todo;
	showAddTaskDialog.value = true;

	// Fetch the full detail
	tasksStore.fetchTodoDetail(todo.id).then(fullTodo => {
		if (fullTodo) {
			currentTodoToEdit.value = fullTodo;
		}
	}).catch(err => {
		console.error("Failed to fetch task details:", err);
		notify(getErrorMessage(err, "Failed to fetch task details."));
	});
}

const MENU_WIDTH = 176; // w-44
const MENU_MAX_HEIGHT = 220;

function toggleTodoMenu(todo, event) {
	const id = typeof todo === "object" ? todo.id : todo;
	if (activeTodoMenuId.value === id) {
		closeTodoMenu();
		return;
	}
	activeTodoMenuId.value = id;
	menuTodo.value = typeof todo === "object" ? todo : (tasksStore.todos || []).find((t) => t.id === id);

	const rect = event?.currentTarget?.getBoundingClientRect();
	if (!rect) return;
	// Right-align to the button, then pull back inside the viewport; flip above
	// when there is not room below.
	const left = Math.min(
		Math.max(8, rect.right - MENU_WIDTH),
		window.innerWidth - MENU_WIDTH - 8
	);
	const below = window.innerHeight - rect.bottom;
	const top = below < MENU_MAX_HEIGHT ? rect.top - MENU_MAX_HEIGHT - 4 : rect.bottom + 4;
	menuPos.value = { top: Math.max(8, top), left };
}

function closeTodoMenu() {
	activeTodoMenuId.value = null;
	menuTodo.value = null;
}

async function handleDeleteTodo(todoId) {
	closeTodoMenu();
	if (await ask("Are you sure you want to delete this task?")) {
		try {
			await tasksStore.deleteTodoItem(todoId, selectedUserFilter.value);
		} catch (err) {
			console.error("Failed to delete todo:", err);
			notify(getErrorMessage(err, "Failed to delete task."));
		}
	}
}

async function handleUpdateStatus(todoId, status) {
	closeTodoMenu();
	try {
		await tasksStore.updateTodoStatus(todoId, status, selectedUserFilter.value);
	} catch (err) {
		console.error("Failed to update todo status:", err);
		notify(getErrorMessage(err, "Failed to update task status."));
	}
}

async function handleSaveTaskFromForm(formData) {
	try {
		let taskId = formData.id;
		if (isEditing.value) {
			const result = await tasksStore.updateTodo(
				formData.id,
				formData.description,
				formData.dueDate,
				formData.priority,
				formData.assignedTo || null,
				formData.status,
				selectedUserFilter.value
			);
			if (result && result.todo_id) taskId = result.todo_id;
		} else {
			const result = await tasksStore.createTodo(
				formData.description,
				formData.dueDate,
				formData.priority,
				formData.assignedTo || null,
				selectedUserFilter.value,
				formData.status
			);
			if (result && result.todo_id) taskId = result.todo_id;
		}
		
		// Handle attachments upload
		if (taskId && formData.attachments && formData.attachments.length > 0) {
			const newFiles = formData.attachments.filter(f => !f.isExisting);
			for (const file of newFiles) {
				const form = new FormData();
				form.append('file', file, file.name);
				form.append('is_private', 1);
				form.append('doctype', 'ToDo');
				form.append('docname', taskId);
				
				await fetch('/api/method/upload_file', {
					method: 'POST',
					headers: {
						'Accept': 'application/json',
						'X-Frappe-CSRF-Token': window.csrf_token || ''
					},
					body: form
				});
			}
		}
		
		showAddTaskDialog.value = false;
	} catch (err) {
		console.error("Task save error:", err);
		notify(getErrorMessage(err, "Failed to save task."));
	}
}

const priorityOrder = { High: 1, Medium: 2, Low: 3 };

function getTodosByStatus(status) {
	if (!filteredTodos.value) return [];
	return [...filteredTodos.value]
		.filter((t) => t.status === status)
		.sort((a, b) => (priorityOrder[a.priority] || 99) - (priorityOrder[b.priority] || 99));
}

/* Column dot. Open is the accent because it is the working state, not a
   success; green is reserved for something that finished well. */
function getStatusBulletColor(status) {
	if (status === "Closed") return "bg-green-600";
	if (status === "Cancelled") return "bg-[#DC2626]";
	if (status === "Open") return "bg-accent";
	return "bg-[#9AA0A8]";
}

function getPriorityTagClass(priority) {
	if (priority === "High") return "tag-red";
	if (priority === "Medium") return "tag-amber";
	return "tag-neutral";
}

function getStatusBadgeClass(status) {
	if (status === "Closed") return "tag-emerald";
	if (status === "Cancelled") return "tag-red";
	if (status === "Open") return "tag-accent";
	return "tag-neutral";
}

function getInitials(name) {
	if (!name) return "?";
	return name.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2);
}

function formatTodoDate(dateStr) {
	if (!dateStr) return "";
	const d = new Date(dateStr + "T00:00:00");
	return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function isTodoDueToday(todo) {
	if (!todo.date) return false;
	const today = new Date().toISOString().split("T")[0];
	return todo.date === today;
}

function isTodoOverdueOrDueToday(todo) {
	if (!todo.date) return false;
	const today = new Date();
	today.setHours(0, 0, 0, 0);
	const dueDate = new Date(todo.date + "T00:00:00");
	dueDate.setHours(0, 0, 0, 0);
	return dueDate <= today;
}

/* The board turns vertical wheel into horizontal pan — but it used to do that
   unconditionally, so a column with more cards than fit could never be
   scrolled: every wheel tick was swallowed and preventDefault'd. Now a column
   under the pointer that can still move in the wheel's direction keeps the
   event, and the board only pans once that column has nowhere left to go. */
function handleKanbanWheel(e) {
	if (!kanbanContainer.value || e.deltaY === 0) return;

	const col = e.target?.closest?.("[data-column-scroller]");
	if (col && col.scrollHeight > col.clientHeight) {
		const atTop = col.scrollTop <= 0;
		const atBottom = col.scrollTop + col.clientHeight >= col.scrollHeight - 1;
		if ((e.deltaY < 0 && !atTop) || (e.deltaY > 0 && !atBottom)) return;
	}

	kanbanContainer.value.scrollLeft += e.deltaY;
	e.preventDefault();
}

function handlePanStart(e) {
	// If clicking on a card, let the drag-and-drop or click handle it
	// Cards are .task-card now; the old .premium-card selector matched nothing,
	// so a click-drag starting on a card began a board pan as well as the drag.
	if (e.target.closest('.task-card') || e.target.closest('button')) return;
	
	isPanning.value = true;
	startX = e.pageX - kanbanContainer.value.offsetLeft;
	scrollLeft = kanbanContainer.value.scrollLeft;
}

function handlePanMove(e) {
	if (!isPanning.value || !kanbanContainer.value) return;
	e.preventDefault();
	const x = e.pageX - kanbanContainer.value.offsetLeft;
	const walk = (x - startX) * 1.5; // Scroll speed multiplier
	kanbanContainer.value.scrollLeft = scrollLeft - walk;
}

function handlePanEnd() {
	isPanning.value = false;
}

function onDragStart(event, item, type) {
	draggedItem.value = item;
	draggedType.value = type;
	event.dataTransfer.effectAllowed = "move";
}

function onDragEnd() {
	draggedItem.value = null;
	draggedType.value = null;
}

function onDragOver(event, status) {
	event.preventDefault();
	dragOverStatus.value = status;
}

function onDragLeave(event, status) {
	if (!event.currentTarget.contains(event.relatedTarget)) {
		if (dragOverStatus.value === status) {
			dragOverStatus.value = null;
		}
	}
}

async function onDrop(event, targetZone) {
	event.preventDefault();
	dragOverStatus.value = null;
	const item = draggedItem.value;
	const sourceType = draggedType.value;
	onDragEnd();

	if (!item) return;

	if (sourceType === "todo") {
		if (item.status !== targetZone) {
			await tasksStore.updateTodoStatus(item.id, targetZone, selectedUserFilter.value);
		}
	}
}

watch(selectedUserFilter, (newFilter) => {
	tasksStore.fetchTodos(newFilter);
});

onMounted(() => {
	tasksStore.init(selectedUserFilter.value);
	window.addEventListener("click", closeTodoMenu);
	mq = window.matchMedia(MOBILE_QUERY);
	isMobile.value = mq.matches;
	mq.addEventListener("change", onMediaChange);
});

onUnmounted(() => {
	window.removeEventListener("click", closeTodoMenu);
	mq?.removeEventListener("change", onMediaChange);
});

/* Client-side paging for the list(s) above (TablePager). */
const pg = usePager(() => filteredTodos)
</script>

<style scoped>
.no-scrollbar::-webkit-scrollbar {
	display: none;
}
.no-scrollbar {
	-ms-overflow-style: none;
	scrollbar-width: none;
}

/* Column scroller: no bar, as asked. A bar revealed on hover was measured to
   reflow every card in the column by 10px, which is worse than no bar at all.
   overscroll-behavior stops a column that has hit its end from handing the
   scroll up to the page. */
.column-scroll {
	scrollbar-width: none;
	-ms-overflow-style: none;
	overscroll-behavior: contain;
}
.column-scroll::-webkit-scrollbar {
	display: none;
}
</style>
