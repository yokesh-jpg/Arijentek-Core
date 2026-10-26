<template>
	<div class="space-y-4 sm:space-y-5 tab-fill">
		<!-- ===== Header ===== -->
		<div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
			<div>
				<h2 class="section-title">Leave types</h2>
				<p class="section-subtitle">The kinds of leave people can apply for.</p>
			</div>
			<button v-if="leaveStore.canCreateLeaveTypes" @click="handleCreate" class="btn-primary shrink-0">
				<span class="material-symbols-outlined !text-[18px]">add</span>
				Add type
			</button>
		</div>

		<!-- ===== Filters ===== -->
		<div class="glass-card !p-3">
			<div class="flex flex-wrap items-center gap-2">
				<div class="relative flex-[2] min-w-[220px]">
					<span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/55 pointer-events-none">search</span>
					<input v-model="searchQuery" type="text" placeholder="Type name" aria-label="Search" class="field-input !pl-9" />
				</div>
			</div>
		</div>

		<!-- ===== Table ===== -->
		<DataTable
			:columns="listColumns"
			:rows="pager.state.rows"
			:actions="actionsForType"
			:row-key="'name'"
			:loading="pager.state.loading"
			:empty-text="searchQuery ? 'No leave types match that search.' : 'No leave types found.'"
			:show-pager="true"
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
		>
			<template #cell-name="{ row }">
				<div class="flex items-center gap-3 min-w-0">
					<span class="w-9 h-9 shrink-0 rounded-[10px] grid place-items-center bg-accent/[0.10] text-accent dark:text-accent-light">
						<span class="material-symbols-outlined !text-[18px]">beach_access</span>
					</span>
					<div class="min-w-0">
						<span class="block truncate font-medium">{{ row.leave_type_name || row.name }}</span>
						<span v-if="row.max_leaves_allowed" class="sm:hidden block text-xs font-normal tabular-nums text-[#5C6169] dark:text-white/60">
							{{ row.max_leaves_allowed }} days
						</span>
					</div>
				</div>
			</template>
			<template #cell-allowance="{ row }">
				<span v-if="row.max_leaves_allowed" class="tabular-nums whitespace-nowrap">{{ row.max_leaves_allowed }} days</span>
				<span v-else class="text-[#656A72] dark:text-white/30">—</span>
			</template>
		</DataTable>

		<!-- Modals -->
		<CreateLeaveTypes
			v-model="showCreateModal"
			:editId="editTypeId"
			@save="pager.fetchPage"
		/>
	</div>
</template>

<script setup>
import DataTable from '@/components/DataTable.vue'
import { useServerPager } from '@/composables/useServerPager.js'
import CreateLeaveTypes from '../../forms/leave/create_leave_types.vue'
import { useLeaveStore } from '@/stores/leave'
import { notify, ask } from '@/utils/feedback.js'
import { getErrorMessage } from '@/utils'
import { ref, watch, onMounted } from 'vue'
import { call } from 'frappe-ui'

const leaveStore = useLeaveStore()

const searchQuery = ref('')
const showCreateModal = ref(false)
const editTypeId = ref('')

const listColumns = [
	{ key: 'name', label: 'Name', className: 'table-td-strong' },
	{ key: 'allowance', label: 'Allowance', className: 'table-td tabular-nums whitespace-nowrap hidden sm:table-cell' },
]

function actionsForType(row) {
	return [
		{
			label: 'Edit',
			icon: 'edit',
			show: leaveStore.canEditLeaveTypes,
			onClick: () => handleEdit(row),
		},
		{ divider: true },
		{
			label: 'Delete',
			icon: 'delete',
			danger: true,
			show: leaveStore.canDeleteLeaveTypes,
			onClick: () => deleteLeaveType(row.name),
		},
	]
}

function handleCreate() {
	editTypeId.value = ''
	showCreateModal.value = true
}

function handleEdit(row) {
	editTypeId.value = row.name
	showCreateModal.value = true
}

async function deleteLeaveType(name) {
	if (!await ask('Are you sure you want to delete this leave type?')) return
	try {
		const res = await call('arijentek_core.api.leave.delete_leave_type', { name })
		if (res && res.success === false) {
			notify(getErrorMessage(res.error, 'Failed to delete leave type.'))
		} else {
			await pager.fetchPage()
			leaveStore.fetchAllLeaveTypes()
		}
	} catch (err) {
		notify(getErrorMessage(err, 'Failed to delete leave type.'))
	}
}

async function fetchLeaveTypes(page, size) {
	try {
		const params = {
			page: page || 1,
			page_size: size || pager.state.size || 10,
		}
		if (searchQuery.value) {
			params.search_text = searchQuery.value
		}
		const res = await call('arijentek_core.api.leave.get_leave_types', params)
		const rows = res?.rows || (Array.isArray(res) ? res : res?.data || [])
		const total = res?.total != null ? Number(res.total) : rows.length
		return { rows, total }
	} catch (e) {
		console.error('Failed to fetch leave types:', e)
		return { rows: [], total: 0 }
	}
}

const pager = useServerPager((page, size) => fetchLeaveTypes(page, size), { size: 10 })

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

onMounted(() => {
	pager.fetchPage()
})
</script>
