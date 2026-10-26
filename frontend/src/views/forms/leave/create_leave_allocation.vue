<template>
	<Dialog :options="{ size: 'xl' }" v-model="show">
		<template #body>
			<div class="modal-panel">
				<!-- Custom Header -->
				<header class="modal-header">
					<div>
						<h3 class="modal-title">{{ editId ? 'Edit leave allocation' : 'Add new leave allocation' }}</h3>
						<p class="text-[12px] text-[#656A72] dark:text-white/60">{{ editId ? editId : 'Fill in the leave allocation details below' }}</p>
					</div>
					<button @click="show = false" class="btn-icon-ghost shrink-0" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span>
					</button>
				</header>

				<!-- Main Content -->
				<div v-if="noActivePeriodError" class="p-8 flex flex-col items-center justify-center text-center gap-4 py-12">
					<span class="material-symbols-outlined text-amber-500 text-5xl">warning</span>
					<p class="text-[#17181B] dark:text-white/80 font-semibold max-w-md">
						{{ noActivePeriodError }}
					</p>
				</div>
				<div v-else class="p-6 overflow-y-auto max-h-[70vh] flex flex-col gap-6">
					
					<div class="flex flex-col gap-1.5">
						<label class="field-label">Employee <span class="text-red-500 dark:text-red-400">*</span></label>
						<SearchableDropdown
							v-model="formData.employee"
							:options="leaveStore.employeeList"
							labelKey="employee_name"
							valueKey="name"
							placeholder="Select employee"
							:disabled="!!editId"
						/>
						<p v-if="errors.employee" class="field-error">{{ errors.employee }}</p>
					</div>

					<div class="flex flex-col gap-1.5">
						<label class="field-label">Leave type <span class="text-red-500 dark:text-red-400">*</span></label>
						<SearchableDropdown
							v-model="formData.leave_type"
							:options="leaveStore.allLeaveTypesList"
							labelKey="leave_type_name"
							valueKey="name"
							placeholder="Select leave type"
						/>
						<p v-if="errors.leave_type" class="field-error">{{ errors.leave_type }}</p>
					</div>

					<div class="flex flex-col gap-1.5">
						<label class="field-label">New leaves allocated <span class="text-red-500 dark:text-red-400">*</span></label>
						<input v-model.number="formData.new_leaves_allocated" type="number" min="0" step="0.5" class="field-input" placeholder="0">
						<p v-if="errors.new_leaves_allocated" class="field-error">{{ errors.new_leaves_allocated }}</p>
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
							:disabled="submitting || !!noActivePeriodError"
						>
							<span v-if="submitting" class="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></span>
							{{ submitting ? 'Saving…' : 'Save leave allocation' }}
						</button>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { Dialog, call } from 'frappe-ui';
import { getErrorMessage } from '../../../utils.js';
import { useLeaveStore } from '../../../stores/leave';
import SearchableDropdown from '@/components/SearchableDropdown.vue';

const leaveStore = useLeaveStore();

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

const getInitialFormData = () => ({
	employee: '',
	leave_type: '',
	from_date: '',
	to_date: '',
	new_leaves_allocated: '',
	leave_period: '',
	description: ''
});

const formData = ref(getInitialFormData());
const errors = ref({});
const submitError = ref('');
const submitting = ref(false);

onMounted(() => {
	leaveStore.fetchEmployeeList();
	leaveStore.fetchAllLeaveTypes();
	leaveStore.fetchLeavePeriods();
});

const activeLeavePeriod = ref(null);
const noActivePeriodError = ref('');

const fetchActivePeriod = async () => {
	noActivePeriodError.value = '';
	activeLeavePeriod.value = null;
	
	if (!leaveStore.leavePeriods.length) {
		await leaveStore.fetchLeavePeriods();
	}
	
	const active = leaveStore.leavePeriods.find(lp => lp.is_active === 1 || lp.is_active === true);
	if (active) {
		activeLeavePeriod.value = active;
		formData.value.from_date = active.from_date;
		formData.value.to_date = active.to_date;
		formData.value.leave_period = active.name;
	} else if (!props.editId) {
		noActivePeriodError.value = 'There is no active leave period created. Contact HR to create a leave period.';
	}
};

watch(show, async (newVal) => {
	if (newVal) {
		formData.value = getInitialFormData();
		errors.value = {};
		submitError.value = '';
		
		// Ensure lists are fetched if not yet available
		if (!leaveStore.employeeList.length) leaveStore.fetchEmployeeList();
		if (!leaveStore.allLeaveTypesList.length) leaveStore.fetchAllLeaveTypes();
		
		await fetchActivePeriod();

		if (props.editId) {
			await fetchLeaveAllocationDetails();
		}
	}
});

const fetchLeaveAllocationDetails = async () => {
	try {
		const doc = await call('arijentek_core.api.leave.get_leave_allocations', {
			name: props.editId
		});
		if (doc && doc.name) {
			formData.value = {
				name: doc.name,
				employee: doc.employee,
				leave_type: doc.leave_type,
				from_date: doc.from_date,
				to_date: doc.to_date,
				new_leaves_allocated: doc.new_leaves_allocated,
				leave_period: doc.leave_period || '',
				description: doc.description || ''
			};
		}
	} catch (err) {
		submitError.value = getErrorMessage(err, 'Failed to fetch leave allocation details');
	}
};

const validate = () => {
	errors.value = {};
	let isValid = true;

	if (!formData.value.employee) {
		errors.value.employee = 'Employee is mandatory';
		isValid = false;
	}

	if (!formData.value.leave_type) {
		errors.value.leave_type = 'Leave Type is mandatory';
		isValid = false;
	}

	if (!formData.value.from_date) {
		errors.value.from_date = 'From Date is mandatory';
		isValid = false;
	}

	if (!formData.value.to_date) {
		errors.value.to_date = 'To Date is mandatory';
		isValid = false;
	}
	
	if (formData.value.new_leaves_allocated === '' || formData.value.new_leaves_allocated === null) {
		errors.value.new_leaves_allocated = 'Allocation amount is mandatory';
		isValid = false;
	} else if (parseFloat(formData.value.new_leaves_allocated) < 0) {
		errors.value.new_leaves_allocated = 'Allocation cannot be negative';
		isValid = false;
	}

	if (formData.value.from_date && formData.value.to_date && formData.value.from_date >= formData.value.to_date) {
		submitError.value = 'To Date must be greater than From Date.';
		isValid = false;
	}

	return isValid;
};

// Deprecated as from_date is auto-populated and hidden
const handleFromDateChange = (e) => {};

const handleSave = async () => {
	submitError.value = '';
	if (validate()) {
		submitting.value = true;
		try {
			const res = await call('arijentek_core.api.leave.save_leave_allocation', { leave_allocation_data: formData.value });
			if (res && res.success === false) {
				submitError.value = getErrorMessage(res.error || res.message, 'Failed to save leave allocation');
			} else {
				emit('save', formData.value);
				show.value = false;
			}
		} catch (err) {
			submitError.value = getErrorMessage(err, 'Failed to save leave allocation');
		} finally {
			submitting.value = false;
		}
	}
};
</script>
