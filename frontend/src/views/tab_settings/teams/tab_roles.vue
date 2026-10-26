<template>
	<div class="space-y-4 sm:space-y-5 tab-fill">
		<!-- ===== Header / Filters ===== -->
		<div class="glass-card !p-3 flex flex-col sm:flex-row sm:items-center gap-2">
			<div class="relative flex-1 min-w-0">
				<span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/60 pointer-events-none">search</span>
				<input
					v-model="searchQuery"
					type="text"
					placeholder="Search roles"
					class="field-input !pl-9"
				/>
			</div>
			<button
				v-if="teamStore.createRolePermissionResource?.data"
				@click="handleCreateRole"
				class="btn-primary shrink-0"
			>
				<span class="material-symbols-outlined !text-[18px]">add</span>
				Add role
			</button>
		</div>

		<!-- ===== Table ===== -->
		<DataTable
			:columns="columns"
			:rows="pager.state.rows"
			:actions="roleActions"
			:row-key="'name'"
			:loading="pager.state.loading"
			:empty-text="searchQuery ? `No roles match “${searchQuery}”.` : 'No roles found.'"
			:show-pager="true"
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
			:on-row-click="(row) => handleViewRole(row.name || row.role)"
		>
			<template #cell-role="{ row }">
				<span class="table-td-strong">
					{{ row.name || row.role }}
					<span v-if="PROTECTED.includes(row.name || row.role)" class="premium-tag tag-neutral ml-2 align-middle">Built in</span>
				</span>
			</template>
		</DataTable>

		<!-- Modals -->
		<CreateRoleForm v-model="showCreateRole" :editRoleName="editRoleName" @save="pager.fetchPage" />
		<ViewRolesModal v-model="showViewRole" :roleName="viewRoleName" />
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
import CreateRoleForm from '@/views/forms/teams/create_role.vue'
import ViewRolesModal from '@/views/page_views/teams/view_roles.vue'

const PROTECTED = ['HR Manager', 'System Manager']

const teamStore = useTeamStore()
const showCreateRole = ref(false)
const editRoleName = ref('')
const showViewRole = ref(false)
const viewRoleName = ref('')
const searchQuery = ref('')
const isDeleting = ref('')

const columns = [
	{ key: 'role', label: 'Role', className: 'table-td' }
]

function roleActions(row) {
	const role = row.name || row.role
	const amendable = !PROTECTED.includes(role)
	return [
		{ label: 'View', icon: 'visibility', onClick: () => handleViewRole(role) },
		{
			label: 'Edit',
			icon: 'edit',
			show: !!teamStore.editRolePermissionResource?.data && amendable,
			onClick: () => handleEditRole(role)
		},
		{ divider: true },
		{
			label: isDeleting.value === role ? 'Deleting…' : 'Delete',
			icon: 'delete',
			danger: true,
			disabled: isDeleting.value === role,
			show: !!teamStore.deleteRolePermissionResource?.data && amendable,
			onClick: () => handleDeleteRole(role)
		}
	]
}

const handleCreateRole = () => {
	editRoleName.value = ''
	showCreateRole.value = true
}

const handleEditRole = (roleName) => {
	editRoleName.value = roleName
	showCreateRole.value = true
}

const handleViewRole = (roleName) => {
	viewRoleName.value = roleName
	showViewRole.value = true
}

const handleDeleteRole = async (roleName) => {
	if (!await ask(`Are you sure you want to delete the role '${roleName}'?`)) {
		return
	}

	isDeleting.value = roleName

	try {
		await call('arijentek_core.api.teams_permissons.delete_role', { role_name: roleName })
		pager.fetchPage()
		teamStore.rolesResource?.reload()
	} catch (err) {
		notify(getErrorMessage(err, 'Failed to delete role'))
	} finally {
		isDeleting.value = ''
	}
}

async function fetchRoles(page, size) {
	try {
		const params = {
			page: page || 1,
			page_size: size || pager.state.size || 10,
			search_term: searchQuery.value || ''
		}
		const res = await call('arijentek_core.api.teams_permissons.get_roles', params)
		const rows = res?.rows || (Array.isArray(res) ? res.map(r => typeof r === 'string' ? { name: r, role: r } : r) : [])
		const total = res?.total != null ? Number(res.total) : rows.length
		return { rows, total }
	} catch (err) {
		console.error('Failed to fetch roles:', err)
		return { rows: [], total: 0 }
	}
}

const pager = useServerPager((page, size) => fetchRoles(page, size), { size: 10 })

function triggerFilterRefresh() {
	if (pager.state.page !== 1) {
		pager.state.page = 1
	} else {
		pager.fetchPage()
	}
}

let debounceTimer = null
watch(searchQuery, () => {
	clearTimeout(debounceTimer)
	debounceTimer = setTimeout(() => {
		triggerFilterRefresh()
	}, 300)
})

onMounted(() => {
	pager.fetchPage()
})
</script>
