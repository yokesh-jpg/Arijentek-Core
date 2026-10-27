<template>
  <div>
    <Dialog :options="{ size: '3xl' }" v-model="show">
    <template #body>
      <div class="modal-panel">
        <!-- Custom Header -->
        <header class="modal-header">
          <div>
            <h3 class="modal-title">{{ editId ? 'Edit employee' : 'Add new employee' }}</h3>
            <p class="text-[12px] text-[#656A72] dark:text-white/60">{{ editId ? editId : 'Fill in the details below' }}</p>
          </div>
          <button @click="show = false" class="btn-icon-ghost shrink-0" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span>
          </button>
        </header>

        <div class="px-6 shrink-0 border-b border-[#F2F2F6] dark:border-white/[0.08]">
          <div class="flex gap-1 overflow-x-auto">
        <button 
          @click="activeTab = 'basic'"
          class="tab-item" :class="{ 'tab-item-active': activeTab === 'basic' }"
        >
          Basic details <span class="text-red-600 dark:text-red-400">*</span>
        </button>
        <button 
          @click="activeTab = 'approvers'"
          class="tab-item" :class="{ 'tab-item-active': activeTab === 'approvers' }"
        >
          Approvers
        </button>
        <button 
          @click="activeTab = 'address'"
          class="tab-item" :class="{ 'tab-item-active': activeTab === 'address' }"
        >
          Address & contacts
        </button>
        <button 
          v-if="userConnectionType === 'create'"
          @click="activeTab = 'user_details'"
          class="tab-item" :class="{ 'tab-item-active': activeTab === 'user_details' }"
        >
          User details <span class="text-red-600 dark:text-red-400">*</span>
        </button>
        <button 
          v-if="userConnectionType === 'create'"
          @click="activeTab = 'user_roles'"
          class="tab-item" :class="{ 'tab-item-active': activeTab === 'user_roles' }"
        >
        </button>
      </div>
    </div>

      <!-- Tab Content -->
      <div class="flex-1 overflow-y-auto px-6 py-5">
        <!-- Basic Details -->
        <div v-if="activeTab === 'basic'" class="flex flex-col gap-6">
          <div class="flex flex-col gap-1.5 col-span-full">
            <label class="field-label">Employee image</label>
            <div class="flex items-center gap-4">
              <div class="w-16 h-16 rounded-full overflow-hidden bg-black/[0.04] dark:bg-white/[0.06] grid place-items-center shrink-0">
                <img v-if="formData.image" :src="formData.image" class="w-full h-full object-cover">
                <span v-else class="material-symbols-outlined text-[#656A72] dark:text-white/60 text-3xl">person</span>
              </div>
              <label class="btn-secondary !h-9 cursor-pointer"><span class="material-symbols-outlined !text-[18px]">upload</span>Upload photo<input type="file" accept="image/*" @change="handleImageUpload" class="sr-only"></label>
              <span v-if="imageUploading" class="text-xs text-[#656A72] dark:text-white/55 flex items-center gap-1.5"><span class="w-3 h-3 rounded-full border-2 border-black/10 dark:border-white/15 border-t-accent animate-spin"></span>Uploading…</span>
            </div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="flex flex-col gap-4">
              <div class="flex flex-col gap-1.5">
                <label class="field-label">First name <span class="text-red-600 dark:text-red-400">*</span></label>
                <input v-model="formData.first_name" type="text" class="field-input">
                <p v-if="errors.first_name" class="field-error">{{ errors.first_name }}</p>
              </div>
              <div class="flex flex-col gap-1.5">
                <label class="field-label">Middle name</label>
                <input v-model="formData.middle_name" type="text" class="field-input">
              </div>
              <div class="flex flex-col gap-1.5">
                <label class="field-label">Last name</label>
                <input v-model="formData.last_name" type="text" class="field-input">
              </div>
            </div>
            
            <div class="flex flex-col gap-4">
              <div class="flex flex-col gap-1.5">
                <label class="field-label">Gender <span class="text-red-600 dark:text-red-400">*</span></label>
                <div class="flex items-center gap-2">
                  <SearchableDropdown v-model="formData.gender" :options="teamStore.gendersResource?.data || []" placeholder="Select gender" class="flex-1" />
                  <button v-if="teamStore.createGenderPermissionResource?.data" @click.prevent="showCreateGender = true" type="button" class="btn-add-option" title="Add a new gender" aria-label="Add a new gender"><span class="material-symbols-outlined !text-[18px]">add</span></button>
                </div>
                <p v-if="errors.gender" class="field-error">{{ errors.gender }}</p>
              </div>
              <div class="flex flex-col gap-1.5">
                <label class="field-label">Date of birth <span class="text-red-600 dark:text-red-400">*</span></label>
                <DateField v-model="formData.date_of_birth" />
                <p v-if="errors.date_of_birth" class="field-error">{{ errors.date_of_birth }}</p>
              </div>
              <div class="flex flex-col gap-1.5">
                <label class="field-label">Salutation</label>
                <div class="flex items-center gap-2">
                  <SearchableDropdown v-model="formData.salutation" :options="teamStore.salutationsResource?.data || []" placeholder="Select salutation" class="flex-1" />
                  <button v-if="teamStore.createSalutationPermissionResource?.data" @click.prevent="showCreateSalutation = true" type="button" class="btn-add-option" title="Add a new salutation" aria-label="Add a new salutation"><span class="material-symbols-outlined !text-[18px]">add</span></button>
                </div>
              </div>
            </div>
          </div>
          
          <div class="h-px bg-black/[0.07] dark:bg-white/10"></div>
          
          <!-- User Connection Options -->
          <div v-if="isLoading" class="flex flex-col gap-2 animate-pulse">
            <div class="h-4 rounded bg-black/[0.06] dark:bg-white/[0.08] w-1/3"></div>
            <div class="h-9 rounded bg-black/[0.06] dark:bg-white/[0.08] w-1/2"></div>
          </div>
          <div v-else class="flex flex-col gap-3">
            <label class="field-label">User account association</label>
            
            <div v-if="!teamStore.createUserPermissionResource?.data">
              <div v-if="initialUserId" class="flex items-center">
                <span class="premium-tag tag-emerald !normal-case !tracking-normal">
                  Linked User: {{ initialUserName || initialUserId }} <span class="opacity-75 ml-1">({{ initialUserId }})</span>
                </span>
              </div>
              <div v-else class="flex items-center">
                <span class="premium-tag tag-neutral !normal-case !tracking-normal">
                  No User Linked
                </span>
              </div>
            </div>
            
            <div v-else>
              <div v-if="editId && initialUserId" class="flex items-center">
                <span class="premium-tag tag-emerald !normal-case !tracking-normal">
                  Connected to User: {{ initialUserName || initialUserId }} <span class="opacity-75 ml-1">({{ initialUserId }})</span>
                </span>
              </div>
              
              <template v-else>
                <div class="flex flex-wrap gap-6">
                  <label class="flex items-center gap-2 text-[13px] text-[#17181B] dark:text-white cursor-pointer select-none">
                    <input type="radio" v-model="userConnectionType" value="" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40">
                    Do not connect user
                  </label>
                  <label class="flex items-center gap-2 text-[13px] text-[#17181B] dark:text-white cursor-pointer select-none">
                    <input type="radio" v-model="userConnectionType" value="create" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40">
                    Create new user
                  </label>
                  <label class="flex items-center gap-2 text-[13px] text-[#17181B] dark:text-white cursor-pointer select-none">
                    <input type="radio" v-model="userConnectionType" value="connect" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40">
                    Connect existing user
                  </label>
                </div>
                
                <div v-if="userConnectionType === 'connect'" class="mt-2">
                  <div class="w-full md:w-1/2"><SearchableDropdown v-model="formData.user_id" :options="teamStore.unlinkedUsersResource?.data || []" placeholder="Select existing user" /></div>
                  <p v-if="errors.user_id" class="field-error">{{ errors.user_id }}</p>
                </div>
              </template>
            </div>
          </div>
          
          <div class="h-px bg-black/[0.07] dark:bg-white/10"></div>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="field-label">Employee number</label>
              <input v-model="formData.employee_number" type="text" class="field-input">
              <p v-if="errors.employee_number" class="field-error">{{ errors.employee_number }}</p>
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="field-label">Date of joining <span class="text-red-600 dark:text-red-400">*</span></label>
              <DateField v-model="formData.date_of_joining" />
              <p v-if="errors.date_of_joining" class="field-error">{{ errors.date_of_joining }}</p>
            </div>
            <div v-if="editId" class="flex flex-col gap-1.5">
              <label class="field-label">Status</label>
              <SearchableDropdown v-model="formData.status" :options="['Active', 'Inactive', 'Suspended', 'Left']" placeholder="Select status" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="field-label">Designation</label>
              <div class="flex items-center gap-2">
                <SearchableDropdown v-model="formData.designation" :options="teamStore.designationsResource?.data || []" placeholder="Select designation" class="flex-1" />
                <button v-if="teamStore.createDesignationPermissionResource?.data" @click.prevent="showCreateDesignation = true" type="button" class="btn-add-option" title="Add a new designation" aria-label="Add a new designation"><span class="material-symbols-outlined !text-[18px]">add</span></button>
              </div>
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="field-label">Branch</label>
              <div class="flex items-center gap-2">
                <SearchableDropdown v-model="formData.branch" :options="teamStore.branchesResource?.data || []" placeholder="Select branch" class="flex-1" />
                <button v-if="teamStore.createBranchPermissionResource?.data" @click.prevent="showCreateBranch = true" type="button" class="btn-add-option" title="Add a new branch" aria-label="Add a new branch"><span class="material-symbols-outlined !text-[18px]">add</span></button>
              </div>
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="field-label">Department</label>
              <div class="flex items-center gap-2">
                <SearchableDropdown v-model="formData.department" :options="teamStore.departmentsResource?.data || []" placeholder="Select department" @change="handleDepartmentChange" class="flex-1" />
                <button v-if="teamStore.createDepartmentPermissionResource?.data" @click.prevent="showCreateDepartment = true" type="button" class="btn-add-option" title="Add a new department" aria-label="Add a new department"><span class="material-symbols-outlined !text-[18px]">add</span></button>
              </div>
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="field-label">Reports to</label>
              <SearchableDropdown v-model="formData.reports_to" :options="teamStore.employeeListResource?.data || []" placeholder="Select reports to" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="field-label">Grade</label>
              <div class="flex items-center gap-2">
                <SearchableDropdown v-model="formData.grade" :options="teamStore.employeeGradesResource?.data || []" placeholder="Select grade" class="flex-1" />
                <button v-if="teamStore.createEmployeeGradePermissionResource?.data" @click.prevent="showCreateEmployeeGrade = true" type="button" class="btn-add-option" title="Add a new grade" aria-label="Add a new grade"><span class="material-symbols-outlined !text-[18px]">add</span></button>
              </div>
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="field-label">Employee type</label>
              <div class="flex items-center gap-2">
                <SearchableDropdown v-model="formData.employee_type" :options="teamStore.employmentTypesResource?.data || []" placeholder="Select employee type" class="flex-1" />
                <button v-if="teamStore.createEmployeeTypePermissionResource?.data" @click.prevent="showCreateEmployeeType = true" type="button" class="btn-add-option" title="Add a new employee type" aria-label="Add a new employee type"><span class="material-symbols-outlined !text-[18px]">add</span></button>
              </div>
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="field-label">Holiday list</label>
              <div class="flex items-center gap-2">
                <SearchableDropdown v-model="formData.holiday_list" :options="leaveStore.holidayLists || []" placeholder="Select holiday list" labelKey="holiday_list_name" valueKey="name" class="flex-1" />
                <button @click.prevent="showCreateHolidayList = true" type="button" class="btn-add-option" title="Add a new holiday list" aria-label="Add a new holiday list"><span class="material-symbols-outlined !text-[18px]">add</span></button>
              </div>
              <p v-if="errors.holiday_list" class="field-error">{{ errors.holiday_list }}</p>
            </div>
          </div>
        </div>

        <!-- Approvers -->
        <div v-else-if="activeTab === 'approvers'" class="flex flex-col gap-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="field-label">Expense approver</label>
              <SearchableDropdown v-model="formData.expense_approver" :options="teamStore.usersListResource?.data || []" placeholder="Select expense approver" />
              <p v-if="errors.expense_approver" class="field-error">{{ errors.expense_approver }}</p>
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="field-label">Shift approver</label>
              <SearchableDropdown v-model="formData.shift_approver" :options="teamStore.usersListResource?.data || []" placeholder="Select shift approver" />
              <p v-if="errors.shift_approver" class="field-error">{{ errors.shift_approver }}</p>
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="field-label">Leave approver</label>
              <SearchableDropdown v-model="formData.leave_approver" :options="teamStore.usersListResource?.data || []" placeholder="Select leave approver" />
              <p v-if="errors.leave_approver" class="field-error">{{ errors.leave_approver }}</p>
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="field-label">Default shift</label>
              <div class="flex items-center gap-2">
                <SearchableDropdown v-model="formData.default_shift" :options="teamStore.shiftTypesResource?.data || []" placeholder="Select default shift" class="flex-1" />
                <button @click.prevent="showCreateShiftType = true" type="button" class="btn-add-option" title="Add a new shift type" aria-label="Add a new shift type"><span class="material-symbols-outlined !text-[18px]">add</span></button>
              </div>
            </div>
          </div>
        </div>

        <!-- Address & contacts -->
        <div v-else-if="activeTab === 'address'" class="flex flex-col gap-6">
          <div class="flex flex-col gap-4">
            <p class="status-label">Contact details</p>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="flex flex-col gap-1.5">
                <label class="field-label">Mobile no</label>
                <input v-model="formData.cell_number" type="tel" class="field-input">
              </div>
              <div class="flex flex-col gap-1.5">
                <label class="field-label">Company email</label>
                <input v-model="formData.company_email" type="email" class="field-input">
              </div>
              <div class="flex flex-col gap-1.5 md:col-span-2">
                <label class="field-label">Personal email</label>
                <input v-model="formData.personal_email" type="email" class="field-input">
              </div>
            </div>
          </div>

          <div class="flex flex-col gap-4">
            <p class="status-label">Address</p>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="flex flex-col gap-1.5">
                <label class="field-label">Current address</label>
                <textarea v-model="formData.current_address" rows="3" class="field-input"></textarea>
              </div>
              <div class="flex flex-col gap-1.5">
                <label class="field-label">Permanent address</label>
                <textarea v-model="formData.permanent_address" rows="3" class="field-input"></textarea>
              </div>
            </div>
          </div>

          <div class="flex flex-col gap-4">
            <p class="status-label">Emergency contact</p>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div class="flex flex-col gap-1.5">
                <label class="field-label">Contact person name</label>
                <input v-model="formData.emergency_contact_name" type="text" class="field-input">
              </div>
              <div class="flex flex-col gap-1.5">
                <label class="field-label">Phone number</label>
                <input v-model="formData.emergency_phone_number" type="tel" class="field-input">
              </div>
              <div class="flex flex-col gap-1.5">
                <label class="field-label">Relationship</label>
                <input v-model="formData.emergency_relation" type="text" class="field-input">
              </div>
            </div>
          </div>
        </div>

        <!-- User details Tab -->
        <div v-else-if="activeTab === 'user_details'" class="flex flex-col gap-6">
          <div class="flex flex-col gap-1.5 col-span-full">
            <label class="field-label">User image</label>
            <div class="flex items-center gap-4">
              <div class="w-16 h-16 rounded-full overflow-hidden bg-black/[0.04] dark:bg-white/[0.06] grid place-items-center shrink-0">
                <img v-if="formData.user_image" :src="formData.user_image" class="w-full h-full object-cover">
                <span v-else class="material-symbols-outlined text-[#656A72] dark:text-white/60 text-3xl">person</span>
              </div>
              <label class="btn-secondary !h-9 cursor-pointer"><span class="material-symbols-outlined !text-[18px]">upload</span>Upload photo<input type="file" accept="image/*" @change="handleUserImageUpload" class="sr-only"></label>
              <span v-if="userImageUploading" class="text-xs text-[#656A72] dark:text-white/55 flex items-center gap-1.5"><span class="w-3 h-3 rounded-full border-2 border-black/10 dark:border-white/15 border-t-accent animate-spin"></span>Uploading…</span>
            </div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="flex flex-col gap-4">
              <div class="flex flex-col gap-1.5">
                <label class="field-label">Email <span class="text-red-600 dark:text-red-400">*</span></label>
                <input v-model="formData.email" type="email" class="field-input">
                <p v-if="errors.email" class="field-error">{{ errors.email }}</p>
              </div>
              <div class="flex flex-col gap-1.5">
                <label class="field-label">Password <span class="text-red-600 dark:text-red-400">*</span></label>
                <div class="relative flex items-center">
                  <input v-model="formData.password" :type="showPassword ? 'text' : 'password'" class="field-input">
                  <button @click.prevent="showPassword = !showPassword" class="reveal-btn" title="Toggle Password Visibility">
                    <span class="material-symbols-outlined text-[18px]">{{ showPassword ? 'visibility_off' : 'visibility' }}</span>
                  </button>
                </div>
                <p v-if="errors.password" class="field-error">{{ errors.password }}</p>
              </div>
            </div>
            <div class="flex flex-col gap-4">
              <div class="flex flex-col gap-1.5">
                <label class="field-label">Username</label>
                <input v-model="formData.username" type="text" class="field-input">
              </div>
            </div>
          </div>
          <div class="text-[13px] text-[#5C6169] dark:text-white/65">
            First Name, Last Name, Gender, and Date of Birth will be automatically copied from the Employee Basic Details.
          </div>
        </div>

        <!-- User roles Tab -->
        <div v-else-if="activeTab === 'user_roles'" class="flex flex-col gap-4">
          <div class="flex flex-col sm:flex-row sm:items-center gap-2.5">
            <input v-model="searchRole" type="text" placeholder="Search roles" class="field-input">
            <div class="flex gap-2 w-full md:w-auto justify-end">
              <button @click="selectAllRoles" class="btn-ghost !h-9 !px-3">Select all</button>
              <button @click="unselectAllRoles" class="btn-ghost !h-9 !px-3">Clear</button>
            </div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4 max-h-[40vh] overflow-y-auto p-1">
            <div v-for="role in filteredRoles" :key="role" class="flex items-center gap-2">
              <input type="checkbox" :id="'role_'+role" :value="role" v-model="formData.roles" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40">
              <label :for="'role_'+role" class="field-label">{{ role }}</label>
            </div>
            <div v-if="filteredRoles.length === 0" class="col-span-full text-center text-[#656A72] dark:text-white/60 text-sm py-4">No roles found matching "{{ searchRole }}"</div>
          </div>
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
              <span v-if="submitting || isLoading" class="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></span>
              {{ (submitting || isLoading) ? 'Working…' : 'Save employee' }}
            </button>
          </div>
        </div>
      </div>
    </template>
    </Dialog>
    <CreateGenderForm v-model="showCreateGender" @save="teamStore.gendersResource.reload()" />
    <CreateSalutationForm v-model="showCreateSalutation" @save="teamStore.salutationsResource.reload()" />
    <CreateDesignationForm v-model="showCreateDesignation" @save="teamStore.designationsResource.reload()" />
    <CreateBranchForm v-model="showCreateBranch" @save="teamStore.branchesResource.reload()" />
    <CreateDepartmentForm v-model="showCreateDepartment" @save="teamStore.departmentsResource.reload()" />
    <CreateEmployeeGradeForm v-model="showCreateEmployeeGrade" @save="teamStore.employeeGradesResource.reload()" />
    <CreateEmployeeTypeForm v-model="showCreateEmployeeType" @save="teamStore.employmentTypesResource.reload()" />
    <CreateShiftTypeForm v-if="showCreateShiftType" @close="showCreateShiftType = false" @saved="teamStore.shiftTypesResource.reload(); showCreateShiftType = false" />
    <CreateHolidayListForm v-model="showCreateHolidayList" @save="leaveStore.fetchHolidayLists()" />
  </div>
</template>

<script setup>
import { notify } from '@/utils/feedback.js'
import { ref, computed } from 'vue';
import { Dialog, call } from 'frappe-ui';
import SearchableDropdown from '../../components/SearchableDropdown.vue';
import { useTeamStore } from '../../stores/team';
import CreateGenderForm from './create_gender.vue';
import CreateSalutationForm from './create_salutation.vue';
import CreateDesignationForm from './create_designation.vue';
import CreateBranchForm from './create_branch.vue';
import CreateDepartmentForm from './create_department.vue';
import CreateEmployeeGradeForm from './create_employee_grade.vue';
import CreateEmployeeTypeForm from './create_employee_type.vue';
import CreateShiftTypeForm from './roster/shift_type.vue';
import CreateHolidayListForm from './holiday/create_holiday_list.vue';
import { useLeaveStore } from '../../stores/leave';

const teamStore = useTeamStore();
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

const activeTab = ref('basic');
const userConnectionType = ref('');
const showCreateGender = ref(false);
const showCreateSalutation = ref(false);
const showCreateDesignation = ref(false);
const showCreateBranch = ref(false);
const showCreateDepartment = ref(false);
const showCreateEmployeeGrade = ref(false);
const showCreateEmployeeType = ref(false);
const showCreateShiftType = ref(false);
const showCreateHolidayList = ref(false);
const companyHasHolidayList = ref(true);
const showPassword = ref(false);
const searchRole = ref('');

const filteredRoles = computed(() => {
  const allRoles = teamStore.rolesResource?.data || [];
  if (!searchRole.value) return allRoles;
  const q = searchRole.value.toLowerCase();
  return allRoles.filter(r => r.toLowerCase().includes(q));
});

const selectAllRoles = () => {
  formData.value.roles = [...filteredRoles.value];
};

const unselectAllRoles = () => {
  formData.value.roles = [];
};

const getInitialFormData = () => ({
  user_id: '',
  email: '',
  password: '',
  username: '',
  roles: [],
  first_name: '',
  middle_name: '',
  last_name: '',
  gender: '',
  date_of_birth: '',
  salutation: '',
  image: '',
  user_image: '',
  employee_number: '',
  date_of_joining: '',
  status: 'Active',
  designation: '',
  branch: '',
  department: '',
  reports_to: '',
  grade: '',
  employee_type: '',
  cell_number: '',
  company_email: '',
  personal_email: '',
  current_address: '',
  permanent_address: '',
  emergency_contact_name: '',
  emergency_phone_number: '',
  emergency_relation: '',
  expense_approver: '',
  shift_approver: '',
  leave_approver: '',
  default_shift: '',
  holiday_list: ''
});

const formData = ref(getInitialFormData());
const imageUploading = ref(false);
const userImageUploading = ref(false);

const handleImageUpload = async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  
  imageUploading.value = true;
  const form = new FormData();
  form.append('file', file, file.name);
  form.append('is_private', 0);
  form.append('folder', 'Home/Attachments');
  
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
      formData.value.image = data.message.file_url;
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

const handleUserImageUpload = async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  userImageUploading.value = true;
  const uploadData = new FormData();
  uploadData.append('file', file, file.name);
  uploadData.append('is_private', 0);

  try {
    const response = await fetch('/api/method/upload_file', {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'X-Frappe-CSRF-Token': window.csrf_token || ''
      },
      body: uploadData
    });
    const result = await response.json();
    if (result.message && result.message.file_url) {
      formData.value.user_image = result.message.file_url;
    }
  } catch (err) {
    console.error('User image upload failed:', err);
  } finally {
    userImageUploading.value = false;
  }
};

const handleDepartmentChange = async (newDept) => {
  if (newDept) {
    try {
      const data = await call('arijentek_core.api.teams_permissons.get_department_list', { department_id: newDept });
      if (data) {
        if (data.expense_approver) formData.value.expense_approver = data.expense_approver;
        if (data.leave_approver) formData.value.leave_approver = data.leave_approver;
        if (data.shift_approver) formData.value.shift_approver = data.shift_approver;
      }
    } catch (e) {
      console.error('Failed to fetch department approvers:', e);
    }
  }
};

import { watch } from 'vue';

const isLoading = ref(false);
const initialUserId = ref('');
const initialUserName = ref('');

watch(show, async (newVal) => {
  if (newVal) {
    formData.value = getInitialFormData();
    userConnectionType.value = '';
    initialUserId.value = '';
    initialUserName.value = '';
    userConnectionType.value = '';
    activeTab.value = 'basic';
    submitError.value = '';
    searchRole.value = '';
    
    leaveStore.fetchHolidayLists();
    teamStore.unlinkedUsersResource.reload();
    teamStore.usersListResource.reload();
    teamStore.employeeListResource.reload();
    
    try {
      const hlRes = await call('frappe.client.get_list', {
        doctype: 'Holiday List Assignment',
        filters: { applicable_for: 'Company' },
        limit_page_length: 1
      });
      companyHasHolidayList.value = hlRes && hlRes.length > 0;
    } catch (e) {
      console.error(e);
      companyHasHolidayList.value = true;
    }

    if (props.editId) {
      isLoading.value = true;
      try {
        const data = await call('arijentek_core.api.teams_permissons.get_employee_list', { employee_id: props.editId });
        if (data) {
          formData.value = { ...formData.value, ...data };
          initialUserId.value = data.user_id || '';
          initialUserName.value = data.user_full_name || '';
          
          if (data.employment_type) formData.value.employee_type = data.employment_type;
          if (data.relation) formData.value.emergency_relation = data.relation;
          if (data.person_to_be_contacted) formData.value.emergency_contact_name = data.person_to_be_contacted;
          if (data.shift_request_approver) formData.value.shift_approver = data.shift_request_approver;
          if (data.reports_to) formData.value.reports_to = data.reports_to;
        }
        
        // Fetch employee's current holiday list assignment
        try {
          const empHlRes = await call('frappe.client.get_list', {
            doctype: 'Holiday List Assignment',
            filters: { applicable_for: 'Employee', assigned_to: props.editId },
            fields: ['holiday_list'],
            limit_page_length: 1
          });
          if (empHlRes && empHlRes.length > 0) {
            formData.value.holiday_list = empHlRes[0].holiday_list;
          }
        } catch (e) {
          console.error('Failed to fetch employee holiday list assignment', e);
        }
      } catch (err) {
        submitError.value = getErrorMessage(err, 'Failed to fetch employee details');
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

  // Basic Details validations
  if (!formData.value.first_name) {
    errors.value.first_name = 'First Name is mandatory';
    isValid = false;
    firstErrorTab = firstErrorTab || 'basic';
  }
  if (!formData.value.gender) {
    errors.value.gender = 'Gender is mandatory';
    isValid = false;
    firstErrorTab = firstErrorTab || 'basic';
  }
  if (!formData.value.date_of_birth) {
    errors.value.date_of_birth = 'Date of Birth is mandatory';
    isValid = false;
    firstErrorTab = firstErrorTab || 'basic';
  }
  if (!formData.value.date_of_joining) {
    errors.value.date_of_joining = 'Date of Joining is mandatory';
    isValid = false;
    firstErrorTab = firstErrorTab || 'basic';
  }



  // User connection validations
  if (userConnectionType.value === 'connect' && !formData.value.user_id) {
    errors.value.user_id = 'Please select a user to connect';
    isValid = false;
    firstErrorTab = firstErrorTab || 'basic';
  }
  
  if (userConnectionType.value === 'create') {
    if (!formData.value.email) {
      errors.value.email = 'Email is mandatory for User creation';
      isValid = false;
      firstErrorTab = firstErrorTab || 'user_details';
    }
    if (!formData.value.password) {
      errors.value.password = 'Password is mandatory for User creation';
      isValid = false;
      firstErrorTab = firstErrorTab || 'user_details';
    }
  }

  if (firstErrorTab) {
    activeTab.value = firstErrorTab;
  }

  return isValid;
};


import { getErrorMessage } from '../../utils.js';
import DateField from '../../components/DateField.vue'

const handleSave = async () => {
  submitError.value = '';
  if (validate()) {
    submitting.value = true;
    try {
      // Create user first if requested
      if (userConnectionType.value === 'create') {
        const userData = {
          email: formData.value.email,
          password: formData.value.password,
          username: formData.value.username,
          first_name: formData.value.first_name,
          middle_name: formData.value.middle_name,
          last_name: formData.value.last_name,
          gender: formData.value.gender,
          date_of_birth: formData.value.date_of_birth,
          roles: formData.value.roles,
          user_image: formData.value.user_image
        };
        const newUserId = await call('arijentek_core.api.teams_permissons.create_user', {
          user_data: userData
        });
        formData.value.user_id = newUserId;
      }
      
      const employeeId = await call('arijentek_core.api.teams_permissons.create_employee', {
        employee_data: formData.value
      });
      
      if (formData.value.holiday_list) {
        let hlFromDate = formData.value.date_of_joining;
        const hlDoc = (leaveStore.holidayLists || []).find(hl => hl.name === formData.value.holiday_list);
        if (hlDoc && hlDoc.from_date) {
          hlFromDate = hlDoc.from_date;
        }
        await call('arijentek_core.api.leave.save_holiday_list_assignment', {
          applicable_for: 'Employee',
          assigned_to: employeeId,
          holiday_list: formData.value.holiday_list,
          from_date: hlFromDate
        });
      }
      
      // Refresh unlinked users resource if we linked one
      if (userConnectionType.value !== '') {
        teamStore.unlinkedUsersResource.reload();
      }
      
      emit('save', formData.value);
      show.value = false;
    } catch (err) {
      submitError.value = getErrorMessage(err, 'Failed to create employee');
    } finally {
      submitting.value = false;
    }
  }
};
</script>

