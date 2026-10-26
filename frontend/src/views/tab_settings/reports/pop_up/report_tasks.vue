<template>
	<ReportDialog
		:show="show"
		title="Tasks"
		subtitle="Tasks assigned to staff, with their status and due date."
		:loading="loading"
		:empty="!reportData.length"
		empty-icon="task_alt"
		empty-title="No tasks match these filters."
		empty-text="Try widening the date range or clearing the status filter."
		:count="reportData.length"
		unit="task"
		unit-plural="tasks"
		@close="emitClose"
		@export-excel="exportExcel"
		@export-pdf="exportPDF"
	>
		<template #filters>
			<div class="flex flex-wrap items-end gap-3">
				<div class="min-w-[170px] flex-1">
					<label class="field-label">Assigned to</label>
					<SearchableDropdown
						v-model="filters.user"
						:options="filterOptions.users"
						placeholder="Anyone"
						@change="fetchReportData"
					/>
				</div>
				<div class="min-w-[170px] flex-1">
					<label class="field-label">Priority</label>
					<SearchableDropdown
						v-model="filters.priority"
						:options="filterOptions.priorities"
						placeholder="Any priority"
						@change="fetchReportData"
					/>
				</div>
				<div class="min-w-[170px] flex-1">
					<label class="field-label">Status</label>
					<SearchableDropdown
						v-model="filters.status"
						:options="filterOptions.statuses"
						placeholder="Any status"
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
import { createResource } from 'frappe-ui';
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

const emitClose = () => {
	emit('close');
};

const loading = ref(false);

const filterOptions = reactive({
	users: [],
	priorities: [],
	statuses: []
});

const filters = reactive({
	user: '',
	priority: '',
	status: '',
});

const resetFilters = () => {
	filters.user = '';
	filters.priority = '';
	filters.status = '';
	fetchReportData();
};

const columns = [
	{ label: 'Task', fieldname: 'task_id' },
	{ label: 'Assigned to', fieldname: 'assigned_to_name' },
	{ label: 'Priority', fieldname: 'priority' },
	{ label: 'Status', fieldname: 'status' },
	{ label: 'Due', fieldname: 'due_date' },
	{ label: 'Description', fieldname: 'description' },
];

const reportData = ref([]);

const metadataResource = createResource({
	url: 'arijentek_core.api.tasks.get_todo_creation_metadata',
	auto: false,
	onSuccess(data) {
		if (data) {
			if (data.users && data.users.length > 0) {
				filterOptions.users = data.users.map(u => ({ id: u.name, name: u.full_name || u.name }));
			}
			if (data.priorities) {
				filterOptions.priorities = data.priorities.map(p => ({ id: p, name: p }));
			}
			if (data.statuses) {
				filterOptions.statuses = data.statuses.map(s => ({ id: s, name: s }));
			}
		}
	}
});

const dataResource = createResource({
	url: 'arijentek_core.api.tasks.get_task_report_data',
	auto: false,
	onSuccess(data) {
		reportData.value = data || [];
		loading.value = false;
	},
	onError() {
		loading.value = false;
	}
});

function fetchReportData() {
	loading.value = true;
	dataResource.fetch({
		filters: {
			user: filters.user,
			priority: filters.priority,
			status: filters.status
		}
	});
}

function exportExcel() {
	if (!reportData.value.length) return;
	
	const csvContent = [];
	
	// Headers
	csvContent.push(columns.map(c => `"${c.label}"`).join(','));
	
	// Data
	for (const row of reportData.value) {
		const rowData = columns.map(col => {
			let val = row[col.fieldname] || '';
			// Escape quotes
			val = String(val).replace(/"/g, '""');
			return `"${val}"`;
		});
		csvContent.push(rowData.join(','));
	}
	
	const blob = new Blob([csvContent.join('\n')], { type: 'text/csv;charset=utf-8;' });
	const url = URL.createObjectURL(blob);
	const link = document.createElement('a');
	link.setAttribute('href', url);
	link.setAttribute('download', `Tasks_Report_${new Date().toISOString().split('T')[0]}.csv`);
	link.style.visibility = 'hidden';
	document.body.appendChild(link);
	link.click();
	document.body.removeChild(link);
}

function exportPDF() {
	if (!reportData.value.length) return;
	
	const params = new URLSearchParams();
	params.append('filters', JSON.stringify({
		user: filters.user,
		priority: filters.priority,
		status: filters.status
	}));
	
	const url = `/api/method/arijentek_core.api.tasks.download_task_report_pdf?${params.toString()}`;
	window.open(url, '_blank');
}

watch(() => props.show, (newVal) => {
	if (newVal) {
		metadataResource.fetch();
		fetchReportData();
	}
});
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
