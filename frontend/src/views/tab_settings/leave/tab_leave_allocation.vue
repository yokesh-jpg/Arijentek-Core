<template>
	<div class="space-y-4 sm:space-y-5 tab-fill">
		<!-- ===== Header ===== -->
		<div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
			<div>
				<h2 class="section-title">Leave allocations</h2>
				<p class="section-subtitle">Days granted per person, per leave type.</p>
			</div>
			<button v-if="leaveStore.canCreateLeaveAllocation" @click="handleCreate" class="btn-primary shrink-0">
				<span class="material-symbols-outlined !text-[18px]">add</span>
				Add allocation
			</button>
		</div>

		<!-- ===== Filters ===== -->
		<div class="glass-card !p-3">
			<div class="flex flex-wrap items-center gap-2">
				<div class="relative flex-[2] min-w-[220px]">
					<span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/55 pointer-events-none">search</span>
					<input v-model="searchQuery" type="text" placeholder="Allocation ID or employee" aria-label="Search" class="field-input !pl-9" />
				</div>
				<div class="flex-1 min-w-[180px]">
					<label class="sr-only">Employee</label>
					<SearchableDropdown
						v-model="employeeFilter"
						:options="leaveStore.employeeList"
						labelKey="employee_name"
						valueKey="name"
						placeholder="All employees"
						showAllOption
						allOptionLabel="All employees"
					/>
				</div>
			</div>
		</div>

		<!-- ===== Table ===== -->
		<DataTable
			:columns="listColumns"
			:rows="pager.state.rows"
			:actions="actionsForAllocation"
			:row-key="'name'"
			:loading="pager.state.loading"
			:empty-text="searchQuery || employeeFilter ? 'No leave allocations match these filters.' : 'No leave allocations found.'"
			:show-pager="true"
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
		>
			<template #cell-name="{ row }">
				<div class="max-w-[180px] sm:max-w-none">
					<span class="block tabular-nums break-words leading-snug sm:truncate font-medium">{{ row.name }}</span>
					<span class="block sm:hidden text-xs font-normal text-[#5C6169] dark:text-white/60 leading-snug">
						{{ row.employee_name }} · {{ row.leave_type }}
					</span>
				</div>
			</template>
			<template #cell-employee="{ row }">
				<span class="truncate">{{ row.employee_name }}</span>
			</template>
			<template #cell-leave_type="{ row }">
				<span class="whitespace-nowrap">{{ row.leave_type }}</span>
			</template>
			<template #cell-days="{ row }">
				<span class="tabular-nums whitespace-nowrap">{{ row.new_leaves_allocated }}</span>
			</template>
			<template #cell-period="{ row }">
				<span class="tabular-nums whitespace-nowrap">{{ formatDate(row.from_date) }} – {{ formatDate(row.to_date) }}</span>
			</template>
		</DataTable>

		<!-- Modals -->
		<CreateLeaveAllocation
			v-model="showCreateModal"
			:editId="editAllocationId"
			@save="pager.fetchPage"
		/>
	</div>
</template>

<script setup>
import DataTable from '@/components/DataTable.vue'
import { useServerPager } from '@/composables/useServerPager.js'
import SearchableDropdown from '@/components/SearchableDropdown.vue'
import CreateLeaveAllocation from '../../forms/leave/create_leave_allocation.vue'
import { useLeaveStore } from '@/stores/leave'
import { notify, ask } from '@/utils/feedback.js'
import { getErrorMessage } from '@/utils'
import { ref, watch, onMounted } from 'vue'
import { call } from 'frappe-ui'

const leaveStore = useLeaveStore()

const searchQuery = ref('')
const employeeFilter = ref('')
const showCreateModal = ref(false)
const editAllocationId = ref('')

const listColumns = [
	{ key: 'name', label: 'Allocation', className: 'table-td-strong max-w-[180px] sm:max-w-none' },
	{ key: 'employee', label: 'Employee', className: 'table-td hidden sm:table-cell' },
	{ key: 'leave_type', label: 'Leave type', className: 'table-td hidden sm:table-cell whitespace-nowrap' },
	{ key: 'days', label: 'Days', className: 'table-td tabular-nums whitespace-nowrap' },
	{ key: 'period', label: 'Period', className: 'table-td tabular-nums whitespace-nowrap hidden lg:table-cell' },
]

function actionsForAllocation(row) {
	return [
		{
			label: 'Edit',
			icon: 'edit',
			show: leaveStore.canEditLeaveAllocation,
			onClick: () => handleEdit(row),
		},
		{ divider: true },
		{
			label: 'Delete',
			icon: 'delete',
			danger: true,
			show: leaveStore.canDeleteLeaveAllocation,
			onClick: () => deleteLeaveAllocation(row.name),
		},
	]
}

function handleCreate() {
	editAllocationId.value = ''
	showCreateModal.value = true
}

function handleEdit(row) {
	editAllocationId.value = row.name
	showCreateModal.value = true
}

async function deleteLeaveAllocation(name) {
	if (!await ask('Are you sure you want to delete this leave allocation?')) return
	try {
		const res = await call('arijentek_core.api.leave.delete_leave_allocation', { name })
		if (res && res.success === false) {
			notify(getErrorMessage(res.error || res, 'Failed to delete leave allocation.'))
		} else {
			await pager.fetchPage()
		}
	} catch (err) {
		notify(getErrorMessage(err, 'Failed to delete leave allocation.'))
	}
}

async function fetchAllocations(page, size) {
	try {
		const params = {
			page: page || 1,
			page_size: size || pager.state.size || 10,
		}
		if (employeeFilter.value) {
			params.employee = employeeFilter.value
		}
		if (searchQuery.value) {
			params.search_text = searchQuery.value
		}
		const res = await call('arijentek_core.api.leave.get_leave_allocations', params)
		const rows = res?.rows || (Array.isArray(res) ? res : res?.data || [])
		const total = res?.total != null ? Number(res.total) : rows.length
		return { rows, total }
	} catch (e) {
		console.error('Failed to fetch leave allocations:', e)
		return { rows: [], total: 0 }
	}
}

const pager = useServerPager((page, size) => fetchAllocations(page, size), { size: 10 })

function triggerFilterRefresh() {
	if (pager.state.page !== 1) {
		pager.state.page = 1
	} else {
		pager.fetchPage()
	}
}

let debounceTimer
watch(searchQuery, () => {
	clearTimeout(debounceTimer)
	debounceTimer = setTimeout(() => {
		triggerFilterRefresh()
	}, 300)
})

watch(employeeFilter, () => {
	triggerFilterRefresh()
})

onMounted(async () => {
	await leaveStore.fetchEmployeeList()
	pager.fetchPage()
})

function formatDate(dateStr) {
	if (!dateStr) return '-'
	return new Date(dateStr).toLocaleDateString('en-US', {
		month: 'short',
		day: 'numeric',
		year: 'numeric',
	})
}
</script>
