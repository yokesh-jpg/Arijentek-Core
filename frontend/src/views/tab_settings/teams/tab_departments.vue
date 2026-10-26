<template>
	<div class="space-y-4 sm:space-y-5 tab-fill">
		<!-- ===== Header / Filters ===== -->
		<div class="glass-card !p-3 flex flex-col sm:flex-row sm:items-center gap-2">
			<div class="relative flex-1 min-w-0">
				<span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/60 pointer-events-none">search</span>
				<input
					v-model="searchQuery"
					type="text"
					placeholder="Search departments"
					class="field-input !pl-9"
				/>
			</div>
			<button
				v-if="teamStore.createDepartmentPermissionResource?.data"
				@click="handleCreateDepartment"
				class="btn-primary shrink-0"
			>
				<span class="material-symbols-outlined !text-[18px]">add</span>
				Add department
			</button>
		</div>

		<!-- ===== Table ===== -->
		<DataTable
			:columns="columns"
			:rows="pager.state.rows"
			:actions="departmentActions"
			:row-key="'name'"
			:loading="pager.state.loading"
			:empty-text="searchQuery ? `No departments match “${searchQuery}”.` : 'No departments found.'"
			:show-pager="true"
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
			:on-row-click="(row) => viewDepartment(row.name)"
		>
			<template #cell-department="{ row }">
				<span class="table-td-strong">
					<span class="block">{{ row.department_name || row.name }}</span>
					<span v-if="row.department_name && row.department_name !== row.name" class="block text-[12px] font-normal text-[#656A72] dark:text-white/55">{{ row.name }}</span>
				</span>
			</template>
			<template #cell-expense_approver="{ row }">
				<span class="text-[13px]" :class="!row.expense_approver_name && 'text-[#656A72] dark:text-white/50'">
					{{ row.expense_approver_name || 'Not set' }}
				</span>
			</template>
			<template #cell-leave_approver="{ row }">
				<span class="text-[13px]" :class="!row.leave_approver_name && 'text-[#656A72] dark:text-white/50'">
					{{ row.leave_approver_name || 'Not set' }}
				</span>
			</template>
		</DataTable>

		<!-- Modals -->
		<CreateDepartmentForm v-model="showCreateDepartment" :edit-id="selectedDepartmentId" @save="pager.fetchPage" />
		<Dialog v-model="showViewDepartmentModal" :options="{ size: '2xl' }">
			<template #body>
				<div class="modal-panel">
					<DepartmentPageView
						:id="viewDepartmentId"
						:is-modal="true"
						@close="showViewDepartmentModal = false"
						@edit="handleViewDepartmentEdit"
						@delete="handleViewDepartmentDelete"
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
import CreateDepartmentForm from '@/views/forms/create_department.vue'
import DepartmentPageView from '@/views/page_views/DepartmentPageView.vue'

const teamStore = useTeamStore()

const showCreateDepartment = ref(false)
const selectedDepartmentId = ref('')
const showViewDepartmentModal = ref(false)
const viewDepartmentId = ref('')
const searchQuery = ref('')

const columns = [
	{ key: 'department', label: 'Department', className: 'table-td' },
	{ key: 'expense_approver', label: 'Expense approver', className: 'table-td' },
	{ key: 'leave_approver', label: 'Leave approver', className: 'table-td' }
]

function handleCreateDepartment() {
	selectedDepartmentId.value = ''
	showCreateDepartment.value = true
}

function editDepartment(id) {
	selectedDepartmentId.value = id
	showCreateDepartment.value = true
}

function viewDepartment(id) {
	viewDepartmentId.value = id
	showViewDepartmentModal.value = true
}

function handleViewDepartmentEdit({ name }) {
	showViewDepartmentModal.value = false
	editDepartment(name)
}

function handleViewDepartmentDelete({ name }) {
	showViewDepartmentModal.value = false
	deleteDepartment(name)
}

async function deleteDepartment(id) {
	if (!await ask('Are you sure you want to delete this department?')) return
	try {
		const res = await call('arijentek_core.api.teams_permissons.delete_department', { department_id: id })
		if (res && res.success === false) {
			notify(res.error || 'Failed to delete department', 'error')
			return
		}
		notify(res?.message || 'Department deleted successfully', 'success')
		pager.fetchPage()
	} catch (err) {
		notify(getErrorMessage(err, 'Failed to delete department'))
	}
}

function departmentActions(dept) {
	return [
		{ label: 'View', icon: 'visibility', onClick: () => viewDepartment(dept.name) },
		{
			label: 'Edit',
			icon: 'edit',
			show: !!teamStore.createDepartmentPermissionResource?.data,
			onClick: () => editDepartment(dept.name)
		},
		{ divider: true },
		{
			label: 'Delete',
			icon: 'delete',
			danger: true,
			show: !!teamStore.deleteDepartmentPermissionResource?.data,
			onClick: () => deleteDepartment(dept.name)
		}
	]
}

async function fetchDepartments(page, size) {
	try {
		const params = {
			page: page || 1,
			page_size: size || pager.state.size || 10,
			search_term: searchQuery.value || ''
		}
		const res = await call('arijentek_core.api.teams_permissons.get_department_list', params)
		const rows = res?.rows || (Array.isArray(res) ? res : res?.data || [])
		const total = res?.total != null ? Number(res.total) : rows.length
		return { rows, total }
	} catch (err) {
		console.error('Failed to fetch departments:', err)
		return { rows: [], total: 0 }
	}
}

const pager = useServerPager((page, size) => fetchDepartments(page, size), { size: 10 })

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
