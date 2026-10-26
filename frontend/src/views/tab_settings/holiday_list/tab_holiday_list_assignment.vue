<template>
	<div class="space-y-5 tab-fill">
		<!-- ===== Header ===== -->
		<div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
			<div>
				<h2 class="section-title">Holiday list assignment</h2>
				<p class="section-subtitle">Which list a department or a person is measured against.</p>
			</div>
			<div class="flex items-center gap-2">
				<button v-if="leaveStore.canCreateHolidayListAssignment" @click="editAssignmentId = ''; showCreateAssignmentDialog = true" class="btn-primary shrink-0">
					<span class="material-symbols-outlined !text-[18px]">add</span>
					Assign
				</button>
			</div>
		</div>

		<!-- ===== Filters (server-side) ===== -->
		<div class="glass-card !p-3 flex flex-wrap items-center gap-2">
			<div class="relative flex-[2] min-w-[220px]">
				<span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/55 pointer-events-none">search</span>
				<input v-model="searchQuery" type="text" placeholder="Search assignments" class="field-input !pl-9" aria-label="Search assignments" />
			</div>
			<div class="flex-1 min-w-[180px]">
				<SearchableDropdown
					v-model="employeeFilter"
					:options="availableEmployeeOptions"
					labelKey="employee_name"
					valueKey="name"
					placeholder="All employees"
				/>
			</div>
			<div class="flex-1 min-w-[180px]">
				<SearchableDropdown
					v-model="holidayListFilter"
					:options="holidayListOptions"
					labelKey="title"
					valueKey="name"
					placeholder="All holiday lists"
				/>
			</div>
		</div>

		<!-- ===== Table (server-side pagination) ===== -->
		<DataTable
			:columns="listColumns"
			:rows="pager.state.rows"
			:actions="actionsForRow"
			:row-key="'name'"
			:loading="pager.state.loading"
			:empty-text="searchQuery || employeeFilter || holidayListFilter ? 'No assignment matches those filters.' : 'Nothing assigned yet.'"
			:show-pager="true"
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
		>
			<template #cell-assigned_to="{ row }">
				<div class="flex items-center gap-2 sm:gap-3 min-w-0">
					<span
						class="avatar-chip !w-7 !h-7 sm:!w-9 sm:!h-9"
						:class="row.applicable_for === 'Employee' ? '' : '!bg-sky-500/[0.12] !text-sky-600 dark:!text-sky-300'"
					>
						<span class="material-symbols-outlined !text-[16px]">{{ row.applicable_for === 'Employee' ? 'person' : 'groups' }}</span>
					</span>
					<span class="min-w-0">
						<span class="block break-words leading-snug sm:truncate">{{ row.assigned_to || '—' }}</span>
						<!-- Below sm the list and the scope have no columns of
						     their own, so they ride along here. -->
						<span class="block sm:hidden text-xs font-normal text-[#5C6169] dark:text-white/60 break-words leading-snug">
							{{ row.applicable_for }} · {{ row.holiday_list }}
						</span>
						<span class="hidden sm:block md:hidden text-xs font-normal text-[#5C6169] dark:text-white/60 leading-snug">
							{{ row.applicable_for }}
						</span>
					</span>
				</div>
			</template>
			<template #cell-applies_to="{ row }">
				<span class="premium-tag" :class="row.applicable_for === 'Employee' ? 'tag-neutral' : 'tag-accent'">{{ row.applicable_for || '—' }}</span>
			</template>
			<template #cell-holiday_list="{ row }">
				{{ row.holiday_list }}
			</template>
		</DataTable>

		<CreateHolidayListAssignment v-model="showCreateAssignmentDialog" :edit-id="editAssignmentId" @save="pager.fetchPage" />
	</div>
</template>

<script setup>
import DataTable from '@/components/DataTable.vue'
import { useServerPager } from '@/composables/useServerPager.js'
import { notify, ask } from '@/utils/feedback.js'
import { ref, watch, onMounted, computed } from 'vue'
import { createResource, call } from 'frappe-ui'
import { useLeaveStore } from '@/stores/leave'
import SearchableDropdown from '@/components/SearchableDropdown.vue'
import { getErrorMessage } from '@/utils.js'
import CreateHolidayListAssignment from '@/views/forms/holiday/create_holiday_list_assignment.vue'

const leaveStore = useLeaveStore()
const showCreateAssignmentDialog = ref(false)
const searchQuery = ref('')
const employeeFilter = ref(null)
const holidayListFilter = ref(null)
const isDeletingHolidayListAssignment = ref(false)

const editAssignmentId = ref('')
function editAssignment(name) {
	editAssignmentId.value = name
	showCreateAssignmentDialog.value = true
}

const canAct = computed(() => leaveStore.canEditHolidayListAssignment || leaveStore.canDeleteHolidayListAssignment)

async function deleteHolidayListAssignment(name) {
	if (!await ask(`Are you sure you want to delete ${name}?`)) return

	isDeletingHolidayListAssignment.value = name

	try {
		const data = await call('arijentek_core.api.leave.delete_holiday_list_assignment', { name })
		if (data && data.success === false) {
			notify(getErrorMessage(data.error || "Failed to delete"))
		} else {
			await pager.fetchPage()
		}
	} catch (err) {
		notify(getErrorMessage(err, "Failed to delete Holiday List Assignment"))
	} finally {
		isDeletingHolidayListAssignment.value = false
	}
}

const holidayLists = ref([])
const holidayListResource = createResource({
	url: 'arijentek_core.api.leave.get_holiday_list',
	auto: false,
	onSuccess(data) {
		holidayLists.value = data || []
	}
})

const availableEmployeeOptions = computed(() => {
	const opts = [{ name: "", employee_name: "All employees" }]
	;(leaveStore.employeeList || []).forEach((e) => {
		opts.push({
			name: e.name,
			employee_name: e.employee_name || e.name,
		})
	})
	return opts
})

const holidayListOptions = computed(() => {
	const opts = [{ name: "", title: "All Holiday Lists" }]
	;(holidayLists.value || []).forEach((p) => {
		opts.push({
			name: p.name,
			title: p.holiday_list_name || p.name,
		})
	})
	return opts
})

/* Server-side fetch: one page at a time (page/page_size) via
   get_holiday_list_assignment. The employee/holiday-list filters are applied
   server-side (assigned_to / holiday_list). Returns { rows, total } for
   useServerPager. Handles both the paginated dict (page_size > 0) and the
   legacy list (page_size = 0) responses. */
async function fetchHolidayListAssignments(page, size) {
	const params = { page, page_size: size }
	if (searchQuery.value) {
		params.search_text = searchQuery.value
	}
	if (employeeFilter.value) {
		params.assigned_to = employeeFilter.value
	}
	if (holidayListFilter.value) {
		params.holiday_list = holidayListFilter.value
	}
	try {
		const res = await call('arijentek_core.api.leave.get_holiday_list_assignment', params)
		const rows = Array.isArray(res) ? res : (res?.data || [])
		const total = Array.isArray(res) ? res.length : Number(res?.total || 0)
		return { rows, total }
	} catch (e) {
		console.error('Failed to fetch holiday list assignments:', e)
		return { rows: [], total: 0 }
	}
}

const pager = useServerPager((page, size) => fetchHolidayListAssignments(page, size), { size: 10 })

const listColumns = [
	{ key: 'assigned_to', label: 'Assigned to', className: 'table-td-strong max-w-[160px] sm:max-w-none' },
	{ key: 'applies_to', label: 'Applies to', className: 'hidden md:table-cell' },
	{ key: 'holiday_list', label: 'Holiday list', className: 'hidden sm:table-cell' },
]

function actionsForRow(hla) {
	return [
		{ label: 'Edit', icon: 'edit', show: leaveStore.canEditHolidayListAssignment, onClick: () => editAssignment(hla.name) },
		{ label: 'Delete', icon: 'delete', danger: true, show: leaveStore.canDeleteHolidayListAssignment, disabled: isDeletingHolidayListAssignment === hla.name, onClick: () => deleteHolidayListAssignment(hla.name) },
	]
}

// Filter changes reset to page 1. The pager's own [page, size] watch re-fetches
// when the page actually changes; if it is already 1, fetch directly so a filter
// change on page 1 still refreshes.
watch([searchQuery, employeeFilter, holidayListFilter], () => {
	if (pager.state.page !== 1) {
		pager.state.page = 1
	} else {
		pager.fetchPage()
	}
})

onMounted(() => {
	pager.fetchPage()
	holidayListResource.fetch()
	if (!leaveStore.employeeList || leaveStore.employeeList.length === 0) {
		leaveStore.fetchEmployeeList()
	}
})
</script>
