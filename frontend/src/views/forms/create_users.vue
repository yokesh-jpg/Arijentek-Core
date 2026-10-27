<template>
  <Dialog :options="{ size: '5xl' }" v-model="show">
    <template #body>
      <div class="modal-panel">
        <header class="modal-header">
          <div class="min-w-0">
            <h3 class="modal-title">{{ editId ? 'Edit user' : 'Add a user' }}</h3>
            <p class="text-[12px] text-[#656A72] dark:text-white/60 truncate">{{ editId || 'A login for the Staff Hub, with the roles it can use.' }}</p>
          </div>
          <button @click="show = false" class="btn-icon-ghost shrink-0" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span></button>
        </header>

        <!-- The same tab strip the pages use, so it reads as the same control. -->
        <div class="px-6 shrink-0 border-b border-[#F2F2F6] dark:border-white/[0.08] flex gap-1 overflow-x-auto">
          <button @click="activeTab = 'basic'" class="tab-item" :class="{ 'tab-item-active': activeTab === 'basic' }">
            User details <span class="text-red-600 dark:text-red-400">*</span>
          </button>
          <button @click="activeTab = 'roles'" class="tab-item" :class="{ 'tab-item-active': activeTab === 'roles' }">
            Roles <span v-if="formData.roles?.length" class="ml-1 tabular-nums text-[#656A72] dark:text-white/55">{{ formData.roles.length }}</span>
          </button>
          <button
            v-if="employeeConnectionType === 'create'"
            @click="activeTab = 'employee_details'"
            class="tab-item"
            :class="{ 'tab-item-active': activeTab === 'employee_details' }"
          >
            Employee details <span class="text-red-600 dark:text-red-400">*</span>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto px-6 py-5">
          <!-- Server Error Message Banner (Uses getErrorMessage from utils.js) -->
          <div v-if="submitError" class="mb-4 flex items-start gap-2.5 p-3 rounded-[12px] bg-red-500/[0.08] dark:bg-red-500/[0.15] border border-red-500/20" role="alert">
            <span class="material-symbols-outlined !text-[18px] text-red-600 dark:text-red-400 shrink-0">error</span>
            <div class="flex-1 min-w-0">
              <p class="text-[13px] font-medium text-red-700 dark:text-red-300 leading-snug break-words">{{ submitError }}</p>
            </div>
            <button @click="submitError = ''" type="button" class="text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-200">
              <span class="material-symbols-outlined !text-[16px]">close</span>
            </button>
          </div>

          <!-- ===== User details ===== -->
          <div v-if="activeTab === 'basic'">
            <div class="flex items-center gap-4">
              <div class="w-16 h-16 rounded-full overflow-hidden bg-black/[0.04] dark:bg-white/[0.06] grid place-items-center shrink-0">
                <img v-if="formData.user_image" :src="formData.user_image" class="w-full h-full object-cover" alt="" />
                <span v-else class="material-symbols-outlined !text-[28px] text-[#656A72] dark:text-white/55">person</span>
              </div>
              <div class="min-w-0">
                <label class="btn-secondary !h-9 cursor-pointer">
                  <span class="material-symbols-outlined !text-[18px]">upload</span>
                  {{ formData.user_image ? 'Change photo' : 'Upload photo' }}
                  <input type="file" accept="image/*" @change="handleImageUpload" class="sr-only" />
                </label>
                <p v-if="imageUploading" class="text-xs text-[#656A72] dark:text-white/55 mt-1.5 flex items-center gap-1.5">
                  <span class="w-3 h-3 rounded-full border-2 border-black/10 dark:border-white/15 border-t-accent animate-spin"></span>Uploading…
                </p>
              </div>
            </div>

            <div class="modal-section grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-4">
              <div>
                <label class="field-label">Email <span class="text-red-600 dark:text-red-400">*</span></label>
                <input v-model="formData.email" type="email" class="field-input" />
                <p v-if="errors.email" class="field-error">{{ errors.email }}</p>
              </div>
              <div>
                <label class="field-label">First name</label>
                <input v-model="formData.first_name" type="text" class="field-input" />
              </div>
              <div>
                <label class="field-label">
                  Password <span v-if="!editId" class="text-red-600 dark:text-red-400">*</span>
                </label>
                <input v-model="formData.password" type="password" class="field-input" :placeholder="editId ? 'Leave blank to keep the current one' : ''" />
                <p v-if="errors.password" class="field-error">{{ errors.password }}</p>
              </div>
              <div>
                <label class="field-label">Middle name</label>
                <input v-model="formData.middle_name" type="text" class="field-input" />
              </div>
              <div>
                <label class="field-label">Username</label>
                <input v-model="formData.username" type="text" class="field-input" />
              </div>
              <div>
                <label class="field-label">Last name</label>
                <input v-model="formData.last_name" type="text" class="field-input" />
              </div>
            </div>

            <div class="modal-section grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-4">
              <div>
                <label class="field-label">Gender</label>
                <SearchableDropdown v-model="formData.gender" :options="teamStore.gendersResource?.data || []" placeholder="Select gender" />
              </div>
              <div>
                <label class="field-label">Date of birth</label>
                <DateField v-model="formData.date_of_birth" />
              </div>
              <div class="md:col-span-2">
                <label class="field-label">Time zone</label>
                <SearchableDropdown v-model="formData.time_zone" :options="teamStore.timezonesResource?.data?.timezones || teamStore.timezonesResource?.data || []" placeholder="Select time zone" />
              </div>
            </div>

            <!-- Linking the login to an employee record. -->
            <div class="modal-section">
              <p class="status-label">Employee record</p>

              <div v-if="isLoading" class="mt-3 space-y-2 animate-pulse">
                <div class="h-4 rounded bg-black/[0.06] dark:bg-white/[0.08] w-1/3"></div>
                <div class="h-9 rounded bg-black/[0.06] dark:bg-white/[0.08] w-1/2"></div>
              </div>

              <div v-else-if="editId && initialEmployeeId" class="mt-3 flex items-center gap-2.5 text-[13px] text-[#17181B] dark:text-white">
                <span class="material-symbols-outlined !text-[18px] text-green-700 dark:text-green-300">link</span>
                Linked to <span class="font-semibold">{{ initialEmployeeName || initialEmployeeId }}</span>
                <span class="text-[#656A72] dark:text-white/55 tabular-nums">{{ initialEmployeeId }}</span>
              </div>

              <template v-else>
                <div class="mt-3 flex flex-col sm:flex-row sm:flex-wrap gap-x-6 gap-y-2.5">
                  <label class="flex items-center gap-2 text-[13px] text-[#17181B] dark:text-white cursor-pointer select-none">
                    <input type="radio" v-model="employeeConnectionType" value="" class="w-4 h-4 border-black/20 dark:border-white/25 text-accent focus:ring-accent/40" />
                    Don't link an employee
                  </label>
                  <label class="flex items-center gap-2 text-[13px] text-[#17181B] dark:text-white cursor-pointer select-none">
                    <input type="radio" v-model="employeeConnectionType" value="connect" class="w-4 h-4 border-black/20 dark:border-white/25 text-accent focus:ring-accent/40" />
                    Link an existing employee
                  </label>
                  <label class="flex items-center gap-2 text-[13px] text-[#17181B] dark:text-white cursor-pointer select-none">
                    <input type="radio" v-model="employeeConnectionType" value="create" class="w-4 h-4 border-black/20 dark:border-white/25 text-accent focus:ring-accent/40" />
                    Create a new employee
                  </label>
                </div>

                <div v-if="employeeConnectionType === 'connect'" class="mt-4 md:w-1/2">
                  <label class="field-label">Employee <span class="text-red-600 dark:text-red-400">*</span></label>
                  <SearchableDropdown v-model="formData.employee_id" :options="teamStore.unlinkedEmployeesResource?.data || []" placeholder="Select an employee" />
                  <p v-if="errors.employee_id" class="field-error">{{ errors.employee_id }}</p>
                </div>
                <p v-if="employeeConnectionType === 'create'" class="mt-3 text-xs text-[#656A72] dark:text-white/55">
                  Fill in the Employee details tab before saving.
                </p>
              </template>
            </div>
          </div>

          <!-- ===== Roles ===== -->
          <div v-else-if="activeTab === 'roles'" class="flex flex-col gap-4">
            <div class="flex flex-col sm:flex-row sm:items-center gap-2.5">
              <div class="relative flex-1 min-w-0">
                <span class="material-symbols-outlined !text-[18px] absolute left-3.5 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/60 pointer-events-none">search</span>
                <input v-model="searchRole" type="text" placeholder="Search roles" class="field-input !pl-10" aria-label="Search roles" />
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <button @click="selectAllRoles" class="btn-ghost !h-9 !px-3">Select all</button>
                <button @click="unselectAllRoles" class="btn-ghost !h-9 !px-3">Clear</button>
                <button v-if="teamStore.createRolePermissionResource?.data" @click="showCreateRole = true" class="btn-secondary !h-9">
                  <span class="material-symbols-outlined !text-[18px]">add</span>
                  New role
                </button>
              </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-x-4 gap-y-1">
              <div v-for="role in filteredRoles" :key="role" class="flex items-center gap-2 min-h-[36px] group">
                <input type="checkbox" :id="role" :value="role" v-model="formData.roles" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40" />
                <label :for="role" class="text-[13px] text-[#17181B] dark:text-white cursor-pointer select-none truncate">{{ role }}</label>
                <button
                  v-if="teamStore.readRolePermissionResource?.data"
                  @click.prevent="openViewRole(role)"
                  class="btn-icon-ghost !w-7 !h-7 ml-auto opacity-0 group-hover:opacity-100 focus-visible:opacity-100"
                  :aria-label="'View ' + role"
                  :title="'View ' + role"
                >
                  <span class="material-symbols-outlined !text-[16px]">visibility</span>
                </button>
              </div>
              <p v-if="filteredRoles.length === 0" class="col-span-full py-8 text-center text-[13px] text-[#656A72] dark:text-white/55">No roles match “{{ searchRole }}”.</p>
            </div>
          </div>

          <!-- ===== Employee details ===== -->
          <div v-else-if="activeTab === 'employee_details'">
            <p class="text-[13px] text-[#5C6169] dark:text-white/65">
              Name, gender and date of birth start from the user details. Change them here if the employee record should differ.
            </p>

            <div class="modal-section grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-4">
              <div>
                <label class="field-label">First name <span class="text-red-600 dark:text-red-400">*</span></label>
                <input v-model="formData.employee_first_name" type="text" :placeholder="formData.first_name || 'First name'" class="field-input" />
                <p v-if="errors.employee_first_name" class="field-error">{{ errors.employee_first_name }}</p>
              </div>
              <div>
                <label class="field-label">Date of joining <span class="text-red-600 dark:text-red-400">*</span></label>
                <DateField v-model="formData.date_of_joining" />
                <p v-if="errors.date_of_joining" class="field-error">{{ errors.date_of_joining }}</p>
              </div>
              <div>
                <label class="field-label">Last name</label>
                <input v-model="formData.employee_last_name" type="text" :placeholder="formData.last_name || 'Last name'" class="field-input" />
              </div>
              <div>
                <label class="field-label">Expense approver</label>
                <SearchableDropdown v-model="formData.expense_approver" :options="teamStore.usersListResource?.data || []" placeholder="Select approver" />
                <p v-if="errors.expense_approver" class="field-error">{{ errors.expense_approver }}</p>
              </div>
              <div>
                <label class="field-label">Gender <span class="text-red-600 dark:text-red-400">*</span></label>
                <SearchableDropdown v-model="formData.employee_gender" :options="teamStore.gendersResource?.data || []" :placeholder="formData.gender || 'Select gender'" />
                <p v-if="errors.employee_gender" class="field-error">{{ errors.employee_gender }}</p>
              </div>
              <div>
                <label class="field-label">Leave approver</label>
                <SearchableDropdown v-model="formData.leave_approver" :options="teamStore.usersListResource?.data || []" placeholder="Select approver" />
                <p v-if="errors.leave_approver" class="field-error">{{ errors.leave_approver }}</p>
              </div>
              <div>
                <label class="field-label">Date of birth <span class="text-red-600 dark:text-red-400">*</span></label>
                <DateField v-model="formData.employee_date_of_birth" />
                <p v-if="errors.employee_date_of_birth" class="field-error">{{ errors.employee_date_of_birth }}</p>
              </div>
              <div>
                <label class="field-label">Shift approver</label>
                <SearchableDropdown v-model="formData.shift_approver" :options="teamStore.usersListResource?.data || []" placeholder="Select approver" />
                <p v-if="errors.shift_approver" class="field-error">{{ errors.shift_approver }}</p>
              </div>
            </div>
          </div>
        </div>

        <footer class="modal-footer justify-between">
          <p class="text-[13px] text-red-700 dark:text-red-400 min-w-0">{{ submitError }}</p>
          <div class="flex items-center gap-2 shrink-0">
            <button class="btn-secondary" @click="show = false" :disabled="submitting">Cancel</button>
            <button class="btn-primary" @click="handleSave" :disabled="submitting">
              <span v-if="submitting || isLoading" class="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></span>
              {{ (submitting || isLoading) ? 'Working…' : (editId ? 'Save changes' : 'Add user') }}
            </button>
          </div>
        </footer>
      </div>
    </template>
  </Dialog>
  <CreateRole v-model="showCreateRole" @save="handleRoleSaved" />
  <ViewRoles v-model="showViewRole" :roleName="selectedRoleToView" @deleted="handleRoleSaved" />
</template>

<script setup>
import { notify } from '@/utils/feedback.js'
import { ref, computed, watch } from 'vue';
import { Dialog, call } from 'frappe-ui';
import SearchableDropdown from '../../components/SearchableDropdown.vue';
import { useTeamStore } from '../../stores/team';
import { getErrorMessage } from '../../utils.js';
import CreateRole from './teams/create_role.vue';
import ViewRoles from '@/views/page_views/teams/view_roles.vue';
import DateField from '../../components/DateField.vue';

const teamStore = useTeamStore();

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

const activeTab = ref('basic');
const employeeConnectionType = ref('');
const initialEmployeeId = ref('');
const initialEmployeeName = ref('');

const getInitialFormData = () => ({
  name: '',
  email: '',
  password: '',
  first_name: '',
  middle_name: '',
  last_name: '',
  username: '',
  gender: '',
  date_of_birth: '',
  time_zone: '',
  user_image: '',
  roles: [],
  // Employee connection fields
  employee_id: '',
  employee_first_name: '',
  employee_last_name: '',
  employee_gender: '',
  employee_date_of_birth: '',
  date_of_joining: '',
  expense_approver: '',
  leave_approver: '',
  shift_approver: ''
});

const formData = ref(getInitialFormData());

const isLoading = ref(false);
const imageUploading = ref(false);
const searchRole = ref('');
const showCreateRole = ref(false);
const showViewRole = ref(false);
const selectedRoleToView = ref('');

const openViewRole = (role) => {
  selectedRoleToView.value = role;
  showViewRole.value = true;
};

const handleRoleSaved = () => {
  if (teamStore.rolesResource) {
    teamStore.rolesResource.reload();
  }
};

const handleImageUpload = async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  
  imageUploading.value = true;
  submitError.value = '';
  const form = new FormData();
  form.append('file', file, file.name);
  form.append('is_private', 0);
  
  try {
    const res = await fetch('/api/method/upload_file', {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'X-Frappe-CSRF-Token': window.csrf_token || ''
      },
      body: form
    });
    const data = await res.json();
    if (data.message && data.message.file_url) {
      formData.value.user_image = data.message.file_url;
    } else {
      throw new Error('Upload failed');
    }
  } catch (err) {
    notify('Failed to upload image');
    console.error(err);
  } finally {
    imageUploading.value = false;
  }
};

const filteredRoles = computed(() => {
  const allRoles = teamStore.rolesResource?.data || [];
  if (!searchRole.value) return allRoles;
  const lowerSearch = searchRole.value.toLowerCase();
  return allRoles.filter(role => role.toLowerCase().includes(lowerSearch));
});

const selectAllRoles = () => {
  const visibleRoles = filteredRoles.value;
  const currentRoles = new Set(formData.value.roles);
  visibleRoles.forEach(role => currentRoles.add(role));
  formData.value.roles = Array.from(currentRoles);
};

const unselectAllRoles = () => {
  const visibleRoles = new Set(filteredRoles.value);
  formData.value.roles = formData.value.roles.filter(role => !visibleRoles.has(role));
};

watch(show, async (newVal) => {
  if (newVal) {
    formData.value = getInitialFormData();
    employeeConnectionType.value = '';
    initialEmployeeId.value = '';
    initialEmployeeName.value = '';
    errors.value = {};
    activeTab.value = 'basic';
    submitError.value = '';
    searchRole.value = '';

    // Always reload resources so dropdown options (roles, timezones, genders, etc.) are up to date
    teamStore.rolesResource.reload();
    teamStore.timezonesResource.reload().then(() => {
      if (!props.editId && teamStore.timezonesResource.data?.default_timezone) {
        formData.value.time_zone = teamStore.timezonesResource.data.default_timezone;
      }
    });
    teamStore.gendersResource.reload();
    teamStore.usersListResource.reload();
    teamStore.unlinkedEmployeesResource.reload();
    
    if (props.editId) {
      isLoading.value = true;
      try {
        const data = await call('arijentek_core.api.teams_permissons.get_users_details', { user_id: props.editId });
        if (data) {
          formData.value = { ...formData.value, ...data, name: props.editId };
          if (data.birth_date) formData.value.date_of_birth = data.birth_date;
          if (data.employee_id) {
            initialEmployeeId.value = data.employee_id;
            initialEmployeeName.value = data.employee_name || '';
            formData.value.employee_id = data.employee_id;
          }
        }
      } catch (err) {
        submitError.value = getErrorMessage(err, 'Failed to fetch user details');
      } finally {
        isLoading.value = false;
      }
    }
  }
});

const errors = ref({});
const submitError = ref('');
const submitting = ref(false);

const validate = () => {
  errors.value = {};
  let isValid = true;
  let firstErrorTab = null;

  if (!formData.value.email) {
    errors.value.email = 'Email is mandatory';
    isValid = false;
    firstErrorTab = firstErrorTab || 'basic';
  }
  
  if (!formData.value.password && !props.editId) {
    errors.value.password = 'Password is mandatory';
    isValid = false;
    firstErrorTab = firstErrorTab || 'basic';
  }

  // Employee Connection Validations
  if (employeeConnectionType.value === 'connect' && !formData.value.employee_id) {
    errors.value.employee_id = 'Please select an employee to connect';
    isValid = false;
    firstErrorTab = firstErrorTab || 'basic';
  }

  if (employeeConnectionType.value === 'create') {
    const empFirstName = formData.value.employee_first_name || formData.value.first_name;
    if (!empFirstName) {
      errors.value.employee_first_name = 'First Name is mandatory';
      isValid = false;
      firstErrorTab = firstErrorTab || 'employee_details';
    }

    const empGender = formData.value.employee_gender || formData.value.gender;
    if (!empGender) {
      errors.value.employee_gender = 'Gender is mandatory';
      isValid = false;
      firstErrorTab = firstErrorTab || 'employee_details';
    }

    const empDob = formData.value.employee_date_of_birth || formData.value.date_of_birth;
    if (!empDob) {
      errors.value.employee_date_of_birth = 'Date of Birth is mandatory';
      isValid = false;
      firstErrorTab = firstErrorTab || 'employee_details';
    }

    if (!formData.value.date_of_joining) {
      errors.value.date_of_joining = 'Date of Joining is mandatory';
      isValid = false;
      firstErrorTab = firstErrorTab || 'employee_details';
    }


  }

  if (firstErrorTab) {
    activeTab.value = firstErrorTab;
  }

  return isValid;
};

const handleSave = async () => {
  submitError.value = '';
  if (validate()) {
    submitting.value = true;
    try {
      if (props.editId) {
        formData.value.name = props.editId;
      }

      // 1. Create or update User
      const userId = await call('arijentek_core.api.teams_permissons.create_user', {
        user_data: formData.value
      });

      // 2. Connect Existing Employee if selected
      if (employeeConnectionType.value === 'connect' && formData.value.employee_id) {
        await call('arijentek_core.api.teams_permissons.link_user_to_employee', {
          user_id: userId,
          employee_id: formData.value.employee_id
        });
      }

      // 3. Create New Employee if selected
      if (employeeConnectionType.value === 'create') {
        const employeeData = {
          user_id: userId,
          first_name: formData.value.employee_first_name || formData.value.first_name,
          last_name: formData.value.employee_last_name || formData.value.last_name,
          gender: formData.value.employee_gender || formData.value.gender,
          date_of_birth: formData.value.employee_date_of_birth || formData.value.date_of_birth,
          date_of_joining: formData.value.date_of_joining,
          expense_approver: formData.value.expense_approver,
          leave_approver: formData.value.leave_approver,
          shift_approver: formData.value.shift_approver,
          status: 'Active'
        };

        await call('arijentek_core.api.teams_permissons.create_employee', {
          employee_data: employeeData
        });
      }
      
      // Reload relevant resources
      if (employeeConnectionType.value !== '') {
        teamStore.unlinkedEmployeesResource.reload();
        teamStore.unlinkedUsersResource.reload();
        teamStore.employeeListResource.reload();
      }
      teamStore.usersListResource.reload();
      
      emit('save', formData.value);
      show.value = false;
    } catch (err) {
      // Use getErrorMessage from utils.js to extract server error details cleanly
      submitError.value = getErrorMessage(err, 'Failed to save user');
      // Do NOT set show.value = false so the form remains open for user review
    } finally {
      submitting.value = false;
    }
  }
};
</script>
