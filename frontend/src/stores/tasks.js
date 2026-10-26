import { defineStore } from "pinia";
import { createResource } from "frappe-ui";
import { ref, computed } from "vue";

export const useTasksStore = defineStore("tasks", () => {
	const todos = ref([]);
	const loading = ref(false);

	// Get personal todos
	const todosResource = createResource({
		url: "arijentek_core.api.tasks.get_personal_todos",
		auto: false,
		onSuccess(data) {
			todos.value = data || [];
		},
	});

	// Create todo
	const createTodoResource = createResource({
		url: "arijentek_core.api.tasks.create_personal_todo",
		auto: false,
	});

	// Update todo status
	const updateTodoResource = createResource({
		url: "arijentek_core.api.tasks.update_todo_status",
		auto: false,
	});

	// Delete todo
	const deleteTodoResource = createResource({
		url: "arijentek_core.api.tasks.delete_todo",
		auto: false,
	});

	// Update todo details
	const updateTodoDetailResource = createResource({
		url: "arijentek_core.api.tasks.update_personal_todo",
		auto: false,
	});

	// Get single todo detail
	const getTodoResource = createResource({
		url: "arijentek_core.api.tasks.get_todo",
		auto: false,
	});

	// Permissions
	const permissions = ref({
		can_read: false,
		can_create: false,
		can_edit: false,
		can_delete: false,
		can_allocate: false
	});

	const canReadTodoRes = createResource({ url: "arijentek_core.api.tasks.can_read_todo", auto: false, onSuccess(d) { permissions.value.can_read = d; } });
	const canCreateTodoRes = createResource({ url: "arijentek_core.api.tasks.can_create_todo", auto: false, onSuccess(d) { permissions.value.can_create = d; } });
	const canEditTodoRes = createResource({ url: "arijentek_core.api.tasks.can_edit_todo", auto: false, onSuccess(d) { permissions.value.can_edit = d; } });
	const canDeleteTodoRes = createResource({ url: "arijentek_core.api.tasks.can_delete_todo", auto: false, onSuccess(d) { permissions.value.can_delete = d; } });
	const canAllocateTodoRes = createResource({ url: "arijentek_core.api.tasks.can_allocate_todo", auto: false, onSuccess(d) { permissions.value.can_allocate = d; } });

	// Global lists
	const taskStatusList = createResource({
		url: "arijentek_core.api.tasks.get_task_status",
		auto: true,
	});

	const allocatableUsersList = createResource({
		url: "arijentek_core.api.tasks.get_allocatable_users",
		auto: true,
	});

	// Computed
	const openTodos = computed(() => {
		return todos.value.filter((t) => t.status === "Open");
	});

	const completedTodos = computed(() => {
		return todos.value.filter((t) => t.status === "Closed");
	});

	// Actions
	async function fetchTodos(userFilter = null) {
		await todosResource.fetch({ user_filter: userFilter });
	}

	async function createTodo(description, date = null, priority = "Medium", allocated_to = null, userFilter = null, status = "Open") {
		loading.value = true;
		try {
			const result = await createTodoResource.fetch({
				description,
				date,
				priority,
				allocated_to,
				status,
			});
			await fetchTodos(userFilter);
			return result;
		} finally {
			loading.value = false;
		}
	}

	async function updateTodo(todoId, description, date = null, priority = "Medium", allocated_to = null, status = "Open", userFilter = null) {
		loading.value = true;
		try {
			const result = await updateTodoDetailResource.fetch({
				todo_id: todoId,
				description,
				date,
				priority,
				allocated_to,
				status,
			});
			await fetchTodos(userFilter);
			return result;
		} finally {
			loading.value = false;
		}
	}

	async function toggleTodo(todoId, currentStatus, userFilter = null) {
		const newStatus = currentStatus === "Closed" ? "Open" : "Closed";
		await updateTodoResource.fetch({ todo_id: todoId, status: newStatus });
		await fetchTodos(userFilter);
	}

	async function updateTodoStatus(todoId, status, userFilter = null) {
		await updateTodoResource.fetch({ todo_id: todoId, status: status });
		await fetchTodos(userFilter);
	}

	// Optimistic delete - removes from UI immediately
	async function deleteTodoItem(todoId, userFilter = null) {
		const previousTodos = [...todos.value];
		todos.value = todos.value.filter((t) => t.id !== todoId);

		try {
			await deleteTodoResource.fetch({ todo_id: todoId });
			await fetchTodos(userFilter);
		} catch (error) {
			todos.value = previousTodos;
			throw error;
		}
	}

	async function fetchTodoDetail(name) {
		loading.value = true;
		try {
			const result = await getTodoResource.fetch({ name });
			return result;
		} finally {
			loading.value = false;
		}
	}

	async function loadPermissions(consolidatedPerms = null) {
		let perms = consolidatedPerms;
		if (!perms) {
			try {
				const res = await fetch("/api/method/arijentek_core.api.dashboard.get_all_portal_permissions");
				const json = await res.json();
				perms = json.message?.tasks;
			} catch (err) {
				console.error("Failed to load tasks permissions:", err);
			}
		}
		if (perms) {
			permissions.value.can_read = !!perms.can_read_todo;
			permissions.value.can_create = !!perms.can_create_todo;
			permissions.value.can_edit = !!perms.can_edit_todo;
			permissions.value.can_delete = !!perms.can_delete_todo;
			permissions.value.can_allocate = !!perms.can_allocate_todo;
		}
	}

	// Initialize store
	function init(userFilter = null) {
		loadPermissions();
		fetchTodos(userFilter);
	}

	return {
		todos,
		loading,
		openTodos,
		completedTodos,
		fetchTodos,
		fetchTodoDetail,
		createTodo,
		updateTodo,
		toggleTodo,
		updateTodoStatus,
		deleteTodoItem,
		init,
		permissions,
		taskStatusList,
		allocatableUsersList,
		loadPermissions,
	};
});
