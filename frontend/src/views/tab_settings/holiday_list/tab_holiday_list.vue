<template>
	<div class="space-y-5 tab-fill">
		<!-- ===== Header ===== -->
		<div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
			<div>
				<h2 class="section-title">Holiday lists</h2>
				<p class="section-subtitle">The non-working days a roster is measured against.</p>
			</div>
			<div class="flex items-center gap-2">
				<button v-if="leaveStore.canCreateHolidayList" @click="showCreateHolidayList = true" class="btn-primary shrink-0">
					<span class="material-symbols-outlined !text-[18px]">add</span>
					Add list
				</button>
			</div>
		</div>

		<div class="glass-card !p-3 flex flex-wrap items-center gap-2">
			<div class="relative flex-1 min-w-[220px]">
				<span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/55 pointer-events-none">search</span>
				<input v-model="searchQuery" type="text" placeholder="Search holiday lists" class="field-input !pl-9" aria-label="Search holiday lists" />
			</div>
		</div>

		<!-- ===== Table (server-side pagination) ===== -->
		<DataTable
			:columns="listColumns"
			:rows="pager.state.rows"
			:actions="actionsForRow"
			:row-key="'name'"
			:loading="pager.state.loading"
			:empty-text="searchQuery ? 'No holiday list matches that search.' : 'No holiday lists yet.'"
			:show-pager="true"
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			:on-row-click="(hl) => openView(hl)"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
		>
			<template #cell-name="{ row }">
				<div class="flex items-center gap-2 sm:gap-3 min-w-0">
					<span class="avatar-chip !w-7 !h-7 sm:!w-9 sm:!h-9">
						<span class="material-symbols-outlined !text-[16px]">event</span>
					</span>
					<span class="min-w-0">
						<span class="block break-words leading-snug sm:truncate">{{ row.holiday_list_name || row.name }}</span>
						<!-- The period only has its own column from sm up. -->
						<span class="block sm:hidden text-xs font-normal text-[#5C6169] dark:text-white/60 leading-snug">
							{{ formatDate(row.from_date) }} – {{ formatDate(row.to_date) }}
						</span>
					</span>
				</div>
			</template>
			<template #cell-period="{ row }">
				{{ formatDate(row.from_date) }} – {{ formatDate(row.to_date) }}
			</template>
			<template #cell-weekly_off="{ row }">
				<span v-if="row.weekly_off" class="premium-tag tag-neutral">{{ row.weekly_off }}</span>
				<span v-else class="text-[#656A72] dark:text-white/55">—</span>
			</template>
			<template #cell-days_off="{ row }">
				<span class="tabular-nums font-medium text-[#17181B] dark:text-white">{{ row.total_holidays || 0 }}</span>
			</template>
		</DataTable>

		<CreateHolidayList v-model="showCreateHolidayList" :edit-id="editHolidayListId" @save="pager.fetchPage" />
		<ViewHolidayList v-model="showViewHolidayList" :holidayListId="viewHolidayListId"
			:can-edit="leaveStore.canEditHolidayList" :can-delete="leaveStore.canDeleteHolidayList"
			@edit="(d) => { showViewHolidayList = false; openEdit(d) }"
			@delete="(d) => { showViewHolidayList = false; deleteHolidayList(d.name) }" />
	</div>
</template>

<script setup>
import DataTable from '@/components/DataTable.vue'
import { useServerPager } from '@/composables/useServerPager.js'
import { notify, ask } from '@/utils/feedback.js'
import { ref, watch, onMounted } from 'vue'
import { call } from 'frappe-ui'
import { useLeaveStore } from '@/stores/leave'
import { getErrorMessage } from '@/utils.js'
import CreateHolidayList from '@/views/forms/holiday/create_holiday_list.vue'
import ViewHolidayList from '@/views/page_views/holiday/view_holiday_list.vue'

const leaveStore = useLeaveStore()
const searchQuery = ref('')
const isDeletingHolidayList = ref(false)
const showCreateHolidayList = ref(false)
const editHolidayListId = ref('')
const showViewHolidayList = ref(false)
const viewHolidayListId = ref('')

watch(showCreateHolidayList, (val) => {
	if (!val) editHolidayListId.value = ''
})

function openEdit(hl) {
	editHolidayListId.value = hl.name
	showCreateHolidayList.value = true
}

function openView(hl) {
	viewHolidayListId.value = hl.name
	showViewHolidayList.value = true
}

async function deleteHolidayList(name) {
	if (!await ask(`Are you sure you want to delete ${name}?`)) return

	isDeletingHolidayList.value = name

	try {
		const data = await call('arijentek_core.api.leave.delete_holiday_list', { name })
		if (data && data.success === false) {
			notify(getErrorMessage(data.error || "Failed to delete"))
		} else {
			await pager.fetchPage()
		}
	} catch (err) {
		notify(getErrorMessage(err, "Failed to delete Holiday List"))
	} finally {
		isDeletingHolidayList.value = false
	}
}

/* Server-side fetch: one page at a time (page/page_size) via get_holiday_list.
   Returns { rows, total } for useServerPager. Handles both the paginated dict
   (page_size > 0) and the legacy list (page_size = 0) responses. */
async function fetchHolidayLists(page, size) {
	const params = { page, page_size: size }
	if (searchQuery.value) {
		params.search_text = searchQuery.value
	}
	try {
		const res = await call('arijentek_core.api.leave.get_holiday_list', params)
		const rows = Array.isArray(res) ? res : (res?.data || [])
		const total = Array.isArray(res) ? res.length : Number(res?.total || 0)
		return { rows, total }
	} catch (e) {
		console.error('Failed to fetch holiday lists:', e)
		return { rows: [], total: 0 }
	}
}

const pager = useServerPager((page, size) => fetchHolidayLists(page, size), { size: 10 })

const listColumns = [
	{ key: 'name', label: 'Holiday list', className: 'table-td-strong' },
	{ key: 'period', label: 'Period', className: 'hidden sm:table-cell' },
	{ key: 'weekly_off', label: 'Weekly off', className: 'hidden md:table-cell' },
	{ key: 'days_off', label: 'Days off', align: 'right', className: 'text-right tabular-nums font-medium text-[#17181B] dark:text-white' },
]

function actionsForRow(hl) {
	return [
		{ label: 'Edit', icon: 'edit', show: leaveStore.canEditHolidayList, onClick: () => openEdit(hl) },
		{ label: 'Delete', icon: 'delete', danger: true, show: leaveStore.canDeleteHolidayList, disabled: isDeletingHolidayList === hl.name, onClick: () => deleteHolidayList(hl.name) },
	]
}

// Filter changes reset to page 1. The pager's own [page, size] watch re-fetches
// when the page actually changes; if it is already 1, fetch directly so a filter
// change on page 1 still refreshes.
watch(searchQuery, () => {
	if (pager.state.page !== 1) {
		pager.state.page = 1
	} else {
		pager.fetchPage()
	}
})

onMounted(() => {
	pager.fetchPage()
})

function formatDate(dateStr) {
	if (!dateStr) return '-'
	return new Date(dateStr).toLocaleDateString("en-US", {
		month: "short",
		day: "numeric",
		year: "numeric",
	});
}
</script>