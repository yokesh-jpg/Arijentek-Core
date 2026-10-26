<template>
  <Dialog :options="{ size: '4xl' }" v-model="show" :disableOutsideClickToClose="false">
    <template #body>
      <div class="modal-panel">
        <!-- Header -->
        <header class="modal-header">
          <div>
            <h3 class="modal-title truncate">{{ roleName }}</h3>
            <p class="text-[12px] text-[#656A72] dark:text-white/60 truncate tabular-nums">Role permissions</p>
          </div>
          <div class="flex items-center gap-1 shrink-0">
            <button class="btn-icon-ghost" aria-label="Edit" title="Edit"
              v-if="teamStore.editRolePermissionResource?.data && !protectedRoles.includes(roleName)"
              @click="handleEdit"
            ><span class="material-symbols-outlined !text-[18px]">edit</span></button>
            <button
              v-if="teamStore.deleteRolePermissionResource?.data && !protectedRoles.includes(roleName)"
              @click="handleDelete"
              :disabled="isDeleting"
              class="btn-danger-ghost disabled:opacity-40"
              aria-label="Delete"
              title="Delete"
            >
              <span v-if="isDeleting" class="w-4 h-4 rounded-full border-2 border-current/30 border-t-current animate-spin"></span>
              <span v-else class="material-symbols-outlined !text-[18px]">delete</span>
            </button>
            <button @click="show = false" class="btn-icon-ghost shrink-0" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span></button>
          </div>
        </header>

        <!-- Content -->
        <div class="flex-1 overflow-y-auto px-6 py-5">
          <div v-if="loading" class="flex flex-col items-center justify-center py-16 gap-3 text-[#5C6169] dark:text-white/65">
            <span class="material-symbols-outlined animate-spin text-4xl">progress_activity</span>
            <p>Loading permissions...</p>
          </div>

          <div v-else-if="error" class="empty-state">
						<span class="material-symbols-outlined !text-[28px] text-red-600 dark:text-red-400">error</span>
						<p class="empty-state-text">Could not load this record</p>
						<p class="text-[12px] text-[#656A72] dark:text-white/55">{{ error }}</p>
					</div>

          <div v-else class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-white/10 rounded-[12px] overflow-hidden shadow-sm">
            <table class="w-full text-left text-sm whitespace-nowrap">
              <thead>
                <tr>
                  <th class="table-th">Document type</th>
                  <th class="!text-center table-th">Read</th>
                  <th class="!text-center table-th">Write</th>
                  <th class="!text-center table-th">Create</th>
                  <th class="!text-center table-th">Delete</th>
                  <th class="!text-center table-th">Submit</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(perms, doctype) in permissions"
                  :key="doctype"
                  class="border-b last:border-0 border-black/[0.05] dark:border-white/[0.06]"
                >
                  <td class="table-td">{{ doctype }}</td>
                  <td class="!text-center table-td">
                    <span class="material-symbols-outlined text-lg" :class="perms.read ? 'text-green-700 dark:text-green-300' : 'text-[#C4C7CC] dark:text-white/25'">
                      {{ perms.read ? 'check_circle' : 'cancel' }}
                    </span>
                  </td>
                  <td class="!text-center table-td">
                    <span class="material-symbols-outlined text-lg" :class="perms.write ? 'text-green-700 dark:text-green-300' : 'text-[#C4C7CC] dark:text-white/25'">
                      {{ perms.write ? 'check_circle' : 'cancel' }}
                    </span>
                  </td>
                  <td class="!text-center table-td">
                    <span class="material-symbols-outlined text-lg" :class="perms.create ? 'text-green-700 dark:text-green-300' : 'text-[#C4C7CC] dark:text-white/25'">
                      {{ perms.create ? 'check_circle' : 'cancel' }}
                    </span>
                  </td>
                  <td class="!text-center table-td">
                    <span class="material-symbols-outlined text-lg" :class="perms.delete ? 'text-green-700 dark:text-green-300' : 'text-[#C4C7CC] dark:text-white/25'">
                      {{ perms.delete ? 'check_circle' : 'cancel' }}
                    </span>
                  </td>
                  <td class="!text-center table-td">
                    <span class="material-symbols-outlined text-lg" :class="perms.submit ? 'text-green-700 dark:text-green-300' : 'text-[#C4C7CC] dark:text-white/25'">
                      {{ perms.submit ? 'check_circle' : 'cancel' }}
                    </span>
                  </td>
                </tr>
                <tr v-if="!loading && Object.keys(permissions).length === 0">
                  <td colspan="6" class="py-12 text-center text-[13px] text-[#656A72] dark:text-white/55">
                    No permissions found for this role.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Footer -->
        <footer class="px-5 py-4 border-t border-black/[0.07] dark:border-white/10 shrink-0">
          <button class="btn-secondary w-full" @click="show = false">Close</button>
        </footer>
      	<footer class="px-5 py-4 border-t border-black/[0.07] dark:border-white/10 shrink-0">
					<button class="btn-secondary w-full" @click="show = false">Close</button>
				</footer>
			</div>
    </template>
  </Dialog>

  <!-- Edit Role Form -->
  <CreateRoleForm v-model="showEditForm" :editRoleName="roleName" @save="onSaved" />
</template>

<script setup>
import { notify, ask } from '@/utils/feedback.js'
import { ref, computed, watch } from 'vue'
import { Dialog, call } from 'frappe-ui'
import { getErrorMessage } from '@/utils.js'
import { useTeamStore } from '@/stores/team'
import CreateRoleForm from '@/views/forms/teams/create_role.vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  roleName: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue', 'deleted'])

const teamStore = useTeamStore()
const protectedRoles = ['HR Manager', 'System Manager']
const showEditForm = ref(false)
const isDeleting = ref(false)

function handleEdit() {
  showEditForm.value = true
}

function onSaved() {
  // Refresh permission list after edit
  fetchPermissions()
}

async function handleDelete() {
  if (!await ask(`Are you sure you want to delete the role '${props.roleName}'?`)) return
  isDeleting.value = true
  try {
    await call('arijentek_core.api.teams_permissons.delete_role', { role_name: props.roleName })
    teamStore.rolesResource?.reload()
    emit('deleted', props.roleName)
    show.value = false
  } catch (err) {
    notify(getErrorMessage(err, 'Failed to delete role.'))
  } finally {
    isDeleting.value = false
  }
}

const show = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const permissions = ref({})
const loading = ref(false)
const error = ref(null)

const fetchPermissions = async () => {
  if (!props.roleName) {
    error.value = 'Role name is missing.'
    return
  }
  loading.value = true
  error.value = null
  permissions.value = {}
  try {
    const res = await call('arijentek_core.api.teams_permissons.get_roles_for_edit_and_view', {
      role_name: props.roleName
    })
    permissions.value = res || {}
  } catch (err) {
    error.value = getErrorMessage(err, 'Failed to fetch role permissions')
  } finally {
    loading.value = false
  }
}

watch(show, (newVal) => {
  if (newVal) {
    fetchPermissions()
  }
})
</script>
