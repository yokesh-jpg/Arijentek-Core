<template>
	<div class="tab-page">


		<!-- Nav Tabs -->
		<TabBar>
			<button
				v-if="canReadPayrollEntry"
				@click="setActiveTab('payroll')"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'payroll' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">payments</span>
				<span class="tab-label">Payroll</span>
			</button>
			<button
				v-if="canReadSalarySlip"
				@click="setActiveTab('salary_slip')"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'salary_slip' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">receipt</span>
				<span class="tab-label">Salary slips</span>
			</button>
			<button
				v-if="canReadAdditionalSalary"
				@click="setActiveTab('additional_salary')"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'additional_salary' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">add_card</span>
				<span class="tab-label">Additional salary</span>
			</button>
			<button
				v-if="canReadOvertimeSlip"
				@click="setActiveTab('overtime_slip')"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'overtime_slip' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">more_time</span>
				<span class="tab-label">Overtime slips</span>
			</button>
			<button
				v-if="canReadOvertimeType"
				@click="setActiveTab('overtime_type')"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'overtime_type' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">category</span>
				<span class="tab-label">Overtime types</span>
			</button>
			<button
				v-if="canReadSalaryStructureAssignment"
				@click="setActiveTab('salary_structure_assignment')"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'salary_structure_assignment' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">assignment_ind</span>
				<span class="tab-label">Structure assignments</span>
			</button>
			<button
				v-if="canReadSalaryStructure"
				@click="setActiveTab('salary_structure')"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'salary_structure' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">account_tree</span>
				<span class="tab-label">Salary structures</span>
			</button>
			<button
				v-if="canReadSalaryComponent"
				@click="setActiveTab('salary_component')"
				class="tab-item"
				:class="{ 'tab-item-active': activeTab === 'salary_component' }"
			>
				<span class="material-symbols-outlined tab-icon" aria-hidden="true">widgets</span>
				<span class="tab-label">Salary components</span>
			</button>
		</TabBar>

		<!-- Tab Content -->
		<div class="pb-20 lg:pb-0 tab-fill">
			<TabPayroll v-if="activeTab === 'payroll' && canReadPayrollEntry" />
			<TabSalarySlip v-if="activeTab === 'salary_slip' && canReadSalarySlip" />
			<TabAdditionalSalary v-if="activeTab === 'additional_salary' && canReadAdditionalSalary" />
			<TabOvertimeSlip v-if="activeTab === 'overtime_slip' && canReadOvertimeSlip" />
			<TabOvertimeType v-if="activeTab === 'overtime_type' && canReadOvertimeType" />
			<TabSalaryStructureAssignment v-if="activeTab === 'salary_structure_assignment' && canReadSalaryStructureAssignment" />
			<TabSalaryStructure v-if="activeTab === 'salary_structure' && canReadSalaryStructure" />
			<TabSalaryComponent v-if="activeTab === 'salary_component' && canReadSalaryComponent" />
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue';
import { useRoute } from 'vue-router';
import { storeToRefs } from 'pinia';
import { usePayrollStore } from '../stores/payroll';

import TabPayroll from './tab_settings/payroll/tab_payroll.vue';
import TabSalarySlip from './tab_settings/payroll/tab_salary_slip.vue';
import TabSalaryStructureAssignment from './tab_settings/payroll/tab_salary_structure_assignment.vue';
import TabSalaryStructure from './tab_settings/payroll/tab_salary_structure.vue';
import TabSalaryComponent from './tab_settings/payroll/tab_salary_component.vue';
import TabOvertimeType from './tab_settings/payroll/tab_overtime_type.vue';
import TabOvertimeSlip from './tab_settings/payroll/tab_overtime_slip.vue';
import TabAdditionalSalary from './tab_settings/payroll/tab_additional_salary.vue';
import TabBar from "@/components/TabBar.vue";

const payrollStore = usePayrollStore();
const { 
	canReadPayrollEntry, 
	canReadSalarySlip, 
	canReadSalaryStructureAssignment, 
	canReadSalaryStructure, 
	canReadSalaryComponent,
	canReadOvertimeType,
	canReadOvertimeSlip,
	canReadAdditionalSalary
} = storeToRefs(payrollStore);

const route = useRoute();
const activeTab = ref(route.query.tab || 'payroll');
const userInteracted = ref(!!route.query.tab);

watch(
	() => route.query.tab,
	(newTab) => {
		if (newTab) {
			activeTab.value = newTab;
			userInteracted.value = true;
		}
	}
);

function setActiveTab(tab) {
	activeTab.value = tab;
	userInteracted.value = true;
}

const allowedTabs = computed(() => {
	const tabs = [];
	if (canReadPayrollEntry.value) tabs.push('payroll');
	if (canReadSalarySlip.value) tabs.push('salary_slip');
	if (canReadAdditionalSalary.value) tabs.push('additional_salary');
	if (canReadOvertimeSlip.value) tabs.push('overtime_slip');
	if (canReadOvertimeType.value) tabs.push('overtime_type');
	if (canReadSalaryStructureAssignment.value) tabs.push('salary_structure_assignment');
	if (canReadSalaryStructure.value) tabs.push('salary_structure');
	if (canReadSalaryComponent.value) tabs.push('salary_component');
	return tabs;
});

watch(
	allowedTabs,
	(newTabs) => {
		if (!userInteracted.value && newTabs.length > 0) {
			activeTab.value = newTabs[0];
		}
	},
	{ immediate: true }
);

onMounted(() => {
	payrollStore.init();
});
</script>
