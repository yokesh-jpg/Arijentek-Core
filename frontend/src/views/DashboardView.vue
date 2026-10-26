<template>
	<div class="space-y-5 sm:space-y-6">
		<!-- ===== Greeting + manager action =====
		     The manager control lives with the greeting rather than in a card of
		     its own: it is one button, and a card around one button reads as a
		     section that never arrived. -->
		<div class="flex items-start justify-between gap-4">
			<div class="min-w-0">
				<h1 class="page-title truncate">
					{{ greeting }},
					<span class="text-accent dark:text-accent-light">{{ firstName }}</span>
				</h1>
				<p class="page-subtitle">{{ todayLabel }}</p>
			</div>

			<button
				v-if="canCreateAttendance"
				@click="showActiveEmployeesDialog = true"
				class="btn-secondary shrink-0"
			>
				<span class="material-symbols-outlined !text-[18px]">pending_actions</span>
				<span class="hidden sm:inline">Active shift monitoring</span>
				<span class="sm:hidden">On shift</span>
			</button>
		</div>

		<!-- ===== Shift row =====
		     Three standalone cards rather than one panel with rules through it.
		     The shift clock, today's figures and today's work are separate
		     things you act on separately, so each gets its own edge. The clock
		     keeps a fixed column; the other two stack beside it. -->
		<div
			class="grid grid-cols-1 lg:grid-cols-[minmax(0,320px)_1fr] gap-4 sm:gap-5 items-stretch"
		>
			<!-- Plain card, same as its neighbours. The accent tint set it apart
			     from the two cards beside it for no reason a reader could act on —
			     the clock is already the loudest thing in the column.
			     items-stretch on the grid + justify-center here makes this column
			     end level with Priority tasks instead of stopping short. -->
			<section class="glass-card flex flex-col items-center justify-center !py-7">
				<ClockWidget @punched="refreshDashboard" />
			</section>

			<div class="flex flex-col gap-4 sm:gap-5 min-w-0">
				<!-- Quick actions. Every tile routes somewhere that exists; a
				     shortcut that opens nothing is worse than no shortcut. -->
				<section class="glass-card">
					<h2 class="text-lg font-semibold tracking-[-0.01em] text-[#17181B] dark:text-white mb-3">
						Quick actions
					</h2>
					<div class="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
						<button
							v-for="action in quickActions"
							:key="action.label"
							@click="action.run()"
							class="glass-inner flex flex-col items-start gap-2 p-3 text-left hover:border-accent/30 hover:bg-accent/[0.04] transition-colors"
						>
							<span
								class="w-8 h-8 rounded-[10px] grid place-items-center shrink-0 bg-accent/[0.10] dark:bg-accent/20 text-accent dark:text-accent-light"
							>
								<span class="material-symbols-outlined !text-[18px]">{{ action.icon }}</span>
							</span>
							<!-- Wraps rather than truncates: "Submit expense" does not fit
							     one line at 2-up on a phone. -->
							<span class="text-[13px] font-medium text-[#17181B] dark:text-white leading-snug">
								{{ action.label }}
							</span>
						</button>
					</div>
				</section>

				<!-- Priority tasks. flex-1 so this column ends level with the clock
				     beside it; the slack goes to the task list, which can use it. -->
				<section class="glass-card flex flex-col flex-1">
					<div class="flex items-center justify-between gap-3 mb-2">
						<h2 class="text-lg font-semibold tracking-[-0.01em] text-[#17181B] dark:text-white">
							Priority tasks
						</h2>
						<div class="flex items-center gap-2 shrink-0">
							<span class="premium-tag tag-red">{{ pendingTasksCount }} pending</span>
							<router-link
								to="/tasks"
								class="inline-flex items-center min-h-[32px] sm:min-h-0 text-xs font-medium text-accent dark:text-accent-light hover:underline"
								>View all</router-link
							>
						</div>
					</div>

					<ul v-if="sortedOpenTodos.length" class="flex-1 -mx-2">
						<li
							v-for="todo in sortedOpenTodos.slice(0, 4)"
							:key="todo.id"
							class="flex items-center gap-3 px-2 py-2 rounded-[10px] hover:bg-black/[0.025] dark:hover:bg-white/[0.04] transition-colors"
						>
							<p
								class="text-[13px] font-medium text-[#17181B] dark:text-white truncate flex-1"
								:class="todo.status === 'Closed' ? 'line-through opacity-50' : ''"
							>
								{{ todo.description }}
							</p>
							<span
								class="text-xs font-medium shrink-0 tabular-nums"
								:class="dueMeta(todo).tone"
								>{{ dueMeta(todo).label }}</span
							>
						</li>
					</ul>
					<p
						v-else
						class="flex-1 grid place-items-center py-6 text-[13px] text-[#5C6169] dark:text-white/55"
					>
						Nothing assigned to you today.
					</p>

					<router-link
						to="/tasks"
						class="mt-2 h-9 lg:h-8 flex items-center justify-center gap-1.5 rounded-[12px] border border-dashed border-black/15 dark:border-white/20 text-xs font-medium text-[#5C6169] dark:text-white/65 hover:border-accent hover:text-accent dark:hover:text-accent-light transition-colors"
					>
						<span class="material-symbols-outlined !text-[18px]">add</span>
						Add new task
					</router-link>
				</section>
			</div>
		</div>

		<!-- ===== Counts =====
		     Four across on desktop, two across on a phone. Earnings joins them
		     rather than owning a purple billboard — see the note on masking. -->
		<div class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
			<div v-for="stat in stats" :key="stat.label" class="glass-card !p-4 sm:!p-5">
				<div class="flex items-center gap-2.5 mb-3">
					<span
						class="w-8 h-8 rounded-[10px] grid place-items-center shrink-0"
						:class="stat.wash"
					>
						<span class="material-symbols-outlined !text-[18px]">{{ stat.icon }}</span>
					</span>
					<!-- Wraps rather than truncates: at 2-up on a phone "Available
					     leaves" does not fit one line, and "Available le…" is worse
					     than two lines. -->
					<p class="text-xs font-medium text-[#5C6169] dark:text-white/65 leading-tight">
						{{ stat.label }}
					</p>
				</div>
				<p
					class="text-[28px] font-semibold tracking-[-0.02em] text-[#17181B] dark:text-white tabular-nums leading-none"
				>
					{{ stat.value }}
				</p>
				<p class="text-xs text-[#5C6169] dark:text-white/55 mt-1.5">{{ stat.hint }}</p>
			</div>
		</div>

		<!-- ===== Schedule + pay ===== -->
		<div class="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-5 items-stretch">
			<!-- Upcoming roster.
			     Rows are separated by hairlines rather than each being its own
			     rounded tile — four tiles inside a card is a card of cards. Today
			     is marked by a filled date chip, so the accent lands on the thing
			     that identifies the row instead of ringing the whole line. The
			     header carries the week's scheduled hours, which the list of
			     ranges makes you add up yourself. -->
			<section class="glass-card flex flex-col">
				<div class="flex items-center justify-between gap-3 mb-1">
					<h2 class="text-lg font-semibold tracking-[-0.01em] text-[#17181B] dark:text-white">
						Upcoming roster
					</h2>
					<button
						@click="openroster()"
						class="inline-flex items-center min-h-[32px] sm:min-h-0 shrink-0 text-xs font-medium text-accent dark:text-accent-light hover:underline"
					>
						View all
					</button>
				</div>
				<p v-if="scheduledHours" class="text-xs text-[#5C6169] dark:text-white/65 mb-3">
					{{ scheduledHours }} scheduled over {{ upcomingRoster.length }} days
				</p>

				<ul
					v-if="upcomingRoster.length"
					class="flex-1 divide-y divide-black/[0.06] dark:divide-white/[0.07]"
				>
					<li
						v-for="(day, i) in upcomingRoster"
						:key="i"
						class="flex items-center gap-3 py-2.5 first:pt-0"
					>
						<div
							class="w-10 h-10 shrink-0 rounded-[10px] grid place-content-center text-center leading-none"
							:class="i === 0 ? 'bg-accent text-white' : 'bg-black/[0.03] dark:bg-white/[0.06] text-[#17181B] dark:text-white'"
						>
							<span
								class="text-xs font-medium"
								:class="i === 0 ? 'text-white/90' : 'text-[#656A72] dark:text-white/60'"
								>{{ day.dayLabel }}</span
							>
							<span class="text-[14px] font-semibold tabular-nums mt-0.5 block">{{
								day.dayNumber
							}}</span>
						</div>
						<div class="min-w-0 flex-1">
							<p
								class="text-[13px] font-medium text-[#17181B] dark:text-white leading-snug truncate"
							>
								{{ day.shift_name }}
							</p>
							<p
								class="text-xs tabular-nums mt-0.5"
								:class="day.isOff ? 'text-[#656A72] dark:text-white/55' : 'text-[#5C6169] dark:text-white/65'"
							>
								{{ day.timeLocation }}
							</p>
						</div>
						<span v-if="i === 0" class="premium-tag tag-accent shrink-0">Today</span>
					</li>
				</ul>
				<p
					v-else
					class="flex-1 grid place-items-center py-8 text-[13px] text-[#5C6169] dark:text-white/55 text-center"
				>
					No upcoming roster scheduled.
				</p>
			</section>

			<!-- ===== Payroll =====
			     The one filled card on the page, so it has to be the thing worth
			     pointing at. Figures still start masked: this screen is opened on
			     a shop floor where customers and other staff can see it. The
			     reveal is one tap, and nothing is removed. -->
			<section
				class="rounded-[18px] p-6 flex flex-col text-white bg-gradient-to-br from-accent to-accent-hover shadow-[0_14px_34px_-14px_rgb(var(--accent-rgb)/0.55)]"
			>
				<div class="flex items-start justify-between gap-3 mb-6">
					<div class="flex items-center gap-2.5 min-w-0">
						<span class="material-symbols-outlined !text-[20px] shrink-0">payments</span>
						<h2 class="text-base font-semibold truncate">My payroll</h2>
					</div>

				</div>

				<p class="text-xs text-white/85 mb-1.5">Current period earnings</p>
				<p class="text-[28px] font-semibold tabular-nums leading-none tracking-[-0.02em]">
					{{ mask(currentPeriodEarnings) }}
				</p>

				<!-- mt-auto pins the button to the bottom so this card lines up with
				     the two beside it however tall the row grows. -->
				<div class="mt-6 mb-6 space-y-3">
					<div class="flex items-baseline justify-between gap-3">
						<span class="text-[13px] text-white/85">Tax deductions</span>
						<span class="text-[13px] font-medium tabular-nums">{{
							`-${money(taxDeductions)}`
						}}</span>
					</div>
					<div class="h-px bg-white/15"></div>
					<div class="flex items-baseline justify-between gap-3">
						<span class="text-[13px] text-white/85">Bonus items</span>
						<span class="text-[13px] font-medium tabular-nums">{{
							`+${money(bonusItems)}`
						}}</span>
					</div>
				</div>

				<button
					class="mt-auto h-11 w-full inline-flex items-center justify-center gap-2 rounded-[12px] bg-white text-accent text-[13px] font-semibold hover:bg-white/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
					:disabled="!latestSlipId"
					:title="latestSlipId ? '' : 'No salary slip available yet'"
					@click="downloadStatement()"
				>
					<span class="material-symbols-outlined !text-[18px]">download</span>
					Download statement
				</button>
			</section>
		</div>

		<ActiveEmployeesList v-model="showActiveEmployeesDialog" @save-success="refreshDashboard" />
		<!-- Create Task Dialog Modal -->
		<CreateTasks
			v-if="showAddTaskDialog"
			:metadata="taskMetadata"
			:allocatableUsers="tasksStore.allocatableUsersList?.data || []"
			:loading="tasksStore.loading"
			@close="showAddTaskDialog = false"
			@save="handleSaveTaskFromDashboard"
		/>
		<!-- Request Leave Dialog Modal -->
		<CreateLeaveApplication
			v-model="showRequestLeaveDialog"
			@save="handleSaveLeaveFromDashboard"
		/>
		<!-- View Leave Application Dialog Modal -->
		<ViewLeaveApplication
			v-model="showViewLeaveDialog"
			:leaveApplicationId="viewLeaveApplicationId"
		/>
		<!-- Create Expense Claim Dialog Modal -->
		<CreateExpenseClaim
			v-model="showCreateExpenseDialog"
			@save="handleSaveExpenseFromDashboard"
		/>
		<!-- Create Issue Dialog Modal -->
		<CreateIssue
			v-model="showCreateIssueDialog"
			@save="handleSaveIssueFromDashboard"
		/>

	</div>
</template>

<script setup>
import CreateTasks from "@/views/forms/tasks/create_tasks.vue"
import CreateLeaveApplication from "@/views/forms/leave/create_leave_application.vue"
import ViewLeaveApplication from "@/views/page_views/leave/view_leave_application.vue"
import CreateExpenseClaim from "@/views/forms/expense/create_expense_claim.vue"
import CreateIssue from "@/views/forms/issues/create_issue.vue"
import { useLeaveStore } from "@/stores/leave"
import { createResource } from "frappe-ui"
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useEmployeeStore } from '@/stores/employee'
import { useAttendanceStore } from '@/stores/attendance'
import { useTasksStore } from '@/stores/tasks'
import ClockWidget from '@/components/ClockWidget.vue'
import '@/services/api'
import { usePayrollStore } from '../stores/payroll'
import ActiveEmployeesList from './forms/attendance/active_employees_list.vue'

const auth = useAuthStore()
const employeeStore = useEmployeeStore()
const attendance = useAttendanceStore()
const tasksStore = useTasksStore()
const loading = ref(true)

const leaveStore = useLeaveStore()
const showRequestLeaveDialog = ref(false)
const showViewLeaveDialog = ref(false)
const viewLeaveApplicationId = ref('')
const showCreateExpenseDialog = ref(false)
const showCreateIssueDialog = ref(false)
const showAddTaskDialog = ref(false)
const showActiveEmployeesDialog = ref(false)
const canCreateAttendance = computed(() => {
	const d = attendance.createAttendancePermissionResource?.data
	return d === true || d === 1
})
const payrollStore = usePayrollStore()
let loadInProgress = false

// values for payroll card
const currentPeriodEarnings = ref(0)
const taxDeductions = ref(0)
const bonusItems = ref(0)
const latestSlipId = ref(null)

const money = (n) => `$${Number(n || 0).toFixed(2)}`
const mask = (n) => money(n)

const firstName = computed(
	() => auth.user?.first_name || auth.user?.full_name?.split(' ')[0] || 'there'
)
const greeting = computed(() => {
	const h = new Date().getHours()
	if (h < 12) return 'Good morning'
	if (h < 17) return 'Good afternoon'
	return 'Good evening'
})
const todayLabel = computed(() =>
	new Date().toLocaleDateString([], {
		weekday: 'long',
		day: 'numeric',
		month: 'long',
	})
)

/* Read shift state from the store's derived getters, not from raw fields.
   A break is recorded as an OUT punch, so `last_log_type === 'OUT'` is true
   mid-break — testing showed the tag reading "Shift complete" while the ring
   said "On break". `isDayCompleted` accounts for that; the raw field cannot. */
const isOnBreak = computed(() => attendance.isOnBreak)
const isCompleted = computed(() => attendance.isDayCompleted)
const isClockedIn = computed(() => attendance.isCheckedIn)

const shiftState = computed(() => {
	if (isOnBreak.value) return { label: 'On break', tone: 'tag-amber' }
	if (isCompleted.value) return { label: 'Shift complete', tone: 'tag-emerald' }
	if (isClockedIn.value) return { label: 'On shift', tone: 'tag-accent' }
	return { label: 'Not started', tone: 'tag-neutral' }
})

const clockInTimeFormatted = computed(() => {
	const firstIn = attendance.todayStatus?.logs?.find((l) => l.log_type === 'IN')
	if (!firstIn) return ''
	return new Date(firstIn.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
})
const breakCount = computed(
	() => attendance.todayStatus?.logs?.filter((l) => l.note === 'Break Start').length || 0
)
const totalBreakMinutes = computed(() => {
	const logs = attendance.todayStatus?.logs || []
	const breakStartLogs = logs.filter((l) => l.note === 'Break Start')
	const breakEndLogs = logs.filter((l) => l.note === 'Break End')
	let totalMs = 0
	for (let i = 0; i < breakEndLogs.length; i++) {
		totalMs += new Date(breakEndLogs[i].time).getTime() - new Date(breakStartLogs[i].time).getTime()
	}
	return totalMs / 60000
})

const breakMinutesFormatted = computed(() => {
	const totalMinutes = Math.floor(totalBreakMinutes.value)
	const h = Math.floor(totalMinutes / 60)
	const m = Math.floor(totalMinutes % 60)
	const s = Math.floor((totalBreakMinutes.value * 60) % 60)
	return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

/* Use the store's worked seconds rather than recomputing here.
   The old version took `logs.find(OUT)` — the FIRST out, which is the start of
   a break, not the end of the shift — then subtracted the break on top. After
   one break it read "-1m". The backend already sums the IN->OUT spans, and a
   break is an OUT, so breaks are excluded by construction. */
const hoursWorked = computed(() => {
	if (!attendance.todayStatus?.logs?.length) return '—'
	const secs = attendance.workedSecondsToday ?? attendance.totalSecondsToday ?? 0
	if (secs < 60) return `${Math.max(0, Math.round(secs))}s`
	const mins = Math.floor(secs / 60)
	if (mins < 60) return `${mins}m`
	const h = Math.floor(mins / 60)
	const m = mins % 60
	return m > 0 ? `${h}h ${m}m` : `${h}h`
})

// Always rendered, unlike the old card that only appeared mid-shift.
const todayMetrics = computed(() => [
	{ label: 'Clocked in', icon: 'schedule', value: clockInTimeFormatted.value || '—' },
	{
		label: 'Breaks',
		icon: 'coffee',
		value: breakCount.value ? `${breakCount.value} · ${breakMinutesFormatted.value}` : '—',
	},
	{ label: 'Hours worked', icon: 'timer', value: hoursWorked.value },
])

const todayShift = computed(() => {
	const first = upcomingRoster.value[0]
	if (!first) return { title: 'No shift scheduled' }
	return { title: first.isOff ? `${first.shift_name} · Off` : first.shift_name }
})

// Leave / holiday / working days data
const availableLeaves = ref(0)
const precentInThisMonth = ref(0)
const absentInThisMonth = ref(0)

const stats = computed(() => [
	{
		label: 'Available leaves',
		icon: 'event_available',
		value: availableLeaves.value,
		hint: 'days remaining',
		wash: 'bg-accent/10 text-accent dark:text-accent-light',
	},
	{
		label: 'Present',
		icon: 'check_circle',
		value: precentInThisMonth.value,
		hint: 'days this month',
		wash: 'bg-green-500/10 text-green-700 dark:text-green-400',
	},
	{
		label: 'Absent',
		icon: 'cancel',
		value: absentInThisMonth.value,
		hint: 'days this month',
		wash: 'bg-red-500/10 text-red-600 dark:text-red-400',
	},
	{
		label: 'Earnings',
		icon: 'payments',
		value: mask(currentPeriodEarnings.value),
		hint: 'current period',
		wash: 'bg-accent/10 text-accent dark:text-accent-light',
	},
])

/* One meta line per task instead of a date, a status and a priority pill all
   competing. Due date wins when it is near, because that is what makes a task
   urgent; priority is the fallback. */
function dueMeta(todo) {
	const due = todo.date ? new Date(`${todo.date}T00:00:00`) : null
	if (due && !Number.isNaN(due.getTime())) {
		const today = new Date()
		today.setHours(0, 0, 0, 0)
		const days = Math.round((due - today) / 86400000)
		if (days < 0)
			return { label: `Overdue by ${Math.abs(days)} day${days === -1 ? '' : 's'}`, tone: 'text-[#DC2626] dark:text-red-400' }
		if (days === 0) return { label: 'Due today', tone: 'text-[#DC2626] dark:text-red-400' }
		if (days === 1) return { label: 'Due tomorrow', tone: 'text-[#D97706]' }
		if (days <= 7)
			return { label: `Due in ${days} days`, tone: 'text-[#5C6169] dark:text-white/60' }
	}
	if (todo.priority === 'High')
		return { label: 'High priority', tone: 'text-accent dark:text-accent-light' }
	return { label: `${todo.priority || 'Normal'} priority`, tone: 'text-[#5C6169] dark:text-white/60' }
}

function relativeTime(iso) {
	const then = new Date(iso).getTime()
	if (Number.isNaN(then)) return ''
	const mins = Math.round((Date.now() - then) / 60000)
	if (mins < 1) return 'just now'
	if (mins < 60) return `${mins}m ago`
	const hrs = Math.round(mins / 60)
	if (hrs < 24) return `${hrs}h ago`
	const days = Math.round(hrs / 24)
	return days === 1 ? 'yesterday' : `${days}d ago`
}

async function loadDashboard() {
	const empId = employeeStore.employee?.name
	if (loadInProgress || !empId) return
	loadInProgress = true

	try {
		const res = await fetch(
			`/api/method/arijentek_core.api.dashboard.get_employee_dashboard_data?employee_id=${encodeURIComponent(empId)}`
		)
		const data = await res.json()
		if (data.message) {
			const msg = data.message

			// 1. Attendance status
			if (msg.today_status) {
				attendance.todayStatus = msg.today_status
				attendance.syncTimerFromStatus()
			}

			// 2. Leave balance
			if (msg.leave_balance !== undefined) {
				availableLeaves.value = msg.leave_balance
			}

			// Attendance Summary
			if (msg.attendance_summary) {
				precentInThisMonth.value = msg.attendance_summary.present || 0
				absentInThisMonth.value = msg.attendance_summary.absent || 0
			}

			// Next 3 days roster
			if (Array.isArray(msg.roster)) {
				upcomingRosterData.value = msg.roster
			}

			// Payroll
			if (msg.salary_slips && msg.salary_slips.length > 0) {
				const latest = msg.salary_slips[0]
				latestSlipId.value = latest.id
				currentPeriodEarnings.value = latest.gross_pay || 0
				taxDeductions.value = latest.total_deduction || 0
				bonusItems.value = 0
			}
		}
	} catch (e) {
		console.error('Failed to load dashboard data:', e)
	} finally {
		loading.value = false
		loadInProgress = false
	}
}

const priorityOrder = { High: 1, Medium: 2, Low: 3 }
const sortedOpenTodos = computed(() =>
	[...tasksStore.openTodos].sort(
		(a, b) => (priorityOrder[a.priority] || 0) - (priorityOrder[b.priority] || 0)
	)
)
const pendingTasksCount = computed(() => tasksStore.openTodos.length)

const upcomingRosterData = ref([])
const upcomingRoster = computed(() =>
	upcomingRosterData.value.map((d) => ({
		dayLabel: (d.day_name || '').slice(0, 3).toUpperCase(),
		// The backend may not send a day number; derive it from the date when
		// it does not, so the rail never renders blank.
		dayNumber: d.day_number ?? (d.date ? new Date(`${d.date}T00:00:00`).getDate() : ''),
		shift_name: d.shift_name,
		isOff: Boolean(d.is_off),
		timeLocation: d.is_off ? 'Off' : `${formatTime(d.start_time)} – ${formatTime(d.end_time)}`,
	}))
)

/* Total scheduled hours across the upcoming days. The list gives four time
   ranges; nobody adds those up in their head to answer "how much am I on
   this week". */
const scheduledHours = computed(() => {
	const mins = upcomingRosterData.value.reduce((sum, d) => {
		if (d.is_off || !d.start_time || !d.end_time) return sum
		const [sh, sm] = String(d.start_time).split(':').map(Number)
		const [eh, em] = String(d.end_time).split(':').map(Number)
		if ([sh, sm, eh, em].some(Number.isNaN)) return sum
		// An end before the start means the shift runs past midnight.
		const span = eh * 60 + em - (sh * 60 + sm)
		return sum + (span < 0 ? span + 1440 : span)
	}, 0)
	if (!mins) return ''
	const h = Math.floor(mins / 60)
	const m = mins % 60
	return m ? `${h}h ${m}m` : `${h}h`
})

function formatTime(t) {
	if (!t) return ''
	if (typeof t === 'string') {
		const [h, m] = t.split(':')
		return `${h}:${m}`
	}
	return t.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

/* The six things people actually open this screen to start. Each one routes
   to a page that exists - a tile that opens nothing is worse than no tile.

   router.push, not a hand-built URL: window.open('/employee-portal#/expense')
   drops the trailing slash the dev server's base URL needs and lands on an
   error page. The router already knows the base. */
const router = useRouter()
function go(path) {
	router.push(path)
}

const quickActions = [
	{ label: 'Request leave', icon: 'event_available', run: () => (showRequestLeaveDialog.value = true) },
	{ label: 'Add task', icon: 'add_task', run: () => (showAddTaskDialog.value = true) },
	{ label: 'Submit expense', icon: 'receipt_long', run: () => (showCreateExpenseDialog.value = true) },
	{ label: 'View roster', icon: 'calendar_month', run: () => go('/roster') },
	{ label: 'My payslips', icon: 'payments', run: () => go('/payroll') },
	{ label: 'Report an issue', icon: 'report', run: () => (showCreateIssueDialog.value = true) },
]

/* Same trailing-slash trap as the quick actions had: the hand-built URL misses
   the base the dev server expects. */
function openroster() {
	go('/roster')
}
async function downloadStatement() {
	if (!latestSlipId.value) return

	// Calling our custom, secure backend method
	const url = `/api/method/arijentek_core.api.payroll.download_salary_slip?slip_name=${encodeURIComponent(latestSlipId.value)}`
	window.open(url, '_blank')
}
onMounted(async () => {
	await employeeStore.init()
	const empId = employeeStore.employee?.name
	if (empId) {
		attendance.employeeId = empId
		leaveStore.init(empId)
		tasksStore.init()
		loadDashboard()
	}
})

// Called from ClockWidget when punch changes
async function refreshDashboard() {
	await employeeStore.init()
	const empId = employeeStore.employee?.name
	if (empId) {
		// Clear caches and reload
		localStorage.removeItem('cache_today_status')
		await attendance.fetchTodayStatus(empId)
		await loadDashboard()
	}
}

async function handleSaveLeaveFromDashboard() {
	showRequestLeaveDialog.value = false
	await loadDashboard()
}

async function handleSaveExpenseFromDashboard() {
	showCreateExpenseDialog.value = false
	await loadDashboard()
}

async function handleSaveIssueFromDashboard() {
	showCreateIssueDialog.value = false
	await loadDashboard()
}

const taskMetadata = ref({
	can_assign_to_others: false,
	priorities: ["Low", "Medium", "High"],
	statuses: ["Open", "Closed", "Cancelled"],
	users: [],
	current_user: null,
	today: new Date().toISOString().split("T")[0]
})

const taskMetadataResource = createResource({
	url: "arijentek_core.api.tasks.get_todo_creation_metadata",
	auto: true,
	onSuccess(data) {
		if (data) {
			taskMetadata.value = data
		}
	}
})

async function handleSaveTaskFromDashboard(formData) {
	try {
		let taskId = formData.id
		const result = await tasksStore.createTodo(
			formData.description,
			formData.dueDate,
			formData.priority,
			formData.assignedTo || null,
			"",
			formData.status
		)
		if (result && result.name) {
			taskId = result.name
		}

		if (taskId && formData.attachments && formData.attachments.length > 0) {
			const newFiles = formData.attachments.filter((f) => !f.isExisting)
			for (const file of newFiles) {
				const form = new FormData()
				form.append("file", file, file.name)
				form.append("is_private", 1)
				form.append("doctype", "ToDo")
				form.append("docname", taskId)

				await fetch("/api/method/upload_file", {
					method: "POST",
					headers: {
						"X-Frappe-CSRF-Token": window.csrf_token || "",
					},
					body: form,
				})
			}
		}

		showAddTaskDialog.value = false
		await tasksStore.init()
	} catch (err) {
		console.error("Failed to save task from dashboard:", err)
		alert(err?.message || "Failed to create task")
	}
}

async function toggleTodo(todoId, currentStatus) {
	await tasksStore.toggleTodo(todoId, currentStatus)
}

</script>
