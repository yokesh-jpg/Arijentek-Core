<template>
	<Teleport to="body">
		<Transition name="fade">
			<div
				v-if="show"
				class="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6"
			>
				<div
					class="absolute inset-0 bg-black/40 backdrop-blur-sm"
					@click="show = false"
				></div>
				<div
					class="relative flex flex-col bg-white dark:bg-surface-1 sm:rounded-[12px] overflow-hidden max-h-[90vh] shadow-2xl w-full max-w-xl"
				>
					<!-- Header -->
					<header class="modal-header">
						<div>
							<h3 class="modal-title">
								{{ editId ? 'Edit leave application' : 'Request leave' }}
							</h3>
							<p class="text-[12px] text-[#656A72] dark:text-white/60">
								{{ editId ? editId : 'Application for absence' }}
							</p>
						</div>
						<button @click="show = false" class="btn-icon-ghost shrink-0" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span>
						</button>
					</header>

					<!-- Form Content -->
					<div v-if="loadingDetails" class="flex-1 px-5 py-16 flex flex-col items-center justify-center gap-3">
						<span class="w-6 h-6 rounded-full border-2 border-black/10 dark:border-white/15 border-t-accent animate-spin"></span>
						<p class="text-xs text-[#5C6169] dark:text-white/60">Loading application details…</p>
					</div>
					<div v-else class="flex-1 px-5 py-5 overflow-y-auto flex flex-col gap-5">
						<!-- Employee -->
						<div class="flex flex-col gap-1.5">
							<label class="field-label">
								Employee <span class="text-red-500 dark:text-red-400">*</span>
							</label>
							<SearchableDropdown
								v-if="leaveStore.isApprover"
								v-model="formData.employee"
								:options="approvedEmployeeOptions"
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

						<!-- Leave Type + Balance -->
						<div class="flex flex-col gap-1.5">
							<div class="flex justify-between items-baseline">
								<label class="field-label">
									Leave type <span class="text-red-500 dark:text-red-400">*</span>
								</label>
								<span v-if="selectedBalanceLabel" class="text-xs font-semibold text-[#5C6169] dark:text-white/65 ">
									Available: {{ selectedBalanceLabel }}
								</span>
							</div>
							<SearchableDropdown
								v-model="formData.leave_type"
								:options="availableLeaveTypes"
								labelKey="name"
								valueKey="name"
								placeholder="Select leave type"
							/>
							<p v-if="errors.leave_type" class="field-error">{{ errors.leave_type }}</p>
						</div>

						<!-- Leave Approver -->
						<div v-if="formData.leave_approver" class="flex flex-col gap-1.5">
							<label class="field-label">
								Leave approver
							</label>
							<input
								type="text"
								:value="formData.leave_approver"
								readonly
							 class="field-input"
							/>
						</div>

						<!-- From Date + To Date -->
						<div class="grid grid-cols-2 gap-4">
							<div class="flex flex-col gap-1.5">
								<label class="field-label">
									From date <span class="text-red-500 dark:text-red-400">*</span>
								</label>
								<DateField v-model="formData.from_date" />
								<p v-if="errors.from_date" class="field-error">{{ errors.from_date }}</p>
							</div>
							<div v-if="!formData.half_day" class="flex flex-col gap-1.5">
								<label class="field-label">
									To date <span class="text-red-500 dark:text-red-400">*</span>
								</label>
								<DateField v-model="formData.to_date" :min="formData.from_date" />
								<p v-if="errors.to_date" class="field-error">{{ errors.to_date }}</p>
							</div>
						</div>

						<!-- Leave Duration Summary & Multi-year Alert -->
						<div v-if="totalDays > 0" class="flex items-center justify-between px-3 py-2 rounded-[10px] bg-black/[0.03] dark:bg-white/[0.05] border border-black/[0.06] dark:border-white/[0.08] text-xs">
							<span class="text-[#5C6169] dark:text-white/70 font-medium">Requested duration:</span>
							<div class="flex items-center gap-2">
								<span class="font-bold text-[#17181B] dark:text-white">{{ totalDays }} {{ totalDays === 1 ? 'Day' : 'Days' }}</span>
								<span v-if="isCrossYear" class="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">
									Multi-year ({{ formData.from_date.slice(0, 4) }} – {{ formData.to_date.slice(0, 4) }})
								</span>
							</div>
						</div>

						<!-- Half Day -->
						<div class="flex items-center gap-3">
							<input
								type="checkbox"
								id="half_day"
								v-model="formData.half_day"
								@change="onHalfDayToggle"
							 class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40"
							/>
							<label for="half_day" class="field-label">Half day</label>
						</div>

						<!-- Status (only for approvers) -->
						<div v-if="leaveStore.isApprover" class="flex flex-col gap-1.5">
							<label class="field-label">
								Status
							</label>
							<SearchableDropdown
								v-model="formData.status"
								:options="statusOptions"
								placeholder="Select status"
							/>
						</div>

						<!-- Reason -->
						<div class="flex flex-col gap-1.5">
							<label class="field-label">
								Reason
							</label>
							<textarea
								v-model="formData.description"
								rows="3"
							 class="field-input"
								placeholder="Brief explanation for the request..."
							></textarea>
						</div>
						
						<!-- Attachments -->
						<div class="border-t border-black/[0.07] dark:border-white/10 pt-6 mt-2">
							<div class="flex items-center justify-between mb-4">
								<p class="status-label">Attachments</p>
								<button type="button" @click="$refs.fileInput.click()" class="btn-secondary !h-9">
									<span class="material-symbols-outlined !text-[18px]">attach_file</span>
									Add files
								</button>
								<input type="file" multiple class="hidden" ref="fileInput" @change="onFilesSelected" />
							</div>

							<div v-if="attachments.length > 0" class="flex flex-col gap-2">
								<div v-for="(file, index) in attachments" :key="index" class="flex items-center justify-between px-3 py-2 bg-black/[0.02] dark:bg-black/20 border border-black/[0.07] dark:border-white/10 rounded-[12px]">
									<div class="flex items-center gap-2 overflow-hidden">
										<span class="material-symbols-outlined text-[#656A72] dark:text-white/60 text-lg shrink-0">description</span>
										<span class="text-xs font-semibold text-[#17181B] dark:text-white/80 truncate">{{ file.file_name || file.name }}</span>
									</div>
									<div class="flex items-center gap-3 shrink-0">
										<span v-if="file.isExisting" class="text-xs font-semibold text-[#656A72] dark:text-white/60 ">Saved</span>
										<button type="button" @click="removeAttachment(index)" class="text-red-400 hover:text-red-600 dark:text-red-400 dark:hover:text-red-400 p-1 rounded-[6px] hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors" title="Remove Attachment">
											<span class="material-symbols-outlined text-[16px]">delete</span>
										</button>
									</div>
								</div>
							</div>
							<div v-else class="text-center py-6 bg-black/[0.02] dark:bg-black/20 border border-dashed border-black/[0.07] dark:border-white/10 rounded-[12px]">
								<p class="text-xs font-medium text-[#656A72] dark:text-white/60">No attachments added yet.</p>
							</div>
						</div>
					</div>

					<!-- Footer Actions -->
					<div class="px-5 py-4 border-t border-black/[0.06] dark:border-white/[0.08] shrink-0">
						<p v-if="submitError" class="text-[13px] text-red-600 dark:text-red-400 mb-3">{{ submitError }}</p>
						<div class="flex justify-end gap-2">
							<button
							 class="btn-secondary"
								@click="show = false"
								:disabled="submitting || loadingDetails"
							>
								Cancel
							</button>
							<button
								class="btn-primary"
								@click="handleSave"
								:disabled="submitting || loadingDetails || !canSubmit"
							>
								<span v-if="submitting" class="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></span>
								{{ submitting ? (editId ? 'Saving…' : 'Submitting…') : (editId ? 'Save changes' : 'Submit request') }}
							</button>
						</div>
					</div>
				</div>
			</div>
		</Transition>
	</Teleport>
</template>

<script setup>
import { notify, ask } from '@/utils/feedback.js'
import { ref, computed, watch } from 'vue';
import { Dialog, call, createResource } from 'frappe-ui';
import { getErrorMessage } from '../../../utils.js';
import { useLeaveStore } from '../../../stores/leave';
import { useEmployeeStore } from '../../../stores/employee';
import SearchableDropdown from '../../../components/SearchableDropdown.vue';
import DateField from '../../../components/DateField.vue'

const props = defineProps({
	modelValue: { type: Boolean, default: false },
	editId: { type: String, default: '' },
});

const emit = defineEmits(['update:modelValue', 'save']);

const leaveStore = useLeaveStore();
const employeeStore = useEmployeeStore();

const show = computed({
	get: () => props.modelValue,
	set: (val) => emit('update:modelValue', val),
});

const currEmployee = computed(() => employeeStore.employee?.name || '');
const currEmployeeName = computed(() => {
	if (formData.value.employee_name) return formData.value.employee_name;
	if (formData.value.employee && leaveStore.approvedEmployeeList?.length) {
		const match = leaveStore.approvedEmployeeList.find(e => e.name === formData.value.employee);
		if (match?.employee_name) return match.employee_name;
	}
	return employeeStore.employee?.employee_name || '';
});

const approvedEmployeeOptions = computed(() => {
	const list = leaveStore.approvedEmployeeList || [];
	const empId = formData.value.employee;
	if (empId && !list.some(e => e.name === empId)) {
		return [...list, { name: empId, employee_name: formData.value.employee_name || empId }];
	}
	return list;
});

const getInitialFormData = () => ({
	employee: '',
	employee_name: '',
	leave_type: '',
	from_date: '',
	to_date: '',
	half_day: false,
	leave_approver: '',
	status: 'Open',
	description: '',
});

const formData = ref(getInitialFormData());
const errors = ref({});
const submitError = ref('');
const submitting = ref(false);
const loadingDetails = ref(false);

const fileInput = ref(null);
const attachments = ref([]);

const statusOptions = ref([]);

async function initializeForm() {
	formData.value = getInitialFormData();
	errors.value = {};
	submitError.value = '';
	attachments.value = [];

	// Fetch status options
	try {
		const opts = await call('arijentek_core.api.leave.get_leave_status_options');
		statusOptions.value = opts || [];
	} catch (e) {
		statusOptions.value = [];
	}

	if (props.editId) {
		loadingDetails.value = true;
		try {
			await fetchLeaveApplicationDetails();
			await fetchAttachments();
		} finally {
			loadingDetails.value = false;
		}
	} else {
		// Set employee for new request
		if (currEmployee.value) {
			formData.value.employee = currEmployee.value;
			formData.value.employee_name = employeeStore.employee?.employee_name || '';
			fetchApprovalDetails(currEmployee.value);
		}

		// Fetch leave types for employee
		if (formData.value.employee) {
			await leaveStore.fetchLeaveTypes(formData.value.employee);
		}
	}
}

async function fetchLeaveApplicationDetails() {
	if (!props.editId) return;
	try {
		const appData = await call('arijentek_core.api.leave.get_leave_application', {
			name: props.editId,
		});
		if (appData) {
			const formatDateStr = (d) => {
				if (!d) return '';
				return String(d).split(' ')[0];
			};

			formData.value = {
				employee: appData.employee || '',
				employee_name: appData.employee_name || '',
				leave_type: appData.leave_type || '',
				from_date: formatDateStr(appData.from_date),
				to_date: formatDateStr(appData.to_date),
				half_day: Boolean(appData.half_day),
				leave_approver: appData.leave_approver || '',
				status: appData.status || 'Open',
				description: appData.description || '',
			};

			if (appData.employee) {
				await leaveStore.fetchLeaveTypes(appData.employee);
				if (!appData.leave_approver) {
					fetchApprovalDetails(appData.employee);
				}
			}
		}
	} catch (err) {
		console.error('Failed to fetch leave application details', err);
		submitError.value = getErrorMessage(err, 'Failed to fetch leave application details');
	}
}

async function fetchAttachments() {
	if (!props.editId) return;
	try {
		const files = await call('frappe.client.get_list', {
			doctype: 'File',
			filters: {
				attached_to_doctype: 'Leave Application',
				attached_to_name: props.editId,
			},
			fields: ['name', 'file_name', 'file_url'],
		});
		if (files && files.length > 0) {
			files.forEach((f) => {
				f.isExisting = true;
				attachments.value.push(f);
			});
		}
	} catch (e) {
		console.error('Failed to fetch attachments', e);
	}
}

// Watch for modal open
watch(show, async (newVal) => {
	if (newVal) {
		await initializeForm();
	}
});

// Watch for editId changes while modal is open
watch(
	() => props.editId,
	async (newVal, oldVal) => {
		if (show.value && newVal !== oldVal) {
			await initializeForm();
		}
	}
);

// Watch employee changes to fetch leave types and approval details
watch(
	() => formData.value.employee,
	async (empId, oldVal) => {
		if (empId && empId !== oldVal) {
			await leaveStore.fetchLeaveTypes(empId);
			if (!props.editId || oldVal) {
				fetchApprovalDetails(empId);
			}
		}
	}
);

const leaveApprovalResource = createResource({
	url: 'arijentek_core.api.leave.get_leave_approval_details',
	auto: false,
	onSuccess(data) {
		if (data?.leave_approver && (!props.editId || !formData.value.leave_approver)) {
			formData.value.leave_approver = data.leave_approver;
		}
	},
});

function fetchApprovalDetails(empId) {
	leaveApprovalResource.fetch({ employee: empId });
}

// Available leave types from store
const availableLeaveTypes = computed(() => {
	const types = leaveStore.leaveTypes || [];
	// Ensure current selection is in the list
	const currentSelected = formData.value.leave_type;
	if (currentSelected && !types.some(t => t.name === currentSelected)) {
		return [...types, { name: currentSelected, leave_type_name: currentSelected }];
	}
	return types;
});

// Balance label for selected leave type
const selectedBalanceLabel = computed(() => {
	const leaveType = formData.value.leave_type;
	if (!leaveType || !leaveStore.leaveBalances?.length) return null;

	const balance = leaveStore.leaveBalances.find(b => b.leave_type === leaveType);
	if (balance) {
		const bal = balance.balance_leaves ?? 0;
		return `${bal} Day${bal !== 1 ? 's' : ''}`;
	}
	return '0 Days';
});

const onFilesSelected = (e) => {
	const files = Array.from(e.target.files);
	files.forEach(f => {
		attachments.value.push(f);
	});
	e.target.value = '';
};

const removeAttachment = async (index) => {
	const file = attachments.value[index];
	if (file.isExisting) {
		if (await ask('Are you sure you want to delete this attachment? It will be removed immediately.')) {
			try {
				await call('frappe.client.delete', { doctype: 'File', name: file.name });
				attachments.value.splice(index, 1);
			} catch (err) {
				notify(getErrorMessage(err, 'Failed to delete file'));
			}
		}
	} else {
		attachments.value.splice(index, 1);
	}
};

// Auto-sync to_date when from_date is picked
watch(
	() => formData.value.from_date,
	(newFrom) => {
		if (!newFrom) return;
		if (formData.value.half_day) return;
		if (!formData.value.to_date || formData.value.to_date < newFrom) {
			formData.value.to_date = newFrom;
		}
	}
);

// Total leave days calculation
const totalDays = computed(() => {
	if (!formData.value.from_date) return 0;
	if (formData.value.half_day) return 0.5;
	if (!formData.value.to_date) return 0;
	if (formData.value.to_date < formData.value.from_date) return 0;
	const from = new Date(formData.value.from_date + 'T00:00:00');
	const to = new Date(formData.value.to_date + 'T00:00:00');
	const diff = Math.round((to.getTime() - from.getTime()) / (1000 * 60 * 60 * 24));
	return diff >= 0 ? diff + 1 : 0;
});

// Check if leave spans across different years (helps avoid accidental 2024 to 2026 selections)
const isCrossYear = computed(() => {
	if (!formData.value.from_date || !formData.value.to_date || formData.value.half_day) return false;
	const fromYear = formData.value.from_date.slice(0, 4);
	const toYear = formData.value.to_date.slice(0, 4);
	return fromYear !== toYear;
});

// Can submit check
const canSubmit = computed(() => {
	const base = formData.value.leave_type && formData.value.from_date;
	if (!base) return false;
	if (formData.value.half_day) return true;
	if (!formData.value.to_date) return false;
	return formData.value.to_date >= formData.value.from_date;
});

// Half day toggle
function onHalfDayToggle() {
	if (formData.value.half_day) {
		formData.value.to_date = '';
	} else if (!formData.value.to_date && formData.value.from_date) {
		formData.value.to_date = formData.value.from_date;
	}
}

// Validation
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
	if (!formData.value.from_date) {
		errors.value.from_date = 'From Date is required';
		isValid = false;
	}
	if (!formData.value.half_day) {
		if (!formData.value.to_date) {
			errors.value.to_date = 'To Date is required';
			isValid = false;
		} else if (formData.value.to_date < formData.value.from_date) {
			errors.value.to_date = 'To Date cannot be earlier than From Date';
			isValid = false;
		}
	}

	return isValid;
}

// Save handler
async function handleSave() {
	submitError.value = '';
	if (!validate()) return;

	submitting.value = true;
	try {
		// Validate on backend first
		const validation = await call('arijentek_core.api.leave.validate_leave_application', {
			leave_type: formData.value.leave_type,
			from_date: formData.value.from_date,
			to_date: formData.value.half_day ? formData.value.from_date : formData.value.to_date,
			employee: formData.value.employee,
		});

		if (validation && validation.success === false) {
			submitError.value = validation.error || 'Validation failed';
			submitting.value = false;
			return;
		}

		// Create the leave application
		const payload = {
			employee: formData.value.employee,
			leave_type: formData.value.leave_type,
			from_date: formData.value.from_date,
			to_date: formData.value.half_day ? formData.value.from_date : formData.value.to_date,
			half_day: formData.value.half_day || false,
			leave_approver: formData.value.leave_approver,
			description: formData.value.description,
			status: formData.value.status || 'Open',
		};

		if (props.editId) {
			payload.name = props.editId;
		}

		const result = await call('arijentek_core.api.leave.create_leave_application', payload);

		if (result && result.success === false) {
			submitError.value = result.error || 'Failed to save';
		} else {
			const appName = result.name || props.editId;
			if (appName && attachments.value.length > 0) {
				const newFiles = attachments.value.filter(f => !f.isExisting);
				for (const file of newFiles) {
					const form = new FormData();
					form.append('file', file, file.name);
					form.append('is_private', 1);
					form.append('doctype', 'Leave Application');
					form.append('docname', appName);
					
					await fetch('/api/method/upload_file', {
						method: 'POST',
						headers: {
							'Accept': 'application/json',
							'X-Frappe-CSRF-Token': window.csrf_token || ''
						},
						body: form
					});
				}
			}
			notify(props.editId ? 'Leave application updated successfully' : 'Leave application submitted successfully', 'success');
			emit('save', result);
			show.value = false;
		}
	} catch (err) {
		submitError.value = getErrorMessage(err, 'Failed to submit leave request');
	} finally {
		submitting.value = false;
	}
}
</script>
