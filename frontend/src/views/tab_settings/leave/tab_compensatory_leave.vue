<template>
	<div class="space-y-4 sm:space-y-5 tab-fill">
		<!-- ===== Header ===== -->
		<div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
			<div>
				<h2 class="section-title">Compensatory leave</h2>
				<p class="section-subtitle">Time back for days worked outside the rota.</p>
			</div>
			<button v-if="leaveStore.canCreateCompLeave" @click="handleCreate" class="btn-primary shrink-0">
				<span class="material-symbols-outlined !text-[18px]">add</span>
				New request
			</button>
		</div>

		<!-- ===== Filters ===== -->
		<div class="glass-card !p-3 flex flex-wrap items-center gap-2">
			<div class="relative flex-[2] min-w-[220px]">
				<span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/55 pointer-events-none">search</span>
				<input v-model="searchQuery" type="text" placeholder="Search requests" class="field-input !pl-9" aria-label="Search requests" />
			</div>
			<div v-if="compEmployeeOptions.length > 1" class="flex-1 min-w-[180px]">
				<SearchableDropdown
					v-model="employeeFilter"
					:options="compEmployeeOptions"
					labelKey="employee_name"
					valueKey="name"
					placeholder="All employees"
				/>
			</div>
		</div>

		<!-- ===== Table ===== -->
		<DataTable
			:columns="listColumns"
			:rows="pager.state.rows"
			:actions="actionsForComp"
			:row-key="'name'"
			:loading="pager.state.loading"
			:empty-text="searchQuery || employeeFilter ? 'No compensatory leave requests match these filters.' : 'No compensatory leave requests.'"
			:show-pager="true"
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			:on-row-click="(req) => showCompViewModal(req.name)"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
		>
			<template #cell-name="{ row }">
				<div class="max-w-[180px] sm:max-w-none">
					<span class="block tabular-nums break-words leading-snug sm:truncate font-medium">{{ row.name }}</span>
					<span class="block sm:hidden text-xs font-normal text-[#5C6169] dark:text-white/60 leading-snug">
						{{ row.employee_name }} · {{ formatDate(row.work_from_date) }}
					</span>
				</div>
			</template>
			<template #cell-employee="{ row }">
				<span class="truncate">{{ row.employee_name }}</span>
			</template>
			<template #cell-worked="{ row }">
				<span class="tabular-nums whitespace-nowrap">
					{{ formatDate(row.work_from_date) }}<template v-if="row.work_end_date !== row.work_from_date"> – {{ formatDate(row.work_end_date) }}</template>
				</span>
				<span v-if="row.half_day" class="block text-xs text-[#656A72] dark:text-white/55">Half day</span>
			</template>
			<template #cell-status="{ row }">
				<span class="premium-tag" :class="getStatusStyle(row.status)">{{ row.status }}</span>
			</template>
		</DataTable>

		<!-- Create / Edit Modal -->
		<CreateCompensatoryLeave
			v-model="showCompModal"
			:editId="editCompId"
			@save="pager.fetchPage"
		/>

		<!-- View Modal -->
		<ViewCompensatoryLeave
			v-model="showCompDetailModal"
			:compLeaveId="viewCompName"
			:canApprove="canApproveComp"
			@edit="handleEditCompFromView"
			@delete="confirmDeleteComp"
			@status-updated="pager.fetchPage"
		/>

		<!-- Delete confirmation: compensatory leave -->
		<Teleport to="body">
			<div
				v-if="showDeleteCompPopup"
				class="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 p-4"
				@click.self="showDeleteCompPopup = false"
			>
				<div role="alertdialog" aria-modal="true" class="bg-white dark:bg-surface-2 rounded-2xl shadow-2xl max-w-md w-full p-6 border-t-4 border-red-500" @keydown.esc="showDeleteCompPopup = false">
					<h3 class="text-xl font-semibold text-[#17181B] dark:text-white mb-2">Delete compensatory leave?</h3>
					<p class="text-base text-[#5C6169] dark:text-white/60 mb-2">This request has already been approved or rejected.</p>
					<p class="text-[13px] text-red-700 dark:text-red-400 mb-6">The leave it allocated is deleted with it.</p>
					<p v-if="deleteCompError" class="text-[13px] font-medium text-red-600 dark:text-red-400 -mt-3 mb-5">{{ deleteCompError }}</p>
					<div class="flex gap-3">
						<button
							type="button"
							class="flex-1 py-3.5 rounded-xl border-2 border-black/[0.12] dark:border-white/[0.08] text-[#2D3138] dark:text-white/80 font-semibold text-base hover:bg-black/[0.03] dark:hover:bg-surface-3 transition"
							@click="showDeleteCompPopup = false"
						>
							Cancel
						</button>
						<button
							type="button"
							class="flex-1 py-3.5 rounded-xl bg-red-500 hover:bg-red-600 text-white font-semibold text-base transition inline-flex items-center justify-center gap-2 disabled:opacity-50"
							:disabled="deleteCompLoading"
							@click="handleApprovedRejectedCompDelete"
						>
							<span v-if="deleteCompLoading" class="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></span>
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
import CreateCompensatoryLeave from '../../forms/leave/create_compensatory_leave.vue'
import ViewCompensatoryLeave from '../../page_views/leave/view_compensatory_leave.vue'
import { useLeaveStore } from '@/stores/leave'
import { useEmployeeStore } from '@/stores/employee'
import { notify, ask } from '@/utils/feedback.js'
import { ref, computed, watch, onMounted } from 'vue'
import { call } from 'frappe-ui'

const leaveStore = useLeaveStore()
const employeeStore = useEmployeeStore()

const searchQuery = ref('')
const employeeFilter = ref('')

const showCompModal = ref(false)
const editCompId = ref('')
const canApproveComp = ref(false)

const showCompDetailModal = ref(false)
const viewCompName = ref('')

// Delete Comp popup state
const showDeleteCompPopup = ref(false)
const deleteCompLoading = ref(false)
const compToDelete = ref(null)
const deleteCompError = ref('')

const currEmployee = computed(() => employeeStore.employee?.name || '')

const compEmployeeOptions = computed(() => {
	const opts = [{ name: '', employee_name: 'All employees' }]
	if (leaveStore.approvedEmployeeList) {
		leaveStore.approvedEmployeeList.forEach((emp) => {
			opts.push({
				name: emp.name,
				employee_name: emp.employee_name + (emp.name === currEmployee.value ? ' (Me)' : ''),
			})
		})
	}
	return opts
})

const listColumns = [
	{ key: 'name', label: 'Request', className: 'table-td-strong max-w-[180px] sm:max-w-none' },
	{ key: 'employee', label: 'Employee', className: 'table-td hidden sm:table-cell' },
	{ key: 'worked', label: 'Worked', className: 'table-td tabular-nums whitespace-nowrap hidden sm:table-cell' },
	{ key: 'status', label: 'Status', className: 'table-td' },
]

function actionsForComp(req) {
	return [
		{
			label: 'Approve',
			icon: 'check_circle',
			show: req.docstatus === 0 && leaveStore.canSubmitCompLeave,
			onClick: () => handleApproveComp(req.name),
		},
		{
			label: 'Reject',
			icon: 'cancel',
			show: req.docstatus === 0 && leaveStore.canSubmitCompLeave,
			onClick: () => handleRejectComp(req.name),
		},
		{
			label: 'Edit',
			icon: 'edit',
			show: req.docstatus === 0,
			onClick: () => handleEditComp(req),
		},
		{ divider: true },
		{
			label: 'Delete',
			icon: 'delete',
			danger: true,
			onClick: () => confirmDeleteComp(req),
		},
	]
}

function handleCreate() {
	editCompId.value = ''
	showCompModal.value = true
}

function handleEditComp(req) {
	editCompId.value = req.name
	showCompModal.value = true
}

function handleEditCompFromView(req) {
	editCompId.value = req.name
	showCompDetailModal.value = false
	showCompModal.value = true
}

function showCompViewModal(name) {
	viewCompName.value = name
	showCompDetailModal.value = true
}

async function fetchCompRequests(page, size) {
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
		const res = await call('arijentek_core.api.leave.get_compensatory_leave_requests', params)
		const rows = res?.rows || (Array.isArray(res) ? res : res?.data || [])
		const total = res?.total != null ? Number(res.total) : rows.length
		return { rows, total }
	} catch (e) {
		console.error('Failed to fetch compensatory leave requests:', e)
		return { rows: [], total: 0 }
	}
}

const pager = useServerPager((page, size) => fetchCompRequests(page, size), { size: 10 })

function triggerFilterRefresh() {
	if (pager.state.page !== 1) {
		pager.state.page = 1
	} else {
		pager.fetchPage()
	}
}

async function handleApproveComp(name) {
	if (!await ask('Are you sure you want to approve this compensatory leave request?')) return
	try {
		const res = await call('arijentek_core.api.leave.approve_compensatory_leave_request', { name })
		if (res && res.success === false) {
			notify(res.error || 'Failed to approve request')
		} else {
			await pager.fetchPage()
			leaveStore.fetchLeaveBalances()
		}
	} catch (err) {
		notify(err.message || 'Failed to approve request')
	}
}

async function handleRejectComp(name) {
	if (!await ask('Are you sure you want to reject this compensatory leave request?')) return
	try {
		const res = await call('arijentek_core.api.leave.reject_compensatory_leave_request', { name })
		if (res && res.success === false) {
			notify(res.error || 'Failed to reject request')
		} else {
			await pager.fetchPage()
			leaveStore.fetchLeaveBalances()
		}
	} catch (err) {
		notify(err.message || 'Failed to reject request')
	}
}

async function confirmDeleteComp(req) {
	if (req.docstatus === 0) {
		if (!await ask('Are you sure you want to delete this compensatory leave request?')) return
		try {
			const res = await call('arijentek_core.api.leave.validate_delete_approved_entry', { name: req.name })
			if (res && res.success === false) {
				notify(res.error || 'Failed to delete request')
			} else {
				await pager.fetchPage()
				if (showCompDetailModal.value && viewCompName.value === req.name) {
					showCompDetailModal.value = false
				}
			}
		} catch (err) {
			notify(err.message || 'Failed to delete request')
		}
	} else {
		compToDelete.value = req
		deleteCompError.value = ''
		showDeleteCompPopup.value = true
	}
}

async function handleApprovedRejectedCompDelete() {
	if (!compToDelete.value) return
	deleteCompLoading.value = true
	deleteCompError.value = ''
	try {
		const res = await call('arijentek_core.api.leave.validate_delete_approved_entry', { name: compToDelete.value.name })
		if (res && res.success === false) {
			deleteCompError.value = res.error || 'Failed to delete request'
		} else {
			showDeleteCompPopup.value = false
			compToDelete.value = null
			await pager.fetchPage()
			if (showCompDetailModal.value) {
				showCompDetailModal.value = false
			}
		}
	} catch (err) {
		deleteCompError.value = err.message || 'Failed to delete request'
	} finally {
		deleteCompLoading.value = false
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
	try {
		const canApprove = await call('arijentek_core.api.leave.can_approve_compensatory_leaves')
		canApproveComp.value = !!canApprove
	} catch (e) {
		console.error('Failed to check can_approve_compensatory_leaves:', e)
	}
	pager.fetchPage()
})

function getStatusStyle(status) {
	const s = status?.toLowerCase()
	if (s === 'approved') return 'tag-emerald'
	if (s === 'draft' || s === 'open' || s === 'pending') return 'tag-amber'
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
