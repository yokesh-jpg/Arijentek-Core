<template>
	<div class="space-y-4 sm:space-y-5 tab-fill">
		<!-- ===== Header / Filters ===== -->
		<div class="glass-card !p-3 flex flex-col sm:flex-row sm:items-center gap-2">
			<div class="relative flex-1 min-w-0">
				<span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/60 pointer-events-none">search</span>
				<input
					v-model="searchQuery"
					type="text"
					placeholder="Search branches"
					class="field-input !pl-9"
				/>
			</div>
			<button
				v-if="teamStore.createBranchPermissionResource?.data"
				@click="handleCreateBranch"
				class="btn-primary shrink-0"
			>
				<span class="material-symbols-outlined !text-[18px]">add</span>
				Add branch
			</button>
		</div>

		<!-- ===== Table ===== -->
		<DataTable
			:columns="columns"
			:rows="pager.state.rows"
			:actions="branchActions"
			:row-key="'name'"
			:loading="pager.state.loading"
			:empty-text="searchQuery ? `No branches match “${searchQuery}”.` : 'No branches found.'"
			:show-pager="true"
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
		>
			<template #cell-branch="{ row }">
				<span class="table-td-strong">{{ row.branch_name || row.name }}</span>
			</template>
		</DataTable>

		<!-- Modals -->
		<CreateBranchForm v-model="showCreateBranch" :edit-id="selectedBranchId" @save="pager.fetchPage" />
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
import CreateBranchForm from '@/views/forms/create_branch.vue'

const teamStore = useTeamStore()

const showCreateBranch = ref(false)
const selectedBranchId = ref('')
const searchQuery = ref('')

const columns = [
	{ key: 'branch', label: 'Branch', className: 'table-td' }
]

function handleCreateBranch() {
	selectedBranchId.value = ''
	showCreateBranch.value = true
}

function editBranch(id) {
	selectedBranchId.value = id
	showCreateBranch.value = true
}

async function deleteBranch(id) {
	if (!await ask('Are you sure you want to delete this branch?')) return
	try {
		const res = await call('arijentek_core.api.teams_permissons.delete_branch', { branch_id: id })
		if (res && res.success === false) {
			notify(res.error || 'Failed to delete branch', 'error')
			return
		}
		notify(res?.message || 'Branch deleted successfully', 'success')
		pager.fetchPage()
	} catch (err) {
		notify(getErrorMessage(err, 'Failed to delete branch'))
	}
}

function branchActions(branch) {
	return [
		{
			label: 'Edit',
			icon: 'edit',
			show: !!teamStore.editBranchPermissionResource?.data,
			onClick: () => editBranch(branch.name)
		},
		{ divider: true },
		{
			label: 'Delete',
			icon: 'delete',
			danger: true,
			show: !!teamStore.deleteBranchPermissionResource?.data,
			onClick: () => deleteBranch(branch.name)
		}
	]
}

async function fetchBranches(page, size) {
	try {
		const params = {
			page: page || 1,
			page_size: size || pager.state.size || 10,
			search_term: searchQuery.value || ''
		}
		const res = await call('arijentek_core.api.teams_permissons.get_branch_list', params)
		const rows = res?.rows || (Array.isArray(res) ? res : res?.data || [])
		const total = res?.total != null ? Number(res.total) : rows.length
		return { rows, total }
	} catch (err) {
		console.error('Failed to fetch branches:', err)
		return { rows: [], total: 0 }
	}
}

const pager = useServerPager((page, size) => fetchBranches(page, size), { size: 10 })

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
