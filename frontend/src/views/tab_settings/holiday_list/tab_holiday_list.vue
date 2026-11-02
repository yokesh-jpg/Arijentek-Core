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
			:sort="{ key: sortBy, dir: sortDir }"
			:on-row-click="(hl) => openView(hl)"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
			@sort="toggleSort"
		>
			<template #cell-name="{ row }">
				<div class="flex items-center gap-2 sm:gap-3 min-w-0">
					<span class="avatar-chip !w-7 !h-7 sm:!w-9 sm:!h-9 shrink-0">
						<span class="material-symbols-outlined !text-[16px]">event</span>
					</span>
					<span class="min-w-0">
						<span class="block break-words leading-snug font-medium text-[#17181B] dark:text-white">{{ row.holiday_list_name || row.name }}</span>
						<!-- The period only has its own column from sm up. -->
						<div class="flex items-center gap-1.5 sm:hidden mt-0.5">
							<span class="text-xs font-normal text-[#5C6169] dark:text-white/60 leading-snug">
								{{ formatDate(row.from_date) }} – {{ formatDate(row.to_date) }}
							</span>
							<span
								v-if="isCurrentList(row)"
								class="px-1.5 py-0.2 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400 shrink-0"
							>
								Current
							</span>
						</div>
					</span>
				</div>
			</template>
			<template #cell-period="{ row }">
				<div class="flex items-center gap-2 flex-wrap">
					<span class="text-[13px] text-[#4A4D55] dark:text-white/70 whitespace-nowrap">
						{{ formatDate(row.from_date) }} – {{ formatDate(row.to_date) }}
					</span>
					<span
						v-if="isCurrentList(row)"
						class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/60 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800/40 shrink-0"
					>
						Current
					</span>
				</div>
			</template>
			<template #cell-days_off="{ row }">
				<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold tag-neutral tabular-nums">
					{{ row.total_holidays || 0 }} {{ row.total_holidays === 1 ? 'day' : 'days' }}
				</span>
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
import { ref, watch, onMounted, computed } from 'vue'
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
	const params = { page, page_size: size, order_by: orderParam.value }
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

/* Sort state: the list whose period starts latest first is the default
   reading order; Holiday list and Period headers toggle it server-side
   (sorted on holiday_list_name / from_date). */
const sortBy = ref('period') // 'period' | 'name'
const sortDir = ref('desc') // 'asc' | 'desc'
const orderParam = computed(() => `${sortBy.value === 'period' ? 'from_date' : 'holiday_list_name'} ${sortDir.value}`)

function toggleSort(col) {
	if (sortBy.value === col) {
		sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
	} else {
		sortBy.value = col
		sortDir.value = 'asc'
	}
	if (pager.state.page !== 1) {
		pager.state.page = 1
	} else {
		pager.fetchPage()
	}
}

const listColumns = [
	{ key: 'name', label: 'Holiday list', className: 'table-td-strong min-w-[220px]', sortable: true },
	{ key: 'period', label: 'Period', className: 'hidden sm:table-cell min-w-[200px]', sortable: true },
	{ key: 'days_off', label: 'Days off', align: 'right', className: 'text-right tabular-nums font-medium text-[#17181B] dark:text-white w-[130px]' },
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

function isCurrentList(row) {
	if (!row?.from_date || !row?.to_date) return false
	const today = new Date().toISOString().slice(0, 10)
	return today >= row.from_date && today <= row.to_date
}
</script>