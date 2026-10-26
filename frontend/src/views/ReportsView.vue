<template>
	<div class="tab-page">
		<div class="page-head">
			<h1 class="page-title">Reports</h1>
			<p class="page-subtitle">Exports and summaries across attendance, leave, pay and the rest.</p>
		</div>

		<TabBar>
			<button
				v-for="tab in reportTabs"
				:key="tab.id"
				@click="activeTab = tab.id"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === tab.id }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">{{ tab.icon }}</span>
				<span class="tab-label">{{ tab.label }}</span>
			</button>
		</TabBar>

		<component :is="activeTabComponent" />
	</div>
</template>

<script setup>
import { ref, computed } from 'vue';
import TabBar from '@/components/TabBar.vue';

import TabAttendance from './tab_settings/reports/tab_attendance.vue';
import TabRoster from './tab_settings/reports/tab_roster.vue';
import TabTasks from './tab_settings/reports/tab_tasks.vue';
import TabLeave from './tab_settings/reports/tab_leave.vue';
import TabPayroll from './tab_settings/reports/tab_payroll.vue';
import TabExpense from './tab_settings/reports/tab_expense.vue';
import TabIssues from './tab_settings/reports/tab_issues.vue';
import TabTeams from './tab_settings/reports/tab_teams.vue';

const activeTab = ref('attendance');

const reportTabs = [
	{ id: 'attendance', label: 'Attendance', icon: 'calendar_today', component: TabAttendance },
	{ id: 'roster', label: 'Roster', icon: 'schedule', component: TabRoster },
	{ id: 'tasks', label: 'Tasks', icon: 'task_alt', component: TabTasks },
	{ id: 'leave', label: 'Leave', icon: 'beach_access', component: TabLeave },
	{ id: 'payroll', label: 'Payroll', icon: 'account_balance_wallet', component: TabPayroll },
	{ id: 'expense', label: 'Expense', icon: 'payments', component: TabExpense },
	{ id: 'issues', label: 'Issues', icon: 'support_agent', component: TabIssues },
	{ id: 'teams', label: 'Teams', icon: 'groups', component: TabTeams },
];

const activeTabComponent = computed(() => {
	const tab = reportTabs.find(t => t.id === activeTab.value);
	return tab ? tab.component : null;
});
</script>
