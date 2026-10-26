<template>
	<ReportDialog
		:show="show"
		title="User directory"
		subtitle="Portal accounts, the people behind them and whether they are active."
		:loading="loading"
		:empty="!reportData.length"
		empty-icon="person"
		empty-title="No users match these filters."
		empty-text="Try clearing the role filter."
		:count="reportData.length"
		unit="user"
		unit-plural="users"
		@close="emitClose"
		@export-excel="exportExcel"
		@export-pdf="exportPDF"
	>
		<template #filters>
			<div class="flex flex-wrap items-end gap-3">
				<div class="min-w-[170px] flex-1">
					<label class="field-label">System role</label>
					<SearchableDropdown
						v-model="filters.role"
						:options="filterOptions.roles"
						placeholder="All roles"
						@change="fetchReportData"
					/>
				</div>
			</div>
		</template>
		<div class="overflow-x-auto table-scroll">
			<ReportTable :columns="columns" :rows="reportData" />
		</div>
	</ReportDialog>
</template>

<script setup>
import { ref, reactive, watch } from 'vue';
import SearchableDropdown from '../../../../components/SearchableDropdown.vue';
import SelectField from '../../../../components/SelectField.vue'
import ReportDialog from '@/components/ReportDialog.vue';
import ReportTable from '@/components/ReportTable.vue';

const props = defineProps({
	show: {
		type: Boolean,
		default: false,
	},
});

const emit = defineEmits(['close']);

const emitClose = () => {
	emit('close');
};

const loading = ref(false);
let searchTimeout = null;

const filterOptions = reactive({
	roles: [],
});

const filters = reactive({
	role: '',
	status: 'Active',
	search: '',
});

const columns = ref([]);
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
		const res = await fetch('/api/method/arijentek_core.api.teams_permissons.get_roles', {
			method: 'GET',
			headers: { 'Content-Type': 'application/json' },
		});
		if (res.ok) {
			const data = await res.json();
			filterOptions.roles = data.message || [];
		}
	} catch (e) {
		console.warn('Failed to load roles list', e);
	}
};

async function fetchReportData() {
	loading.value = true;
	try {
		const params = new URLSearchParams();
		if (filters.role) params.set('role', filters.role);
		if (filters.status) params.set('status', filters.status);
		if (filters.search) params.set('search', filters.search);

		const res = await fetch(`/api/method/arijentek_core.api.teams_permissons.report_user_list?${params.toString()}`, {
			method: 'GET',
			headers: { 'Content-Type': 'application/json' },
		});

		if (res.ok) {
			const json = await res.json();
			const result = json.message || {};
			if (result.columns) columns.value = result.columns;
			reportData.value = result.data || [];
		} else {
			reportData.value = [];
		}
	} catch (e) {
		console.error('Error fetching user report data', e);
		reportData.value = [];
	} finally {
		loading.value = false;
	}
};

const debouncedFetch = () => {
	clearTimeout(searchTimeout);
	searchTimeout = setTimeout(() => {
		fetchReportData();
	}, 300);
};

const resetFilters = () => {
	filters.role = '';
	filters.status = 'Active';
	filters.search = '';
	fetchReportData();
};

const downloadRowProfilePDF = (userId) => {
	const url = `/api/method/arijentek_core.api.teams_permissons.generate_user_profile_pdf?user_id=${encodeURIComponent(userId)}`;
	window.open(url, '_blank');
};

const exportExcel = () => {
	const params = new URLSearchParams();
	if (filters.role) params.set('role', filters.role);
	if (filters.status) params.set('status', filters.status);
	if (filters.search) params.set('search', filters.search);
	params.set('export', '1');

	const url = `/api/method/arijentek_core.api.teams_permissons.report_user_list?${params.toString()}`;
	window.open(url, '_blank');
};

const exportPDF = () => {
	const params = new URLSearchParams();
	if (filters.role) params.set('role', filters.role);
	if (filters.status) params.set('status', filters.status);
	if (filters.search) params.set('search', filters.search);
	params.set('pdf', '1');

	const url = `/api/method/arijentek_core.api.teams_permissons.report_user_list?${params.toString()}`;
	window.open(url, '_blank');
};

;
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
