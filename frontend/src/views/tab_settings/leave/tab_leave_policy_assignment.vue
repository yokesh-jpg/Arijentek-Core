<template>
	<div class="space-y-4 sm:space-y-5 tab-fill">
		<!-- ===== Header ===== -->
		<div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
			<div>
				<h2 class="section-title">Policy assignments</h2>
				<p class="section-subtitle">Which leave policy each person is on.</p>
			</div>
			<div class="flex items-center gap-2">
				<button v-if="leaveStore.canCreateLeavePolicyAssignment" @click="handleBulkAssign" class="btn-secondary shrink-0">
					<span class="material-symbols-outlined !text-[18px]">group_add</span>
					Bulk assign
				</button>
				<button v-if="leaveStore.canCreateLeavePolicyAssignment" @click="handleAssign" class="btn-primary shrink-0">
					<span class="material-symbols-outlined !text-[18px]">add</span>
					Assign policy
				</button>
			</div>
		</div>

		<!-- ===== Filters ===== -->
		<div class="glass-card !p-3 flex flex-wrap items-center gap-2">
			<div class="relative flex-[2] min-w-[220px]">
				<span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/55 pointer-events-none">search</span>
				<input v-model="searchQuery" type="text" placeholder="Employee or assignment ID" aria-label="Search" class="field-input !pl-9" />
			</div>
			<div class="flex-1 min-w-[180px]">
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
			<div class="flex-1 min-w-[180px]">
				<SearchableDropdown
					v-model="policyFilter"
					:options="policyOptions"
					labelKey="title"
					valueKey="name"
					placeholder="All policies"
					showAllOption
					allOptionLabel="All policies"
				/>
			</div>
		</div>

		<!-- ===== Table ===== -->
		<DataTable
			:columns="listColumns"
			:rows="pager.state.rows"
			:actions="actionsForAssignment"
			:row-key="'name'"
			:loading="pager.state.loading"
			:empty-text="searchQuery || employeeFilter || policyFilter ? 'No policy assignments match these filters.' : 'No policy assignments found.'"
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
						{{ row.employee_name }} · {{ row.leave_policy_title || row.leave_policy }}
					</span>
				</div>
			</template>
			<template #cell-employee="{ row }">
				<span class="truncate">{{ row.employee_name }}</span>
			</template>
			<template #cell-policy="{ row }">
				<span>{{ row.leave_policy_title || row.leave_policy }}</span>
			</template>
		</DataTable>

		<!-- Modals -->
		<CreateLeavePolicyAssignment
			v-model="showCreateModal"
			:editId="editAssignmentId"
			@save="pager.fetchPage"
			@create-leave-policy="showCreatePolicyModal = true"
			@create-leave-period="showCreatePeriodModal = true"
		/>

		<CreateBulkLeavePolicyAssignment
			v-model="showBulkModal"
			@save="pager.fetchPage"
			@create-leave-policy="showCreatePolicyModal = true"
			@create-leave-period="showCreatePeriodModal = true"
		/>

		<CreateLeavePolicy
			v-model="showCreatePolicyModal"
			@save="leaveStore.fetchLeavePolicies"
		/>

		<CreateLeavePeriod
			v-model="showCreatePeriodModal"
			@save="leaveStore.fetchLeavePeriods"
		/>
	</div>
</template>

<script setup>
import DataTable from '@/components/DataTable.vue'
import { useServerPager } from '@/composables/useServerPager.js'
import SearchableDropdown from '@/components/SearchableDropdown.vue'
import CreateLeavePolicyAssignment from '../../forms/leave/create_leave_policy_assignment.vue'
import CreateBulkLeavePolicyAssignment from '../../forms/leave/create_bulk_leave_policy_assignment.vue'
import CreateLeavePolicy from '../../forms/leave/create_leave_policy.vue'
import CreateLeavePeriod from '../../forms/leave/create_leave_period.vue'
import { useLeaveStore } from '@/stores/leave'
import { notify, ask } from '@/utils/feedback.js'
import { ref, computed, watch, onMounted } from 'vue'
import { call } from 'frappe-ui'

const leaveStore = useLeaveStore()

const searchQuery = ref('')
const employeeFilter = ref('')
const policyFilter = ref('')

const showCreateModal = ref(false)
const showBulkModal = ref(false)
const editAssignmentId = ref('')

const showCreatePolicyModal = ref(false)
const showCreatePeriodModal = ref(false)

const listColumns = [
	{ key: 'name', label: 'Assignment', className: 'table-td-strong max-w-[180px] sm:max-w-none' },
	{ key: 'employee', label: 'Employee', className: 'table-td hidden sm:table-cell' },
	{ key: 'policy', label: 'Policy', className: 'table-td hidden sm:table-cell' },
]

const policyOptions = computed(() => {
	const opts = [{ name: '', title: 'All policies' }]
	;(leaveStore.leavePolicies || []).forEach((p) => {
		opts.push({
			name: p.name,
			title: p.title || p.name,
		})
	})
	return opts
})

function actionsForAssignment(row) {
	return [
		{
			label: 'Edit',
			icon: 'edit',
			show: leaveStore.canEditLeavePolicyAssignment,
			onClick: () => handleEdit(row),
		},
		{ divider: true },
		{
			label: 'Delete',
			icon: 'delete',
			danger: true,
			show: leaveStore.canDeleteLeavePolicyAssignment,
			onClick: () => handleDelete(row.name),
		},
	]
}

function handleAssign() {
	editAssignmentId.value = ''
	showCreateModal.value = true
}

function handleBulkAssign() {
	showBulkModal.value = true
}

function handleEdit(row) {
	editAssignmentId.value = row.name
	showCreateModal.value = true
}

async function handleDelete(name) {
	if (!await ask('Are you sure you want to delete this leave policy assignment?')) return
	try {
		const res = await call('arijentek_core.api.leave.delete_leave_policy_assignment', { name })
		if (res && res.success === false) {
			notify(res.error || 'Failed to delete leave policy assignment')
		} else {
			await pager.fetchPage()
			leaveStore.fetchLeaveAllocations()
		}
	} catch (err) {
		notify(err.message || 'Failed to delete leave policy assignment')
	}
}

async function fetchAssignments(page, size) {
	try {
		const params = {
			page: page || 1,
			page_size: size || pager.state.size || 10,
		}
		if (employeeFilter.value) {
			params.employee = employeeFilter.value
		}
		if (policyFilter.value) {
			params.leave_policy = policyFilter.value
		}
		if (searchQuery.value) {
			params.search_text = searchQuery.value
		}
		const res = await call('arijentek_core.api.leave.get_leave_policy_assignments', params)
		const rows = res?.rows || (Array.isArray(res) ? res : res?.data || [])
		const total = res?.total != null ? Number(res.total) : rows.length
		return { rows, total }
	} catch (e) {
		console.error('Failed to fetch leave policy assignments:', e)
		return { rows: [], total: 0 }
	}
}

const pager = useServerPager((page, size) => fetchAssignments(page, size), { size: 10 })

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

watch([employeeFilter, policyFilter], () => {
	triggerFilterRefresh()
})

onMounted(async () => {
	await leaveStore.fetchEmployeeList()
	await leaveStore.fetchLeavePolicies()
	pager.fetchPage()
})
</script>
