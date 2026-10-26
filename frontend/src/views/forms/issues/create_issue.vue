<template>
	<Dialog :options="{ size: 'xl' }" v-model="show">
		<template #body>
			<div class="modal-panel">
				<header class="modal-header">
					<div class="min-w-0">
						<h3 class="modal-title">{{ isEdit ? 'Edit issue' : 'Raise an issue' }}</h3>
						<p class="text-[12px] text-[#656A72] dark:text-white/60">
							{{ isEdit ? 'Update the record and what has been done about it.' : 'Describe what happened and who it concerns.' }}
						</p>
					</div>
					<button @click="show = false" class="btn-icon-ghost" aria-label="Close">
						<span class="material-symbols-outlined !text-[18px]">close</span>
					</button>
				</header>

				<div class="flex-1 overflow-y-auto px-6 py-5">
					<div v-if="submitError" class="flex items-start gap-2.5 p-3.5 mb-5 rounded-[12px] bg-red-500/[0.07] border border-red-500/20">
						<span class="material-symbols-outlined !text-[18px] text-red-600 dark:text-red-400 shrink-0">error</span>
						<p class="text-[13px] text-red-700 dark:text-red-400 leading-relaxed">{{ submitError }}</p>
					</div>

					<!-- The four groups were tinted cards inside the panel. A rule
					     groups them without stacking a second surface. -->
					<div class="modal-section">
						<div class="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-4">
							<div class="sm:col-span-2">
								<label class="field-label">Subject <span class="text-red-600 dark:text-red-400">*</span></label>
								<input
									v-model="formData.subject"
									type="text"
									placeholder="One line on what happened"
									class="field-input"
									:class="{ '!border-red-500/60': errors.subject }"
								/>
								<p v-if="errors.subject" class="field-error">{{ errors.subject }}</p>
							</div>

							<div>
								<label class="field-label">Date <span class="text-red-600 dark:text-red-400">*</span></label>
								<DateField v-model="formData.date" :invalid="!!errors.date" />
								<p v-if="errors.date" class="field-error">{{ errors.date }}</p>
							</div>

							<div>
								<label class="field-label">Raised by <span class="text-red-600 dark:text-red-400">*</span></label>
								<SearchableDropdown
									v-model="formData.raised_by"
									:options="employees"
									valueKey="name"
									labelKey="employee_name"
									placeholder="Select employee"
									:disabled="employees.length <= 1"
								/>
								<p v-if="errors.raised_by" class="field-error">{{ errors.raised_by }}</p>
							</div>

							<div class="sm:col-span-2">
								<label class="field-label">Status <span class="text-red-600 dark:text-red-400">*</span></label>
								<SearchableDropdown
									v-model="formData.status"
									:options="statusOptions"
									placeholder="Select status"
									:disabled="statusOptions.length <= 1"
								/>
								<p v-if="errors.status" class="field-error">{{ errors.status }}</p>
							</div>
						</div>
					</div>

					<div class="modal-section">
						<p class="status-label">Who and what it concerns</p>
						<div class="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-4 mt-3">
							<div>
								<label class="field-label">Raised against <span class="text-red-600 dark:text-red-400">*</span></label>
								<SearchableDropdown
									v-model="formData.grievance_against_party"
									:options="partyOptions"
									placeholder="Select party"
									@change="handlePartyChange"
								/>
								<p v-if="errors.grievance_against_party" class="field-error">{{ errors.grievance_against_party }}</p>
							</div>

							<div>
								<label class="field-label">Which one <span class="text-red-600 dark:text-red-400">*</span></label>
								<SearchableDropdown
									v-model="formData.grievance_against"
									:options="againstOptions"
									valueKey="name"
									labelKey="label"
									:placeholder="formData.grievance_against_party ? 'Select' : 'Pick a party first'"
									:disabled="!formData.grievance_against_party"
								/>
								<p v-if="errors.grievance_against" class="field-error">{{ errors.grievance_against }}</p>
							</div>

							<div class="sm:col-span-2">
								<label class="field-label">Issue type <span class="text-red-600 dark:text-red-400">*</span></label>
								<div class="flex items-start gap-2">
									<div class="flex-1 min-w-0">
										<SearchableDropdown
											v-model="formData.grievance_type"
											:options="issueTypes"
											valueKey="name"
											labelKey="name"
											placeholder="Select issue type"
										/>
									</div>
									<button
										v-if="canCreateType"
									
										@click="showCreateIssueTypeModal = true" type="button" class="btn-add-option" title="Add a new issue type" aria-label="Add a new issue type"><span class="material-symbols-outlined !text-[18px]">add</span></button>
								</div>
								<p v-if="errors.grievance_type" class="field-error">{{ errors.grievance_type }}</p>
							</div>

							<div class="sm:col-span-2">
								<label class="field-label">What happened</label>
								<textarea
									v-model="formData.description"
									rows="4"
									placeholder="When, where, who was there, and what the effect was"
									class="field-input"
								></textarea>
							</div>
						</div>
					</div>

					<!-- Investigation and resolution appear as the status moves on, so
					     an untouched Open issue is not asked for either. -->
					<div v-if="formData.status === 'Investigated' || formData.status === 'Resolved'" class="modal-section">
						<p class="status-label flex items-center gap-1.5">
							<span class="material-symbols-outlined !text-[16px]">search_insights</span>
							Investigation
						</p>
						<div class="mt-3">
							<label class="field-label">Cause of the issue <span class="text-red-600 dark:text-red-400">*</span></label>
							<textarea
								v-model="formData.cause_of_grievance"
								rows="4"
								placeholder="What the investigation found"
								class="field-input"
								:class="{ '!border-red-500/60': errors.cause_of_grievance }"
							></textarea>
							<p v-if="errors.cause_of_grievance" class="field-error">{{ errors.cause_of_grievance }}</p>
						</div>
					</div>

					<div v-if="formData.status === 'Resolved'" class="modal-section">
						<p class="status-label flex items-center gap-1.5">
							<span class="material-symbols-outlined !text-[16px]">check_circle</span>
							Resolution
						</p>
						<div class="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-4 mt-3">
							<div>
								<label class="field-label">Resolved by <span class="text-red-600 dark:text-red-400">*</span></label>
								<SearchableDropdown
									v-model="formData.resolved_by"
									:options="users"
									valueKey="name"
									labelKey="full_name"
									placeholder="Select user"
								/>
								<p v-if="errors.resolved_by" class="field-error">{{ errors.resolved_by }}</p>
							</div>

							<div>
								<label class="field-label">Resolution date <span class="text-red-600 dark:text-red-400">*</span></label>
								<DateField v-model="formData.resolution_date" :invalid="!!errors.resolution_date" />
								<p v-if="errors.resolution_date" class="field-error">{{ errors.resolution_date }}</p>
							</div>

							<div class="sm:col-span-2">
								<label class="field-label">What was done</label>
								<textarea
									v-model="formData.resolution_detail"
									rows="4"
									placeholder="The action taken, and anything changed to stop it recurring"
									class="field-input"
								></textarea>
							</div>
						</div>
					</div>
				</div>

				<footer class="modal-footer justify-end">
					<button class="btn-secondary" @click="show = false">Cancel</button>
					<button class="btn-primary" @click="submitForm" :disabled="submitting || loadingData">
						<span v-if="submitting || loadingData" class="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></span>
						{{ isEdit ? 'Save changes' : 'Raise issue' }}
					</button>
				</footer>
			</div>
		</template>
	</Dialog>

	<!-- Create Issue Types Modal -->
	<CreateIssueTypes
		v-model="showCreateIssueTypeModal"
		@save="handleIssueTypeCreated"
	/>
</template>
<script setup>
import { ref, watch, computed } from 'vue';
import { Dialog, call } from 'frappe-ui';
import SearchableDropdown from '@/components/SearchableDropdown.vue';
import CreateIssueTypes from './create_issue_types.vue';
import { getErrorMessage } from '@/utils';
import DateField from '../../../components/DateField.vue'

const show = defineModel();
const emit = defineEmits(['save']);

const props = defineProps({
  editData: {
    type: Object,
    default: null
  },
  targetStatus: {
    type: String,
    default: null
  }
});

const submitting = ref(false);
const loadingData = ref(false);
const submitError = ref('');
const showCreateIssueTypeModal = ref(false);

const employees = ref([]);
const users = ref([]);
const statusOptions = ref([]);
const partyOptions = ref([]);
const againstOptions = ref([]);
const issueTypes = ref([]);
const canCreateType = ref(false);

const errors = ref({});

const isEdit = computed(() => !!props.editData);

const defaultFormData = () => ({
  name: '',
  subject: '',
  date: new Date().toISOString().split('T')[0],
  raised_by: '',
  status: 'Open',
  grievance_against_party: '',
  grievance_against: '',
  grievance_type: '',
  description: '',
  cause_of_grievance: '',
  resolved_by: '',
  resolution_date: '',
  resolution_detail: ''
});

const formData = ref(defaultFormData());

const fetchDropdownOptions = async () => {
  try {
    const [empRes, statusRes, partyRes, typeRes, userRes, typePermRes] = await Promise.all([
      call('arijentek_core.api.issues.get_employees'),
      call('arijentek_core.api.issues.get_statuses'),
      call('arijentek_core.api.issues.get_grievance_against_party_options'),
      call('arijentek_core.api.issues.get_issues_types'),
      call('arijentek_core.api.issues.get_users'),
      call('arijentek_core.api.issues.can_create_grievance_type')
    ]);

    employees.value = empRes || [];
    if (!formData.value.raised_by && employees.value.length === 1) {
      formData.value.raised_by = employees.value[0].name;
    }
    statusOptions.value = statusRes || ['Open', 'Investigated', 'Resolved', 'Invalid'];
    partyOptions.value = partyRes || ['Company', 'Department', 'Employee', 'Others'];
    issueTypes.value = typeRes || [];
    users.value = userRes || [];
    canCreateType.value = !!typePermRes;
  } catch (err) {
    console.error('Failed to load form dropdown options:', err);
  }
};

const handlePartyChange = async (party) => {
  formData.value.grievance_against = '';
  againstOptions.value = [];
  if (!party) return;

  try {
    const res = await call('arijentek_core.api.issues.get_grievance_against_list', { party });
    againstOptions.value = res || [];
  } catch (err) {
    console.error('Failed to fetch grievance against options:', err);
  }
};

const handleIssueTypeCreated = async () => {
  try {
    const res = await call('arijentek_core.api.issues.get_issues_types');
    issueTypes.value = res || [];
    // Auto-select the latest issue type
    if (res && res.length > 0) {
      formData.value.grievance_type = res[res.length - 1].name;
    }
  } catch (err) {
    console.error('Failed to reload issue types:', err);
  }
};

watch(show, async (newVal) => {
  if (newVal) {
    submitError.value = '';
    errors.value = {};
    loadingData.value = true;

    await fetchDropdownOptions();

    if (props.editData && props.editData.name) {
      try {
        const res = await call('arijentek_core.api.issues.get_issues', { id: props.editData.name });
        if (res && res.length > 0) {
          const doc = res[0];
          formData.value = {
            name: doc.name || '',
            subject: doc.subject || '',
            date: doc.date || '',
            raised_by: doc.raised_by || '',
            status: doc.status || 'Open',
            grievance_against_party: doc.grievance_against_party || '',
            grievance_against: doc.grievance_against || '',
            grievance_type: doc.grievance_type || '',
            description: doc.description || '',
            cause_of_grievance: doc.cause_of_grievance || '',
            resolved_by: doc.resolved_by || '',
            resolution_date: doc.resolution_date || '',
            resolution_detail: doc.resolution_detail || ''
          };
          if (doc.grievance_against_party) {
            await handlePartyChange(doc.grievance_against_party);
            formData.value.grievance_against = doc.grievance_against || '';
          }
        }
      } catch (err) {
        console.error('Failed to load issue details:', err);
        submitError.value = getErrorMessage(err, 'Failed to load record details.');
      }
    } else {
      formData.value = defaultFormData();
      if (employees.value.length === 1) {
        formData.value.raised_by = employees.value[0].name;
      }
    }

    if (props.targetStatus) {
      formData.value.status = props.targetStatus;
      if (props.targetStatus === 'Resolved' && !formData.value.resolution_date) {
        formData.value.resolution_date = new Date().toISOString().split('T')[0];
      }
    }

    loadingData.value = false;
  }
});

function validate() {
  errors.value = {};
  let isValid = true;

  if (!formData.value.subject?.trim()) {
    errors.value.subject = 'Subject is required';
    isValid = false;
  }
  if (!formData.value.date) {
    errors.value.date = 'Date is required';
    isValid = false;
  }
  if (!formData.value.raised_by) {
    errors.value.raised_by = 'Raised By employee is required';
    isValid = false;
  }
  if (!formData.value.status) {
    errors.value.status = 'Status is required';
    isValid = false;
  }
  if (!formData.value.grievance_against_party) {
    errors.value.grievance_against_party = 'Issue Against Party is required';
    isValid = false;
  }
  if (!formData.value.grievance_against?.trim()) {
    errors.value.grievance_against = 'Issue Against is required';
    isValid = false;
  }
  if (!formData.value.grievance_type) {
    errors.value.grievance_type = 'Issue Type is required';
    isValid = false;
  }

  // Mandatory fields for Investigated / Resolved status
  if (formData.value.status === 'Investigated' || formData.value.status === 'Resolved') {
    if (!formData.value.cause_of_grievance?.trim()) {
      errors.value.cause_of_grievance = 'Cause of Grievance is required for this status';
      isValid = false;
    }
  }

  // Mandatory fields for Resolved status
  if (formData.value.status === 'Resolved') {
    if (!formData.value.resolved_by) {
      errors.value.resolved_by = 'Resolved By is required when status is Resolved';
      isValid = false;
    }
    if (!formData.value.resolution_date) {
      errors.value.resolution_date = 'Resolution Date is required when status is Resolved';
      isValid = false;
    }
  }

  return isValid;
}

async function submitForm() {
  submitError.value = '';
  if (!validate()) return;

  submitting.value = true;
  try {
    await call('arijentek_core.api.issues.save_issue', { doc: formData.value });
    emit('save');
    show.value = false;
  } catch (err) {
    console.error(err);
    submitError.value = getErrorMessage(err, 'Failed to save grievance');
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
</style>
