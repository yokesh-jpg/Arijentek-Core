<template>
	<ReportDialog
		:show="show"
		title="Monthly attendance"
		subtitle="Attendance per employee across the month, by status."
		:loading="loading"
		:empty="!reportData.length"
		empty-icon="calendar_month"
		empty-title="No attendance records."
		empty-text="Nothing was recorded for this month under these filters."
		:count="reportData.length"
		unit="employee"
		unit-plural="employees"
		wide
		extra-wide
		@close="emitClose"
		@export-excel="exportExcel"
		@export-pdf="exportPDF"
	>
		<template #filters>
			<div class="flex flex-wrap items-end gap-3">
				<div class="min-w-[200px] flex-1">
					<label class="field-label">Date range (max 31 days)</label>
					<DateRangePicker
						v-model:fromDate="filters.fromDate"
						v-model:toDate="filters.toDate"
						v-model:preset="filters.preset"
						@change="handleDateRangeChange"
					/>
				</div>
				<div class="min-w-[170px] flex-1">
					<label class="field-label">Department</label>
					<SearchableDropdown
						v-model="filters.department"
						:options="filterOptions.departments"
						placeholder="All departments"
						@change="fetchReportData"
					/>
				</div>
				<div class="min-w-[170px] flex-1">
					<label class="field-label">Branch</label>
					<SearchableDropdown
						v-model="filters.branch"
						:options="filterOptions.branches"
						placeholder="All branches"
						@change="fetchReportData"
					/>
				</div>
				<div class="min-w-[170px] flex-1">
					<label class="field-label">Employee</label>
					<SearchableDropdown
						v-model="filters.employee"
						:options="filterOptions.employees"
						placeholder="All employees"
						@change="fetchReportData"
					/>
				</div>
				<div class="basis-full flex flex-wrap items-center gap-x-5 gap-y-2 pt-0.5">
					<label class="flex items-center gap-2 text-[13px] text-[#17181B] dark:text-white cursor-pointer select-none shrink-0">
						<input
							type="checkbox"
							v-model="filters.lateEntry"
							@change="fetchReportData"
							class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40"
						/>
						Has late entry
					</label>
					<label class="flex items-center gap-2 text-[13px] text-[#17181B] dark:text-white cursor-pointer select-none shrink-0">
						<input
							type="checkbox"
							v-model="filters.earlyExit"
							@change="fetchReportData"
							class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40"
						/>
						Has early exit
					</label>
				</div>
			</div>
		</template>

		<template #legend>
			<div class="flex items-center gap-1.5 mr-2 shrink-0">
				<span class="material-symbols-outlined !text-[16px] text-[#656A72] dark:text-white/60">info</span>
				<span class="text-[11px] font-bold uppercase tracking-wider text-[#656A72] dark:text-white/60">Legend:</span>
			</div>
			<div class="flex flex-wrap items-center gap-1.5 sm:gap-2">
				<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800">
					<span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> P = Present
				</span>
				<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium text-rose-700 dark:text-rose-300 bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800">
					<span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span> A = Absent
				</span>
				<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/60 border border-amber-200 dark:border-amber-800">
					<span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span> HD = Half Day
				</span>
				<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-950/60 border border-blue-200 dark:border-blue-800">
					<span class="w-1.5 h-1.5 rounded-full bg-blue-500"></span> L = On Leave
				</span>
				<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium text-purple-700 dark:text-purple-300 bg-purple-50 dark:bg-purple-950/60 border border-purple-200 dark:border-purple-800">
					<span class="w-1.5 h-1.5 rounded-full bg-purple-500"></span> H = Holiday
				</span>
				<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800/80 border border-gray-200 dark:border-gray-700">
					<span class="w-1.5 h-1.5 rounded-full bg-gray-400"></span> WO = Weekly Off
				</span>
			</div>
		</template>

		<!-- Monthly Attendance Matrix Crosstab Table -->
		<div class="w-full select-text">
			<table class="w-full border-separate border-spacing-0 text-left text-xs min-w-max">
				<thead>
					<tr>
						<!-- Pinned Column 1: ID (Locked to exactly 130px) -->
						<th class="sticky top-0 left-0 z-30 bg-[#F8F9FA] dark:bg-surface-2 px-3 py-2 text-left text-[11px] font-bold uppercase tracking-wider w-[130px] min-w-[130px] max-w-[130px] border-b border-black/[0.08] dark:border-white/10 select-none">
							ID
						</th>
						<!-- Pinned Column 2: Employee Name (Starts exactly at 130px) -->
						<th class="sticky top-0 left-[130px] z-30 bg-[#F8F9FA] dark:bg-surface-2 px-3 py-2 text-left text-[11px] font-bold uppercase tracking-wider w-[160px] min-w-[160px] max-w-[160px] border-b border-r border-black/[0.08] dark:border-white/10 select-none shadow-[4px_0_8px_-3px_rgba(0,0,0,0.08)] dark:shadow-[4px_0_8px_-3px_rgba(0,0,0,0.3)]">
							Employee
						</th>
						<!-- Department -->
						<th class="sticky top-0 z-20 bg-[#F8F9FA] dark:bg-surface-2 px-2.5 py-2 text-left text-[11px] font-bold uppercase tracking-wider w-[105px] min-w-[105px] max-w-[105px] border-b border-black/[0.08] dark:border-white/10 select-none">
							Department
						</th>
						<!-- Shift -->
						<th class="sticky top-0 z-20 bg-[#F8F9FA] dark:bg-surface-2 px-2 py-2 text-left text-[11px] font-bold uppercase tracking-wider w-[80px] min-w-[80px] max-w-[80px] border-b border-black/[0.08] dark:border-white/10 select-none">
							Shift
						</th>

						<!-- Day Columns (1..31) with 100% Solid Backgrounds (No Bleed-Through on Vertical Scroll) -->
						<th
							v-for="day in dayColumns"
							:key="day.fieldname"
							class="sticky top-0 z-20 px-0.5 py-1.5 text-center w-[32px] min-w-[32px] max-w-[32px] border-b border-l border-black/[0.06] dark:border-white/10 select-none"
							:class="isWeekend(day.dayAbbr) ? 'bg-[#FEF6E9] dark:bg-[#2A2318]' : 'bg-[#F8F9FA] dark:bg-surface-2'"
						>
							<div class="font-bold text-[11px] leading-tight text-[#17181B] dark:text-white tabular-nums">{{ day.dayNum }}</div>
							<div
								class="text-[9px] font-semibold uppercase leading-tight"
								:class="isWeekend(day.dayAbbr) ? 'text-amber-700 dark:text-amber-400' : 'text-[#656A72] dark:text-white/50'"
							>
								{{ day.dayAbbr }}
							</div>
						</th>

						<!-- Summary Columns (P, A, HD, L, Late, Early) with 100% Solid Backgrounds -->
						<th class="sticky top-0 z-20 px-1 py-1.5 text-center w-[34px] min-w-[34px] max-w-[34px] text-[10px] font-bold text-emerald-800 dark:text-emerald-300 bg-[#ECFDF5] dark:bg-[#0D281E] border-b border-l border-emerald-500/25 select-none" title="Total Present">P</th>
						<th class="sticky top-0 z-20 px-1 py-1.5 text-center w-[34px] min-w-[34px] max-w-[34px] text-[10px] font-bold text-rose-800 dark:text-rose-300 bg-[#FFF1F2] dark:bg-[#2D1217] border-b border-l border-rose-500/25 select-none" title="Total Absent">A</th>
						<th class="sticky top-0 z-20 px-1 py-1.5 text-center w-[34px] min-w-[34px] max-w-[34px] text-[10px] font-bold text-amber-800 dark:text-amber-300 bg-[#FFFBEB] dark:bg-[#2B1D0E] border-b border-l border-amber-500/25 select-none" title="Total Half Day">HD</th>
						<th class="sticky top-0 z-20 px-1 py-1.5 text-center w-[34px] min-w-[34px] max-w-[34px] text-[10px] font-bold text-blue-800 dark:text-blue-300 bg-[#EFF6FF] dark:bg-[#0E1D33] border-b border-l border-blue-500/25 select-none" title="Total Leave">L</th>
						<th class="sticky top-0 z-20 px-1 py-1.5 text-center w-[36px] min-w-[36px] max-w-[36px] text-[10px] font-bold text-orange-800 dark:text-orange-300 bg-[#FFF7ED] dark:bg-[#2E190E] border-b border-l border-orange-500/25 select-none" title="Total Late Entries">Late</th>
						<th class="sticky top-0 z-20 px-1 py-1.5 text-center w-[36px] min-w-[36px] max-w-[36px] text-[10px] font-bold text-purple-800 dark:text-purple-300 bg-[#FAF5FF] dark:bg-[#221233] border-b border-l border-purple-500/25 select-none" title="Total Early Exits">Early</th>
					</tr>
				</thead>
				<tbody class="text-[#17181B] dark:text-white">
					<tr
						v-for="(row, idx) in reportData"
						:key="row.employee || idx"
						class="group hover:bg-black/[0.02] dark:hover:bg-white/[0.03] transition-colors"
					>
						<!-- Pinned Column 1: ID (Locked to 130px) -->
						<td class="sticky left-0 z-10 bg-white dark:bg-surface-1 group-hover:bg-[#F9FAFB] dark:group-hover:bg-surface-2 px-3 py-1.5 font-mono text-[11px] font-medium text-[#656A72] dark:text-white/60 whitespace-nowrap w-[130px] min-w-[130px] max-w-[130px] border-b border-black/[0.05] dark:border-white/[0.06] truncate" :title="row.employee">
							{{ row.employee }}
						</td>
						<!-- Pinned Column 2: Name (Locked to 160px at left: 130px - No Overlap) -->
						<td class="sticky left-[130px] z-10 bg-white dark:bg-surface-1 group-hover:bg-[#F9FAFB] dark:group-hover:bg-surface-2 px-3 py-1.5 whitespace-nowrap w-[160px] min-w-[160px] max-w-[160px] border-b border-r border-black/[0.08] dark:border-white/10 shadow-[4px_0_8px_-3px_rgba(0,0,0,0.08)] dark:shadow-[4px_0_8px_-3px_rgba(0,0,0,0.3)]">
							<div class="font-semibold text-[12px] text-[#17181B] dark:text-white truncate" :title="row.employee_name">
								{{ row.employee_name }}
							</div>
							<div v-if="row.branch && row.branch !== '-'" class="text-[10px] text-[#656A72] dark:text-white/50 truncate">
								{{ row.branch }}
							</div>
						</td>
						<!-- Department -->
						<td class="px-2.5 py-1.5 text-[11px] text-[#656A72] dark:text-white/70 whitespace-nowrap w-[105px] min-w-[105px] max-w-[105px] truncate border-b border-black/[0.05] dark:border-white/[0.06]" :title="row.department">
							{{ row.department || '—' }}
						</td>
						<!-- Shift -->
						<td class="px-2 py-1.5 text-[11px] text-[#656A72] dark:text-white/70 whitespace-nowrap w-[80px] min-w-[80px] max-w-[80px] truncate border-b border-black/[0.05] dark:border-white/[0.06]" :title="row.shift">
							{{ row.shift || '—' }}
						</td>

						<!-- Day Columns (1..31) -->
						<td
							v-for="day in dayColumns"
							:key="day.fieldname"
							class="px-0.5 py-1 text-center w-[32px] min-w-[32px] max-w-[32px] border-b border-l border-black/[0.04] dark:border-white/[0.06]"
							:class="isWeekend(day.dayAbbr) ? 'bg-amber-500/[0.03] dark:bg-amber-400/[0.03]' : ''"
						>
							<span
								class="inline-flex items-center justify-center w-[24px] h-[22px] rounded text-[10px] font-bold leading-none tracking-tight transition-transform"
								:class="getDayBadgeClass(row[day.fieldname])"
								:title="formatDayTooltip(day, row[day.fieldname])"
							>
								{{ formatDayValue(row[day.fieldname]) }}
							</span>
						</td>

						<!-- Summary Columns -->
						<td class="px-1 py-1.5 text-center text-[11px] font-semibold text-emerald-700 dark:text-emerald-400 bg-emerald-500/[0.04] border-b border-l border-black/[0.04] dark:border-white/[0.06] tabular-nums w-[34px] min-w-[34px] max-w-[34px]">
							{{ row.total_present ?? 0 }}
						</td>
						<td class="px-1 py-1.5 text-center text-[11px] font-semibold text-rose-700 dark:text-rose-400 bg-rose-500/[0.04] border-b border-l border-black/[0.04] dark:border-white/[0.06] tabular-nums w-[34px] min-w-[34px] max-w-[34px]">
							{{ row.total_absent ?? 0 }}
						</td>
						<td class="px-1 py-1.5 text-center text-[11px] font-semibold text-amber-700 dark:text-amber-400 bg-amber-500/[0.04] border-b border-l border-black/[0.04] dark:border-white/[0.06] tabular-nums w-[34px] min-w-[34px] max-w-[34px]">
							{{ row.total_half_day ?? 0 }}
						</td>
						<td class="px-1 py-1.5 text-center text-[11px] font-semibold text-blue-700 dark:text-blue-400 bg-blue-500/[0.04] border-b border-l border-black/[0.04] dark:border-white/[0.06] tabular-nums w-[34px] min-w-[34px] max-w-[34px]">
							{{ row.total_leave ?? 0 }}
						</td>
						<td class="px-1 py-1.5 text-center text-[11px] font-semibold text-orange-700 dark:text-orange-400 bg-orange-500/[0.04] border-b border-l border-black/[0.04] dark:border-white/[0.06] tabular-nums w-[36px] min-w-[36px] max-w-[36px]">
							{{ row.total_late_entries ?? 0 }}
						</td>
						<td class="px-1 py-1.5 text-center text-[11px] font-semibold text-purple-700 dark:text-purple-400 bg-purple-500/[0.04] border-b border-l border-black/[0.04] dark:border-white/[0.06] tabular-nums w-[36px] min-w-[36px] max-w-[36px]">
							{{ row.total_early_exits ?? 0 }}
						</td>
					</tr>
				</tbody>
			</table>
		</div>
	</ReportDialog>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue';
import SearchableDropdown from '../../../../components/SearchableDropdown.vue';
import DateRangePicker from '../../../../components/DateRangePicker.vue';
import ReportDialog from '@/components/ReportDialog.vue';

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
	departments: [],
	branches: [],
	employees: [],
});

const getDefaultDates = () => {
	const now = new Date();
	const yyyy = now.getFullYear();
	const mm = String(now.getMonth() + 1).padStart(2, '0');
	const firstDay = `${yyyy}-${mm}-01`;
	const lastDayObj = new Date(yyyy, now.getMonth() + 1, 0);
	const lastDay = `${yyyy}-${mm}-${String(lastDayObj.getDate()).padStart(2, '0')}`;
	return { fromDate: firstDay, toDate: lastDay };
};

const defaultDates = getDefaultDates();

const filters = reactive({
	fromDate: defaultDates.fromDate,
	toDate: defaultDates.toDate,
	preset: 'This Month',
	department: '',
	branch: '',
	employee: '',
	lateEntry: false,
	earlyExit: false,
});

const columns = ref([]);
const reportData = ref([]);

const dayColumns = computed(() => {
	return columns.value
		.filter((c) => c.fieldname && c.fieldname.startsWith('day_'))
		.map((c) => {
			const rawLabel = String(c.label || '').trim();
			const parts = rawLabel.split(/\s+/);
			return {
				fieldname: c.fieldname,
				label: rawLabel,
				dayNum: parts[0] || c.fieldname.replace('day_', ''),
				dayAbbr: parts[1] || '',
			};
		});
});

const isWeekend = (abbr) => {
	if (!abbr) return false;
	const a = String(abbr).toLowerCase();
	return a.startsWith('sat') || a.startsWith('sun');
};

const formatDayValue = (val) => {
	if (!val || val === '-') return '—';
	return String(val).toUpperCase();
};

const formatDayTooltip = (day, status) => {
	const s = String(status || '').toUpperCase().trim();
	const names = {
		P: 'Present',
		A: 'Absent',
		HD: 'Half Day',
		L: 'On Leave',
		H: 'Holiday',
		WO: 'Weekly Off',
		WFH: 'Work From Home',
	};
	return `Day ${day.dayNum} (${day.dayAbbr}): ${names[s] || s || 'No Record'}`;
};

const getDayBadgeClass = (status) => {
	const s = String(status || '').toUpperCase().trim();
	switch (s) {
		case 'P':
			return 'text-emerald-700 dark:text-emerald-300 bg-emerald-100/90 dark:bg-emerald-950/80 border border-emerald-300/80 dark:border-emerald-700/80 shadow-2xs';
		case 'A':
			return 'text-rose-700 dark:text-rose-300 bg-rose-100/90 dark:bg-rose-950/80 border border-rose-300/80 dark:border-rose-700/80 shadow-2xs';
		case 'HD':
		case 'HD/P':
		case 'HD/A':
			return 'text-amber-700 dark:text-amber-300 bg-amber-100/90 dark:bg-amber-950/80 border border-amber-300/80 dark:border-amber-700/80 shadow-2xs';
		case 'L':
			return 'text-blue-700 dark:text-blue-300 bg-blue-100/90 dark:bg-blue-950/80 border border-blue-300/80 dark:border-blue-700/80 shadow-2xs';
		case 'H':
			return 'text-purple-700 dark:text-purple-300 bg-purple-100/90 dark:bg-purple-950/80 border border-purple-300/80 dark:border-purple-700/80 shadow-2xs';
		case 'WO':
			return 'text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800/80 border border-gray-200 dark:border-gray-700';
		case 'WFH':
			return 'text-teal-700 dark:text-teal-300 bg-teal-100/90 dark:bg-teal-950/80 border border-teal-300/80 dark:border-teal-700/80 shadow-2xs';
		default:
			return 'text-gray-400 dark:text-white/20 font-normal';
	}
};

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
		const res = await fetch('/api/method/arijentek_core.api.reports.get_attendance_report_filter_options', {
			method: 'GET',
			headers: { 'Content-Type': 'application/json' },
		});
		if (res.ok) {
			const data = await res.json();
			const msg = data.message || {};
			filterOptions.departments = msg.departments || [];
			filterOptions.branches = msg.branches || [];
			filterOptions.employees = msg.employees || [];
		}
	} catch (e) {
		console.warn('Failed to load filter options', e);
	}
}

const handleDateRangeChange = (range) => {
	if (range) {
		if (range.fromDate) filters.fromDate = range.fromDate;
		if (range.toDate) filters.toDate = range.toDate;
		if (range.preset) filters.preset = range.preset;
	}
	if (filters.fromDate && filters.toDate) {
		const start = new Date(filters.fromDate);
		const end = new Date(filters.toDate);
		const diffTime = end - start;
		const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
		if (diffDays > 31) {
			const newEnd = new Date(start);
			newEnd.setDate(newEnd.getDate() + 30);
			const yyyy = newEnd.getFullYear();
			const mm = String(newEnd.getMonth() + 1).padStart(2, '0');
			const dd = String(newEnd.getDate()).padStart(2, '0');
			filters.toDate = `${yyyy}-${mm}-${dd}`;
		}
	}
	fetchReportData();
};

async function fetchReportData() {
	loading.value = true;
	try {
		const params = new URLSearchParams();
		if (filters.fromDate) params.set('from_date', filters.fromDate);
		if (filters.toDate) params.set('to_date', filters.toDate);
		if (filters.department) params.set('department', filters.department);
		if (filters.branch) params.set('branch', filters.branch);
		if (filters.employee) params.set('employee', filters.employee);
		if (filters.lateEntry) params.set('late_entry', '1');
		if (filters.earlyExit) params.set('early_exit', '1');

		const res = await fetch(`/api/method/arijentek_core.api.attendance.report_mark_attendance_list?${params.toString()}`, {
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
}

const resetFilters = () => {
	const d = getDefaultDates();
	filters.fromDate = d.fromDate;
	filters.toDate = d.toDate;
	filters.preset = 'This Month';
	filters.department = '';
	filters.branch = '';
	filters.employee = '';
	filters.lateEntry = false;
	filters.earlyExit = false;
	fetchReportData();
};

const exportExcel = () => {
	const params = new URLSearchParams();
	if (filters.fromDate) params.set('from_date', filters.fromDate);
	if (filters.toDate) params.set('to_date', filters.toDate);
	if (filters.department) params.set('department', filters.department);
	if (filters.branch) params.set('branch', filters.branch);
	if (filters.employee) params.set('employee', filters.employee);
	if (filters.lateEntry) params.set('late_entry', '1');
	if (filters.earlyExit) params.set('early_exit', '1');
	params.set('export', '1');

	const url = `/api/method/arijentek_core.api.attendance.report_mark_attendance_list?${params.toString()}`;
	window.open(url, '_blank');
};

const exportPDF = () => {
	const params = new URLSearchParams();
	if (filters.fromDate) params.set('from_date', filters.fromDate);
	if (filters.toDate) params.set('to_date', filters.toDate);
	if (filters.department) params.set('department', filters.department);
	if (filters.branch) params.set('branch', filters.branch);
	if (filters.employee) params.set('employee', filters.employee);
	if (filters.lateEntry) params.set('late_entry', '1');
	if (filters.earlyExit) params.set('early_exit', '1');
	params.set('pdf', '1');

	const url = `/api/method/arijentek_core.api.attendance.report_mark_attendance_list?${params.toString()}`;
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
