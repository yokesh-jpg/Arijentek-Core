<template>
	<div v-if="modelValue" @click="close" class="fixed inset-0 z-50 flex items-center justify-center bg-[#0B0B0E]/70 backdrop-blur-sm p-4">
		<div @click.stop class="modal-panel max-w-5xl">

			<!-- Header -->
			<header class="flex items-start justify-between gap-3 px-5 py-4 border-b border-black/[0.07] dark:border-white/10 shrink-0">
				<div class="min-w-0">
					<h3 class="modal-title">Active shifts</h3>
					<p class="text-[13px] text-[#5C6169] dark:text-white/65">
						Clocked in within the last 24 hours with no clock-out.
					</p>
				</div>
				<button @click="close" class="btn-icon-ghost shrink-0" aria-label="Close">
					<span class="material-symbols-outlined !text-[18px]">close</span>
				</button>
			</header>

			<div class="flex-1 overflow-y-auto px-6 py-5 min-h-0">
				<!-- Toolbar. The counts are read off the rows on screen, so the
				     summary and the table cannot disagree. -->
				<div v-if="!loadingActiveEmployees && activeEmployeesList.length" class="flex flex-col sm:flex-row sm:items-center gap-3 mb-4">
					<div class="flex items-center gap-2 shrink-0">
						<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold tag-neutral tabular-nums">
							{{ activeEmployeesList.length }} on shift
						</span>
						<span v-if="longHoursCount" class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold tag-amber tabular-nums">
							{{ longHoursCount }} over 12h
						</span>
					</div>
					<div class="relative flex-1 min-w-0">
						<span class="material-symbols-outlined !text-[18px] absolute left-3.5 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/60 pointer-events-none">search</span>
						<input
							type="text"
							v-model="searchQuery"
							placeholder="Search by name, ID or department"
							class="field-input !pl-10"
							aria-label="Search active shifts"
						/>
					</div>
				</div>

				<!-- Advice, not an alarm. This used to be a filled amber banner on
				     every open; a warning that is always on is one nobody reads. -->
				<p v-if="!loadingActiveEmployees && activeEmployeesList.length" class="text-xs text-[#5C6169] dark:text-white/60 mb-4 leading-snug">
					Clocking out normally creates the attendance entry on its own. Only mark Present or Absent here for someone who actually forgot.
				</p>

				<!-- Loading -->
				<div v-if="loadingActiveEmployees" class="py-16 grid place-items-center">
					<span class="w-5 h-5 rounded-full border-2 border-black/10 dark:border-white/15 border-t-accent animate-spin"></span>
				</div>

				<!-- Empty -->
				<div v-else-if="filteredEmployees.length === 0" class="py-16 px-6 text-center">
					<span class="material-symbols-outlined !text-[28px] text-green-700 dark:text-green-400">check_circle</span>
					<p class="text-[13px] font-semibold text-[#17181B] dark:text-white mt-2">
						{{ activeEmployeesList.length ? 'No matches' : 'All caught up' }}
					</p>
					<p class="text-[13px] text-[#5C6169] dark:text-white/65 mt-0.5">
						{{ activeEmployeesList.length ? 'No active shift matches that search.' : 'Everyone on shift today has clocked out.' }}
					</p>
				</div>

				<!-- Table, from sm up. Below that the same rows render as cards -
				     see below. -->
				<div v-else class="table-card !rounded-[12px] hidden sm:block">
					<div class="overflow-x-auto max-h-[46vh] overflow-y-auto">
						<table class="w-full border-collapse">
							<thead class="sticky top-0 z-10 bg-white dark:bg-surface-1 border-b border-black/[0.07] dark:border-white/10">
								<tr>
									<th class="table-th !w-10 !text-center">
										<input type="checkbox" @change="toggleAllEmployees" :checked="selectedEmployees.length === filteredEmployees.length && filteredEmployees.length > 0" class="w-4 h-4 rounded accent-accent cursor-pointer" aria-label="Select all" />
									</th>
									<th class="table-th">Employee</th>
									<th class="table-th hidden 2xl:table-cell">Shift</th>
									<th class="table-th">Clocked in</th>
									<th class="table-th hidden lg:table-cell">Clock-out</th>
									<th class="table-th">Elapsed</th>
									<th class="table-th !text-right">Mark</th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="emp in filteredEmployees"
									:key="emp.employee"
									class="border-b last:border-0 border-black/[0.05] dark:border-white/[0.06]"
									:class="emp.forgot_to_clock_out ? 'bg-red-500/[0.03]' : ''"
								>
									<td class="table-td !text-center">
										<input type="checkbox" :value="emp" v-model="selectedEmployees" class="w-4 h-4 rounded accent-accent cursor-pointer" :aria-label="'Select ' + emp.employee_name" />
									</td>

									<td class="table-td-strong max-w-[200px]">
										<span class="flex items-center gap-2.5 min-w-0">
											<span class="avatar-chip !w-7 !h-7">{{ activeInitials(emp.employee_name) }}</span>
											<span class="min-w-0">
												<span class="block truncate">{{ emp.employee_name }}</span>
												<span class="block text-xs font-normal text-[#5C6169] dark:text-white/60 truncate">
													{{ emp.employee }} · {{ emp.department || 'No department' }}
												</span>
											</span>
										</span>
									</td>

									<td class="table-td hidden 2xl:table-cell whitespace-nowrap">{{ emp.shift || 'Default shift' }}</td>

									<td class="table-td whitespace-nowrap">
										<span class="flex items-center gap-1.5 tabular-nums">
											<span class="w-1.5 h-1.5 rounded-full bg-green-500 shrink-0"></span>
											{{ formatTime(emp.checkin_time) }}
										</span>
										<span class="block text-xs text-[#656A72] dark:text-white/55 mt-0.5">{{ formatDate(emp.checkin_time) }}</span>
									</td>

									<td class="table-td hidden lg:table-cell w-[260px]">
										<DateTimeField v-model="emp.checkout_time" />
									</td>

									<td class="table-td whitespace-nowrap">
										<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold tabular-nums" :class="emp.forgot_to_clock_out ? 'tag-red' : 'tag-emerald'">
											{{ emp.elapsed_hours }}h
										</span>
										<!-- The row tint alone does not say why it is tinted. -->
										<span v-if="emp.forgot_to_clock_out" class="block text-xs text-red-600 dark:text-red-400 mt-1">
											No clock-out
										</span>
									</td>

									<td class="table-td !text-right whitespace-nowrap">
										<span class="inline-flex items-center justify-end gap-1.5">
											<button
												@click="reconcileSingle(emp, 'Present')"
												class="h-8 px-2.5 rounded-[12px] text-xs font-semibold bg-green-500/[0.1] text-green-700 dark:bg-green-500/20 dark:text-green-300 hover:bg-green-500/20 dark:hover:bg-green-500/30 border border-green-500/20 transition-colors"
											>
												Present
											</button>
											<button
												@click="reconcileSingle(emp, 'Absent')"
												class="h-8 px-2.5 rounded-[12px] text-xs font-semibold bg-red-500/[0.08] text-red-700 dark:bg-red-500/15 dark:text-red-300 hover:bg-red-500/15 dark:hover:bg-red-500/25 border border-red-500/20 transition-colors"
											>
												Absent
											</button>
										</span>
									</td>
								</tr>
							</tbody>
						</table>
					</div>
				</div>

				<!-- Phone layout. One card per person, so the elapsed time and the
				     two buttons are on screen together - in the table they were
				     six columns apart and needed a sideways swipe. -->
				<div v-if="filteredEmployees.length" class="sm:hidden space-y-2.5">
					<label class="flex items-center gap-2.5 px-1 pb-1 cursor-pointer">
						<input
							type="checkbox"
							@change="toggleAllEmployees"
							:checked="selectedEmployees.length === filteredEmployees.length && filteredEmployees.length > 0"
							class="w-5 h-5 rounded accent-accent cursor-pointer"
						/>
						<span class="text-[13px] font-medium text-[#17181B] dark:text-white">Select all</span>
					</label>

					<div
						v-for="emp in filteredEmployees"
						:key="'card-' + emp.employee"
						class="inset-panel !p-3.5 space-y-3"
						:class="emp.forgot_to_clock_out ? '!border-red-500/25 !bg-red-500/[0.04]' : ''"
					>
						<div class="flex items-start gap-2.5">
							<!-- A 20px box with its own label target: a 16px tick is a
							     hard tap on glass. -->
							<input
								type="checkbox"
								:value="emp"
								v-model="selectedEmployees"
								class="w-5 h-5 rounded accent-accent cursor-pointer shrink-0 mt-0.5"
								:aria-label="'Select ' + emp.employee_name"
							/>
							<span class="avatar-chip !w-8 !h-8 shrink-0">{{ activeInitials(emp.employee_name) }}</span>
							<span class="min-w-0 flex-1">
								<span class="block text-[13px] font-medium text-[#17181B] dark:text-white leading-snug break-words">
									{{ emp.employee_name }}
								</span>
								<span class="block text-xs text-[#5C6169] dark:text-white/60 leading-snug break-words">
									{{ emp.employee }} · {{ emp.department || 'No department' }}
								</span>
							</span>
							<span
								class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold tabular-nums shrink-0"
								:class="emp.forgot_to_clock_out ? 'tag-red' : 'tag-emerald'"
							>
								{{ emp.elapsed_hours }}h
							</span>
						</div>

						<div class="flex items-center justify-between gap-3 text-xs">
							<span class="flex items-center gap-1.5 text-[#5C6169] dark:text-white/65 tabular-nums min-w-0">
								<span class="w-1.5 h-1.5 rounded-full bg-green-500 shrink-0"></span>
								<span class="truncate">In {{ formatTime(emp.checkin_time) }} · {{ emp.shift || 'Default shift' }}</span>
							</span>
							<span v-if="emp.forgot_to_clock_out" class="text-red-600 dark:text-red-400 shrink-0">No clock-out</span>
						</div>

						<div>
							<p class="status-label mb-1.5">Clock-out</p>
							<DateTimeField v-model="emp.checkout_time" />
						</div>

						<div class="grid grid-cols-2 gap-2">
							<button
								@click="reconcileSingle(emp, 'Present')"
								class="h-10 rounded-[12px] text-[13px] font-semibold bg-green-500/[0.1] text-green-700 dark:bg-green-500/20 dark:text-green-300 hover:bg-green-500/20 dark:hover:bg-green-500/30 border border-green-500/20 transition-colors"
							>
								Present
							</button>
							<button
								@click="reconcileSingle(emp, 'Absent')"
								class="h-10 rounded-[12px] text-[13px] font-semibold bg-red-500/[0.08] text-red-700 dark:bg-red-500/15 dark:text-red-300 hover:bg-red-500/15 dark:hover:bg-red-500/25 border border-red-500/20 transition-colors"
							>
								Absent
							</button>
						</div>
					</div>
				</div>
			</div>

			<!-- Footer -->
			<footer class="px-5 py-4 border-t border-black/[0.07] dark:border-white/10 shrink-0 space-y-3">
				<div v-if="errorMessage" class="inset-panel flex items-start gap-2.5 !border-red-500/25">
					<span class="material-symbols-outlined !text-[18px] text-red-500 dark:text-red-400 shrink-0">error</span>
					<p class="text-[13px] text-red-700 dark:text-red-300">{{ errorMessage }}</p>
				</div>

				<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
					<p class="text-[13px] text-[#5C6169] dark:text-white/65 tabular-nums">
						{{ selectedEmployees.length }} of {{ filteredEmployees.length }} selected
					</p>
					<div class="flex items-center gap-2">
						<button @click="close" class="btn-secondary">Close</button>
						<button
							@click="reconcileBulk('Present')"
							:disabled="submitting || selectedEmployees.length === 0"
							class="btn-primary"
						>
							<span v-if="submitting && bulkActionType === 'Present'" class="material-symbols-outlined !text-[18px] animate-spin">progress_activity</span>
							Mark present
						</button>
						<!-- The destructive half of the pair, so it keeps a red tone
						     rather than sharing the accent with Present. -->
						<button
							@click="reconcileBulk('Absent')"
							:disabled="submitting || selectedEmployees.length === 0"
							class="btn-primary !bg-red-600 hover:!bg-red-700"
						>
							<span v-if="submitting && bulkActionType === 'Absent'" class="material-symbols-outlined !text-[18px] animate-spin">progress_activity</span>
							Mark absent
						</button>
					</div>
				</div>
			</footer>
		</div>
	</div>
</template>


<script setup>
import { ask } from '@/utils/feedback.js'
import { ref, computed, watch } from "vue";
import { createResource } from "frappe-ui";
import { getErrorMessage } from "@/utils";
import DateTimeField from '../../../components/DateTimeField.vue'

/* Initials for the row avatar, two words at most so a long name cannot
   overflow the chip. */
function activeInitials(name) {
	return String(name || '?')
		.split(/\s+/)
		.filter(Boolean)
		.slice(0, 2)
		.map((w) => w[0].toUpperCase())
		.join('')
}

const props = defineProps({
	modelValue: Boolean,
});

const emit = defineEmits(["update:modelValue", "save-success"]);

const activeEmployeesList = ref([]);
const selectedEmployees = ref([]);
const loadingActiveEmployees = ref(false);
const submitting = ref(false);
const bulkActionType = ref("");
const errorMessage = ref("");
const searchQuery = ref("");

const getActiveEmployeesResource = createResource({
	url: "arijentek_core.api.attendance.get_active_sessions_for_reconciliation",
	auto: false,
});

const reconcileSessionsResource = createResource({
	url: "arijentek_core.api.attendance.reconcile_active_sessions",
	auto: false,
});

const filteredEmployees = computed(() => {
	if (!searchQuery.value) return activeEmployeesList.value;
	const query = searchQuery.value.toLowerCase().trim();
	return activeEmployeesList.value.filter(emp => 
		emp.employee_name.toLowerCase().includes(query) ||
		emp.employee.toLowerCase().includes(query) ||
		(emp.department && emp.department.toLowerCase().includes(query)) ||
		(emp.designation && emp.designation.toLowerCase().includes(query)) ||
		(emp.shift && emp.shift.toLowerCase().includes(query))
	);
});

const longHoursCount = computed(() => {
	return activeEmployeesList.value.filter(emp => emp.forgot_to_clock_out).length;
});

function close() {
	emit("update:modelValue", false);
}

async function fetchActiveEmployees() {
	errorMessage.value = "";
	loadingActiveEmployees.value = true;
	try {
		const res = await getActiveEmployeesResource.fetch();
		if (res) {
			activeEmployeesList.value = res.map(emp => ({
				...emp,
				checkout_time: ""
			}));
			selectedEmployees.value = [];
		}
	} catch (err) {
		console.error("Failed to load active employees", err);
		errorMessage.value = "Failed to load active employees: " + getErrorMessage(err);
	} finally {
		loadingActiveEmployees.value = false;
	}
}

function toggleAllEmployees(e) {
	if (e.target.checked) {
		selectedEmployees.value = [...filteredEmployees.value];
	} else {
		selectedEmployees.value = [];
	}
}

async function reconcileSingle(emp, status) {
	if (!emp.checkout_time) {
		errorMessage.value = `Clock-out time is mandatory for ${emp.employee_name}.`;
		return;
	}

	const confirmMsg = `Are you sure you want to mark ${emp.employee_name} as ${status}?\n\nOnly proceed if the employee forgot to clock out. Standard attendance entries are created automatically upon normal clock-out.`;
	if (!await ask(confirmMsg)) return;

	errorMessage.value = "";
	submitting.value = true;
	try {
		const payload = [{
			employee: emp.employee,
			date: emp.date,
			status: status,
			checkin_time: emp.checkin_time,
			checkout_time: emp.checkout_time,
			shift: emp.shift || null,
		}];

		await reconcileSessionsResource.fetch({
			data: JSON.stringify(payload),
		});

		emit("save-success");
		await fetchActiveEmployees();
	} catch (err) {
		errorMessage.value = "Failed to mark attendance for employee: " + getErrorMessage(err);
	} finally {
		submitting.value = false;
	}
}

async function reconcileBulk(status) {
	if (selectedEmployees.value.length === 0) return;

	const missing = selectedEmployees.value.filter(emp => !emp.checkout_time);
	if (missing.length > 0) {
		const names = missing.map(emp => emp.employee_name).join(", ");
		errorMessage.value = `Clock-out time is mandatory. Missing for: ${names}`;
		return;
	}

	const count = selectedEmployees.value.length;
	const confirmMsg = `Are you sure you want to mark the ${count} selected employee(s) as ${status}?\n\nOnly proceed for employees who forgot to clock out. Standard attendance entries are created automatically upon normal clock-out.`;
	if (!await ask(confirmMsg)) return;

	errorMessage.value = "";
	submitting.value = true;
	bulkActionType.value = status;
	try {
		const payload = selectedEmployees.value.map(emp => ({
			employee: emp.employee,
			date: emp.date,
			status: status,
			checkin_time: emp.checkin_time,
			checkout_time: emp.checkout_time,
			shift: emp.shift || null,
		}));

		await reconcileSessionsResource.fetch({
			data: JSON.stringify(payload),
		});

		emit("save-success");
		await fetchActiveEmployees();
	} catch (err) {
		errorMessage.value = "Failed to mark attendance for active employees: " + getErrorMessage(err);
	} finally {
		submitting.value = false;
		bulkActionType.value = "";
	}
}


function formatTime(timeStr) {
	if (!timeStr) return "";
	return new Date(timeStr).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: true });
}

function formatDate(timeStr) {
	if (!timeStr) return "";
	return new Date(timeStr).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}



watch(
	() => props.modelValue,
	newVal => {
		if (newVal) {
			fetchActiveEmployees();
		}
	}
);
</script>
