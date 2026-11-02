<template>
	<div class="tab-page">
		<!-- Nav Tabs -->
		<TabBar>
			<button
				@click="activeTab = 'dashboard'"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'dashboard' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">space_dashboard</span>
				<span class="tab-label">Dashboard</span>
			</button>
			<button
				@click="activeTab = 'assignment'"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'assignment' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">assignment_ind</span>
				<span class="tab-label">Shift assignment</span>
			</button>
			<button
				v-if="canManageShiftLocation"
				@click="activeTab = 'shift_location'"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'shift_location' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">location_on</span>
				<span class="tab-label">Shift location</span>
			</button>
			<button
				v-if="canViewShiftType"
				@click="activeTab = 'shift_types'"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'shift_types' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">category</span>
				<span class="tab-label">Shift types</span>
			</button>
		</TabBar>

		<!-- Tab Content -->
		<TabRosterDashboard  
			v-if="visitedTabs.dashboard" 
			v-show="activeTab === 'dashboard'" 
			:is-active="activeTab === 'dashboard'"
		/>
		<TabShiftAssignment  
			v-if="visitedTabs.assignment" 
			v-show="activeTab === 'assignment'" 
		/>
		<TabShiftLocation    
			v-if="visitedTabs.shift_location && canManageShiftLocation" 
			v-show="activeTab === 'shift_location'" 
		/>
		<TabShiftTypes       
			v-if="visitedTabs.shift_types && canViewShiftType" 
			v-show="activeTab === 'shift_types'" 
		/>
	</div>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue';
import { createResource } from 'frappe-ui';
import { useRosterStore } from '@/stores/roster';

defineOptions({ name: 'RosterView' });

import TabRosterDashboard from './tab_settings/roster/tab_roster_dashboard.vue';
import TabShiftAssignment from './tab_settings/roster/tab_shift_assignment.vue';
import TabShiftLocation   from './tab_settings/roster/tab_shift_location.vue';
import TabShiftTypes      from './tab_settings/roster/tab_shift_types.vue';
import TabBar from "@/components/TabBar.vue";

const rosterStore = useRosterStore();

const activeTab              = ref('dashboard');
const visitedTabs = reactive({
	dashboard: activeTab.value === 'dashboard',
	assignment: activeTab.value === 'assignment',
	shift_location: activeTab.value === 'shift_location',
	shift_types: activeTab.value === 'shift_types',
});

watch(activeTab, (newTab) => {
	if (newTab && visitedTabs[newTab] !== undefined) {
		visitedTabs[newTab] = true;
	}
});

const canManageShiftLocation = ref(false);
const canViewShiftType       = ref(false);

onMounted(async () => {
	try {
		canManageShiftLocation.value = await rosterStore.checkCanManageShiftLocation();
	} catch {
		canManageShiftLocation.value = false;
	}

	try {
		const res = createResource({
			url: 'arijentek_core.api.roster.can_view_shift_type',
			auto: false,
		});
		canViewShiftType.value = await res.fetch();
	} catch {
		canViewShiftType.value = false;
	}
});
</script>
