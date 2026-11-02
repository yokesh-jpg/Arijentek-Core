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

		<!-- Tab Content -->
		<div class="px-2 pb-20 lg:pb-0 tab-fill">
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
	</div>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue';
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

const permissions = ref({
  can_read_employee_grievance: false,
  can_read_grievance_type: false,
});

const checkPermissions = async () => {
  try {
    const issuesPerm = await call('arijentek_core.api.issues.can_read_employee_grievance');
    permissions.value.can_read_employee_grievance = !!issuesPerm;

    const typesPerm = await call('arijentek_core.api.issues.can_read_grievance_type');
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
    console.error("Error checking permissions:", error);
  }
};

onMounted(() => {
  checkPermissions();
});
</script>

<style scoped>
</style>
