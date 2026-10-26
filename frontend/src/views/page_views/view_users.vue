<template>
  <Dialog :options="{ size: '3xl' }" v-model="show">
    <template #body>
      <div class="modal-panel">
        <!-- Custom Header -->
        <header class="modal-header">
          <div>
            <h3 class="modal-title truncate">User details</h3>
            <p class="text-[12px] text-[#656A72] dark:text-white/60 truncate tabular-nums">{{ userId }}</p>
          </div>
          <div class="flex items-center gap-1 shrink-0">
            <button class="btn-icon-ghost" aria-label="Edit" title="Edit" v-if="details && teamStore.editUserPermissionResource?.data" @click="emit('edit', { name: details.name }); show = false"><span class="material-symbols-outlined !text-[18px]">edit</span></button>
            <button class="btn-danger-ghost disabled:opacity-40" aria-label="Delete" title="Delete" v-if="details && teamStore.deleteUserPermissionResource?.data" @click="emit('delete', { name: details.name }); show = false"><span class="material-symbols-outlined !text-[18px]">delete</span></button>
            <button @click="show = false" class="btn-icon-ghost shrink-0" aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span></button>
          </div>
        </header>

        <!-- Main Content -->
        <div class="flex-1 overflow-y-auto px-6 py-5">
          <div class="max-w-3xl mx-auto">
				<!-- Loading State -->
				<div v-if="loading" class="flex flex-col items-center justify-center py-16 gap-3">
						<span class="w-5 h-5 rounded-full border-2 border-black/10 dark:border-white/15 border-t-accent animate-spin"></span>
						<span class="text-[13px] text-[#5C6169] dark:text-white/65">Loading details…</span>
					</div>

				<!-- Error State -->
				<div v-else-if="error" class="empty-state">
						<span class="material-symbols-outlined !text-[28px] text-red-600 dark:text-red-400">error</span>
						<p class="empty-state-text">Could not load this record</p>
						<p class="text-[12px] text-[#656A72] dark:text-white/55">{{ error }}</p>
						<button @click="fetchDetails" class="btn-secondary !h-9 mt-1">Try again</button>
					</div>

				<!-- Details Card -->
				<div v-else-if="details">
					<div class="pb-5">
						<div class="flex items-center gap-3">
							<div class="avatar-chip !w-11 !h-11 !text-[14px] overflow-hidden shrink-0">
								<img v-if="details.user_image" :src="details.user_image" class="w-full h-full object-cover">
								<span v-else>{{ (details.full_name || details.name || '?').charAt(0).toUpperCase() }}</span>
							</div>
							<div>
								<h2 class="text-lg font-semibold text-gray-900 dark:text-white leading-tight">{{ details.full_name || details.name }}</h2>
								<p class="text-[13px] text-[#5C6169] dark:text-white/65">{{ details.username || '-' }}</p>
							</div>
						</div>
						<div class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold" :class="details.enabled ? 'tag-emerald' : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'">
							{{ details.enabled ? 'Active' : 'Inactive' }}
						</div>
					</div>

					<div class="pt-5 grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-5">
						<div class="space-y-1">
							<p class="status-label">User ID</p>
							<div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.name }}</div>
						</div>
						
						<div class="space-y-1">
							<p class="status-label">Email</p>
							<div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 flex items-center gap-1.5">
								<span class="material-symbols-outlined text-[16px] text-[#656A72] dark:text-white/60">mail</span>
								{{ details.email || '-' }}
							</div>
						</div>
						
						<div class="space-y-1">
							<p class="status-label">First name</p>
							<div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.first_name || '-' }}</div>
						</div>
						
						<div class="space-y-1">
							<p class="status-label">Middle name</p>
							<div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.middle_name || '-' }}</div>
						</div>

						<div class="space-y-1">
							<p class="status-label">Last name</p>
							<div class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.last_name || '-' }}</div>
						</div>

						<div class="space-y-1 md:col-span-2 mt-4 pt-4 border-t border-gray-100 dark:border-gray-800">
							<p class="status-label">Assigned roles</p>
							<div class="flex flex-wrap gap-2">
								<template v-if="details.roles && details.roles.length > 0">
									<button
										v-for="role in details.roles"
										:key="role"
										@click="openRoleView(role)"
										class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold tag-neutral gap-1"
									>
										<span class="material-symbols-outlined text-[12px]">shield</span>
										{{ role }}
									</button>
								</template>
								<span v-else class="text-sm text-gray-600 dark:text-gray-400 italic">No roles assigned</span>
							</div>
						</div>
					</div>
				</div>
			</div>
        </div>
      	<footer class="px-5 py-4 border-t border-black/[0.07] dark:border-white/10 shrink-0">
					<button class="btn-secondary w-full" @click="show = false">Close</button>
				</footer>
			</div>
    </template>
  </Dialog>

  <!-- Role Permissions Popup -->
  <ViewRoles v-model="showRoleView" :roleName="selectedRole" />
</template>

<script setup>
import { ref, watch, computed } from 'vue';
import ViewRoles from '@/views/page_views/teams/view_roles.vue';
import { Dialog, createResource } from 'frappe-ui';
import { useTeamStore } from '../../stores/team.js';

const teamStore = useTeamStore();

const props = defineProps({
	modelValue: {
		type: Boolean,
		default: false
	},
	userId: {
		type: String,
		default: ''
	}
});

const emit = defineEmits(['update:modelValue', 'edit', 'delete']);

const showRoleView = ref(false);
const selectedRole = ref('');

function openRoleView(role) {
	selectedRole.value = role;
	showRoleView.value = true;
}

const show = computed({
	get: () => props.modelValue,
	set: (val) => emit('update:modelValue', val)
});

const loading = ref(false);
const error = ref('');
const details = ref(null);

watch(() => props.modelValue, (newVal) => {
	if (newVal && props.userId) {
		fetchDetails();
	}
});

async function fetchDetails() {
	if (!props.userId) return;
	
	loading.value = true;
	error.value = '';
	
	try {
		const res = createResource({
			url: 'arijentek_core.api.teams_permissons.get_users_details',
			auto: false
		});
		
		const data = await res.fetch({ user_id: props.userId });
		if (res.error) {
			throw new Error(res.error.message || 'Failed to fetch user details');
		}
		
		details.value = data;
	} catch (err) {
		error.value = err.message || 'An error occurred while fetching details';
	} finally {
		loading.value = false;
	}
}

</script>
