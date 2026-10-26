<template>
  <Dialog :options="{ size: '4xl' }" v-model="show">
    <template #body>
      <div class="modal-panel">
        <!-- Modal Header -->
        <header class="modal-header">
          <div class="flex items-center gap-3 min-w-0">
            <div
              class="w-9 h-9 rounded-full bg-accent/10 dark:bg-accent-soft/15 text-accent dark:text-accent-soft flex items-center justify-center shrink-0 border border-accent/20"
            >
              <span class="material-symbols-outlined !text-xl">{{ editId ? 'manage_accounts' : 'person_add' }}</span>
            </div>
            <div class="min-w-0">
              <h3 class="modal-title">{{ editId ? 'Edit Team Member' : 'Add Team Member' }}</h3>
              <p class="text-[12px] text-[#5C6169] dark:text-white/60 truncate">
                {{ editId ? editId : 'Create login access, assign role personas, and link employee records' }}
              </p>
            </div>
          </div>
          <button @click="show = false" class="btn-icon-ghost shrink-0" aria-label="Close">
            <span class="material-symbols-outlined !text-[18px]">close</span>
          </button>
        </header>

        <!-- Modal Body -->
        <div class="flex-1 overflow-y-auto px-6 py-5 max-h-[75vh]">
          <!-- SUCCESS STATE (Shown immediately after creating a new team member) -->
          <div
            v-if="lastResult"
            class="p-6 rounded-2xl border border-accent/30 bg-accent/[0.04] dark:bg-accent/[0.06] space-y-4"
          >
            <div class="flex items-start gap-3.5">
              <span class="material-symbols-outlined text-accent !text-[28px] shrink-0 mt-0.5">verified</span>
              <div class="min-w-0 flex-1">
                <h4 class="text-base font-semibold text-[#17181B] dark:text-white">
                  {{ lastResult.user }} created successfully
                </h4>
                <p class="text-xs text-[#5C6169] dark:text-white/60 mt-1">
                  Assigned role(s):
                  <span class="font-semibold text-accent dark:text-accent-soft">
                    {{ (lastResult.role_profiles || []).map((p) => getPersonaLabel(p)).join(' + ') }}
                  </span>
                  <template v-if="lastResult.employee">
                    · Employee record <span class="font-semibold">{{ lastResult.employee }}</span> linked
                  </template>
                  · Lands on <span class="font-semibold">{{ getLandingLabel(lastResult.landing_route) }}</span> after sign-in.
                </p>

                <!-- Temporary Password Box -->
                <div
                  v-if="lastResult.generated_password"
                  class="mt-4 p-3.5 rounded-xl bg-white dark:bg-surface-2 border border-[#ECECF1] dark:border-white/[0.08] flex items-center justify-between gap-3 flex-wrap"
                >
                  <div>
                    <div class="text-[11px] font-semibold text-[#5C6169] dark:text-white/55">
                      Temporary Starter Password
                    </div>
                    <code
                      class="text-sm font-mono font-bold text-[#17181B] dark:text-white tracking-wider mt-0.5 block"
                    >{{ lastResult.generated_password }}</code>
                  </div>
                  <div class="flex items-center gap-2">
                    <button
                      type="button"
                      class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-accent/10 hover:bg-accent/20 text-accent dark:text-accent-soft border border-accent/20 transition cursor-pointer flex items-center gap-1"
                      @click="copyPassword"
                    >
                      <span class="material-symbols-outlined !text-[16px]">{{ copied ? 'check' : 'content_copy' }}</span>
                      {{ copied ? 'Copied' : 'Copy' }}
                    </button>
                  </div>
                </div>
                <p v-if="lastResult.generated_password" class="text-[11px] text-[#9AA0A8] dark:text-white/40 mt-1.5">
                  This password is only shown once. Share it with the team member immediately.
                </p>

                <div class="mt-6 flex items-center gap-2.5">
                  <button
                    type="button"
                    class="btn-primary"
                    @click="resetAll"
                  >
                    Add another member
                  </button>
                  <button
                    type="button"
                    class="btn-secondary"
                    @click="show = false"
                  >
                    Done
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- FORM STATE -->
          <form v-else class="space-y-6" @submit.prevent="submit">
            <!-- Server Error Message Banner -->
            <div
              v-if="submitError"
              class="flex items-start gap-2.5 p-3 rounded-[12px] bg-red-500/[0.08] dark:bg-red-500/[0.15] border border-red-500/20"
              role="alert"
            >
              <span class="material-symbols-outlined !text-[18px] text-red-600 dark:text-red-400 shrink-0">error</span>
              <div class="flex-1 min-w-0">
                <p class="text-[13px] font-medium text-red-700 dark:text-red-300 leading-snug break-words">
                  {{ submitError }}
                </p>
              </div>
              <button
                @click="submitError = ''"
                type="button"
                class="text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-200"
              >
                <span class="material-symbols-outlined !text-[16px]">close</span>
              </button>
            </div>

            <!-- Loading Skeleton while options or edit data is fetching -->
            <div v-if="loadingData" class="space-y-4 animate-pulse py-4">
              <div class="h-4 bg-black/[0.06] dark:bg-white/[0.08] rounded w-1/4"></div>
              <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div class="h-24 bg-black/[0.04] dark:bg-white/[0.05] rounded-xl"></div>
                <div class="h-24 bg-black/[0.04] dark:bg-white/[0.05] rounded-xl"></div>
                <div class="h-24 bg-black/[0.04] dark:bg-white/[0.05] rounded-xl"></div>
              </div>
              <div class="h-10 bg-black/[0.04] dark:bg-white/[0.05] rounded-xl"></div>
            </div>

            <template v-else>
              <!-- 1 · Persona(s) Selection -->
              <div>
                <div class="flex items-center justify-between gap-2 mb-2">
                  <label class="block text-xs font-semibold text-[#17181B] dark:text-white">
                    Role & Persona <span class="text-[#B91C1C]">*</span>
                  </label>
                  <span class="text-xs text-[#9AA0A8] dark:text-white/45">
                    Pick one or more personas to combine access
                  </span>
                </div>

                <!-- Persona Quick Search -->
                <div class="relative mb-3">
                  <span
                    class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#9AA0A8] pointer-events-none"
                  >search</span>
                  <input
                    v-model="searchPersona"
                    type="text"
                    placeholder="Search roles by title, keyword, or permission..."
                    class="w-full pl-9 pr-3 py-2 text-xs rounded-xl border border-[#ECECF1] dark:border-white/[0.08] bg-[#F5F5F8] dark:bg-surface-3 text-[#17181B] dark:text-white placeholder-[#9AA0A8] dark:placeholder-white/40 focus:bg-white dark:focus:bg-surface-2 focus:ring-2 focus:ring-accent/20 focus:border-accent outline-none transition"
                  />
                </div>

                <!-- Persona Grid -->
                <div class="max-h-[44vh] overflow-y-auto pr-1 pb-1">
                  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
                    <div
                      v-for="persona in filteredPersonas"
                      :key="persona.name"
                      class="relative"
                    >
                      <button
                        type="button"
                        class="w-full h-full text-left p-3 rounded-xl border transition cursor-pointer group text-xs flex flex-col justify-between"
                        :class="
                          isPersonaSelected(persona.name)
                            ? 'border-accent ring-1 ring-accent bg-accent/[0.08] dark:bg-accent/[0.12]'
                            : 'border-[#ECECF1] dark:border-white/[0.08] bg-white dark:bg-surface-2 hover:border-accent/40 hover:bg-[#FAFAFC] dark:hover:bg-white/[0.03]'
                        "
                        @click="togglePersona(persona.name)"
                      >
                        <div class="w-full">
                          <div class="flex items-start justify-between gap-1.5">
                            <div class="min-w-0 flex-1">
                              <div class="flex items-center gap-1.5 flex-wrap">
                                <p class="font-semibold text-[#17181B] dark:text-white truncate">
                                  {{ persona.label || persona.name }}
                                </p>
                                <span
                                  v-if="persona.custom"
                                  class="shrink-0 px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase tracking-wider bg-black/[0.06] dark:bg-white/[0.12] text-[#5C6169] dark:text-white/70"
                                >
                                  Custom
                                </span>
                                <span
                                  v-if="persona.tier && persona.tier !== 'standard'"
                                  class="shrink-0 px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase tracking-wider"
                                  :class="
                                    persona.tier === 'desk'
                                      ? 'bg-[#B45309]/10 text-[#B45309] dark:bg-[#F59E0B]/15 dark:text-[#FBBF24]'
                                      : 'bg-accent/15 text-accent dark:text-accent-soft'
                                  "
                                >
                                  {{ persona.tier === 'desk' ? 'Desk' : 'Admin' }}
                                </span>
                              </div>
                              <p class="text-[11px] text-[#5C6169] dark:text-white/55 mt-0.5 line-clamp-1">
                                {{ persona.description }}
                              </p>
                            </div>
                            <div
                              class="w-4.5 h-4.5 rounded-full flex items-center justify-center shrink-0 transition-all border mt-0.5"
                              :class="
                                isPersonaSelected(persona.name)
                                  ? 'bg-accent border-accent text-white shadow-xs'
                                  : 'border-[#D1D5DB] dark:border-white/20 bg-transparent group-hover:border-accent/50'
                              "
                            >
                              <span
                                v-if="isPersonaSelected(persona.name)"
                                class="material-symbols-outlined !text-[13px] font-bold text-white leading-none"
                              >check</span>
                            </div>
                          </div>

                          <div class="flex flex-wrap gap-1 mt-2">
                            <span
                              v-for="role in (persona.roles || []).slice(0, 3)"
                              :key="role"
                              class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-[#F5F5F8] dark:bg-surface-3 text-[#5C6169] dark:text-white/65"
                            >
                              {{ role }}
                            </span>
                            <span
                              v-if="(persona.roles || []).length > 3"
                              class="text-[10px] text-[#9AA0A8] dark:text-white/40 self-center"
                            >
                              +{{ persona.roles.length - 3 }}
                            </span>
                          </div>
                        </div>

                        <div class="text-[10px] text-[#9AA0A8] dark:text-white/40 mt-2 flex items-center gap-1">
                          <span>Landing:</span>
                          <span class="font-medium text-accent dark:text-accent-soft">
                            {{ getLandingLabel(persona.landing) }}
                          </span>
                        </div>
                      </button>
                    </div>
                  </div>

                  <div
                    v-if="!filteredPersonas.length"
                    class="py-6 text-center text-xs text-[#9AA0A8] dark:text-white/40"
                  >
                    No personas match "{{ searchPersona }}"
                  </div>
                </div>

                <!-- Combined Permissions Preview Box -->
                <div
                  v-if="form.role_profiles.length > 0"
                  class="mt-3 rounded-xl border border-accent/30 bg-accent/[0.05] dark:bg-accent/[0.08] p-3 text-xs"
                >
                  <p class="text-[11px] font-semibold text-accent dark:text-accent-soft">
                    {{ form.role_profiles.length > 1 ? `${form.role_profiles.length} personas combined — granted permissions:` : 'Granted permissions:' }}
                  </p>
                  <div class="flex flex-wrap gap-1 mt-1.5">
                    <span
                      v-for="role in unionRoles"
                      :key="role"
                      class="px-2 py-0.5 rounded-full text-[10px] font-medium bg-[#F5F5F8] dark:bg-surface-3 text-[#5C6169] dark:text-white/70"
                    >
                      {{ role }}
                    </span>
                  </div>
                  <p class="text-[10px] text-[#9AA0A8] dark:text-white/40 mt-1.5">
                    Lands on <span class="font-semibold text-accent">{{ unionLanding }}</span> after sign-in.
                  </p>
                </div>
                <p v-if="errors.role_profiles" class="field-error">{{ errors.role_profiles }}</p>
              </div>

              <!-- 2 · Member Profile & Credentials -->
              <div class="pt-5 border-t border-[#ECECF1] dark:border-white/[0.08]">
                <h4 class="text-xs font-semibold uppercase tracking-wider text-[#5C6169] dark:text-white/50 mb-3">
                  Member Profile & Credentials
                </h4>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label class="field-label">
                      First name <span class="text-[#B91C1C]">*</span>
                    </label>
                    <input
                      v-model="form.first_name"
                      type="text"
                      placeholder="e.g. Jordan"
                      class="field-input"
                    />
                    <p v-if="errors.first_name" class="field-error">{{ errors.first_name }}</p>
                  </div>

                  <div>
                    <label class="field-label">Last name</label>
                    <input
                      v-model="form.last_name"
                      type="text"
                      placeholder="e.g. Rivera"
                      class="field-input"
                    />
                  </div>

                  <div>
                    <label class="field-label">
                      Email <span class="text-[#B91C1C]">*</span>
                    </label>
                    <input
                      v-model="form.email"
                      type="email"
                      placeholder="jordan@gemora.com"
                      :disabled="!!editId"
                      class="field-input"
                      :class="{ 'opacity-70 cursor-not-allowed': !!editId }"
                    />
                    <p v-if="errors.email" class="field-error">{{ errors.email }}</p>
                  </div>

                  <div>
                    <label class="field-label">
                      {{ editId ? 'Reset Password (optional)' : 'Starter password' }}
                    </label>
                    <div class="flex items-center gap-2">
                      <input
                        v-model="form.password"
                        :type="showPassword ? 'text' : 'password'"
                        :disabled="!editId && autoPassword"
                        :placeholder="!editId && autoPassword ? 'Auto-generated on save' : (editId ? 'Leave blank to keep current' : 'At least 6 characters')"
                        class="field-input"
                        :class="(!editId && autoPassword) ? 'opacity-60 cursor-not-allowed' : ''"
                      />
                      <button
                        v-if="editId || !autoPassword"
                        type="button"
                        class="px-2.5 py-2.5 rounded-xl bg-[#F5F5F8] dark:bg-surface-3 border border-[#ECECF1] dark:border-white/[0.08] transition cursor-pointer text-[#5C6169] dark:text-white/60 hover:text-[#17181B] dark:hover:text-white shrink-0"
                        @click="showPassword = !showPassword"
                      >
                        <span class="material-symbols-outlined !text-[18px]">
                          {{ showPassword ? 'visibility_off' : 'visibility' }}
                        </span>
                      </button>
                    </div>

                    <label
                      v-if="!editId"
                      class="flex items-center gap-2 mt-2 cursor-pointer select-none"
                    >
                      <input
                        v-model="autoPassword"
                        type="checkbox"
                        class="accent-accent cursor-pointer rounded"
                      />
                      <span class="text-xs text-[#5C6169] dark:text-white/60">
                        Generate a strong password automatically
                      </span>
                    </label>
                    <p v-if="errors.password" class="field-error">{{ errors.password }}</p>
                  </div>

                  <!-- Gender & Date of birth (Required if creating an employee record) -->
                  <div v-if="form.employee_mode === 'create'">
                    <label class="field-label">
                      Gender <span class="text-[#B91C1C]">*</span>
                    </label>
                    <SearchableDropdown
                      v-model="form.gender"
                      :options="overviewOptions.genders || []"
                      placeholder="Select gender…"
                    />
                    <p v-if="errors.gender" class="field-error">{{ errors.gender }}</p>
                  </div>

                  <div v-if="form.employee_mode === 'create'">
                    <label class="field-label">
                      Date of birth <span class="text-[#B91C1C]">*</span>
                    </label>
                    <input
                      v-model="form.date_of_birth"
                      type="date"
                      class="field-input"
                    />
                    <p v-if="errors.date_of_birth" class="field-error">{{ errors.date_of_birth }}</p>
                  </div>
                </div>
              </div>

              <!-- 3 · Optional Details Collapsible Accordion -->
              <div class="rounded-2xl border border-[#ECECF1] dark:border-white/[0.08] bg-white dark:bg-surface-2 overflow-hidden">
                <button
                  type="button"
                  class="w-full flex items-center justify-between px-4 py-3.5 text-xs font-semibold text-[#17181B] dark:text-white hover:bg-black/[0.02] dark:hover:bg-white/[0.03] transition cursor-pointer"
                  @click="showOptional = !showOptional"
                >
                  <span class="flex items-center gap-2">
                    <span class="material-symbols-outlined !text-base text-accent dark:text-accent-soft">storefront</span>
                    Optional — Department, designation, and store access
                  </span>
                  <span
                    class="material-symbols-outlined !text-base transition-transform"
                    :class="{ 'rotate-180': showOptional }"
                  >
                    expand_more
                  </span>
                </button>

                <div v-if="showOptional" class="p-4 space-y-4 border-t border-[#ECECF1] dark:border-white/[0.08]">
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label class="field-label">Department</label>
                      <SearchableDropdown
                        v-model="form.department"
                        :options="overviewOptions.departments || []"
                        placeholder="Any department"
                      />
                    </div>
                    <div>
                      <label class="field-label">Designation</label>
                      <SearchableDropdown
                        v-model="form.designation"
                        :options="overviewOptions.designations || []"
                        placeholder="Any designation"
                      />
                    </div>
                  </div>

                  <!-- Store Access (POS Profiles) -->
                  <div>
                    <label class="field-label mb-2">
                      Store Access (POS profiles this member can sell from)
                    </label>
                    <div class="flex flex-wrap gap-2">
                      <label
                        v-for="p in posProfileOptions"
                        :key="p.value"
                        class="flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs cursor-pointer transition select-none"
                        :class="
                          form.pos_profiles.includes(p.value)
                            ? 'border-accent bg-accent/10 text-accent dark:text-accent-soft font-semibold'
                            : 'border-[#ECECF1] dark:border-white/[0.08] bg-[#F5F5F8] dark:bg-surface-3 text-[#5C6169] dark:text-white/70 hover:border-accent/40'
                        "
                      >
                        <input
                          type="checkbox"
                          class="accent-accent cursor-pointer"
                          :checked="form.pos_profiles.includes(p.value)"
                          @change="togglePosProfile(p.value)"
                        />
                        {{ p.label }}
                      </label>
                      <p
                        v-if="!posProfileOptions.length"
                        class="text-xs text-[#9AA0A8] dark:text-white/40"
                      >
                        No POS profiles configured.
                      </p>
                    </div>
                  </div>

                  <!-- Employee Record Mode (Only for new users) -->
                  <div v-if="!editId">
                    <label class="field-label mb-2">Employee Record</label>
                    <div class="flex flex-wrap gap-2">
                      <label
                        v-for="mode in employeeModes"
                        :key="mode.value"
                        class="flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs cursor-pointer transition select-none"
                        :class="
                          form.employee_mode === mode.value
                            ? 'border-accent bg-accent/10 text-accent dark:text-accent-soft font-semibold'
                            : 'border-[#ECECF1] dark:border-white/[0.08] bg-[#F5F5F8] dark:bg-surface-3 text-[#5C6169] dark:text-white/70 hover:border-accent/40'
                        "
                      >
                        <input
                          v-model="form.employee_mode"
                          type="radio"
                          :value="mode.value"
                          class="accent-accent cursor-pointer"
                        />
                        {{ mode.label }}
                      </label>
                    </div>

                    <div v-if="form.employee_mode === 'link'" class="mt-3">
                      <SearchableDropdown
                        v-model="form.employee_id"
                        :options="unlinkedEmployeeOptions"
                        placeholder="Pick existing employee…"
                      />
                      <p v-if="errors.employee_id" class="field-error">{{ errors.employee_id }}</p>
                    </div>
                  </div>
                  <div v-else-if="initialEmployeeId" class="flex items-center gap-2 text-xs text-[#17181B] dark:text-white">
                    <span class="material-symbols-outlined !text-[16px] text-green-600 dark:text-green-400">link</span>
                    Linked to employee: <span class="font-semibold">{{ initialEmployeeName || initialEmployeeId }}</span>
                    <span class="text-[#656A72] dark:text-white/55 tabular-nums">({{ initialEmployeeId }})</span>
                  </div>
                </div>
              </div>

              <!-- Footer Actions -->
              <div class="flex items-center justify-between gap-3 pt-2">
                <p class="text-xs text-[#9AA0A8] dark:text-white/40">
                  {{ editId ? 'Updates user access and role personas in one action.' : 'Creates the login user, employee record, roles and store landing route in one action.' }}
                </p>
                <div class="flex items-center gap-2">
                  <button
                    type="button"
                    class="btn-secondary"
                    @click="show = false"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    :disabled="submitting || !form.role_profiles.length"
                    class="btn-primary flex items-center gap-2"
                  >
                    <span
                      v-if="submitting"
                      class="material-symbols-outlined !text-[16px] animate-spin"
                    >progress_activity</span>
                    {{ submitting ? (editId ? 'Saving…' : 'Creating…') : (editId ? 'Save Changes' : 'Create Team Member') }}
                  </button>
                </div>
              </div>
            </template>
          </form>
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue';
import { Dialog, call } from 'frappe-ui';
import SearchableDropdown from '@/components/SearchableDropdown.vue';
import { useTeamStore } from '@/stores/team';
import { notify } from '@/utils/feedback.js';
import { getErrorMessage } from '@/utils.js';

// --- Friendly Persona & Route Labels ---
const PERSONA_LABELS = {
  'Store Manager': 'Store Manager',
  'Sales': 'POS Cashier',
  'Inventory': 'Inventory & Stock',
  'HR': 'HR & People Ops',
  'Admin User': 'Owner / Admin',
  'Gemora Super Admin': 'Gemora Super Admin',
  'Gemora Developer': 'Gemora Developer',
};

const LANDING_LABELS = {
  '/': 'Dashboard',
  '/terminal': 'POS Register',
  '/inventory': 'Inventory',
  '/repairs': 'Repairs',
  '/reports': 'Reports',
  '/app': 'Admin Desk',
};

function getLandingLabel(route) {
  return LANDING_LABELS[route] || route || 'Dashboard';
}

function getPersonaLabel(name) {
  const match = personas.value.find((p) => p.name === name);
  return match?.label || PERSONA_LABELS[name] || name;
}

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  editId: {
    type: String,
    default: '',
  },
});

const emit = defineEmits(['update:modelValue', 'save']);

const teamStore = useTeamStore();

const show = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
});

// --- State ---
const employeeModes = [
  { value: 'create', label: 'Create new employee' },
  { value: 'link', label: 'Link existing employee' },
  { value: 'none', label: 'No employee record' },
];

const blankForm = () => ({
  role_profiles: [],
  first_name: '',
  last_name: '',
  email: '',
  password: '',
  gender: '',
  date_of_birth: '',
  employee_mode: 'create',
  employee_id: '',
  department: '',
  designation: '',
  pos_profiles: [],
});

const form = reactive(blankForm());
const errors = reactive({});
const submitError = ref('');
const submitting = ref(false);
const loadingData = ref(false);
const showOptional = ref(false);
const showPassword = ref(false);
const autoPassword = ref(true);
const searchPersona = ref('');
const lastResult = ref(null);
const copied = ref(false);

const initialEmployeeId = ref('');
const initialEmployeeName = ref('');

// In-memory cached catalog & options so modal reopens instantly
const personas = ref([]);
const overviewOptions = reactive({
  genders: [],
  departments: [],
  designations: [],
  pos_profiles: [],
  unlinked_employees: [],
});

// --- Options Computeds ---
const posProfileOptions = computed(() =>
  (overviewOptions.pos_profiles || []).map((p) => ({
    label: p.name,
    value: p.name,
  }))
);

const unlinkedEmployeeOptions = computed(() =>
  (overviewOptions.unlinked_employees || []).map((e) => ({
    label: `${e.name} — ${e.employee_name || e.name}`,
    value: e.name,
  }))
);

const filteredPersonas = computed(() => {
  const q = searchPersona.value.trim().toLowerCase();
  return personas.value.filter((p) => {
    if (!q) return true;
    return (
      (p.label && p.label.toLowerCase().includes(q)) ||
      p.name.toLowerCase().includes(q) ||
      (p.description && p.description.toLowerCase().includes(q)) ||
      (p.roles && p.roles.some((r) => r.toLowerCase().includes(q)))
    );
  });
});

const isPersonaSelected = (name) => form.role_profiles.includes(name);

function togglePersona(name) {
  const idx = form.role_profiles.indexOf(name);
  if (idx === -1) {
    form.role_profiles.push(name);
  } else {
    form.role_profiles.splice(idx, 1);
  }
}

function togglePosProfile(name) {
  const i = form.pos_profiles.indexOf(name);
  if (i === -1) {
    form.pos_profiles.push(name);
  } else {
    form.pos_profiles.splice(i, 1);
  }
}

// Union of all roles granted by the selected personas
const selectedSpecs = computed(() =>
  form.role_profiles
    .map((name) => personas.value.find((p) => p.name === name))
    .filter(Boolean)
);

const unionRoles = computed(() => {
  return [...new Set(selectedSpecs.value.flatMap((p) => p.roles || []))];
});

const unionLanding = computed(() => {
  const first = selectedSpecs.value[0];
  return getLandingLabel(first?.landing || '/');
});

// --- Data Fetching ---
async function loadCatalogAndOptions() {
  try {
    const [catalogData, overviewData] = await Promise.all([
      call('arijentek_core.api.staff_access.get_staff_catalog'),
      call('arijentek_core.api.staff_access.get_staff_overview'),
    ]);

    if (Array.isArray(catalogData)) {
      personas.value = catalogData;
    }

    if (overviewData?.options) {
      overviewOptions.genders = overviewData.options.genders || [];
      overviewOptions.departments = overviewData.options.departments || [];
      overviewOptions.designations = overviewData.options.designations || [];
      overviewOptions.pos_profiles = overviewData.options.pos_profiles || [];
      overviewOptions.unlinked_employees = overviewData.options.unlinked_employees || [];
    }
  } catch (err) {
    console.warn('Failed to load full staff access catalog, falling back to teamStore lists:', err);
    // Fallback gracefully to existing team store options
    if (teamStore.gendersResource?.data) overviewOptions.genders = teamStore.gendersResource.data;
    if (teamStore.departmentsResource?.data) overviewOptions.departments = teamStore.departmentsResource.data;
    if (teamStore.designationsResource?.data) overviewOptions.designations = teamStore.designationsResource.data;
  }
}

// Reset form to blank
function resetAll() {
  Object.assign(form, blankForm());
  Object.keys(errors).forEach((k) => delete errors[k]);
  submitError.value = '';
  searchPersona.value = '';
  showOptional.value = false;
  autoPassword.value = true;
  showPassword.value = false;
  lastResult.value = null;
  copied.value = false;
}

// --- Watcher on modal open ---
watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return;

    resetAll();
    loadingData.value = true;

    try {
      await loadCatalogAndOptions();

      // If Edit Mode, load existing user details
      if (props.editId) {
        autoPassword.value = false;
        const data = await call('arijentek_core.api.teams_permissons.get_users_details', {
          user_id: props.editId,
        });

        if (data) {
          form.first_name = data.first_name || '';
          form.last_name = data.last_name || '';
          form.email = data.email || props.editId;
          form.gender = data.gender || '';
          form.date_of_birth = data.birth_date || '';

          if (data.role_profiles && Array.isArray(data.role_profiles)) {
            form.role_profiles = [...data.role_profiles];
          } else if (data.role_profile_name) {
            form.role_profiles = [data.role_profile_name];
          }

          if (data.employee_id) {
            initialEmployeeId.value = data.employee_id;
            initialEmployeeName.value = data.employee_name || '';
            form.employee_mode = 'link';
            form.employee_id = data.employee_id;
          } else {
            form.employee_mode = 'none';
          }
        }
      }
    } catch (err) {
      submitError.value = getErrorMessage(err, 'Failed to load user information.');
    } finally {
      loadingData.value = false;
    }
  }
);

// --- Validation ---
function validate() {
  Object.keys(errors).forEach((k) => delete errors[k]);

  if (!form.role_profiles.length) {
    errors.role_profiles = 'Pick at least one role.';
  }
  if (!form.first_name.trim()) {
    errors.first_name = 'First name is required.';
  }
  if (!form.email.trim()) {
    errors.email = 'Email is required.';
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
    errors.email = 'Enter a valid email address.';
  }

  if (!props.editId) {
    if (!autoPassword.value && form.password && form.password.length < 6) {
      errors.password = 'Password must be at least 6 characters.';
    }
    if (!autoPassword.value && !form.password) {
      errors.password = 'Password is required when auto-generation is disabled.';
    }

    if (form.employee_mode === 'create') {
      if (!form.gender) errors.gender = 'Gender is required for the employee record.';
      if (!form.date_of_birth) errors.date_of_birth = 'Date of birth is required for the employee record.';
    }
    if (form.employee_mode === 'link' && !form.employee_id) {
      errors.employee_id = 'Pick the employee record to link.';
    }
  }

  return !Object.keys(errors).length;
}

// --- Submit ---
async function submit() {
  submitError.value = '';
  if (!validate()) return;

  submitting.value = true;
  try {
    if (props.editId) {
      // 1. Update existing User Details via teams_permissons / staff_access
      await call('arijentek_core.api.teams_permissons.create_user', {
        user_data: {
          name: props.editId,
          email: form.email.trim(),
          first_name: form.first_name.trim(),
          last_name: form.last_name.trim(),
          gender: form.gender,
          date_of_birth: form.date_of_birth,
          password: form.password || undefined,
        },
      });

      // 2. Update role personas if changed
      if (form.role_profiles.length) {
        await call('arijentek_core.api.staff_access.update_staff_member', {
          payload: {
            user: props.editId,
            role_profiles: [...form.role_profiles],
            password: form.password || undefined,
            department: form.department || undefined,
            designation: form.designation || undefined,
          },
        });
      }

      notify('Team member updated successfully', 'success');
      emit('save', { user: props.editId });
      show.value = false;
    } else {
      // Create new Team Member using the atomic staff_access transaction
      const payload = {
        role_profiles: [...form.role_profiles],
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        email: form.email.trim(),
        password: autoPassword.value ? '' : form.password,
        gender: form.gender,
        date_of_birth: form.date_of_birth,
        employee_mode: form.employee_mode,
        employee_id: form.employee_id,
        department: form.department,
        designation: form.designation,
        pos_profiles: form.pos_profiles,
      };

      const res = await call('arijentek_core.api.staff_access.create_staff_member', { payload });
      lastResult.value = res;
      notify(`${res.user} created successfully`, 'success');
      emit('save', res);

      // Reload team store resources in background
      if (teamStore.unlinkedEmployeesResource) teamStore.unlinkedEmployeesResource.reload();
      if (teamStore.usersListResource) teamStore.usersListResource.reload();
      if (teamStore.employeeListResource) teamStore.employeeListResource.reload();
    }
  } catch (err) {
    submitError.value = getErrorMessage(err, 'Failed to save team member.');
  } finally {
    submitting.value = false;
  }
}

// --- Copy Password ---
async function copyPassword() {
  try {
    if (lastResult.value?.generated_password) {
      await navigator.clipboard.writeText(lastResult.value.generated_password);
      copied.value = true;
      setTimeout(() => {
        copied.value = false;
      }, 1500);
    }
  } catch {
    // Clipboard permission blocked - user can still copy manually
  }
}
</script>
