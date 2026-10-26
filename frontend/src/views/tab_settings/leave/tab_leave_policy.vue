<template>
	<div class="space-y-4 sm:space-y-5 tab-fill">
		<!-- ===== Header ===== -->
		<div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
			<div>
				<h2 class="section-title">Leave policies</h2>
				<p class="section-subtitle">Allowance sets that get assigned to people.</p>
			</div>
			<button v-if="leaveStore.canCreateLeavePolicy" @click="handleCreate" class="btn-primary shrink-0">
				<span class="material-symbols-outlined !text-[18px]">add</span>
				Add policy
			</button>
		</div>

		<!-- ===== Filters ===== -->
		<div class="glass-card !p-3">
			<div class="flex flex-wrap items-center gap-2">
				<div class="relative flex-[2] min-w-[220px]">
					<span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/55 pointer-events-none">search</span>
					<input v-model="searchQuery" type="text" placeholder="Policy title or ID" aria-label="Search" class="field-input !pl-9" />
				</div>
			</div>
		</div>

		<!-- ===== Table ===== -->
		<DataTable
			:columns="listColumns"
			:rows="pager.state.rows"
			:actions="actionsForPolicy"
			:row-key="'name'"
			:loading="pager.state.loading"
			:empty-text="searchQuery ? 'No leave policies match that search.' : 'No leave policies found.'"
			:show-pager="true"
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			:on-row-click="(row) => openView(row.name)"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
		>
			<template #cell-name="{ row }">
				<div>
					<span class="block truncate font-medium">{{ row.title || row.name }}</span>
					<span class="block text-xs font-normal text-[#5C6169] dark:text-white/60">{{ row.name }}</span>
				</div>
			</template>
			<template #cell-covers="{ row }">
				<span v-if="row.leave_policy_details?.length" class="flex flex-wrap gap-1">
					<span v-for="d in row.leave_policy_details" :key="d.leave_type" class="premium-tag tag-neutral">
						{{ d.leave_type }} · {{ d.annual_allocation }}
					</span>
				</span>
				<span v-else class="text-[#656A72] dark:text-white/30">—</span>
			</template>
		</DataTable>

		<!-- Modals -->
		<CreateLeavePolicy
			v-model="showCreateModal"
			:editId="editPolicyId"
			@save="pager.fetchPage"
		/>

		<ViewLeavePolicy
			v-model="showViewModal"
			:leavePolicyId="viewPolicyId"
			@edit="handleViewEdit"
			@delete="deleteLeavePolicy"
		/>
	</div>
</template>

<script setup>
import DataTable from '@/components/DataTable.vue'
import { useServerPager } from '@/composables/useServerPager.js'
import CreateLeavePolicy from '../../forms/leave/create_leave_policy.vue'
import ViewLeavePolicy from '../../page_views/leave/view_leave_policy.vue'
import { useLeaveStore } from '@/stores/leave'
import { notify, ask } from '@/utils/feedback.js'
import { getErrorMessage } from '@/utils'
import { ref, watch, onMounted } from 'vue'
import { call } from 'frappe-ui'

const leaveStore = useLeaveStore()

const searchQuery = ref('')
const showCreateModal = ref(false)
const editPolicyId = ref('')
const showViewModal = ref(false)
const viewPolicyId = ref('')

const listColumns = [
	{ key: 'name', label: 'Policy', className: 'table-td-strong' },
	{ key: 'covers', label: 'Covers', className: 'table-td hidden sm:table-cell' },
]

function actionsForPolicy(row) {
	return [
		{
			label: 'Edit',
			icon: 'edit',
			show: leaveStore.canEditLeavePolicy,
			onClick: () => handleEdit(row),
		},
		{ divider: true },
		{
			label: 'Delete',
			icon: 'delete',
			danger: true,
			show: leaveStore.canDeleteLeavePolicy,
			onClick: () => deleteLeavePolicy(row.name),
		},
	]
}

function handleCreate() {
	editPolicyId.value = ''
	showCreateModal.value = true
}

function handleEdit(row) {
	editPolicyId.value = row.name
	showCreateModal.value = true
}

function openView(name) {
	viewPolicyId.value = name
	showViewModal.value = true
}

function handleViewEdit(id) {
	showViewModal.value = false
	editPolicyId.value = id
	showCreateModal.value = true
}

async function deleteLeavePolicy(name) {
	if (!await ask('Are you sure you want to delete this leave policy?')) return
	try {
		const res = await call('arijentek_core.api.leave.delete_leave_policy', { name })
		if (res && res.success === false) {
			notify(getErrorMessage(res.error || res, 'Failed to delete leave policy.'))
		} else {
			await pager.fetchPage()
			if (showViewModal.value && viewPolicyId.value === name) {
				showViewModal.value = false
			}
		}
	} catch (err) {
		notify(getErrorMessage(err, 'Failed to delete leave policy.'))
	}
}

async function fetchPolicies(page, size) {
	try {
		const params = {
			page: page || 1,
			page_size: size || pager.state.size || 10,
		}
		if (searchQuery.value) {
			params.search_text = searchQuery.value
		}
		const res = await call('arijentek_core.api.leave.get_leave_policy', params)
		const rows = res?.rows || (Array.isArray(res) ? res : res?.data || [])
		const total = res?.total != null ? Number(res.total) : rows.length
		return { rows, total }
	} catch (e) {
		console.error('Failed to fetch leave policies:', e)
		return { rows: [], total: 0 }
	}
}

const pager = useServerPager((page, size) => fetchPolicies(page, size), { size: 10 })

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
