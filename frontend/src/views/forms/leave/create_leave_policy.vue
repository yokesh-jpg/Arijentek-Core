<template>
	<Dialog :options="{ size: 'xl' }" v-model="show">
		<template #body>
			<div class="modal-panel">
				<!-- Custom Header -->
				<header class="modal-header">
					<div>
						<h3 class="modal-title">{{ editId ? 'Edit leave policy' : 'Add new leave policy' }}</h3>
						<p class="text-[12px] text-[#656A72] dark:text-white/60">{{ editId ? editId : 'Fill in the leave policy details below' }}</p>
					</div>
					<button @click="show = false" class="btn-icon-ghost shrink-0" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span>
					</button>
				</header>

				<!-- Main Content -->
				<div class="flex-1 px-5 py-5 overflow-y-auto flex flex-col gap-5">
					<div class="flex flex-col gap-1.5">
						<label class="field-label">Title <span class="text-red-500 dark:text-red-400">*</span></label>
						<input v-model="formData.title" type="text" class="field-input" placeholder="e.g. 2024 Leave Policy">
						<p v-if="errors.title" class="field-error">{{ errors.title }}</p>
					</div>

					<!-- Leave Policy Details Table -->
					<div class="flex flex-col gap-2 border border-black/[0.07] dark:border-white/10 rounded-[12px] p-4 bg-white dark:bg-black/10">
						<h3 class="text-sm font-semibold text-[#17181B] dark:text-white/80 mb-2">Leave Allocations</h3>
						<div class="overflow-visible">
							<table class="w-full text-left border-collapse min-w-[400px]">
								<thead class="border-b border-black/[0.07] dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02]">
									<tr>
										<th class="table-th w-1/2">Leave type</th>
										<th class="table-th text-right w-1/3">Annual allocation</th>
										<th class="table-th text-right w-16"></th>
									</tr>
								</thead>
								<tbody class="divide-y divide-black/[0.05] dark:divide-white/[0.06]">
									<tr v-for="(row, index) in formData.leave_policy_details" :key="index" class="hover:bg-black/[0.03] dark:hover:bg-white/[0.01]">
										<td class="px-4 py-2">
											<div class="flex items-center gap-2">
												<div class="flex-1">
													<SearchableDropdown
														v-model="row.leave_type"
														:options="leaveStore.allLeaveTypesList"
														labelKey="leave_type_name"
														valueKey="name"
														placeholder="Select leave type"
														:disabled="formData.is_used"
													/>
												</div>
												<button 
													v-if="leaveStore.canCreateLeaveTypes && !formData.is_used"
													@click="showCreateLeaveTypeModal = true" type="button" class="btn-add-option" title="Add a new leave type" aria-label="Add a new leave type"><span class="material-symbols-outlined !text-[18px]">add</span></button>
											</div>
										</td>
										<td class="px-4 py-2">
											<input v-model.number="row.annual_allocation" type="number" min="0" step="0.5" class="field-input" placeholder="0" :disabled="formData.is_used">
										</td>
										<td class="px-4 py-2 text-right">
											<button v-if="!formData.is_used" @click="removeRow(index)" class="p-1.5 text-[#656A72] dark:text-white/60 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 rounded-[12px] transition-colors" title="Remove">
												<span class="material-symbols-outlined text-[18px]">delete</span>
											</button>
										</td>
									</tr>
									<tr v-if="!formData.leave_policy_details.length">
										<td colspan="3" class="px-4 py-6 text-center text-sm text-[#5C6169] dark:text-white/65 font-medium">
											No leave allocations added yet.
										</td>
									</tr>
								</tbody>
							</table>
						</div>
						
						<!-- Add Row Button at Bottom Left -->
						<div class="mt-2" v-if="!formData.is_used">
							<button
								type="button"
								@click="addRow"
								class="btn-secondary"
							>
								<span class="material-symbols-outlined text-sm">add</span>
								Add Row
							</button>
						</div>
					</div>
				</div>

				<!-- Actions -->
				<div class="px-5 py-4 border-t border-black/[0.06] dark:border-white/[0.08] shrink-0">
					<p v-if="formData.is_used" class="text-xs text-amber-600 dark:text-amber-400 font-medium text-center mb-4">This Leave Policy is already assigned to employees. You can only modify its Title.</p>
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
							{{ submitting ? 'Saving…' : 'Save leave policy' }}
						</button>
					</div>
				</div>
			</div>
		</template>
	</Dialog>

	<CreateLeaveTypes 
		v-model="showCreateLeaveTypeModal" 
		@save="onLeaveTypeSaved" 
	/>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { Dialog, call } from 'frappe-ui';
import { getErrorMessage } from '../../../utils.js';
import { useLeaveStore } from '../../../stores/leave';
import SearchableDropdown from '@/components/SearchableDropdown.vue';
import CreateLeaveTypes from './create_leave_types.vue';

const leaveStore = useLeaveStore();

const showCreateLeaveTypeModal = ref(false);

const onLeaveTypeSaved = async (savedData) => {
	await leaveStore.fetchAllLeaveTypes();
	// Optionally we could try to auto-select the new one, but for now just refresh the list.
};

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
	title: '',
	is_used: false,
	leave_policy_details: [
		{ leave_type: '', annual_allocation: 0 }
	]
});

const addRow = () => {
	formData.value.leave_policy_details.push({
		leave_type: '',
		annual_allocation: 0
	});
};

const removeRow = (index) => {
	formData.value.leave_policy_details.splice(index, 1);
};

const formData = ref(getInitialFormData());

watch(show, async (newVal) => {
	if (newVal) {
		formData.value = getInitialFormData();
		errors.value = {};
		submitError.value = '';
		if (props.editId) {
			await fetchLeavePolicyDetails();
		}
	}
});

const fetchLeavePolicyDetails = async () => {
	try {
		const data = await call('arijentek_core.api.leave.get_leave_policy', {
			name: props.editId
		});
		if (data) {
			formData.value = {
				name: data.name,
				title: data.title,
				is_used: data.is_used || false,
				leave_policy_details: (data.leave_policy_details || []).map(d => ({
					name: d.name,
					leave_type: d.leave_type,
					annual_allocation: d.annual_allocation
				}))
			};
		}
	} catch (err) {
		submitError.value = getErrorMessage(err, 'Failed to fetch leave policy details');
	}
};

const errors = ref({});
const submitError = ref('');
const submitting = ref(false);

const validate = () => {
	errors.value = {};
	let isValid = true;

	if (!formData.value.title) {
		errors.value.title = 'Title is mandatory';
		isValid = false;
	}
	
	if (!formData.value.leave_policy_details.length) {
		submitError.value = 'At least one Leave Type allocation is required.';
		isValid = false;
		return isValid;
	}
	
	const types = new Set();
	for (const row of formData.value.leave_policy_details) {
		if (!row.leave_type) {
			submitError.value = 'All rows must have a Leave Type selected.';
			isValid = false;
			break;
		}
		if (types.has(row.leave_type)) {
			submitError.value = `Leave Type '${row.leave_type}' appears multiple times.`;
			isValid = false;
			break;
		}
		types.add(row.leave_type);
	}

	return isValid;
};

const handleSave = async () => {
	submitError.value = '';
	if (validate()) {
		submitting.value = true;
		try {
			const res = await call('arijentek_core.api.leave.save_leave_policy', { leave_policy_data: formData.value });
			if (res && res.success === false) {
				submitError.value = getErrorMessage(res.error || res.message, 'Failed to save leave policy');
			} else {
				emit('save', formData.value);
				show.value = false;
			}
		} catch (err) {
			submitError.value = getErrorMessage(err, 'Failed to save leave policy');
		} finally {
			submitting.value = false;
		}
	}
};
</script>
