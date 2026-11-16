<template>
	<div class="tab-page">

		<!-- Nav Tabs -->
		<TabBar>
			<button
				v-if="permissions.can_read_employee_grievance"
				@click="activeTab = 'issues'"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'issues' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">report</span>
				<span class="tab-label">Issues</span>
			</button>
			<button
				v-if="permissions.can_read_grievance_type"
				@click="activeTab = 'types'"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'types' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">label</span>
				<span class="tab-label">Issue types</span>
			</button>
		</TabBar>

		<!-- Loading state while resolving permissions -->
		<div v-if="!permissionsLoaded" class="tab-fill flex items-center justify-center p-16">
			<div class="flex flex-col items-center gap-3">
				<span class="w-8 h-8 rounded-full border-2 border-accent/20 border-t-accent animate-spin"></span>
				<p class="text-xs text-[#656A72] dark:text-white/50">Verifying access…</p>
			</div>
		</div>

		<!-- Tab Content -->
		<div v-else-if="hasAnyIssuesPermission" class="px-2 pb-20 lg:pb-0 tab-fill">
			<TabIssues 
				v-if="visitedTabs.issues && permissions.can_read_employee_grievance" 
				v-show="activeTab === 'issues'"
				:is-active="activeTab === 'issues'"
			/>
			<TabIssuesType 
				v-if="visitedTabs.types && permissions.can_read_grievance_type" 
				v-show="activeTab === 'types'"
			/>
		</div>

		<!-- Fallback when user has no permissions to issues -->
		<div v-else class="glass-card p-12 text-center my-6 max-w-lg mx-auto">
			<span class="material-symbols-outlined !text-[48px] text-[#9AA0A8] dark:text-white/30 mb-3">shield</span>
			<h3 class="text-base font-semibold text-[#17181B] dark:text-white">Issues Access Restricted</h3>
			<p class="text-xs text-[#5C6169] dark:text-white/60 mt-1.5 leading-relaxed">
				You do not have permission to view or manage employee issues. Contact your supervisor or HR for assistance.
			</p>
		</div>
	</div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { call } from 'frappe-ui';

defineOptions({ name: 'IssuesView' });

import TabIssues from './tab_settings/issues/tab_issues.vue';
import TabIssuesType from './tab_settings/issues/tab_issues_type.vue';
import TabBar from "@/components/TabBar.vue";

const route = useRoute();
const activeTab = ref(route.query.tab || '');
const visitedTabs = reactive({
  issues: activeTab.value === 'issues',
  types: activeTab.value === 'types',
});

watch(
  () => route.query.tab,
  (newTab) => {
    if (newTab) {
      activeTab.value = newTab;
    }
  }
);

watch(activeTab, (newTab) => {
  if (newTab && visitedTabs[newTab] !== undefined) {
    visitedTabs[newTab] = true;
  }
});

const permissionsLoaded = ref(false);
const permissions = ref({
  can_read_employee_grievance: false,
  can_read_grievance_type: false,
});

const hasAnyIssuesPermission = computed(() => {
  return !!(permissions.value.can_read_employee_grievance || permissions.value.can_read_grievance_type);
});

const checkPermissions = async () => {
  try {
    const [issuesPerm, typesPerm] = await Promise.all([
      call('arijentek_core.api.issues.can_read_employee_grievance').catch(() => false),
      call('arijentek_core.api.issues.can_read_grievance_type').catch(() => false),
    ]);
    permissions.value.can_read_employee_grievance = !!issuesPerm;
    permissions.value.can_read_grievance_type = !!typesPerm;

    // Set default active tab only if not already set by route query
    if (!activeTab.value) {
      if (permissions.value.can_read_employee_grievance) {
        activeTab.value = 'issues';
      } else if (permissions.value.can_read_grievance_type) {
        activeTab.value = 'types';
      }
    }
    if (activeTab.value && visitedTabs[activeTab.value] !== undefined) {
      visitedTabs[activeTab.value] = true;
    }
  } catch (error) {
    console.warn("Permission check notice in IssuesView:", error);
  } finally {
    permissionsLoaded.value = true;
  }
};

onMounted(() => {
  checkPermissions();
});
</script>

<style scoped>
</style>
