<template>
	<div class="tab-page">
		<!-- Nav Tabs -->
		<TabBar>
			<button
				@click="activeTab = 'dashboard'"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'dashboard' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">receipt_long</span>
				<span class="tab-label">Expense claim</span>
			</button>
			<button
				v-if="canReadExpenseTypes"
				@click="activeTab = 'expense_types'"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'expense_types' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">category</span>
				<span class="tab-label">Expense types</span>
			</button>
		</TabBar>

		<!-- Tab Content -->
		<TabExpenseDashboard v-if="activeTab === 'dashboard'" />
		<TabExpenseTypes v-if="activeTab === 'expense_types' && canReadExpenseTypes" />
	</div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { call } from 'frappe-ui';
import TabExpenseDashboard from './tab_settings/expense/tab_expense_dashboard.vue';
import TabExpenseTypes from './tab_settings/expense/tab_expense_types.vue';
import TabBar from "@/components/TabBar.vue";

const route = useRoute();
const activeTab = ref(route.query.tab || 'dashboard');
const canReadExpenseTypes = ref(false);

onMounted(async () => {
  try {
    const res = await call('arijentek_core.api.expense.can_read_expense_types');
    canReadExpenseTypes.value = !!res;
  } catch (e) {
    console.error("Failed to check expense types permission", e);
  }
});
</script>
