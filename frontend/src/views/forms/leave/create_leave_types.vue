<template>
	<Dialog :options="{ size: 'md' }" v-model="show">
		<template #body>
			<div class="modal-panel">
				<!-- Custom Header -->
				<header class="modal-header">
					<div>
						<h3 class="modal-title">{{ editId ? 'Edit leave type' : 'Add new leave type' }}</h3>
						<p class="text-[12px] text-[#656A72] dark:text-white/60">{{ editId ? editId : 'Fill in the leave type details below' }}</p>
					</div>
					<button @click="show = false" class="btn-icon-ghost shrink-0" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span>
					</button>
				</header>

				<!-- Main Content -->
				<div class="flex-1 px-5 py-5 overflow-y-auto flex flex-col gap-5">
					<div class="flex flex-col gap-1.5">
						<label class="field-label">Leave type <span class="text-red-500 dark:text-red-400">*</span></label>
						<input v-model="formData.leave_type_name" type="text" class="field-input" placeholder="e.g. Casual Leave">
						<p v-if="errors.leave_type_name" class="field-error">{{ errors.leave_type_name }}</p>
					</div>
					
					<div class="flex items-center gap-3">
						<input v-model="formData.is_lwp" type="checkbox" :true-value="1" :false-value="0" id="is_lwp" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40">
						<label for="is_lwp" class="text-[13px] text-[#17181B] dark:text-white cursor-pointer select-none">Is loss of pay</label>
					</div>

					<div class="flex items-center gap-3">
						<input v-model="formData.is_compensatory" type="checkbox" :true-value="1" :false-value="0" id="is_compensatory" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40">
						<label for="is_compensatory" class="text-[13px] text-[#17181B] dark:text-white cursor-pointer select-none">Is compensatory off</label>
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
							{{ submitting ? 'Saving…' : 'Save leave type' }}
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
	leave_type_name: '',
	is_lwp: 0,
	is_compensatory: 0
});

const formData = ref(getInitialFormData());

watch(show, async (newVal) => {
	if (newVal) {
		formData.value = getInitialFormData();
		errors.value = {};
		submitError.value = '';
		if (props.editId) {
			await fetchLeaveTypeDetails();
		}
	}
});

const fetchLeaveTypeDetails = async () => {
	try {
		const data = await call('arijentek_core.api.leave.get_leave_type', {
			name: props.editId
		});
		if (data) {
			formData.value = {
				name: data.name,
				leave_type_name: data.leave_type_name,
				is_lwp: data.is_lwp ? 1 : 0,
				is_compensatory: data.is_compensatory ? 1 : 0
			};
		}
	} catch (err) {
		submitError.value = getErrorMessage(err, 'Failed to fetch leave type details');
	}
};

watch(() => formData.value.is_lwp, (val) => {
	if (val) formData.value.is_compensatory = 0;
});

watch(() => formData.value.is_compensatory, (val) => {
	if (val) formData.value.is_lwp = 0;
});

const errors = ref({});
const submitError = ref('');
const submitting = ref(false);

const validate = () => {
	errors.value = {};
	let isValid = true;

	if (!formData.value.leave_type_name) {
		errors.value.leave_type_name = 'Leave Type is mandatory';
		isValid = false;
	}
	
	if (formData.value.is_lwp && formData.value.is_compensatory) {
		submitError.value = 'A leave type cannot be both Loss of Pay and Compensatory Off.';
		isValid = false;
	}

	return isValid;
};

const handleSave = async () => {
	submitError.value = '';
	if (validate()) {
		submitting.value = true;
		try {
			const res = await call('arijentek_core.api.leave.save_leave_type', { leave_type_data: formData.value });
			if (res && res.success === false) {
				submitError.value = getErrorMessage(res.error || res.message, 'Failed to save leave type');
			} else {
				emit('save', formData.value);
				show.value = false;
			}
		} catch (err) {
			submitError.value = getErrorMessage(err, 'Failed to save leave type');
		} finally {
			submitting.value = false;
		}
	}
};
</script>
