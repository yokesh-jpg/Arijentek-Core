<template>
	<div class="space-y-4 sm:space-y-5 tab-fill">
		<!-- ===== Header / Filters ===== -->
		<div class="glass-card !p-3 flex flex-col lg:flex-row lg:items-center gap-2">
			<div class="relative flex-1 min-w-[200px]">
				<span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/55 pointer-events-none">search</span>
				<input
					v-model="filters.search_term"
					type="text"
					placeholder="Search by name, ID or phone"
					class="field-input !pl-9"
				/>
			</div>
			<div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5 lg:contents">
				<div class="lg:w-[170px]">
					<SearchableDropdown v-model="filters.department" :options="departmentOptions" placeholder="All departments" />
				</div>
				<div class="lg:w-[180px]">
					<SearchableDropdown v-model="filters.designation" :options="designationOptions" placeholder="All designations" />
				</div>
				<div class="lg:w-[150px]">
					<SearchableDropdown v-model="filters.gender" :options="genderOptions" placeholder="All genders" />
				</div>
				<div class="lg:w-[160px]">
					<SearchableDropdown v-model="filters.employment_type" :options="employmentTypeOptions" placeholder="All types" />
				</div>
			</div>
			<button
				v-if="teamStore.permissionResource.data"
				@click="handleCreateEmployee"
				class="btn-primary shrink-0"
			>
				<span class="material-symbols-outlined !text-[18px]">add</span>
				Add employee
			</button>
		</div>

		<!-- ===== Table ===== -->
		<DataTable
			:columns="columns"
			:rows="pager.state.rows"
			:actions="employeeActions"
			:row-key="'name'"
			:loading="pager.state.loading"
			:empty-text="hasActiveFilter ? 'No employees match these filters.' : 'No employees found.'"
			:show-pager="true"
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
			:on-row-click="(row) => viewEmployee(row.name)"
		>
			<template #cell-employee="{ row }">
				<span class="flex items-center gap-2.5 min-w-0">
					<span class="avatar-chip shrink-0 overflow-hidden">
						<img v-if="row.image" :src="row.image" class="w-full h-full object-cover" alt="" />
						<template v-else>{{ initials(row.employee_name) }}</template>
					</span>
					<span class="min-w-0">
						<span class="block text-[13px] font-semibold text-[#17181B] dark:text-white truncate">{{ row.employee_name }}</span>
						<span class="block text-[12px] text-[#656A72] dark:text-white/55 tabular-nums">{{ row.name }} · {{ row.employment_type || 'Type not set' }}</span>
					</span>
				</span>
			</template>
			<template #cell-department="{ row }">
				<span class="text-[13px] text-[#17181B] dark:text-white">{{ row.department || '—' }}</span>
			</template>
			<template #cell-designation="{ row }">
				<span class="text-[13px] text-[#17181B] dark:text-white">{{ row.designation || '—' }}</span>
			</template>
			<template #cell-cell_number="{ row }">
				<span class="text-[13px] text-[#17181B] dark:text-white whitespace-nowrap tabular-nums">{{ row.cell_number || '—' }}</span>
			</template>
		</DataTable>

		<!-- Modals -->
		<CreateEmployeeForm v-model="showCreateEmployee" :edit-id="selectedEmployeeId" @save="pager.fetchPage" />
		<ViewEmployeeModal v-model="showViewEmployeeModal" :employee-id="viewEmployeeId" @edit="handleViewEmployeeEdit" @delete="handleViewEmployeeDelete" />
	</div>
</template>

<script setup>
import { reactive, ref, computed, watch, onMounted } from 'vue'
import { call } from 'frappe-ui'
import { useTeamStore } from '@/stores/team'
import { useEmployeeStore } from '@/stores/employee'
import { useAuthStore } from '@/stores/auth'
import { notify, ask } from '@/utils/feedback.js'
import { getErrorMessage } from '@/utils.js'
import DataTable from '@/components/DataTable.vue'
import SearchableDropdown from '@/components/SearchableDropdown.vue'
import { useServerPager } from '@/composables/useServerPager.js'
import CreateEmployeeForm from '@/views/forms/create_employee.vue'
import ViewEmployeeModal from '@/views/page_views/view_employee.vue'

const teamStore = useTeamStore()
const employeeStore = useEmployeeStore()
const authStore = useAuthStore()

const showCreateEmployee = ref(false)
const selectedEmployeeId = ref('')
const showViewEmployeeModal = ref(false)
const viewEmployeeId = ref('')

const filters = reactive({
	search_term: '',
	department: '',
	designation: '',
	gender: '',
	employment_type: ''
})

const hasActiveFilter = computed(() => {
	return !!(filters.search_term || filters.department || filters.designation || filters.gender || filters.employment_type)
})

const departmentOptions = computed(() => [
	{ label: 'All departments', value: '' },
	...(teamStore.departmentsResource.data || [])
])

const designationOptions = computed(() => [
	{ label: 'All designations', value: '' },
	...(teamStore.designationsResource.data || [])
])

const genderOptions = computed(() => [
	{ label: 'All genders', value: '' },
	...(teamStore.gendersResource.data || [])
])

const employmentTypeOptions = computed(() => [
	{ label: 'All types', value: '' },
	...(teamStore.employmentTypesResource.data || [])
])

const columns = [
	{ key: 'employee', label: 'Employee', className: 'table-td' },
	{ key: 'department', label: 'Department', className: 'table-td' },
	{ key: 'designation', label: 'Designation', className: 'table-td' },
	{ key: 'cell_number', label: 'Phone', className: 'table-td' }
]

function initials(name) {
	if (!name) return '?'
	return String(name)
		.split(/[\s@._-]+/)
		.filter(Boolean)
		.slice(0, 2)
		.map((p) => p[0].toUpperCase())
		.join('')
}

function handleCreateEmployee() {
	selectedEmployeeId.value = ''
	showCreateEmployee.value = true
}

function editEmployee(id) {
	selectedEmployeeId.value = id
	showCreateEmployee.value = true
}

function viewEmployee(id) {
	viewEmployeeId.value = id
	showViewEmployeeModal.value = true
}

function handleViewEmployeeEdit({ name }) {
	editEmployee(name)
}

function handleViewEmployeeDelete({ name }) {
	showViewEmployeeModal.value = false
	deleteEmployee(name)
}

async function deleteEmployee(id) {
	if (!await ask('Are you sure you want to delete this employee?')) return
	try {
		const res = await call('arijentek_core.api.teams_permissons.delete_employee', { employee_id: id })
		if (res && res.success === false) {
			notify(res.error || 'Failed to delete employee', 'error')
			return
		}
		notify(res?.message || 'Employee deleted successfully', 'success')
		pager.fetchPage()
	} catch (err) {
		notify(getErrorMessage(err, 'Failed to delete employee'))
	}
}

function canEditEmployee(emp) {
	if (teamStore.editEmployeePermissionResource?.data) {
		return true
	}
	const currentEmpId = employeeStore.employee?.name
	const currentUserId = authStore.user?.user || authStore.user?.email
	if (emp && ((currentEmpId && emp.name === currentEmpId) || (currentUserId && emp.user_id && emp.user_id === currentUserId))) {
		return true
	}
	return false
}

function employeeActions(emp) {
	return [
		{ label: 'View', icon: 'visibility', onClick: () => viewEmployee(emp.name) },
		{
			label: 'Edit',
			icon: 'edit',
			show: canEditEmployee(emp),
			onClick: () => editEmployee(emp.name)
		},
		{ divider: true },
		{
			label: 'Delete',
			icon: 'delete',
			danger: true,
			show: !!teamStore.deleteEmployeePermissionResource?.data,
			onClick: () => deleteEmployee(emp.name)
		}
	]
}

async function fetchEmployees(page, size) {
	try {
		const params = {
			page: page || 1,
			page_size: size || pager.state.size || 10,
			search_term: filters.search_term || '',
			department: filters.department || '',
			designation: filters.designation || '',
			gender: filters.gender || '',
			employment_type: filters.employment_type || ''
		}
		const res = await call('arijentek_core.api.teams_permissons.get_employee_list', params)
		const rows = res?.rows || (Array.isArray(res) ? res : res?.data || [])
		const total = res?.total != null ? Number(res.total) : rows.length
		return { rows, total }
	} catch (err) {
		console.error('Failed to fetch employees:', err)
		return { rows: [], total: 0 }
	}
}

const pager = useServerPager((page, size) => fetchEmployees(page, size), { size: 10 })

function triggerFilterRefresh() {
	if (pager.state.page !== 1) {
		pager.state.page = 1
	} else {
		pager.fetchPage()
	}
}

let debounceTimer = null
watch(() => filters.search_term, () => {
	clearTimeout(debounceTimer)
	debounceTimer = setTimeout(() => {
		triggerFilterRefresh()
	}, 300)
})

watch(
	[() => filters.department, () => filters.designation, () => filters.gender, () => filters.employment_type],
	() => {
		triggerFilterRefresh()
	}
)

onMounted(() => {
	pager.fetchPage()
	teamStore.fetchLists()
})
</script>
