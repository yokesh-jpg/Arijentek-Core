<template>
	<Dialog :options="{ size: 'md' }" v-model="show">
		<template #body>
			<div class="modal-panel">
				<!-- Custom Header -->
				<header class="modal-header">
					<div>
						<h3 class="modal-title">{{ editId ? 'Edit leave period' : 'Add new leave period' }}</h3>
						<p class="text-[12px] text-[#656A72] dark:text-white/60">{{ editId ? editId : 'Fill in the leave period details below' }}</p>
					</div>
					<button @click="show = false" class="btn-icon-ghost shrink-0" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span>
					</button>
				</header>

				<!-- Main Content -->
				<div class="flex-1 px-5 py-5 overflow-y-auto flex flex-col gap-5">
					<div class="grid grid-cols-2 gap-4">
						<div class="flex flex-col gap-1.5">
							<label class="field-label">From date <span class="text-red-500 dark:text-red-400">*</span></label>
							<DateField v-model="formData.from_date" @change="handleFromDateChange" />
							<p v-if="errors.from_date" class="field-error">{{ errors.from_date }}</p>
						</div>

						<div class="flex flex-col gap-1.5">
							<label class="field-label">To date <span class="text-red-500 dark:text-red-400">*</span></label>
							<DateField v-model="formData.to_date" :min="formData.from_date" />
							<p v-if="errors.to_date" class="field-error">{{ errors.to_date }}</p>
						</div>
					</div>

					<div class="flex items-center gap-3">
						<input v-model="formData.is_active" type="checkbox" :true-value="1" :false-value="0" id="is_active" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40">
						<label for="is_active" class="text-[13px] text-[#17181B] dark:text-white cursor-pointer select-none">Is active</label>
					</div>
				</div>

				<!-- Actions -->
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
							:disabled="submitting"
						>
							<span v-if="submitting" class="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></span>
							{{ submitting ? 'Saving…' : 'Save leave period' }}
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
import { useLeaveStore } from '@/stores/leave';
import DateField from '../../../components/DateField.vue'

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

const show = computed({
	get: () => props.modelValue,
	set: (val) => emit('update:modelValue', val)
});

const leaveStore = useLeaveStore();

const getInitialFormData = () => ({
	from_date: '',
	to_date: '',
	is_active: 1
});

const formData = ref(getInitialFormData());

watch(show, async (newVal) => {
	if (newVal) {
		formData.value = getInitialFormData();
		errors.value = {};
		submitError.value = '';
		if (props.editId) {
			await fetchLeavePeriodDetails();
		}
	}
});

const fetchLeavePeriodDetails = async () => {
	try {
		const data = await call('arijentek_core.api.leave.get_leave_period', {
			name: props.editId
		});
		if (data) {
			formData.value = {
				name: data.name,
				from_date: data.from_date,
				to_date: data.to_date,
				is_active: data.is_active ? 1 : 0
			};
		}
	} catch (err) {
		submitError.value = getErrorMessage(err, 'Failed to fetch leave period details');
	}
};

const errors = ref({});
const submitError = ref('');
const submitting = ref(false);

const validate = () => {
	errors.value = {};
	let isValid = true;

	if (!formData.value.from_date) {
		errors.value.from_date = 'From Date is mandatory';
		isValid = false;
	}

	if (!formData.value.to_date) {
		errors.value.to_date = 'To Date is mandatory';
		isValid = false;
	}

	if (formData.value.from_date && formData.value.to_date && formData.value.from_date >= formData.value.to_date) {
		submitError.value = 'To Date must be greater than From Date.';
		isValid = false;
	}

	if (isValid && formData.value.is_active) {
		const activeLeave = leaveStore.leavePeriods.find(lp => lp.is_active && lp.name !== props.editId);
		if (activeLeave) {
			submitError.value = `There is already an active Leave Period (${activeLeave.name}). Please inactive it to continue.`;
			isValid = false;
		}
	}

	return isValid;
};

const handleFromDateChange = (val) => {
	const raw = typeof val === 'string' ? val : val?.target?.value || formData.value.from_date;
	if (!raw) return;
	const parts = String(raw).split('-').map(Number);
	if (parts.length !== 3 || parts.some(isNaN)) return;
	const [year, month, day] = parts;
	
	// Set exact 1 year after minus 1 day (e.g. 2026-01-01 to 2026-12-31)
	const date = new Date(year, month - 1, day);
	date.setFullYear(date.getFullYear() + 1);
	date.setDate(date.getDate() - 1);
	
	const y = date.getFullYear();
	const m = String(date.getMonth() + 1).padStart(2, '0');
	const d = String(date.getDate()).padStart(2, '0');
	formData.value.to_date = `${y}-${m}-${d}`;
};

const handleSave = async () => {
	submitError.value = '';
	if (validate()) {
		submitting.value = true;
		try {
			const res = await call('arijentek_core.api.leave.save_leave_period', { leave_period_data: formData.value });
			if (res && res.success === false) {
				submitError.value = getErrorMessage(res.error || res.message, 'Failed to save leave period');
			} else {
				emit('save', formData.value);
				show.value = false;
			}
		} catch (err) {
			submitError.value = getErrorMessage(err, 'Failed to save leave period');
		} finally {
			submitting.value = false;
		}
	}
};
</script>
