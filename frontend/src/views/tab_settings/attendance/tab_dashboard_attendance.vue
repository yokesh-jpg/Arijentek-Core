<template>
	<div class="space-y-5">
		<!-- ===== Header + clock ===== -->
		<div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
			<div>
				<h2 class="section-title">This month</h2>
				<p class="section-subtitle">{{ monthLabel }} · {{ statusSummary.Present }} of {{ workingDaysInMonth }} days present</p>
			</div>

			<div class="flex items-center gap-2 flex-wrap">
				<button
					v-if="canCreateAttendance"
					@click="showActiveEmployeesDialog = true"
					class="btn-secondary"
				>
					<span class="material-symbols-outlined !text-[18px]">pending_actions</span>
					Active shifts
				</button>

				<template v-if="isCheckedIn">
					<button
						@click="handleBreak"
						class="btn-secondary"
					>
						<span class="material-symbols-outlined !text-[18px]">coffee</span>
						{{ isOnBreak ? 'Resume shift' : 'Break' }}
					</button>
					<button
						@click="handleClockOut"
						class="btn-primary"
					>
						<span class="material-symbols-outlined !text-[18px]">logout</span>
						Clock out
					</button>
				</template>
				<template v-else-if="isShiftComplete && !isOnBreak">
					<div class="h-9 lg:h-8 px-3.5 inline-flex items-center gap-1.5 rounded-[12px] bg-green-500/[0.12] text-green-700 dark:text-green-300 text-xs font-medium">
						<span class="material-symbols-outlined !text-[18px]">check_circle</span>
						Shift complete
					</div>
				</template>
				<template v-else>
					<button
						@click="handleClockIn"
						class="btn-primary"
					>
						<span class="material-symbols-outlined !text-[18px]">login</span>
						Clock in
					</button>
				</template>
			</div>
		</div>

		<!-- ===== Month summary =====
		     One strip instead of four cards. These are counts you read together
		     ("22 present, 1 absent"), not four separate headline figures. -->
		<div class="glass-card !p-0 overflow-hidden">
			<div class="grid grid-cols-3 divide-x divide-black/[0.06] dark:divide-white/[0.07]">
				<div v-for="m in summaryTiles" :key="m.label" class="p-4">
					<div class="flex items-center gap-2">
						<span class="w-2 h-2 rounded-full shrink-0" :class="m.dot"></span>
						<p class="text-xs text-[#5C6169] dark:text-white/60 truncate">{{ m.label }}</p>
					</div>
					<p class="text-2xl font-semibold tabular-nums text-[#17181B] dark:text-white mt-1 leading-none">{{ m.value }}</p>
				</div>
			</div>
		</div>

		<!-- ===== Calendar + day panel ===== -->
		<div class="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_300px] gap-4 lg:gap-5 items-start">
			<section class="glass-card !p-3 sm:!p-5">
				<div class="flex flex-wrap items-center justify-between gap-2 mb-4">
					<div class="flex items-center gap-1 sm:gap-2">
						<div class="relative">
							<SelectField v-model="selectedMonth" :options="monthSelectOptions" :block="false" trigger-class="cal-select" aria-label="Month" />
						</div>
						<div class="relative">
							<SelectField v-model="selectedYear" :options="yearSelectOptions" :block="false" trigger-class="cal-select" aria-label="Year" />
						</div>
					</div>
					<div class="flex items-center gap-1 w-full sm:w-auto">
						<button @click="goToThisMonth" class="btn-ghost !text-accent dark:!text-accent-light hover:!bg-accent/[0.08] mr-auto sm:mr-0">Today</button>
						<button @click="stepMonth(-1)" class="btn-icon-ghost" aria-label="Previous month">
							<span class="material-symbols-outlined !text-[18px]">chevron_left</span>
						</button>
						<button @click="stepMonth(1)" class="btn-icon-ghost" aria-label="Next month">
							<span class="material-symbols-outlined !text-[18px]">chevron_right</span>
						</button>
					</div>
				</div>

				<div class="grid grid-cols-7 gap-1 sm:gap-2 mb-1.5">
					<div v-for="(d, i) in weekdayLabels" :key="d" class="cal-weekday">
						<span class="hidden lg:inline">{{ LONG_WEEKDAYS[i] }}</span>
						<span class="lg:hidden">{{ d }}</span>
					</div>
				</div>

				<div class="grid grid-cols-7 gap-1 sm:gap-2">
					<button
						v-for="day in calendarDays"
						:key="day.dateStr"
						@click="selectedDate = day.dateStr"
						:disabled="!day.inCurrentMonth"
						class="cal-cell overflow-hidden min-w-0 w-full"
						:class="[ !day.inCurrentMonth ? 'cal-cell-muted' : 'cal-cell-hover', day.isToday ? 'cal-cell-today' : '', day.dateStr === selectedDate && !day.isToday ? 'cal-cell-selected' : '', ]"
						:aria-label="dayAria(day)"
						:aria-current="day.isToday ? 'date' : undefined"
					>
						<span class="cal-date shrink-0" :class="[!day.inCurrentMonth ? 'cal-date-muted' : '', day.isToday ? '!text-white' : '']">
							{{ day.day }}
						</span>

						<!-- The status as a word, not a bare dot — the old cell needed
						     the legend to be readable at all. -->
						<span v-if="day.entries.length" class="cal-entries min-w-0 w-full overflow-hidden">
							<span v-for="(e, i) in day.entries" :key="i" class="cal-entry min-w-0 w-full overflow-hidden" :title="e.label">
								<span class="cal-tick shrink-0" :class="day.isToday ? 'bg-white/70' : e.tick"></span>
								<span class="cal-entry-label flex-1 min-w-0 truncate" :class="day.isToday ? '!text-white/85' : ''">{{ e.label }}</span>
							</span>
						</span>
					</button>
				</div>


				<!-- The labels are hidden below sm, so the colour key earns its place
				     there and only there. -->
				<div class="sm:hidden grid grid-cols-3 gap-x-2 gap-y-2 mt-4 pt-4 border-t border-black/[0.06] dark:border-white/[0.07]">
					<span v-for="l in legend" :key="l.label" class="inline-flex items-center gap-1.5 min-w-0 text-xs text-[#5C6169] dark:text-white/65">
						<span class="w-1.5 h-1.5 rounded-full shrink-0" :class="l.dot"></span><span class="truncate">{{ l.label }}</span>
					</span>
				</div>
			</section>

			<!-- ===== Selected day ===== -->
			<section class="glass-card lg:sticky lg:top-0">
				<div class="flex items-baseline justify-between gap-2 mb-4">
					<div>
						<h2 class="text-base font-semibold text-[#17181B] dark:text-white">{{ selectedDayHeading }}</h2>
						<p class="text-xs text-[#5C6169] dark:text-white/60 mt-0.5">{{ selectedDaySub }}</p>
					</div>
					<span v-if="selectedDay?.statusTag" class="premium-tag shrink-0" :class="selectedDay.statusTag.tone">
						{{ selectedDay.statusTag.label }}
					</span>
				</div>

				<div v-if="selectedDay?.entries?.length" class="space-y-2.5">
					<div v-for="(e, i) in selectedDay.entries" :key="i" class="cal-card">
						<span class="cal-card-bar" :class="e.bar"></span>
						<div class="p-3 flex items-start justify-between gap-2">
							<div class="min-w-0 flex-1">
								<p class="text-[13px] font-medium text-[#17181B] dark:text-white leading-snug break-words">{{ e.title }}</p>
								<p v-if="e.detail" class="text-xs text-[#5C6169] dark:text-white/65 mt-0.5 leading-snug break-words">{{ e.detail }}</p>
							</div>
							<span v-if="e.meta" class="shrink-0 text-xs tabular-nums text-[#5C6169] dark:text-white/60">{{ e.meta }}</span>
						</div>
					</div>
				</div>

				<p v-else class="py-10 text-center text-[13px] text-[#5C6169] dark:text-white/55">
					{{ selectedDayEmpty }}
				</p>
			</section>
		</div>

		<ActiveEmployeesList v-model="showActiveEmployeesDialog" @save-success="onSaveSuccess" />
	</div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { createResource } from "frappe-ui";
import { useEmployeeStore } from "@/stores/employee";
import { useAttendanceStore } from "@/stores/attendance";
import ActiveEmployeesList from "../../forms/attendance/active_employees_list.vue";
import SelectField from '../../../components/SelectField.vue'


const employeeStore = useEmployeeStore();
const attendanceStore = useAttendanceStore();

const showActiveEmployeesDialog = ref(false);

const isCheckedIn = computed(() => attendanceStore.isCheckedIn);
const isOnBreak = computed(() => attendanceStore.isOnBreak);
const isShiftComplete = computed(() => attendanceStore.isDayCompleted);
const workingHoursTarget = computed(() => attendanceStore.workingHoursTarget);
const roster = computed(() => attendanceStore.roster);
const canCreateAttendance = computed(() => {
	return attendanceStore.createAttendancePermissionResource?.data === true || attendanceStore.createAttendancePermissionResource?.data === 1;
});

function onSaveSuccess() {
	fetchCurrentUserHistory();
	fetchMonthlyStats();
	fetchMonthlyRoster();
}

const _today = new Date();
const selectedMonth = ref(_today.getMonth() + 1);
const selectedYear = ref(_today.getFullYear());
const workingDaysInMonth = ref(0);

const todayStr = computed(() => {
	const t = new Date();
	return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
});

const currentUserHistoryResource = createResource({
	url: "arijentek_core.api.attendance.get_attendance_history",
	auto: false,
});

async function fetchCurrentUserHistory() {
	const empId = employeeStore.employee?.name;
	if (empId) {
		await currentUserHistoryResource.fetch({
			employee_id: empId,
			month: selectedMonth.value,
			year: selectedYear.value,
			override_employee_id: empId,
		});
	}
}

async function fetchMonthlyStats() {
	try {
		const m = selectedMonth.value;
		const y = selectedYear.value;
		const res = await fetch(`/api/method/arijentek_core.api.attendance.get_monthly_attendance_stats?month=${m}&year=${y}`);
		const data = await res.json();
		if (data.message) workingDaysInMonth.value = data.message.working_days || 0;
	} catch (e) {
		console.error("Stats fetch failed", e);
	}
}

async function fetchMonthlyRoster() {
	const empId = employeeStore.employee?.name;
	if (empId) {
		await attendanceStore.fetchMonthlyRoster(empId, selectedYear.value, selectedMonth.value);
	}
}

const statusSummary = computed(() => {
	const summary = currentUserHistoryResource.data?.summary || {};
	return {
		Present: summary.Present || 0,
		Absent: summary.Absent || 0,
		"Half Day": summary["Half Day"] || 0,
		"On Leave": summary["On Leave"] || 0,
	};
});

/* Dates the roster puts a shift on. Without this a future rostered day was
   indistinguishable from a day off. */
const scheduledDates = computed(() => {
	const set = new Set();
	for (const d of attendanceStore.monthlyRoster?.calendar || []) {
		const list = d.shifts || (d.shift ? [d.shift] : []);
		if (list.filter(Boolean).length) set.add(d.date);
	}
	return set;
});

const dayInfoMap = computed(() => {
	const map = {};
	const cal = attendanceStore.monthlyRoster?.calendar || [];
	cal.forEach((d) => {
		if (d.status === "holiday" && d.shift?.shift_name) {
			map[d.date] = { type: "holiday", label: d.shift.shift_name };
		} else if (d.status === "on_leave" && d.shift?.shift_name) {
			map[d.date] = { type: "on_leave", label: d.shift.shift_name };
		}
	});

	const records = currentUserHistoryResource.data?.records || [];
	records.forEach((r) => {
		if (r.date) {
			if (!map[r.date]) map[r.date] = { type: "working", label: "" };
			map[r.date].attendanceStatus = r.status;
		}
	});
	return map;
});

const calendarDays = computed(() => {
	const days = [];
	const firstOfMonth = new Date(selectedYear.value, selectedMonth.value - 1, 1);
	const lastOfMonth = new Date(selectedYear.value, selectedMonth.value, 0);

	const sundayOffset = firstOfMonth.getDay();
	const gridStart = new Date(firstOfMonth);
	gridStart.setDate(gridStart.getDate() - sundayOffset);

	const today = todayStr.value;
	let current = new Date(gridStart);
	const gridEnd = new Date(gridStart);
	gridEnd.setDate(gridEnd.getDate() + 41);

	while (current <= gridEnd) {
		const dateStr = `${current.getFullYear()}-${String(current.getMonth() + 1).padStart(2, "0")}-${String(current.getDate()).padStart(2, "0")}`;
		const info = dayInfoMap.value[dateStr];
		days.push({
			dateStr,
			day: current.getDate(),
			inCurrentMonth: current.getMonth() === selectedMonth.value - 1,
			isToday: dateStr === today,
			isHoliday: info?.type === "holiday",
			isScheduled: !!info || scheduledDates.value.has(dateStr),
			isOnLeave: info?.type === "on_leave",
			holidayName: info?.label || "",
			attendanceStatus: info?.attendanceStatus || "",
		});
		days[days.length - 1].entries = dayMarkers(days[days.length - 1]);
		current.setDate(current.getDate() + 1);
	}

	while (days.length >= 7 && !days[days.length - 7].inCurrentMonth) {
		days.splice(-7);
	}

	return days;
});

const weekdayLabels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const LONG_WEEKDAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const yearOptions = (() => {
	const y = new Date().getFullYear();
	return [y - 2, y - 1, y, y + 1, y + 2];
})();

const monthSelectOptions = MONTH_NAMES.map((m, i) => ({ label: m, value: i + 1 }))
const yearSelectOptions = yearOptions.map((y) => ({ label: String(y), value: y }))

const monthLabel = computed(() =>
	new Date(selectedYear.value, selectedMonth.value - 1, 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
);

function stepMonth(delta) {
	const d = new Date(selectedYear.value, selectedMonth.value - 1 + delta, 1);
	selectedYear.value = d.getFullYear();
	selectedMonth.value = d.getMonth() + 1;
}

function goToThisMonth() {
	const n = new Date();
	selectedYear.value = n.getFullYear();
	selectedMonth.value = n.getMonth() + 1;
	selectedDate.value = todayStr.value;
}

const selectedDate = ref(todayStr.value);

/* Selecting a month you are not looking at should not leave the panel showing
   a day from the old one. */
watch([selectedMonth, selectedYear], () => {
	const first = `${selectedYear.value}-${String(selectedMonth.value).padStart(2, '0')}-01`;
	if (!selectedDate.value.startsWith(first.slice(0, 7))) {
		selectedDate.value = todayStr.value.startsWith(first.slice(0, 7)) ? todayStr.value : first;
	}
});

const summaryTiles = computed(() => [
	{ label: 'Present', value: statusSummary.value.Present, dot: 'bg-green-500' },
	{ label: 'Absent', value: statusSummary.value.Absent, dot: 'bg-red-500' },
	{ label: 'Half days', value: statusSummary.value['Half Day'], dot: 'bg-amber-500' },
]);

const legend = [
	{ label: 'Present', dot: 'bg-green-500' },
	{ label: 'Absent', dot: 'bg-red-500' },
	{ label: 'Half day', dot: 'bg-amber-500' },
	{ label: 'Leave', dot: 'bg-violet-400' },
	{ label: 'Holiday', dot: 'bg-sky-400' },
];

/* One place that decides what a date means, so the cell, the legend and the
   day panel can never disagree. */
/* One labelled entry per thing true about the day. The old version returned
   bare colours, which meant the cell could not say what it meant. */
function dayMarkers(day) {
	const out = [];
	const S = {
		Present: { label: 'Present', tick: 'bg-green-500' },
		Absent: { label: 'Absent', tick: 'bg-red-500' },
		'Half Day': { label: 'Half day', tick: 'bg-amber-500' },
		'On Leave': { label: 'On leave', tick: 'bg-violet-400' },
	};
	if (S[day.attendanceStatus]) out.push(S[day.attendanceStatus]);
	if (day.isHoliday) out.push({ label: day.holidayName || 'Holiday', tick: 'bg-sky-400' });
	else if (day.isOnLeave && !out.length) out.push({ label: day.holidayName || 'Leave', tick: 'bg-violet-400' });
	return out;
}

function dayAria(day) {
	const d = new Date(day.dateStr + 'T00:00:00').toLocaleDateString('en-US', { weekday: 'long', day: 'numeric', month: 'long' });
	return day.attendanceStatus ? `${d} — ${day.attendanceStatus}` : d;
}

const recordsByDate = computed(() => {
	const map = {};
	for (const r of currentUserHistoryResource.data?.records || []) map[r.date] = r;
	return map;
});

const hm = (t) => (t ? String(t).slice(11, 16) : null);

const selectedDay = computed(() => {
	const date = selectedDate.value;
	const day = calendarDays.value.find((d) => d.dateStr === date);
	const rec = recordsByDate.value[date];
	const entries = [];

	if (day?.isHoliday) {
		entries.push({ title: day.holidayName || 'Holiday', detail: 'Company holiday', bar: 'bg-sky-400' });
	}
	if (day?.isOnLeave) {
		entries.push({ title: day.holidayName || 'Leave', detail: 'Approved leave', bar: 'bg-violet-400' });
	}
	if (rec) {
		if (rec.shift) {
			entries.push({ title: rec.shift, detail: 'Rostered shift', bar: 'bg-accent' });
		}
		if (rec.in_time) {
			entries.push({
				title: 'Clocked in',
				detail: rec.out_time ? null : 'Still clocked in',
				meta: hm(rec.in_time),
				bar: 'bg-green-500',
			});
		}
		if (rec.out_time) {
			entries.push({
				title: 'Clocked out',
				meta: hm(rec.out_time),
				bar: 'bg-amber-500',
			});
		}
		if (rec.working_hours) {
			entries.push({ title: 'Hours worked', meta: `${rec.working_hours} h`, bar: 'bg-black/15 dark:bg-white/25' });
		}
	}

	const TAGS = {
		Present: { label: 'Present', tone: 'tag-emerald' },
		Absent: { label: 'Absent', tone: 'tag-red' },
		'Half Day': { label: 'Half day', tone: 'tag-amber' },
		'On Leave': { label: 'On leave', tone: 'tag-neutral' },
	};

	return { date, entries, statusTag: rec ? TAGS[rec.status] : day?.isHoliday ? { label: 'Holiday', tone: 'tag-accent' } : null };
});

const selectedDayHeading = computed(() => {
	if (selectedDate.value === todayStr.value) return 'Today';
	return new Date(selectedDate.value + 'T00:00:00').toLocaleDateString('en-US', { weekday: 'long' });
});

const selectedDaySub = computed(() =>
	new Date(selectedDate.value + 'T00:00:00').toLocaleDateString('en-US', { day: 'numeric', month: 'long', year: 'numeric' })
);

/* A day in the future has no attendance yet — saying "no records" there would
   read as a problem rather than as a date that has not happened. */
const selectedDayEmpty = computed(() => {
	if (selectedDate.value > todayStr.value) return 'Nothing rostered for this day yet.';
	return 'No attendance recorded for this day.';
});

const monthOptions = computed(() => {
	const opts = [];
	const now = new Date();
	for (let offset = -12; offset <= 2; offset++) {
		const d = new Date(now.getFullYear(), now.getMonth() + offset, 1);
		const m = d.getMonth() + 1;
		const y = d.getFullYear();
		opts.push({
			value: `${y}-${m}`,
			label: d.toLocaleDateString("en-US", { month: "long", year: "numeric" }),
			month: m,
			year: y,
		});
	}
	return opts;
});

const selectedMonthKey = computed({
	get: () => `${selectedYear.value}-${selectedMonth.value}`,
	set: (val) => {
		const [y, m] = val.split("-").map(Number);
		selectedYear.value = y;
		selectedMonth.value = m;
	},
});

async function handleClockIn() {
	const empId = employeeStore.employee?.name;
	if (empId) await attendanceStore.clockIn(empId);
}
async function handleClockOut() {
	const empId = employeeStore.employee?.name;
	if (empId) await attendanceStore.clockOut(empId);
}
async function handleBreak() {
	if (isOnBreak.value) await attendanceStore.endBreak();
	else await attendanceStore.startBreak();
}

watch([selectedMonth, selectedYear], () => {
	fetchCurrentUserHistory();
	fetchMonthlyStats();
	fetchMonthlyRoster();
});

onMounted(async () => {
	await employeeStore.init();
	const empId = employeeStore.employee?.name;
	if (empId) {
		await attendanceStore.init(empId);
	}
	await fetchCurrentUserHistory();
	await fetchMonthlyStats();
	await fetchMonthlyRoster();
});
</script>
