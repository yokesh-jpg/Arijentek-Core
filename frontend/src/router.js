import { createRouter, createWebHashHistory } from "vue-router";
import { useAuthStore } from "./stores/auth";

const router = createRouter({
	history: createWebHashHistory(),
	routes: [
		{
			path: "/login",
			name: "login",
			component: () => import("./views/Login.vue"),
			meta: { guest: true },
		},
		{
			path: "/desk",
			name: "desk",
			component: () => import("./views/DashboardView.vue"), // Placeholder for Desk view
			meta: { requiresAuth: true },
		},
		{
			path: "/",
			name: "dashboard",
			component: () => import("./views/DashboardView.vue"),
			meta: { requiresAuth: true },
		},
		{
			path: "/tasks",
			name: "tasks",
			component: () => import("./views/TasksView.vue"),
			meta: { requiresAuth: true },
		},
		{
			path: "/attendance",
			name: "attendance",
			component: () => import("./views/AttendanceView.vue"),
			meta: { requiresAuth: true },
		},
		{
			path: "/roster",
			name: "roster",
			component: () => import("./views/RosterView.vue"),
			meta: { requiresAuth: true },
		},
		{
			path: "/shift-assignment/:id",
			name: "shiftAssignmentView",
			component: () => import("./views/page_views/ShiftAssignmentPageView.vue"),
			meta: { requiresAuth: true },
		},
		{
			path: "/attendance-record/:id",
			name: "attendancePageView",
			component: () => import("./views/page_views/AttendancePageView.vue"),
			meta: { requiresAuth: true },
		},
		{
			path: "/leave",
			name: "leave",
			component: () => import("./views/LeaveView.vue"),
			meta: { requiresAuth: true },
		},
		{
			path: "/payroll",
			name: "payroll",
			component: () => import("./views/PayrollView.vue"),
			meta: { requiresAuth: true },
		},
		{
			path: "/expense",
			name: "expense",
			component: () => import("./views/ExpenseView.vue"),
			meta: { requiresAuth: true },
		},
		{
			path: "/issues",
			name: "issues",
			component: () => import("./views/IssuesView.vue"),
			meta: { requiresAuth: true },
		},
		{
			path: "/team",
			name: "team",
			component: () => import("./views/TeamView.vue"),
			meta: { requiresAuth: true },
		},
		{
			path: "/teams/roles/view/:role_name",
			name: "viewRole",
			component: () => import("./views/page_views/teams/view_roles.vue"),
			meta: { requiresAuth: true },
		},
		{
			path: "/reports",
			name: "reports",
			component: () => import("./views/ReportsView.vue"),
			meta: { requiresAuth: true },
		},
		{
			path: "/shift-types",
			name: "shift_types",
			component: () => import("./views/tab_settings/roster/tab_shift_types.vue"),
			meta: { requiresAuth: true },
		},
		{
			path: "/settings",
			name: "settings",
			component: () => import("./views/SettingsView.vue"),
			meta: { requiresAuth: true },
		},


		// Catch-all → dashboard
		{
			path: "/:pathMatch(.*)*",
			redirect: "/",
		},
	],
});

router.beforeEach(async (to, _from, next) => {
	const auth = useAuthStore();

	if (!auth.ready) {
		await auth.init();
	}

	if (to.meta.requiresAuth && !auth.isLoggedIn) {
		next({ name: "login" });
	} else if (to.name === "login" && auth.isLoggedIn) {
		next({ name: "dashboard" });
	} else {
		next();
	}
});

router.onError((error, to) => {
	const errors = ["Failed to fetch dynamically imported module", "Importing a module script failed"];
	if (errors.some((e) => error.message.includes(e))) {
		const lastReload = sessionStorage.getItem("last_chunk_error_reload");
		const now = Date.now();
		if (!lastReload || now - parseInt(lastReload, 10) > 10000) {
			sessionStorage.setItem("last_chunk_error_reload", now.toString());
			window.location.reload();
		}
	}
});

export default router;
