<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useEmployeeStore } from "@/stores/employee";
import { useAttendanceStore } from "@/stores/attendance";

const employeeStore = useEmployeeStore();
const attendance = useAttendanceStore();
const loading = ref(false);
const breakLoading = ref(false);
const error = ref("");
const isClockedIn = ref(false);
const isCompleted = computed(() => attendance.isDayCompleted);
const clockInTime = ref(null);
const elapsed = ref(0);
const onBreak = ref(false);
const totalBreakMinutes = ref(0);
const breakCount = ref(0);
const breakStartTime = ref(null);
const breakElapsed = ref(0);
let timerInterval = null;
let breakTickInterval = null;
let statusSynced = false;
const statusLoading = ref(true);
let timerAnchorTime = 0;    // Date.now() when timer started
let timerAnchorElapsed = 0; // elapsed seconds at anchor point
let lastTotalSeconds = 0;   // last known total_seconds_today from backend
let clientServerOffset = 0; // clock drift offset in ms (client - server)

const SHIFT_SECONDS = computed(() => {
  return Math.abs(attendance.workingHoursTarget || 8) * 3600;
});
const RADIUS = 82;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

const progress = computed(() => {
  if (elapsed.value === 0) return 0;
  return Math.min(elapsed.value / SHIFT_SECONDS.value, 1);
});

const shiftTargetDisplay = computed(() => {
  const targetHours = Math.abs(attendance.workingHoursTarget || 8);
  const h = Math.floor(targetHours);
  const m = Math.round((targetHours - h) * 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")} Target`;
});

const shiftComplete = computed(() => progress.value >= 1);

/* The scheduled window, so the ring has a scale to be read against. Without
   it the arc is a proportion of nothing — you cannot tell whether a quarter
   turn means two hours or six. */
const hhmm = (t) => (typeof t === "string" ? t.slice(0, 5) : "");
const shiftWindow = computed(() => {
  const s = attendance.todayStatus;
  const start = hhmm(s?.shift_start);
  const end = hhmm(s?.shift_end);
  return start && end ? `${start} – ${end}` : "";
});

const progressPercent = computed(() => Math.round(progress.value * 100));
const shiftTargetHours = computed(() => Math.abs(attendance.workingHoursTarget || 8));

const remainingDisplay = computed(() => {
  const left = Math.max(0, SHIFT_SECONDS.value - elapsed.value);
  if (left === 0) return "Target met";
  // Round to whole minutes FIRST, then split. Rounding the remainder after
  // splitting produced "7h 60m left" one second into an 8h shift.
  const totalMinutes = Math.round(left / 60);
  const h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;
  if (h && m) return `${h}h ${m}m left`;
  if (h) return `${h}h left`;
  return `${m}m left`;
});

/* Segmented ring. A solid arc of a one-second shift is invisible; discrete
   ticks show the shape of the whole shift and light up as it is worked, so
   the ring reads as a gauge rather than a progress bar. */
const TICKS = 60;
const tickMarks = computed(() => {
  const filledCount = Math.round(progress.value * TICKS);
  return Array.from({ length: TICKS }, (_, i) => ({
    angle: (360 / TICKS) * i,
    filled: i < filledCount,
  }));
});

const dashOffset = computed(() => CIRCUMFERENCE * (1 - progress.value));

const timerDisplay = computed(() => {
  const total = Math.max(0, elapsed.value);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
});

const breakTimerDisplay = computed(() => {
  const total = Math.max(0, breakElapsed.value);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
});

const clockInTimeFormatted = computed(() => {
  if (!clockInTime.value) return "";
  return clockInTime.value.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
});

const breakMinutesFormatted = computed(() => {
  const totalMinutes = Math.floor(totalBreakMinutes.value);
  const h = Math.floor(totalMinutes / 60);
  const m = Math.floor(totalMinutes % 60);
  const s = Math.floor((totalBreakMinutes.value * 60) % 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
});

const ringColor = computed(() => {
  if (onBreak.value) return "#D97706"; // warning
  if (isCompleted.value) return "#059669"; // success
  if (shiftComplete.value) return "#059669";
  // Idle is not an error. This was red, which painted a danger-coloured disc
  // behind 'Tap CLOCK IN to start your shift' — the normal state of the page
  // before a shift begins. Accent instead.
  return "#5B4BC4";
});

const glowColor = computed(() => {
  if (onBreak.value) return "rgba(245, 158, 11, 0.3)";
  if (isCompleted.value) return "rgba(34, 197, 94, 0.35)";
  if (shiftComplete.value) return "rgba(34, 197, 94, 0.35)";
  return "rgba(239, 68, 68, 0.25)";
});

function startTimer() {
  stopTimer();
  stopBreakTick();
  // Tick elapsed locally from the anchor point, adjusting for clock offset
  timerInterval = setInterval(() => {
    const adjustedNow = Date.now() - clientServerOffset;
    elapsed.value = timerAnchorElapsed + Math.floor((adjustedNow - timerAnchorTime) / 1000);
    // Publish to the store so the page shows ONE number. The store runs its own
    // cruder ticker; left alone, the dashboard's "Hours worked" drifted away
    // from the ring by roughly the length of each break.
    attendance.workedSecondsToday = elapsed.value;
  }, 1000);
}

function startBreakTick() {
  stopBreakTick();
  // Tick breakElapsed while on break so the display updates, adjusting for clock offset
  breakTickInterval = setInterval(() => {
    if (onBreak.value && breakStartTime.value) {
      const adjustedNow = Date.now() - clientServerOffset;
      breakElapsed.value = Math.max(0, Math.floor((adjustedNow - breakStartTime.value.getTime()) / 1000));
    }
  }, 1000);
}

function stopBreakTick() {
  if (breakTickInterval) {
    clearInterval(breakTickInterval);
    breakTickInterval = null;
  }
}

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
}

async function fetchStatus(forceFetch = false) {
  try {
    const empId = attendance.employeeId;
    if (!empId) return;

    if (forceFetch || !attendance.todayStatus) {
      await attendance.fetchTodayStatus(empId);
    }

    const data = attendance.todayStatus;
    if (!data) return;

    statusSynced = true;
    const firstInLog = data.logs?.find((l) => l.log_type === "IN");

    const newTotal = data.total_seconds_today || 0;

    // Build clockInTime from logs (first IN log) for display
    if (firstInLog) {
      clockInTime.value = new Date(firstInLog.time);
    }

    // Derive break info from check-in logs (backend returns logs, not a breaks object)
    const entries = data.logs || [];
    breakCount.value = entries.filter((l) => l.note === "Break Start").length;
    const breakStartLogs = entries.filter((l) => l.note === "Break Start");
    const breakEndLogs = entries.filter((l) => l.note === "Break End");
    let totalMs = 0;
    for (let i = 0; i < breakEndLogs.length; i++) {
      totalMs += new Date(breakEndLogs[i].time).getTime() - new Date(breakStartLogs[i].time).getTime();
    }
    totalBreakMinutes.value = totalMs / 60000;

    // Find the most recent break start log without a matching break-end log
    let breakStartIndex = -1;
    for (let i = entries.length - 1; i >= 0; i--) {
      if (entries[i].note === "Break Start") {
        breakStartIndex = i;
        break;
      }
    }
    if (breakStartIndex >= 0) {
      const logTypeAfter = entries[breakStartIndex + 1]?.log_type;
      const isStillOnBreak =
        !logTypeAfter || logTypeAfter === "OUT" || logTypeAfter === "Break Start";
      if (isStillOnBreak) {
        breakStartTime.value = new Date(entries[breakStartIndex].time);
      } else {
        // Break was already ended — don't set breakStartTime
        breakStartTime.value = null;
      }
    } else {
      breakStartTime.value = null;
    }

    // Calculate time offset between client browser and server
    if (data.checked_in && data.last_log_time && data.current_session_seconds !== undefined) {
      const serverTime = new Date(data.last_log_time).getTime() + data.current_session_seconds * 1000;
      clientServerOffset = Date.now() - serverTime;
    } else if (data.is_on_break && data.last_log_time && data.current_break_seconds !== undefined) {
      const serverTime = new Date(data.last_log_time).getTime() + data.current_break_seconds * 1000;
      clientServerOffset = Date.now() - serverTime;
      breakElapsed.value = data.current_break_seconds;
    }

    // Compute elapsed from backend anchor — ticks forward using Date.now() drift
    if (lastTotalSeconds > 0 && data.checked_in) {
      // Resuming: elapsed = last known total + time since last fetch
      const adjustedNow = Date.now() - clientServerOffset;
      const drift = Math.floor((adjustedNow - timerAnchorTime) / 1000);
      elapsed.value = lastTotalSeconds + drift;
    } else {
      // First fetch or not checked in
      elapsed.value = newTotal;
    }

    // Determine state from backend data
    if (data.is_on_break) {
      // Currently on break — stop work timer, start break tick
      isClockedIn.value = true;
      onBreak.value = true;
      lastTotalSeconds = 0;
      stopTimer();
      startBreakTick();
    } else if ((data.checked_in || data.is_still_checked_in) && data.last_log_type !== "OUT") {
      // Clocked in and actively working
      isClockedIn.value = true;
      onBreak.value = false;
      timerAnchorTime = Date.now() - clientServerOffset;
      timerAnchorElapsed = elapsed.value;
      lastTotalSeconds = newTotal;
      stopBreakTick();
      startTimer();
    } else if (data.last_log_type === "OUT" && data.logs?.length >= 2 && isCompleted.value) {
      // Both IN and OUT done for today — day complete
      isClockedIn.value = false;
      onBreak.value = false;
      elapsed.value = data.total_seconds_today || 0;
      stopTimer();
    } else {
      // Nothing happened today OR completed state has vanished
      isClockedIn.value = false;
      clockInTime.value = null;
      elapsed.value = 0;
      onBreak.value = false;
      stopTimer();
    }
  } catch {
    // Silently fail
  } finally {
    statusLoading.value = false;
  }
}

async function handleClockIn() {
  const empId = employeeStore.employee?.name;
  if (!empId) {
    error.value = "No employee ID found";
    return;
  }
  if (isCompleted.value || onBreak.value) return;

  loading.value = true;
  error.value = "";
  try {
    const shift = attendance.todayStatus?.active_shift_name;
    const result = await attendance.clockIn(empId, null, null, null, shift);
    if (result && (result.success || result.checked_in)) {
      // Refresh status from backend to get accurate state (forceFetch = true)
      await fetchStatus(true);
      startCooldown();
      emit("punched");
    } else {
      error.value = result?.message || result?.error || "Clock in failed";
    }
  } catch (e) {
    error.value = attendance.error || e.message || "Something went wrong";
  } finally {
    loading.value = false;
  }
}

/* Mis-punch guards.
   A double click on Clock in used to land on Clock out the moment the button
   re-rendered, ending the shift one second in. Two things stop that:
     1. a short cooldown after any punch, during which the primary is inert;
     2. a confirm step when the shift is younger than MIN_SHIFT_SECONDS, since
        nobody means to end a shift a minute after starting it.
   Both are client-side; the real backend should reject or flag a sub-minute
   shift too, because this guard is only as good as the client. */
const PUNCH_COOLDOWN_MS = 2500;
const MIN_SHIFT_SECONDS = 60;
const cooldown = ref(false);
let cooldownTimer = null;
const confirmingClockOut = ref(false);

function startCooldown() {
  cooldown.value = true;
  clearTimeout(cooldownTimer);
  cooldownTimer = setTimeout(() => (cooldown.value = false), PUNCH_COOLDOWN_MS);
}

function requestClockOut() {
  if (elapsed.value < MIN_SHIFT_SECONDS) {
    confirmingClockOut.value = true;
    return;
  }
  handleClockOut();
}

function confirmClockOut() {
  confirmingClockOut.value = false;
  handleClockOut();
}

async function handleClockOut() {
  const empId = employeeStore.employee?.name;
  if (!empId) {
    error.value = "No employee ID found";
    return;
  }
  if (!isClockedIn.value || isCompleted.value || onBreak.value) return;
  loading.value = true;
  error.value = "";
  try {
    const shift = attendance.todayStatus?.active_shift_name;
    const result = await attendance.clockOut(empId, null, null, null, shift);
    if (result && (result.success || result.checked_out)) {
      // Refresh status from backend to get accurate elapsed time and state (forceFetch = true)
      await fetchStatus(true);
      startCooldown();
      emit("punched");
    } else {
      error.value = result?.message || result?.error || "Clock out failed";
    }
  } catch (e) {
    error.value = attendance.error || e.message || "Something went wrong";
  } finally {
    loading.value = false;
  }
}

async function handleBreak() {
  breakLoading.value = true;
  error.value = "";
  try {
    if (onBreak.value) {
      // End break — refresh status from backend to get accurate state
      await attendance.endBreak();
      await fetchStatus(true);
      startCooldown();
    } else {
      // Start break
      await attendance.startBreak();
      // Refresh status from backend to get accurate state
      await fetchStatus(true);
      startCooldown();
    }
  } catch (e) {
    error.value = attendance.error || e.message || "Something went wrong";
  } finally {
    breakLoading.value = false;
  }
}

onMounted(async () => {
  await employeeStore.init();
  // attendance.employeeId may already be set by Dashboard init
  // Wait briefly for it to be ready if not
  if (!attendance.employeeId) {
    await new Promise((resolve) => {
      const check = () => {
        if (attendance.employeeId) resolve();
        else setTimeout(check, 50);
      };
      setTimeout(resolve, 1000); // reduced timeout
      check();
    });
  }
  await fetchStatus(false);
});

// Reactively watch for todayStatus updates in the store
watch(() => attendance.todayStatus, () => {
  fetchStatus(false);
}, { immediate: true, deep: true });

watch(isCompleted, () => {
  fetchStatus(false);
});

onUnmounted(() => {
  clearTimeout(cooldownTimer);
  stopTimer();
  stopBreakTick();
});

const emit = defineEmits(["punched"]);

/* The ring's caption says what the number counts, so the number needs no
   label of its own. Was red while simply working — danger styling on the
   normal state, the same bug the idle ring had. */
const ringCaption = computed(() => {
  if (onBreak.value) return "On break";
  if (isCompleted.value) return "Day complete";
  if (isClockedIn.value) return shiftComplete.value ? "Shift complete" : "Hours worked";
  return "Not started";
});

const timerTone = computed(() => {
  if (onBreak.value) return "text-amber-600 dark:text-amber-400";
  if (isCompleted.value || shiftComplete.value) return "text-green-700 dark:text-green-400";
  return "text-[#17181B] dark:text-white";
});

const statusText = computed(() => {
  if (isCompleted.value) return `Worked ${timerDisplay.value} today`;
  if (onBreak.value) return `On break ${breakTimerDisplay.value} · timer paused`;
  if (isClockedIn.value) return "";
  return "Tap Clock in to start your shift";
});

const statusTone = computed(() =>
  onBreak.value
    ? "text-amber-600 dark:text-amber-400"
    : "text-[#5C6169] dark:text-white/65"
);

</script>

<template>
  <div class="flex flex-col items-center w-full max-w-[280px]">
    <p class="status-label !mb-3 !text-center w-full">Shift timer</p>

    <!-- SVG Clock Ring -->
    <div class="relative mb-5">
      <!-- No -rotate-90 here. That was left over from the stroke-dasharray arc,
           where 0° sits at 3 o'clock. The ticks are already drawn from the top
           of the box, so the rotation was pushing the start round to 9 o'clock. -->
      <svg width="200" height="200">
        <g
          v-for="(tick, i) in tickMarks"
          :key="i"
          :transform="`rotate(${tick.angle} 100 100)`"
        >
          <line
            x1="100"
            y1="16"
            x2="100"
            y2="30"
            stroke-width="4"
            stroke-linecap="round"
            :stroke="tick.filled ? ringColor : 'currentColor'"
            :class="tick.filled ? '' : 'text-black/[0.08] dark:text-white/[0.12]'"
            class="transition-colors duration-500"
          />
        </g>
      </svg>

      <!-- Center: the elapsed time, then what it counts. -->
      <div
        class="absolute inset-0 m-auto w-[140px] h-[140px] rounded-full flex flex-col items-center justify-center gap-1"
      >
        <div
          v-if="statusLoading || loading"
          class="w-6 h-6 border-2 border-current border-t-transparent rounded-full animate-spin text-accent dark:text-accent-light"
        />
        <template v-else>
          <span
            v-if="isClockedIn || isCompleted || onBreak"
            class="text-2xl font-semibold tabular-nums tracking-tight"
            :class="timerTone"
          >
            {{ timerDisplay }}
          </span>
          <span v-else class="text-2xl font-semibold tabular-nums tracking-tight text-[#656A72] dark:text-white/85">
            00:00:00
          </span>

          <span class="text-xs font-medium text-[#656A72] dark:text-white/55">
            {{ ringCaption }}
          </span>
        </template>
      </div>
    </div>

    <!-- The scheduled window and how much of it is left. The ring shows a
         proportion; this says a proportion of what. -->
    <div
      v-if="shiftWindow"
      class="w-full mb-4 flex items-center justify-between gap-2 px-3 py-2 rounded-[10px] bg-black/[0.03] dark:bg-white/[0.06]"
    >
      <span class="text-xs font-medium tabular-nums text-[#17181B] dark:text-white">{{
        shiftWindow
      }}</span>
      <span class="text-xs text-[#5C6169] dark:text-white/65 tabular-nums">{{
        isClockedIn || isCompleted || onBreak ? remainingDisplay : `${shiftTargetHours}h shift`
      }}</span>
    </div>

    <!-- Primary action. Disabled for a beat after any punch so a double click
         cannot carry through to the button that replaces it. -->
    <button
      v-if="!isClockedIn && !isCompleted"
      @click="handleClockIn"
      :disabled="loading || cooldown"
      class="w-full h-12 inline-flex items-center justify-center gap-2 rounded-[12px] bg-accent hover:bg-accent-hover active:bg-accent-hover text-white font-medium text-sm transition-colors disabled:opacity-45 disabled:cursor-not-allowed"
    >
      <span v-if="loading" class="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
      <template v-else>
        <span class="material-symbols-outlined !text-[20px]">play_circle</span>
        Clock in
      </template>
    </button>

    <button
      v-else-if="isClockedIn && !isCompleted"
      @click="requestClockOut"
      :disabled="loading || onBreak || cooldown"
      :title="onBreak ? 'End your break before clocking out' : ''"
      class="w-full h-12 inline-flex items-center justify-center gap-2 rounded-[12px] bg-accent hover:bg-accent-hover active:bg-accent-hover text-white font-medium text-sm transition-colors disabled:opacity-45 disabled:cursor-not-allowed"
    >
      <span v-if="loading" class="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
      <template v-else>
        <span class="material-symbols-outlined !text-[20px]">stop_circle</span>
        End shift
      </template>
    </button>

    <div
      v-else
      class="w-full h-12 inline-flex items-center justify-center gap-2 text-sm font-medium text-green-700 dark:text-green-400"
    >
      <span class="material-symbols-outlined !text-[20px]">check_circle</span>
      Day complete
    </div>

    <!-- Short-shift confirm. Nobody means to end a shift a minute in, so that
         case asks instead of acting. -->
    <div
      v-if="confirmingClockOut"
      class="w-full mt-2 p-3 rounded-[12px] bg-amber-500/10 border border-amber-500/25"
    >
      <p class="text-[13px] text-amber-800 dark:text-amber-200 leading-snug">
        You clocked in {{ timerDisplay }} ago. End the shift?
      </p>
      <div class="flex gap-2 mt-2.5">
        <button
          @click="confirmClockOut"
          class="flex-1 h-9 rounded-[10px] bg-amber-600 hover:bg-amber-700 text-white text-[13px] font-medium transition-colors"
        >
          End shift
        </button>
        <button
          @click="confirmingClockOut = false"
          class="flex-1 h-9 rounded-[10px] border border-black/[0.09] dark:border-white/[0.16] text-[13px] font-medium text-[#17181B] dark:text-white"
        >
          Keep working
        </button>
      </div>
    </div>

    <!-- Secondary actions, 2-up. The row keeps its shape when not clocked in so
         the card does not change height the moment you punch in; break is
         disabled instead of vanishing, and says why. -->
    <div class="grid grid-cols-1 gap-1 w-full mt-2 p-1 rounded-[13px] bg-black/[0.02] dark:bg-white/[0.03]">
      <button
        @click="handleBreak"
        :disabled="breakLoading || !isClockedIn || isCompleted || cooldown"
        :title="!isClockedIn ? 'Clock in first' : ''"
        class="h-10 px-2 inline-flex items-center justify-center gap-1.5 rounded-[10px] text-[13px] font-medium text-[#17181B] dark:text-white bg-black/[0.035] dark:bg-white/[0.07] hover:bg-black/[0.06] dark:hover:bg-white/[0.11] hover:text-accent dark:hover:text-accent-light transition-colors disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-black/[0.035] disabled:hover:text-[#17181B] truncate"
        :class="onBreak ? '!bg-amber-500/15 !text-amber-700 dark:text-amber-400 dark:!text-amber-300' : ''"
      >
        <span v-if="breakLoading" class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin mx-auto block" />
        <!-- Label only: "End break · 00:00:12" did not fit half the row and
             truncated to "End break · 00…". The elapsed break is on the status
             line below, where it has the full width. -->
        <template v-else>
          <span class="material-symbols-outlined !text-[18px]">{{ onBreak ? 'play_arrow' : 'coffee' }}</span>
          {{ onBreak ? 'End break' : 'Break' }}
        </template>
      </button>

    </div>

    <!-- Today's figures. These used to live in a separate "Today" card; the
         start time in particular was only ever on the status line while the
         shift ran, so it vanished the moment the shift completed. -->
    <p
      v-if="(isClockedIn || isCompleted) && clockInTimeFormatted"
      class="mt-3 text-xs text-[#5C6169] dark:text-white/65 text-center tabular-nums"
    >
      Clocked in {{ clockInTimeFormatted }}
    </p>
    <p
      v-if="(isClockedIn || isCompleted) && breakCount > 0 && !onBreak"
      class="mt-1 text-xs text-[#5C6169] dark:text-white/65 text-center tabular-nums"
    >
      {{ breakCount }} break{{ breakCount !== 1 ? "s" : "" }} · {{ breakMinutesFormatted }}
    </p>

    <!-- Status line -->
    <p v-if="statusText" class="mt-3 text-[13px] text-center" :class="statusTone">{{ statusText }}</p>

    <p v-if="error" class="mt-2 text-xs text-red-600 dark:text-red-400 text-center font-medium max-w-[240px]">
      {{ error }}
    </p>
  </div>
</template>
