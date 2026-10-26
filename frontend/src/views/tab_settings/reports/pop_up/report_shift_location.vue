<template>
	<ReportDialog
		:show="show"
		title="Shift locations"
		subtitle="The places a shift can be clocked from, with their geofence radius."
		:loading="loading"
		:empty="!reportData.length"
		empty-icon="location_on"
		empty-title="No shift locations configured."
		empty-text="A location sets where staff are allowed to clock in from."
		:count="reportData.length"
		unit="location"
		unit-plural="locations"
		@close="emitClose"
		@export-excel="exportExcel"
		@export-pdf="exportPDF"
	>
		<div class="overflow-x-auto table-scroll">
			<ReportTable :columns="columns" :rows="reportData" />
		</div>
	</ReportDialog>
</template>

<script setup>
import { ref, watch } from 'vue';
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
const columns = ref([]);
const reportData = ref([]);

watch(
	() => props.show,
	async (newVal) => {
		if (newVal) {
			await fetchReportData();
		}
	},
	{ immediate: true }
);

async function fetchReportData() {
	loading.value = true;
	try {
		const res = await fetch(`/api/method/arijentek_core.api.roster.report_shift_location_list`, {
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
		console.error('Error fetching report data', e);
		reportData.value = [];
	} finally {
		loading.value = false;
	}
};

const exportExcel = () => {
	const url = `/api/method/arijentek_core.api.roster.report_shift_location_list?export=1`;
	window.open(url, '_blank');
};

const exportPDF = () => {
	const url = `/api/method/arijentek_core.api.roster.report_shift_location_list?pdf=1`;
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
