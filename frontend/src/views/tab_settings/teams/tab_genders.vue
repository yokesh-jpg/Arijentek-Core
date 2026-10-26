<template>
	<div class="space-y-4 sm:space-y-5 tab-fill">
		<!-- ===== Header / Filters ===== -->
		<div class="glass-card !p-3 flex flex-col sm:flex-row sm:items-center gap-2">
			<div class="relative flex-1 min-w-0">
				<span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/60 pointer-events-none">search</span>
				<input
					v-model="searchQuery"
					type="text"
					placeholder="Search genders"
					class="field-input !pl-9"
				/>
			</div>
			<button
				v-if="teamStore.createGenderPermissionResource?.data"
				@click="handleCreateGender"
				class="btn-primary shrink-0"
			>
				<span class="material-symbols-outlined !text-[18px]">add</span>
				Add gender
			</button>
		</div>

		<!-- ===== Table ===== -->
		<DataTable
			:columns="columns"
			:rows="pager.state.rows"
			:actions="genderActions"
			:row-key="'name'"
			:loading="pager.state.loading"
			:empty-text="searchQuery ? `No genders match “${searchQuery}”.` : 'No genders found.'"
			:show-pager="true"
			:total="pager.state.total"
			:page="pager.state.page"
			:page-size="pager.state.size"
			@update:page="pager.state.page = $event"
			@update:page-size="pager.setPageSize($event)"
		>
			<template #cell-gender="{ row }">
				<span class="table-td-strong">{{ row.gender_name || row.name }}</span>
			</template>
		</DataTable>

		<!-- Modals -->
		<CreateGenderForm v-model="showCreateGender" :edit-id="selectedGenderId" @save="pager.fetchPage" />
	</div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { call } from 'frappe-ui'
import { useTeamStore } from '@/stores/team'
import { notify, ask } from '@/utils/feedback.js'
import { getErrorMessage } from '@/utils.js'
import DataTable from '@/components/DataTable.vue'
import { useServerPager } from '@/composables/useServerPager.js'
import CreateGenderForm from '@/views/forms/create_gender.vue'

const teamStore = useTeamStore()

const showCreateGender = ref(false)
const selectedGenderId = ref('')
const searchQuery = ref('')

const columns = [
	{ key: 'gender', label: 'Gender', className: 'table-td' }
]

function handleCreateGender() {
	selectedGenderId.value = ''
	showCreateGender.value = true
}

function editGender(id) {
	selectedGenderId.value = id
	showCreateGender.value = true
}

async function deleteGender(id) {
	if (!await ask('Are you sure you want to delete this gender?')) return
	try {
		const res = await call('arijentek_core.api.teams_permissons.delete_gender', { gender_id: id })
		if (res && res.success === false) {
			notify(res.error || 'Failed to delete gender', 'error')
			return
		}
		notify(res?.message || 'Gender deleted successfully', 'success')
		pager.fetchPage()
	} catch (err) {
		notify(getErrorMessage(err, 'Failed to delete gender'))
	}
}

function genderActions(gen) {
	return [
		{
			label: 'Edit',
			icon: 'edit',
			show: !!teamStore.editGenderPermissionResource?.data,
			onClick: () => editGender(gen.name)
		},
		{ divider: true },
		{
			label: 'Delete',
			icon: 'delete',
			danger: true,
			show: !!teamStore.deleteGenderPermissionResource?.data,
			onClick: () => deleteGender(gen.name)
		}
	]
}

async function fetchGenders(page, size) {
	try {
		const params = {
			page: page || 1,
			page_size: size || pager.state.size || 10,
			search_term: searchQuery.value || ''
		}
		const res = await call('arijentek_core.api.teams_permissons.get_gender_list', params)
		const rows = res?.rows || (Array.isArray(res) ? res : res?.data || [])
		const total = res?.total != null ? Number(res.total) : rows.length
		return { rows, total }
	} catch (err) {
		console.error('Failed to fetch genders:', err)
		return { rows: [], total: 0 }
	}
}

const pager = useServerPager((page, size) => fetchGenders(page, size), { size: 10 })

function triggerFilterRefresh() {
	if (pager.state.page !== 1) {
		pager.state.page = 1
	} else {
		pager.fetchPage()
	}
}

let debounceTimer = null
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
