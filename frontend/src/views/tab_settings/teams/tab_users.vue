<template>
	<div class="space-y-4 sm:space-y-5 tab-fill">
		<!-- ===== Header / Filters ===== -->
		<div class="glass-card !p-3 flex flex-col sm:flex-row sm:items-center gap-2">
			<div class="relative flex-1 min-w-0">
				<span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/55 pointer-events-none">search</span>
				<input
					v-model="searchTerm"
					type="text"
					placeholder="Search by name, email or username"
					class="field-input !pl-9"
				/>
			</div>
			<button
				v-if="teamStore.createUserPermissionResource?.data"
				@click="handleCreateUser"
				class="btn-primary shrink-0"
			>
				<span class="material-symbols-outlined !text-[18px]">add</span>
				Add user
			</button>
		</div>

		<!-- ===== Table ===== -->
		<DataTable
			:columns="columns"
			:rows="pager.state.rows"
			:actions="userActions"
			:row-key="'name'"
			:loading="pager.state.loading"
			:empty-text="searchTerm ? 'No users match that search.' : 'No users found.'"
			:show-pager="true"
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
			:on-row-click="(row) => viewUser(row.name)"
		>
			<template #cell-user="{ row }">
				<span class="flex items-center gap-2.5 min-w-0">
					<span class="avatar-chip shrink-0 overflow-hidden">
						<img v-if="row.user_image" :src="row.user_image" class="w-full h-full object-cover" alt="" />
						<template v-else>{{ initials(row.full_name || row.name) }}</template>
					</span>
					<span class="block text-[13px] font-semibold text-[#17181B] dark:text-white truncate">
						{{ row.full_name || row.name }}
					</span>
				</span>
			</template>
			<template #cell-email="{ row }">
				<span class="block truncate max-w-[260px] text-[13px] text-[#17181B] dark:text-white">
					{{ row.email || '—' }}
				</span>
			</template>
			<template #cell-username="{ row }">
				<span class="text-[13px] text-[#17181B] dark:text-white">
					{{ row.username || '—' }}
				</span>
			</template>
			<template #cell-status="{ row }">
				<span class="premium-tag" :class="row.enabled ? 'tag-emerald' : 'tag-neutral'">
					{{ row.enabled ? 'Active' : 'Disabled' }}
				</span>
			</template>
		</DataTable>

		<!-- Modals -->
		<CreateUsersForm v-model="showCreateUser" :edit-id="selectedUserId" @save="pager.fetchPage" />
		<ViewUserModal v-model="showViewUserModal" :user-id="viewUserId" @edit="handleViewUserEdit" @delete="handleViewUserDelete" />
	</div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { call } from 'frappe-ui'
import { useTeamStore } from '@/stores/team'
import { notify, ask } from '@/utils/feedback.js'
import { getErrorMessage } from '@/utils.js'
import DataTable from '@/components/DataTable.vue'
import { useServerPager } from '@/composables/useServerPager.js'
import CreateUsersForm from '@/views/forms/create_users.vue'
import ViewUserModal from '@/views/page_views/view_users.vue'

const teamStore = useTeamStore()

const showCreateUser = ref(false)
const selectedUserId = ref('')
const showViewUserModal = ref(false)
const viewUserId = ref('')
const searchTerm = ref('')

const columns = [
	{ key: 'user', label: 'User', className: 'table-td' },
	{ key: 'email', label: 'Email', className: 'table-td' },
	{ key: 'username', label: 'Username', className: 'table-td' },
	{ key: 'status', label: 'Status', className: 'table-td' }
]

function initials(name) {
	if (!name) return '?'
	return String(name)
		.split(/[\s@._-]+/)
		.filter(Boolean)
		.slice(0, 2)
		.map((p) => p[0].toUpperCase())
		.join('')
}

function handleCreateUser() {
	selectedUserId.value = ''
	showCreateUser.value = true
}

function editUser(id) {
	selectedUserId.value = id
	showCreateUser.value = true
}

function viewUser(id) {
	viewUserId.value = id
	showViewUserModal.value = true
}

function handleViewUserEdit({ name }) {
	editUser(name)
}

function handleViewUserDelete({ name }) {
	showViewUserModal.value = false
	deleteUser(name)
}

async function deleteUser(id) {
	if (!await ask('Are you sure you want to delete this user?')) return
	try {
		const res = await call('arijentek_core.api.teams_permissons.delete_users', { user_id: id })
		if (res && res.success === false) {
			notify(res.error || 'Failed to delete user', 'error')
			return
		}
		notify(res?.message || 'User deleted successfully', 'success')
		pager.fetchPage()
	} catch (err) {
		notify(getErrorMessage(err, 'Failed to delete user'))
	}
}

function userActions(user) {
	return [
		{ label: 'View', icon: 'visibility', onClick: () => viewUser(user.name) },
		{
			label: 'Edit',
			icon: 'edit',
			show: !!teamStore.editUserPermissionResource?.data,
			onClick: () => editUser(user.name)
		},
		{ divider: true },
		{
			label: 'Delete',
			icon: 'delete',
			danger: true,
			show: !!teamStore.deleteUserPermissionResource?.data,
			onClick: () => deleteUser(user.name)
		}
	]
}

async function fetchUsers(page, size) {
	try {
		const params = {
			page: page || 1,
			page_size: size || pager.state.size || 10,
			search_term: searchTerm.value || ''
		}
		const res = await call('arijentek_core.api.teams_permissons.get_users_details', params)
		const rows = res?.rows || (Array.isArray(res) ? res : res?.data || [])
		const total = res?.total != null ? Number(res.total) : rows.length
		return { rows, total }
	} catch (err) {
		console.error('Failed to fetch users:', err)
		return { rows: [], total: 0 }
	}
}

const pager = useServerPager((page, size) => fetchUsers(page, size), { size: 10 })

function triggerFilterRefresh() {
	if (pager.state.page !== 1) {
		pager.state.page = 1
	} else {
		pager.fetchPage()
	}
}

let debounceTimer = null
watch(searchTerm, () => {
	clearTimeout(debounceTimer)
	debounceTimer = setTimeout(() => {
		triggerFilterRefresh()
	}, 300)
})

onMounted(() => {
	pager.fetchPage()
})
</script>
