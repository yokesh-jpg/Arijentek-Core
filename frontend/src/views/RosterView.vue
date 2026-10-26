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
		<TabRosterDashboard  v-if="activeTab === 'dashboard'" />
		<TabShiftAssignment  v-if="activeTab === 'assignment'" />
		<TabShiftLocation    v-if="activeTab === 'shift_location' && canManageShiftLocation" />
		<TabShiftTypes       v-if="activeTab === 'shift_types'   && canViewShiftType" />
	</div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { createResource } from 'frappe-ui';
import { useRosterStore } from '@/stores/roster';

import TabRosterDashboard from './tab_settings/roster/tab_roster_dashboard.vue';
import TabShiftAssignment from './tab_settings/roster/tab_shift_assignment.vue';
import TabShiftLocation   from './tab_settings/roster/tab_shift_location.vue';
import TabShiftTypes      from './tab_settings/roster/tab_shift_types.vue';
import TabBar from "@/components/TabBar.vue";

const rosterStore = useRosterStore();

const activeTab              = ref('dashboard');
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
