<template>
	<div class="space-y-4 sm:space-y-5 tab-fill">
		<!-- ===== Header / Filters ===== -->
		<div class="glass-card !p-3 flex flex-col sm:flex-row sm:items-center gap-2">
			<div class="relative flex-1 min-w-0">
				<span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/60 pointer-events-none">search</span>
				<input
					v-model="searchQuery"
					type="text"
					placeholder="Search employment types"
					class="field-input !pl-9"
				/>
			</div>
			<button
				v-if="teamStore.createEmployeeTypePermissionResource?.data"
				@click="handleCreateEmployeeType"
				class="btn-primary shrink-0"
			>
				<span class="material-symbols-outlined !text-[18px]">add</span>
				Add type
			</button>
		</div>

		<!-- ===== Table ===== -->
		<DataTable
			:columns="columns"
			:rows="pager.state.rows"
			:actions="employeeTypeActions"
			:row-key="'name'"
			:loading="pager.state.loading"
			:empty-text="searchQuery ? `No employment types match “${searchQuery}”.` : 'No employment types found.'"
			:show-pager="true"
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
		>
			<template #cell-employee_type="{ row }">
				<span class="table-td-strong">{{ row.employee_type_name || row.name }}</span>
			</template>
		</DataTable>

		<!-- Modals -->
		<CreateEmployeeTypeForm v-model="showCreateEmployeeType" :edit-id="selectedEmployeeTypeId" @save="pager.fetchPage" />
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
import CreateEmployeeTypeForm from '@/views/forms/create_employee_type.vue'

const teamStore = useTeamStore()

const showCreateEmployeeType = ref(false)
const selectedEmployeeTypeId = ref('')
const searchQuery = ref('')

const columns = [
	{ key: 'employee_type', label: 'Employment type', className: 'table-td' }
]

function handleCreateEmployeeType() {
	selectedEmployeeTypeId.value = ''
	showCreateEmployeeType.value = true
}

function editEmployeeType(id) {
	selectedEmployeeTypeId.value = id
	showCreateEmployeeType.value = true
}

async function deleteEmployeeType(id) {
	if (!await ask('Are you sure you want to delete this employment type?')) return
	try {
		const res = await call('arijentek_core.api.teams_permissons.delete_employee_type', { type_id: id })
		if (res && res.success === false) {
			notify(res.error || 'Failed to delete employment type', 'error')
			return
		}
		notify(res?.message || 'Employment type deleted successfully', 'success')
		pager.fetchPage()
	} catch (err) {
		notify(getErrorMessage(err, 'Failed to delete employment type'))
	}
}

function employeeTypeActions(type) {
	return [
		{
			label: 'Edit',
			icon: 'edit',
			show: !!teamStore.editEmployeeTypePermissionResource?.data,
			onClick: () => editEmployeeType(type.name)
		},
		{ divider: true },
		{
			label: 'Delete',
			icon: 'delete',
			danger: true,
			show: !!teamStore.deleteEmployeeTypePermissionResource?.data,
			onClick: () => deleteEmployeeType(type.name)
		}
	]
}

async function fetchEmployeeTypes(page, size) {
	try {
		const params = {
			page: page || 1,
			page_size: size || pager.state.size || 10,
			search_term: searchQuery.value || ''
		}
		const res = await call('arijentek_core.api.teams_permissons.get_employee_type_list', params)
		const rows = res?.rows || (Array.isArray(res) ? res : res?.data || [])
		const total = res?.total != null ? Number(res.total) : rows.length
		return { rows, total }
	} catch (err) {
		console.error('Failed to fetch employment types:', err)
		return { rows: [], total: 0 }
	}
}

const pager = useServerPager((page, size) => fetchEmployeeTypes(page, size), { size: 10 })

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
