<template>
	<Dialog :options="{ size: 'xl' }" v-model="show">
		<template #body>
			<div class="modal-panel">
				<!-- Header -->
				<header class="modal-header">
					<div>
						<h3 class="modal-title">
							{{ editId ? 'Edit compensatory leave request' : 'Compensatory leave request' }}
						</h3>
						<p class="text-[12px] text-[#656A72] dark:text-white/60">
							{{ editId ? editId : 'For working on holidays or weekends' }}
						</p>
					</div>
					<button @click="show = false" class="btn-icon-ghost shrink-0" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span>
					</button>
				</header>

				<!-- Form Content -->
				<div v-if="noActivePeriodError" class="p-8 flex flex-col items-center justify-center text-center gap-4 py-12">
					<span class="material-symbols-outlined text-amber-500 text-5xl">warning</span>
					<p class="text-[#17181B] dark:text-white/80 font-semibold max-w-md">
						{{ noActivePeriodError }}
					</p>
				</div>
				<div v-else class="p-6 overflow-y-auto max-h-[60vh] flex flex-col gap-6">
					<!-- Employee -->
					<div class="flex flex-col gap-1.5">
						<label class="field-label">
							Employee <span class="text-red-500 dark:text-red-400">*</span>
						</label>
						<SearchableDropdown
							v-if="leaveStore.isApprover"
							v-model="formData.employee"
							:options="employeeOptions"
							labelKey="employee_name"
							valueKey="name"
							placeholder="Select employee"
						/>
						<input
							v-else
							:value="currEmployeeName"
							readonly
						 class="field-input"
						/>
						<p v-if="errors.employee" class="field-error">{{ errors.employee }}</p>
					</div>

					<!-- Leave Type -->
					<div class="flex flex-col gap-1.5">
						<label class="field-label">
							Leave type <span class="text-red-500 dark:text-red-400">*</span>
						</label>
						<SearchableDropdown
							v-model="formData.leave_type"
							:options="compLeaveTypes"
							placeholder="Select compensatory leave type"
						/>
						<p v-if="errors.leave_type" class="field-error">{{ errors.leave_type }}</p>
					</div>

					<!-- Holiday Worked On -->
					<div class="flex flex-col gap-1.5">
						<label class="field-label">
							Holiday worked on <span class="text-red-500 dark:text-red-400">*</span>
						</label>
						<SearchableDropdown
							v-model="formData.holiday_date"
							:options="availableHolidays"
							labelKey="label"
							valueKey="holiday_date"
							placeholder="Select holiday"
						/>
						<p v-if="errors.holiday_date" class="field-error">{{ errors.holiday_date }}</p>
					</div>

					<!-- Half Day -->
					<div class="flex items-center gap-3">
						<input
							type="checkbox"
							id="comp_half_day"
							v-model="formData.half_day"
							@change="onHalfDayToggle"
						 class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40"
						/>
						<label for="comp_half_day" class="field-label">Half day</label>
					</div>

					<!-- Half Day Date (Read-only) -->
					<div v-if="formData.half_day && formData.holiday_date" class="flex flex-col gap-1.5">
						<label class="field-label">
							Half day date
						</label>
						<input
							:value="formatDate(formData.holiday_date)"
							readonly
						 class="field-input"
						/>
					</div>

					<!-- Reason -->
					<div class="flex flex-col gap-1.5">
						<label class="field-label">
							Reason <span class="text-red-500 dark:text-red-400">*</span>
						</label>
						<textarea
							v-model="formData.reason"
							rows="3"
						 class="field-input"
							placeholder="Provide the holiday or weekend work details..."
						></textarea>
						<p v-if="errors.reason" class="field-error">{{ errors.reason }}</p>
					</div>
				</div>

				<!-- Footer Actions -->
				<div class="px-5 py-4 border-t border-black/[0.06] dark:border-white/[0.08] shrink-0">
					<p v-if="submitError" class="text-[13px] text-red-600 dark:text-red-400 mb-3">{{ submitError }}</p>
					<div class="flex justify-end gap-2">
						<button
						 class="btn-secondary"
							@click="show = false"
							:disabled="submitting"
						>
							Cancel
						</button>
						<button
						 class="btn-primary"
							@click="handleSave"
							:disabled="submitting || !canSubmit || !!noActivePeriodError"
						>
							<span v-if="submitting" class="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></span>
							{{ submitting ? 'Saving…' : 'Save request' }}
						</button>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { Dialog, call } from 'frappe-ui';
import { getErrorMessage } from '../../../utils.js';
import { useLeaveStore } from '../../../stores/leave';
import { useEmployeeStore } from '../../../stores/employee';
import SearchableDropdown from '../../../components/SearchableDropdown.vue';

const props = defineProps({
	modelValue: {
		type: Boolean,
		default: false
	},
	editId: {
		type: String,
		default: ''
	}
});

const emit = defineEmits(['update:modelValue', 'save']);

const leaveStore = useLeaveStore();
const employeeStore = useEmployeeStore();

const show = computed({
	get: () => props.modelValue,
	set: (val) => emit('update:modelValue', val)
});

const currEmployee = computed(() => employeeStore.employee?.name || '');
const currEmployeeName = computed(() => employeeStore.employee?.employee_name || '');

const employeeOptions = computed(() => {
	const opts = [];
	if (leaveStore.approvedEmployeeList) {
		leaveStore.approvedEmployeeList.forEach(emp => {
			opts.push({
				name: emp.name,
				employee_name: emp.employee_name
			});
		});
	}
	return opts;
});

const getInitialFormData = () => ({
	employee: '',
	leave_type: '',
	holiday_date: '',
	work_from_date: '',
	work_end_date: '',
	half_day: false,
	half_day_date: '',
	reason: ''
});

const formData = ref(getInitialFormData());
const noActivePeriodError = ref('');

const availableHolidays = computed(() => {
	const list = holidays.value.map(h => ({
		...h,
		label: `${formatDate(h.holiday_date)} - ${h.description || 'No Description'}`
	}));
	const currentDateVal = formData.value.holiday_date;
	if (currentDateVal && !list.some(h => h.holiday_date === currentDateVal)) {
		list.push({
			holiday_date: currentDateVal,
			description: 'Selected Holiday Date',
			label: `${formatDate(currentDateVal)} - Selected Holiday Date`
		});
	}
	return list;
});

const canSubmit = computed(() => {
	const base = formData.value.leave_type && formData.value.holiday_date && formData.value.reason;
	if (!base) return false;
	if (formData.value.half_day) return !!formData.value.half_day_date;
	return true;
});

const errors = ref({});
const submitError = ref('');
const submitting = ref(false);
const compLeaveTypes = ref([]);
const holidays = ref([]);

const checkActivePeriod = async () => {
	noActivePeriodError.value = '';
	if (!leaveStore.leavePeriods.length) {
		await leaveStore.fetchLeavePeriods();
	}
	const active = leaveStore.leavePeriods.find(lp => lp.is_active === 1 || lp.is_active === true);
	if (!active && !props.editId) {
		noActivePeriodError.value = 'There is no active leave period created. Contact HR to create a leave period.';
	}
};

watch(show, async (newVal) => {
	if (newVal) {
		formData.value = getInitialFormData();
		errors.value = {};
		submitError.value = '';
		noActivePeriodError.value = '';

		if (currEmployee.value) {
			formData.value.employee = currEmployee.value;
		}

		await checkActivePeriod();
		await fetchCompLeaveTypes();

		if (props.editId) {
			await fetchDetails();
		}
	}
});

watch(
	() => formData.value.employee,
	(employee_id) => {
		if (employee_id) {
			fetchHolidays(employee_id);
		}
	}
);

watch(
	() => formData.value.holiday_date,
	(selectedDate) => {
		if (selectedDate) {
			formData.value.work_from_date = selectedDate;
			formData.value.work_end_date = selectedDate;
			if (formData.value.half_day) {
				formData.value.half_day_date = selectedDate;
			}
		} else {
			formData.value.work_from_date = '';
			formData.value.work_end_date = '';
			formData.value.half_day_date = '';
		}
	}
);

async function fetchCompLeaveTypes() {
	try {
		const data = await call('arijentek_core.api.leave.get_compensatory_leave_types');
		compLeaveTypes.value = data || [];
		if (data && data.length > 0 && !formData.value.leave_type) {
			formData.value.leave_type = data[0];
		}
	} catch (err) {
		compLeaveTypes.value = [];
	}
}

async function fetchHolidays(employee_id) {
	try {
		const data = await call('arijentek_core.api.leave.get_holidays_for_employee', { employee: employee_id });
		holidays.value = data || [];
	} catch (err) {
		holidays.value = [];
	}
}

async function fetchDetails() {
	try {
		const data = await call('arijentek_core.api.leave.get_compensatory_leave_requests', {
			employee: formData.value.employee
		});
		const record = data?.find(r => r.name === props.editId);
		if (record) {
			formData.value = {
				employee: record.employee,
				leave_type: record.leave_type,
				holiday_date: record.work_from_date,
				work_from_date: record.work_from_date,
				work_end_date: record.work_end_date,
				half_day: record.half_day === 1 || record.half_day === true,
				half_day_date: record.half_day_date || '',
				reason: record.reason || ''
			};
		}
	} catch (err) {
		submitError.value = getErrorMessage(err, 'Failed to fetch request details');
	}
}

function onHalfDayToggle() {
	if (formData.value.half_day) {
		formData.value.half_day_date = formData.value.holiday_date;
	} else {
		formData.value.half_day_date = '';
	}
}

function formatDate(dateStr) {
	if (!dateStr) return '';
	return new Date(dateStr).toLocaleDateString('en-US', {
		month: 'short',
		day: 'numeric',
		year: 'numeric'
	});
}

function validate() {
	errors.value = {};
	let isValid = true;

	if (!formData.value.employee) {
		errors.value.employee = 'Employee is required';
		isValid = false;
	}
	if (!formData.value.leave_type) {
		errors.value.leave_type = 'Leave Type is required';
		isValid = false;
	}
	if (!formData.value.holiday_date) {
		errors.value.holiday_date = 'Holiday Worked On is required';
		isValid = false;
	}
	if (!formData.value.reason) {
		errors.value.reason = 'Reason is required';
		isValid = false;
	}

	return isValid;
}

async function handleSave() {
	submitError.value = '';
	if (!validate()) return;

	submitting.value = true;
	try {
		const payload = {
			employee: formData.value.employee || currEmployee.value,
			leave_type: formData.value.leave_type,
			work_from_date: formData.value.work_from_date,
			work_end_date: formData.value.work_end_date,
			half_day: formData.value.half_day ? 1 : 0,
			half_day_date: formData.value.half_day ? formData.value.half_day_date : null,
			reason: formData.value.reason
		};

		let result;
		if (props.editId) {
			payload.name = props.editId;
			result = await call('arijentek_core.api.leave.update_compensatory_leave_request', payload);
		} else {
			result = await call('arijentek_core.api.leave.create_compensatory_leave_request', payload);
		}

		if (result && result.success === false) {
			submitError.value = result.error || 'Failed to save request';
		} else {
			emit('save', result);
			show.value = false;
		}
	} catch (err) {
		submitError.value = getErrorMessage(err, 'Failed to save request');
	} finally {
		submitting.value = false;
	}
}
</script>
