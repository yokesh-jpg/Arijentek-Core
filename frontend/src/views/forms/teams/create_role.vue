<template>
  <Dialog :options="{ size: '4xl' }" v-model="show" :disableOutsideClickToClose="true">
    <template #body>
      <div class="modal-panel">
        <!-- Custom Header -->
        <header class="modal-header">
          <div>
            <h3 class="modal-title">{{ editRoleName ? 'Edit role' : 'Add new role' }}</h3>
            <p class="text-[12px] text-[#656A72] dark:text-white/60">Define role and assign permissions</p>
          </div>
          <button @click="show = false" class="btn-icon-ghost shrink-0" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span>
          </button>
        </header>

        <!-- Main Content -->
        <div class="flex-1 px-5 py-5 overflow-y-auto flex flex-col gap-5">
          <div class="flex flex-col gap-4">
            <div class="flex flex-col gap-1.5 max-w-md">
              <label class="field-label">Role name <span class="text-red-600 dark:text-red-400">*</span></label>
              <input 
                type="text" 
                v-model="formData.role_name" 
                class="field-input"
                :class="{ '!border-red-500/60': errors.role_name, 'opacity-60 cursor-not-allowed': editRoleName }"
                :disabled="!!editRoleName"
                placeholder="e.g. Sales Manager"
              >
              <p v-if="errors.role_name" class="field-error">{{ errors.role_name }}</p>
            </div>
            
            <div class="modal-section flex flex-col gap-3">
              <p class="status-label flex items-center justify-between">
                <span>Permissions</span>
                <span v-if="loadingDoctypes" class="normal-case tracking-normal font-normal text-[#656A72] dark:text-white/55">Loading…</span>
              </p>
              
              <div class="relative max-w-md">
                <span class="material-symbols-outlined !text-[18px] absolute left-3.5 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/60 pointer-events-none">search</span>
                <input v-model="searchQuery" type="text" placeholder="Search record types" class="field-input !pl-10" aria-label="Search record types">
              </div>
            </div>
            
            <div class="table-card overflow-x-auto table-scroll">
              <table class="w-full" v-if="filteredDoctypes.length">
                <thead>
                  <tr class="border-b border-black/[0.07] dark:border-white/10">
                    <th class="table-th">Record type</th>
                    <th class="table-th !text-center">
                      <div class="flex flex-col items-center gap-1">
                        <span>All</span>
                        <input type="checkbox" :checked="isGlobalSelected('all')" @change="toggleGlobal('all', $event.target.checked)" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40">
                      </div>
                    </th>
                    <th class="table-th !text-center">
                      <div class="flex flex-col items-center gap-1">
                        <span>Read</span>
                        <input type="checkbox" :checked="isGlobalSelected('read')" @change="toggleGlobal('read', $event.target.checked)" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40">
                      </div>
                    </th>
                    <th class="table-th !text-center">
                      <div class="flex flex-col items-center gap-1">
                        <span>Create</span>
                        <input type="checkbox" :checked="isGlobalSelected('create')" @change="toggleGlobal('create', $event.target.checked)" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40">
                      </div>
                    </th>
                    <th class="table-th !text-center">
                      <div class="flex flex-col items-center gap-1">
                        <span>Edit</span>
                        <input type="checkbox" :checked="isGlobalSelected('write')" @change="toggleGlobal('write', $event.target.checked)" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40">
                      </div>
                    </th>
                    <th class="table-th !text-center">
                      <div class="flex flex-col items-center gap-1">
                        <span>Delete</span>
                        <input type="checkbox" :checked="isGlobalSelected('delete')" @change="toggleGlobal('delete', $event.target.checked)" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40">
                      </div>
                    </th>
                    <th class="table-th !text-center">
                      <div class="flex flex-col items-center gap-1">
                        <span>Submit</span>
                        <input type="checkbox" :checked="isGlobalSelected('submit')" @change="toggleGlobal('submit', $event.target.checked)" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40">
                      </div>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="doctype in filteredDoctypes" :key="doctype" class="border-b last:border-0 border-black/[0.05] dark:border-white/[0.06] hover:bg-black/[0.02] dark:hover:bg-white/[0.04] transition-colors">
                    <td class="table-td-strong">{{ doctype }}</td>
                    <td class="table-td !text-center">
                      <input type="checkbox" :checked="isAllSelected(doctype)" @change="toggleAll(doctype, $event.target.checked)" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40">
                    </td>
                    <td class="table-td !text-center">
                      <input type="checkbox" v-model="permissions[doctype].read" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40">
                    </td>
                    <td class="table-td !text-center">
                      <input type="checkbox" v-model="permissions[doctype].create" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40">
                    </td>
                    <td class="table-td !text-center">
                      <input type="checkbox" v-model="permissions[doctype].write" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40">
                    </td>
                    <td class="table-td !text-center">
                      <input type="checkbox" v-model="permissions[doctype].delete" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40">
                    </td>
                    <td class="table-td !text-center">
                      <input type="checkbox" v-model="permissions[doctype].submit" class="w-4 h-4 rounded border-black/20 dark:border-white/25 text-accent focus:ring-accent/40">
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
        
        <!-- Actions -->
        <div class="modal-footer justify-between">
          <div class="text-[13px] min-w-0">
            <span v-if="submitError" class="text-red-700 dark:text-red-400 flex items-center gap-1.5"><span class="material-symbols-outlined !text-[16px]">error</span>{{ submitError }}</span>
            <span v-else-if="showLongSaveMessage" class="text-amber-800 dark:text-amber-300 flex items-center gap-1.5"><span class="material-symbols-outlined !text-[16px]">hourglass_top</span>Saving a large selection — this can take a moment.</span>
          </div>
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
              {{ submitting ? 'Saving…' : 'Save role' }}
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
import { getErrorMessage } from '@/utils.js';

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  editRoleName: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['save', 'update:modelValue']);

const show = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
});

const formData = ref({
  role_name: ''
});
const errors = ref({});
const doctypes = ref([]);
const loadingDoctypes = ref(false);
const permissions = ref({});
const submitting = ref(false);
const showLongSaveMessage = ref(false);
const submitError = ref('');
let longSaveTimer = null;

const fetchDoctypes = async () => {
  loadingDoctypes.value = true;
  try {
    const data = await call('arijentek_core.api.teams_permissons.get_doctypes');
    if (data) {
      doctypes.value = data;
      const perms = {};
      data.forEach(d => {
        perms[d] = {
          read: false,
          create: false,
          write: false,
          delete: false,
          submit: false
        };
      });
      permissions.value = perms;
    }
  } catch (err) {
    console.error(getErrorMessage(err, 'Failed to load doctypes'));
  } finally {
    loadingDoctypes.value = false;
  }
};

const isAllSelected = (doctype) => {
  const p = permissions.value[doctype];
  return p && p.read && p.create && p.write && p.delete && p.submit;
};

const toggleAll = (doctype, checked) => {
  if (permissions.value[doctype]) {
    permissions.value[doctype].read = checked;
    permissions.value[doctype].create = checked;
    permissions.value[doctype].write = checked;
    permissions.value[doctype].delete = checked;
    permissions.value[doctype].submit = checked;
  }
};

const searchQuery = ref('');

const filteredDoctypes = computed(() => {
  if (!searchQuery.value) return doctypes.value;
  const q = searchQuery.value.toLowerCase();
  return doctypes.value.filter(d => d.toLowerCase().includes(q));
});

const isGlobalSelected = (permType) => {
  if (!filteredDoctypes.value.length) return false;
  return filteredDoctypes.value.every(doctype => {
    const p = permissions.value[doctype];
    if (!p) return false;
    if (permType === 'all') {
      return p.read && p.create && p.write && p.delete && p.submit;
    }
    return p[permType];
  });
};

const toggleGlobal = (permType, checked) => {
  filteredDoctypes.value.forEach(doctype => {
    const p = permissions.value[doctype];
    if (p) {
      if (permType === 'all') {
        p.read = checked;
        p.create = checked;
        p.write = checked;
        p.delete = checked;
        p.submit = checked;
      } else {
        p[permType] = checked;
      }
    }
  });
};

watch(show, async (newVal) => {
  if (newVal) {
    formData.value.role_name = props.editRoleName || '';
    searchQuery.value = '';
    errors.value = {};
    submitError.value = '';
    
    // Always clear permissions first
    if (Object.keys(permissions.value).length > 0) {
      Object.keys(permissions.value).forEach(d => {
        permissions.value[d] = {
          read: false, create: false, write: false, delete: false, submit: false
        };
      });
    }

    if (!doctypes.value.length) {
      await fetchDoctypes();
    }
    
    if (props.editRoleName) {
      try {
        const data = await call('arijentek_core.api.teams_permissons.get_roles_for_edit_and_view', { role_name: props.editRoleName });
        if (data) {
          Object.keys(data).forEach(d => {
            if (permissions.value[d]) {
              permissions.value[d] = { ...permissions.value[d], ...data[d] };
            }
          });
        }
      } catch (err) {
        submitError.value = getErrorMessage(err, 'Failed to load role permissions');
      }
    }
  }
});

const validate = () => {
  errors.value = {};
  if (!formData.value.role_name) {
    errors.value.role_name = 'Role Name is mandatory';
    return false;
  }
  return true;
};

const handleSave = async () => {
  submitError.value = '';
  showLongSaveMessage.value = false;
  if (!validate()) return;
  
  submitting.value = true;
  
  longSaveTimer = setTimeout(() => {
    showLongSaveMessage.value = true;
  }, 3000);
  
  const activePermissions = {};
  Object.keys(permissions.value).forEach(d => {
    const p = permissions.value[d];
    if (p && (p.read || p.write || p.create || p.delete || p.submit)) {
      activePermissions[d] = p;
    }
  });
  
  try {
    await call('arijentek_core.api.teams_permissons.create_role', {
      role_name: formData.value.role_name,
      permissions: JSON.stringify(activePermissions)
    });
    
    emit('save');
    show.value = false;
  } catch (err) {
    submitError.value = getErrorMessage(err, 'Failed to save role');
  } finally {
    clearTimeout(longSaveTimer);
    showLongSaveMessage.value = false;
    submitting.value = false;
  }
};
</script>
