<template>
	<div class="space-y-4 sm:space-y-5 tab-fill">
		<!-- ===== Header ===== -->
		<div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
			<div>
				<h2 class="section-title">My leave</h2>
				<p class="section-subtitle">Your balance, your applications, and time off to come.</p>
			</div>
			<div class="flex items-center gap-2 flex-wrap">
				<div v-if="leaveStore.isApprover || canSubmitLeaveApplication" class="w-full sm:w-56">
					<SearchableDropdown
						v-model="balanceEmployee"
						:options="availableEmployeeOptions"
						labelKey="employee_name"
						valueKey="name"
						placeholder="All employees"
					/>
				</div>
				<button v-if="leaveStore.canCreate" @click="handleCreate" class="btn-primary shrink-0">
					<span class="material-symbols-outlined !text-[18px]">add</span>
					Request leave
				</button>
			</div>
		</div>

		<!-- ===== Balances ===== -->
		<div v-if="balanceEmployee && displayedLeaveBalances?.length" class="grid grid-cols-2 lg:grid-cols-5 gap-3 sm:gap-4">
			<div v-for="lb in displayedLeaveBalances" :key="lb.leave_type" class="glass-card !p-4">
				<p class="text-xs text-[#5C6169] dark:text-white/60 truncate" :title="lb.leave_type">{{ lb.leave_type }}</p>
				<div class="flex items-baseline gap-1.5 mt-1">
					<span class="text-2xl font-semibold tabular-nums text-[#17181B] dark:text-white leading-none">{{ lb.balance_leaves ?? 0 }}</span>
					<span class="text-xs text-[#656A72] dark:text-white/55 tabular-nums">/ {{ lb.allocated_leaves ?? 0 }} days</span>
				</div>
				<div class="mt-3 h-1.5 rounded-full bg-black/[0.06] dark:bg-white/[0.09] overflow-hidden">
					<div class="h-full rounded-full bg-accent transition-[width] duration-500" :style="{ width: balancePct(lb) + '%' }"></div>
				</div>
				<p class="text-xs text-[#656A72] dark:text-white/55 mt-1.5 tabular-nums">
					{{ lb.used_leaves ?? 0 }} taken<template v-if="lb.pending_leaves"> · {{ lb.pending_leaves }} pending</template>
				</p>
			</div>
		</div>

		<!-- ===== Filters ===== -->
		<div class="glass-card !p-3 flex flex-wrap items-center gap-2">
			<div class="relative flex-[2] min-w-[220px]">
				<span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/55 pointer-events-none">search</span>
				<input v-model="searchQuery" type="text" placeholder="Search applications" class="field-input !pl-9" aria-label="Search applications" />
			</div>
			<div class="flex-1 min-w-[160px]">
				<SearchableDropdown
					v-model="statusFilter"
					:options="statusOptions"
					placeholder="All statuses"
					:showAllOption="true"
					allOptionLabel="All statuses"
				/>
			</div>
		</div>

		<!-- ===== Table ===== -->
		<DataTable
			:columns="listColumns"
			:rows="pager.state.rows"
			:actions="actionsForApp"
			:row-key="'name'"
			:loading="pager.state.loading"
			:empty-text="searchQuery || statusFilter ? 'No leave applications match these filters.' : 'No leave applications yet.'"
			:show-pager="true"
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			:on-row-click="(app) => showViewModal(app.name)"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
		>
			<template #cell-name="{ row }">
				<div class="max-w-[180px] sm:max-w-none">
					<span class="block tabular-nums break-words leading-snug sm:truncate font-medium">{{ row.name }}</span>
					<span class="block sm:hidden text-xs font-normal text-[#5C6169] dark:text-white/60 leading-snug">
						{{ row.employee_name }} · {{ row.total_leave_days }}d · {{ row.leave_type }}
					</span>
				</div>
			</template>
			<template #cell-employee="{ row }">
				<span class="truncate">{{ row.employee_name }}</span>
				<span class="block md:hidden text-xs text-[#5C6169] dark:text-white/60">{{ row.leave_type }}</span>
			</template>
			<template #cell-period="{ row }">
				<span class="tabular-nums whitespace-nowrap">{{ formatDate(row.from_date) }}<template v-if="row.to_date !== row.from_date"> – {{ formatDate(row.to_date) }}</template></span>
			</template>
			<template #cell-leave_type="{ row }">
				<span class="whitespace-nowrap">{{ row.leave_type }}</span>
			</template>
			<template #cell-total_leave_days="{ row }">
				<span class="tabular-nums whitespace-nowrap">
					{{ row.total_leave_days }}
					<span v-if="row.half_day" class="block text-xs text-[#656A72] dark:text-white/55">half day</span>
				</span>
			</template>
			<template #cell-status="{ row }">
				<span class="premium-tag" :class="getStatusStyle(row.status)">{{ row.status }}</span>
			</template>
		</DataTable>

		<!-- New / Edit Request Modal -->
		<CreateLeaveApplication
			v-model="showCreateForm"
			:editId="editApplicationName"
			@save="onLeaveSaved"
		/>

		<!-- View Detail Modal -->
		<ViewLeaveApplication
			v-model="showDetailModal"
			:leaveApplicationId="viewApplicationName"
			@edit="handleEdit"
			@delete="(app) => handleDelete(app.name)"
			@status-updated="onStatusUpdated"
			@delete-approved-rejected="confirmDeleteApprovedRejected"
		/>

		<!-- Delete confirmation: approved / rejected leave -->
		<Teleport to="body">
			<div
				v-if="showDeletePopup"
				class="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 p-4"
				@click.self="showDeletePopup = false"
			>
				<div role="alertdialog" aria-modal="true" class="bg-white dark:bg-surface-2 rounded-2xl shadow-2xl max-w-md w-full p-6 border-t-4 border-red-500" @keydown.esc="showDeletePopup = false">
					<h3 class="text-xl font-semibold text-[#17181B] dark:text-white mb-2">Delete leave application?</h3>
					<p class="text-base text-[#5C6169] dark:text-white/60 mb-2">This application has already been approved or rejected.</p>
					<p class="text-[13px] text-red-700 dark:text-red-400 mb-6">The attendance records for the leave period are deleted along with the application.</p>
					<p v-if="deleteError" class="text-[13px] font-medium text-red-600 dark:text-red-400 -mt-3 mb-5">{{ deleteError }}</p>
					<div class="flex gap-3">
						<button
							type="button"
							class="flex-1 py-3.5 rounded-xl border-2 border-black/[0.12] dark:border-white/[0.08] text-[#2D3138] dark:text-white/80 font-semibold text-base hover:bg-black/[0.03] dark:hover:bg-surface-3 transition"
							@click="showDeletePopup = false"
						>
							Cancel
						</button>
						<button
							type="button"
							class="flex-1 py-3.5 rounded-xl bg-red-500 hover:bg-red-600 text-white font-semibold text-base transition inline-flex items-center justify-center gap-2 disabled:opacity-50"
							:disabled="deleteLoading"
							@click="handleApprovedRejectedDelete"
						>
							<span v-if="deleteLoading" class="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></span>
							Delete
						</button>
					</div>
				</div>
			</div>
		</Teleport>
	</div>
</template>

<script setup>
import DataTable from '@/components/DataTable.vue'
import { useServerPager } from '@/composables/useServerPager.js'
import SearchableDropdown from '@/components/SearchableDropdown.vue'
import CreateLeaveApplication from '../../forms/leave/create_leave_application.vue'
import ViewLeaveApplication from '../../page_views/leave/view_leave_application.vue'
import { useLeaveStore } from '@/stores/leave'
import { useEmployeeStore } from '@/stores/employee'
import { notify, ask } from '@/utils/feedback.js'
import { ref, computed, watch, onMounted } from 'vue'
import { call, createResource } from 'frappe-ui'

const leaveStore = useLeaveStore()
const employeeStore = useEmployeeStore()

const currEmployee = computed(() => employeeStore.employee?.name || '')
const currEmployeeName = computed(() => employeeStore.employee?.employee_name || employeeStore.employee?.name || '')
const canSubmitLeaveApplication = computed(() => leaveStore.canSubmit)

const balanceEmployee = ref('')
const searchQuery = ref('')
const statusFilter = ref('')

const statusOptions = [
	{ label: 'Open', value: 'Open' },
	{ label: 'Approved', value: 'Approved' },
	{ label: 'Rejected', value: 'Rejected' },
	{ label: 'Cancelled', value: 'Cancelled' },
]

const showCreateForm = ref(false)
const editApplicationName = ref('')
const showDetailModal = ref(false)
const viewApplicationName = ref('')

// Delete popup state
const showDeletePopup = ref(false)
const deleteLoading = ref(false)
const leaveToDelete = ref(null)
const deleteError = ref('')

const listColumns = [
	{ key: 'name', label: 'Application', className: 'table-td-strong max-w-[180px] sm:max-w-none' },
	{ key: 'employee', label: 'Employee', className: 'table-td hidden sm:table-cell' },
	{ key: 'period', label: 'Period', className: 'table-td tabular-nums whitespace-nowrap hidden sm:table-cell' },
	{ key: 'leave_type', label: 'Type', className: 'table-td hidden md:table-cell whitespace-nowrap' },
	{ key: 'total_leave_days', label: 'Days', className: 'table-td tabular-nums whitespace-nowrap hidden sm:table-cell' },
	{ key: 'status', label: 'Status', className: 'table-td w-[78px] sm:w-auto' },
]

const availableEmployeeList = computed(() => {
	if (leaveStore.isApprover && leaveStore.approvedEmployeeList?.length > 0) {
		return leaveStore.approvedEmployeeList
	}
	if (canSubmitLeaveApplication.value && leaveStore.employeeList?.length > 0) {
		return leaveStore.employeeList
	}
	return []
})

const availableEmployeeOptions = computed(() => {
	const opts = [{ name: '', employee_name: 'All employees' }]
	availableEmployeeList.value.forEach((emp) => {
		opts.push({
			name: emp.name,
			employee_name: emp.employee_name + (emp.name === currEmployee.value ? ' (Me)' : ''),
		})
	})
	return opts
})

function balancePct(lb) {
	const total = Number(lb?.allocated_leaves || 0)
	if (!total) return 0
	return Math.max(0, Math.min(100, (Number(lb.balance_leaves || 0) / total) * 100))
}

const displayedLeaveBalances = computed(() => {
	if (leaveStore.leaveBalances && leaveStore.leaveBalances.length > 0) {
		return leaveStore.leaveBalances
	}
	const types = leaveStore.allLeaveTypesList || []
	if (types.length > 0) {
		return types.map((lt) => ({
			leave_type: lt.leave_type_name || lt.name,
			allocated_leaves: Number(lt.max_leaves_allowed || 0),
			balance_leaves: Number(lt.max_leaves_allowed || 0),
			used_leaves: 0,
			pending_leaves: 0,
		}))
	}
	return []
})

function actionsForApp(app) {
	return [
		{
			label: 'Approve',
			icon: 'check_circle',
			show: leaveStore.canApproveOrRejectLeaveApplication(app),
			onClick: () => handleUpdateStatus(app.name, 'Approved'),
		},
		{
			label: 'Reject',
			icon: 'cancel',
			show: leaveStore.canApproveOrRejectLeaveApplication(app),
			onClick: () => handleUpdateStatus(app.name, 'Rejected'),
		},
		{
			label: 'Edit',
			icon: 'edit',
			show: leaveStore.canEditLeaveApplication(app),
			onClick: () => handleEdit(app),
		},
		{ divider: true },
		{
			label: 'Delete',
			icon: 'delete',
			danger: true,
			show: leaveStore.canDeleteLeaveApplication(app),
			onClick: () => handleDelete(app.name),
		},
	]
}

async function fetchApplications(page, size) {
	try {
		const params = {
			page: page || 1,
			page_size: size || pager.state.size || 10,
		}
		if (balanceEmployee.value) {
			params.employee = balanceEmployee.value
		}
		if (statusFilter.value) {
			params.status = statusFilter.value
		}
		if (searchQuery.value) {
			params.search_text = searchQuery.value
		}
		const res = await call('arijentek_core.api.leave.get_leave_applications_for_all', params)
		const rows = res?.rows || (Array.isArray(res) ? res : res?.data || [])
		const total = res?.total != null ? Number(res.total) : rows.length
		return { rows, total }
	} catch (e) {
		console.error('Failed to fetch leave applications:', e)
		return { rows: [], total: 0 }
	}
}

const pager = useServerPager((page, size) => fetchApplications(page, size), { size: 10 })

function triggerFilterRefresh() {
	if (pager.state.page !== 1) {
		pager.state.page = 1
	} else {
		pager.fetchPage()
	}
}

function handleCreate() {
	editApplicationName.value = ''
	showCreateForm.value = true
}

function handleEdit(app) {
	const name = typeof app === 'string' ? app : app?.name || ''
	editApplicationName.value = name
	showDetailModal.value = false
	showCreateForm.value = true
}

function showViewModal(name) {
	viewApplicationName.value = name
	showDetailModal.value = true
}

function onLeaveSaved() {
	showCreateForm.value = false
	editApplicationName.value = ''
	pager.fetchPage()
	if (balanceEmployee.value) {
		leaveStore.fetchLeaveBalances(balanceEmployee.value)
	}
}

function onStatusUpdated() {
	pager.fetchPage()
	if (balanceEmployee.value) {
		leaveStore.fetchLeaveBalances(balanceEmployee.value)
	}
}

async function handleUpdateStatus(name, status) {
	if (!await ask(`Are you sure you want to mark this application as ${status}?`)) return
	try {
		const res = await call('arijentek_core.api.leave.update_leave_status', { name, status })
		if (res && res.success === false) {
			notify(res.error || 'Failed to update status')
		} else {
			await pager.fetchPage()
			if (balanceEmployee.value) {
				leaveStore.fetchLeaveBalances(balanceEmployee.value)
			}
			if (showDetailModal.value && viewApplicationName.value === name) {
				showDetailModal.value = false
			}
		}
	} catch (err) {
		notify(err.message || 'Failed to update status')
	}
}

async function handleDelete(name) {
	if (!await ask('Are you sure you want to delete this leave application?')) return
	try {
		const res = await call('arijentek_core.api.leave.delete_leave_application', { name })
		if (res && res.success === false) {
			notify(res.error || 'Failed to delete')
		} else {
			await pager.fetchPage()
			if (balanceEmployee.value) {
				leaveStore.fetchLeaveBalances(balanceEmployee.value)
			}
		}
	} catch (e) {
		notify(e.message || 'Failed to delete leave application')
	}
}

function confirmDeleteApprovedRejected(app) {
	leaveToDelete.value = app
	deleteError.value = ''
	showDeletePopup.value = true
}

async function handleApprovedRejectedDelete() {
	if (!leaveToDelete.value) return
	deleteLoading.value = true
	deleteError.value = ''
	try {
		const res = await call('arijentek_core.api.leave.delete_approved_rejected_leave', {
			leave_application: leaveToDelete.value.name,
		})
		if (res && res.success) {
			showDeletePopup.value = false
			leaveToDelete.value = null
			await pager.fetchPage()
			if (balanceEmployee.value) {
				leaveStore.fetchLeaveBalances(balanceEmployee.value)
			}
		} else {
			deleteError.value = res?.error || 'Failed to delete'
		}
	} catch (e) {
		deleteError.value = e.message || 'Error deleting leave application'
	} finally {
		deleteLoading.value = false
	}
}

let debounceTimer
watch(searchQuery, () => {
	clearTimeout(debounceTimer)
	debounceTimer = setTimeout(() => {
		triggerFilterRefresh()
	}, 300)
})

watch(statusFilter, () => {
	triggerFilterRefresh()
})

watch(balanceEmployee, (newVal) => {
	if (newVal) {
		leaveStore.fetchLeaveBalances(newVal)
	} else {
		leaveStore.leaveBalances = []
	}
	triggerFilterRefresh()
})

onMounted(async () => {
	await employeeStore.init()
	const employeeId = employeeStore.employee?.name
	if (employeeId && !balanceEmployee.value) {
		balanceEmployee.value = employeeId
	}
	await leaveStore.checkApproverStatus()
	if (leaveStore.isApprover || leaveStore.canSubmit) {
		await leaveStore.fetchEmployeeList()
	}
	if (employeeId && leaveStore.isApprover) {
		const hasSelf = leaveStore.approvedEmployeeList.some((e) => e.name === employeeId)
		if (!hasSelf) {
			leaveStore.approvedEmployeeList.unshift({
				name: employeeId,
				employee_name: currEmployeeName.value,
			})
		}
	}
	if (balanceEmployee.value) {
		leaveStore.fetchLeaveBalances(balanceEmployee.value)
	}
	pager.fetchPage()
})

function getStatusStyle(status) {
	const s = status?.toLowerCase()
	if (s === 'approved') return 'tag-emerald'
	if (s === 'open' || s === 'pending') return 'tag-amber'
	if (s === 'rejected') return 'tag-red'
	return 'tag-neutral'
}

function formatDate(dateStr) {
	if (!dateStr) return '-'
	return new Date(dateStr).toLocaleDateString('en-US', {
		month: 'short',
		day: 'numeric',
		year: 'numeric',
	})
}
</script>
