<template>
	<div class="space-y-4 sm:space-y-5 tab-fill">
		<!-- ===== Header / Filters ===== -->
		<div class="glass-card !p-3 flex flex-col sm:flex-row sm:items-center gap-2">
			<div class="relative flex-1 min-w-0">
				<span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/60 pointer-events-none">search</span>
				<input
					v-model="searchQuery"
					type="text"
					placeholder="Search designations"
					class="field-input !pl-9"
				/>
			</div>
			<button
				v-if="teamStore.createDesignationPermissionResource?.data"
				@click="handleCreateDesignation"
				class="btn-primary shrink-0"
			>
				<span class="material-symbols-outlined !text-[18px]">add</span>
				Add designation
			</button>
		</div>

		<!-- ===== Table ===== -->
		<DataTable
			:columns="columns"
			:rows="pager.state.rows"
			:actions="designationActions"
			:row-key="'name'"
			:loading="pager.state.loading"
			:empty-text="searchQuery ? `No designations match “${searchQuery}”.` : 'No designations found.'"
			:show-pager="true"
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
			:on-row-click="(row) => viewDesignation(row.name)"
		>
			<template #cell-designation="{ row }">
				<span class="table-td-strong">{{ row.designation_name || row.name }}</span>
			</template>
			<template #cell-description="{ row }">
				<span class="text-[13px] text-[#5C6169] dark:text-white/65">{{ row.description || '—' }}</span>
			</template>
		</DataTable>

		<!-- Modals -->
		<CreateDesignationForm v-model="showCreateDesignation" :edit-id="selectedDesignationId" @save="pager.fetchPage" />
		<Dialog v-model="showViewDesignationModal" :options="{ size: '2xl' }">
			<template #body>
				<div class="modal-panel">
					<DesignationPageView
						:id="viewDesignationId"
						:is-modal="true"
						@close="showViewDesignationModal = false"
						@edit="handleViewDesignationEdit"
						@delete="handleViewDesignationDelete"
					/>
				</div>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { call, Dialog } from 'frappe-ui'
import { useTeamStore } from '@/stores/team'
import { notify, ask } from '@/utils/feedback.js'
import { getErrorMessage } from '@/utils.js'
import DataTable from '@/components/DataTable.vue'
import { useServerPager } from '@/composables/useServerPager.js'
import CreateDesignationForm from '@/views/forms/create_designation.vue'
import DesignationPageView from '@/views/page_views/DesignationPageView.vue'

const teamStore = useTeamStore()

const showCreateDesignation = ref(false)
const selectedDesignationId = ref('')
const showViewDesignationModal = ref(false)
const viewDesignationId = ref('')
const searchQuery = ref('')

const columns = [
	{ key: 'designation', label: 'Designation', className: 'table-td' },
	{ key: 'description', label: 'Description', className: 'table-td' }
]

function handleCreateDesignation() {
	selectedDesignationId.value = ''
	showCreateDesignation.value = true
}

function editDesignation(id) {
	selectedDesignationId.value = id
	showCreateDesignation.value = true
}

function viewDesignation(id) {
	viewDesignationId.value = id
	showViewDesignationModal.value = true
}

function handleViewDesignationEdit({ name }) {
	showViewDesignationModal.value = false
	editDesignation(name)
}

function handleViewDesignationDelete({ name }) {
	showViewDesignationModal.value = false
	deleteDesignation(name)
}

async function deleteDesignation(id) {
	if (!await ask('Are you sure you want to delete this designation?')) return
	try {
		const res = await call('arijentek_core.api.teams_permissons.delete_designation', { designation_id: id })
		if (res && res.success === false) {
			notify(res.error || 'Failed to delete designation', 'error')
			return
		}
		notify(res?.message || 'Designation deleted successfully', 'success')
		pager.fetchPage()
	} catch (err) {
		notify(getErrorMessage(err, 'Failed to delete designation'))
	}
}

function designationActions(desig) {
	return [
		{ label: 'View', icon: 'visibility', onClick: () => viewDesignation(desig.name) },
		{
			label: 'Edit',
			icon: 'edit',
			show: !!teamStore.editDesignationPermissionResource?.data,
			onClick: () => editDesignation(desig.name)
		},
		{ divider: true },
		{
			label: 'Delete',
			icon: 'delete',
			danger: true,
			show: !!teamStore.deleteDesignationPermissionResource?.data,
			onClick: () => deleteDesignation(desig.name)
		}
	]
}

async function fetchDesignations(page, size) {
	try {
		const params = {
			page: page || 1,
			page_size: size || pager.state.size || 10,
			search_term: searchQuery.value || ''
		}
		const res = await call('arijentek_core.api.teams_permissons.get_designation_list', params)
		const rows = res?.rows || (Array.isArray(res) ? res : res?.data || [])
		const total = res?.total != null ? Number(res.total) : rows.length
		return { rows, total }
	} catch (err) {
		console.error('Failed to fetch designations:', err)
		return { rows: [], total: 0 }
	}
}

const pager = useServerPager((page, size) => fetchDesignations(page, size), { size: 10 })

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
