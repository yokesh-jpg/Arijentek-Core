<template>
	<ReportDialog
		:show="show"
		title="Expense types"
		subtitle="The categories a claim can be filed under, and the account each posts to."
		:loading="loading"
		:empty="!reportData.length"
		empty-icon="category"
		empty-title="No expense types configured."
		empty-text="Expense types are the categories staff pick from when claiming."
		:count="reportData.length"
		unit="type"
		unit-plural="types"
		@close="emitClose"
		@export-excel="exportExcel"
		@export-pdf="exportPDF"
	>
		<template #filters>
			<div class="flex flex-wrap items-end gap-3">
				<div class="min-w-[170px] flex-1">
					<label class="field-label">Account</label>
					<SearchableDropdown
						v-model="filters.account"
						:options="filterOptions.accounts"
						placeholder="All expense accounts"
						@change="fetchReportData"
					/>
				</div>
			</div>
		</template>
		<div class="overflow-x-auto table-scroll">
			<ReportTable :columns="REPORT_COLUMNS" :rows="reportData" />
		</div>
	</ReportDialog>
</template>

<script setup>
import { ref, reactive, watch } from 'vue';
import SearchableDropdown from '../../../../components/SearchableDropdown.vue';
import ReportDialog from '@/components/ReportDialog.vue';
import ReportTable from '@/components/ReportTable.vue';

const props = defineProps({
	show: {
		type: Boolean,
		default: false,
	},
});

const emit = defineEmits(['close']);

/* This report names its own columns rather than taking them from the
   server, so they live here instead of in the markup. */
const REPORT_COLUMNS = [
	{ fieldname: 'expense_type', label: 'Type' },
	{ fieldname: 'default_account', label: 'Default account' },
	{ fieldname: 'description', label: 'Description' },
];

const emitClose = () => {
	emit('close');
};

const loading = ref(false);

const filterOptions = reactive({
	accounts: [],
});

const filters = reactive({
	account: '',
});

const reportData = ref([]);

watch(
	() => props.show,
	async (newVal) => {
		if (newVal) {
			await fetchFilterOptions();
			await fetchReportData();
		}
	},
	{ immediate: true }
);

async function fetchFilterOptions() {
	try {
		const res = await fetch('/api/method/arijentek_core.api.expense.get_expense_type_report_filter_options', {
			method: 'GET',
			headers: { 'Content-Type': 'application/json' },
		});
		if (res.ok) {
			const data = await res.json();
			const msg = data.message || {};
			filterOptions.accounts = msg.accounts || [];
		}
	} catch (e) {
		console.warn('Failed to load filter options', e);
	}
};

async function fetchReportData() {
	loading.value = true;
	try {
		const params = new URLSearchParams();
		if (filters.account) params.set('account', filters.account);

		const res = await fetch(`/api/method/arijentek_core.api.expense.report_expense_type_list?${params.toString()}`, {
			method: 'GET',
			headers: { 'Content-Type': 'application/json' },
		});

		if (res.ok) {
			const json = await res.json();
			reportData.value = json.message || [];
		} else {
			reportData.value = [];
		}
	} catch (e) {
		console.error('Error fetching report data', e);
		reportData.value = [];
	} finally {
		loading.value = false;
	}
};

const resetFilters = () => {
	filters.account = '';
	fetchReportData();
};

const exportExcel = () => {
	const params = new URLSearchParams();
	if (filters.account) params.set('account', filters.account);
	params.set('export', '1');

	const url = `/api/method/arijentek_core.api.expense.report_expense_type_list?${params.toString()}`;
	window.open(url, '_blank');
};

const exportPDF = () => {
	const params = new URLSearchParams();
	if (filters.account) params.set('account', filters.account);
	params.set('pdf', '1');

	const url = `/api/method/arijentek_core.api.expense.report_expense_type_list?${params.toString()}`;
	window.open(url, '_blank');
};
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
	transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
	opacity: 0;
}
</style>
