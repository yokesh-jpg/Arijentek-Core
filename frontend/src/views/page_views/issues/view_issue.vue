<template>
	<Dialog :options="{ size: '2xl' }" v-model="show">
		<template #body>
			<div class="modal-panel">
				<!-- Header. The id is what you quote when chasing an issue, so it
				     sits under the subject rather than replacing it. -->
				<header class="modal-header">
					<div class="min-w-0">
						<h3 class="modal-title truncate">{{ details?.subject || 'Issue' }}</h3>
						<p class="text-[12px] text-[#656A72] dark:text-white/60 truncate tabular-nums">{{ details?.name || issueId }}</p>
					</div>
					<div class="flex items-center gap-2 shrink-0 relative">
						<span v-if="details" class="premium-tag" :class="statusTag(details.status)">{{ details.status || 'Unknown' }}</span>
						<RowActions v-if="details" :actions="[
								{ label: 'Investigate', icon: 'search_insights', show: !!(permissions.can_submit && details.status === 'Open'), onClick: () => { handleAction('Investigated') } },
								{ label: 'Resolve', icon: 'check_circle', show: !!(permissions.can_submit && (details.status === 'Open' || details.status === 'Investigated')), onClick: () => { handleAction('Resolved') } },
								{ label: 'Mark invalid', icon: 'block', show: !!(permissions.can_submit && details.status !== 'Invalid'), onClick: () => { handleAction('Invalid') } },
								{ label: 'Edit', icon: 'edit', show: !!(permissions.can_edit), onClick: () => { handleEdit() } },
								{ divider: true },
								{ label: 'Delete', icon: 'delete', danger: true, show: !!(permissions.can_delete), onClick: () => { handleDelete() } },
							]" />
						<button @click="show = false" class="btn-icon-ghost" aria-label="Close">
							<span class="material-symbols-outlined !text-[18px]">close</span>
						</button>
					</div>
				</header>

				<div class="flex-1 overflow-y-auto px-6 py-5">
					<div v-if="loading" class="flex flex-col items-center justify-center py-16 gap-3">
						<span class="material-symbols-outlined !text-[28px] text-accent dark:text-accent-light animate-spin">progress_activity</span>
						<span class="text-[13px] text-[#5C6169] dark:text-white/65">Loading issue…</span>
					</div>

					<div v-else-if="error" class="empty-state">
						<span class="material-symbols-outlined !text-[28px] text-red-500 dark:text-red-400">error</span>
						<p class="empty-state-text">{{ error }}</p>
						<button @click="fetchDetails" class="btn-secondary !h-9 mt-1">Try again</button>
					</div>

					<template v-else-if="details">
						<!-- Facts read as plain fields on the panel. Tinted cards here
						     would be second surfaces inside the dialog. -->
						<div class="grid grid-cols-2 gap-x-6 gap-y-5">
							<div>
								<p class="status-label">Raised by</p>
								<div class="flex items-center gap-2 mt-1">
									<span class="avatar-chip !w-7 !h-7 !text-[12px]">{{ initials(details.employee_name || details.raised_by) }}</span>
									<span class="text-[14px] font-semibold text-[#17181B] dark:text-white truncate">{{ details.employee_name || details.raised_by || '—' }}</span>
								</div>
							</div>
							<div>
								<p class="status-label">Date raised</p>
								<p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 tabular-nums">{{ formatDate(details.date) }}</p>
							</div>
							<div>
								<p class="status-label">Issue type</p>
								<p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.grievance_type || '—' }}</p>
							</div>
							<div>
								<p class="status-label">Raised against</p>
								<p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">
									{{ details.grievance_against || '—' }}
									<span v-if="details.grievance_against_party" class="block text-[12px] font-normal text-[#656A72] dark:text-white/55">{{ details.grievance_against_party }}</span>
								</p>
							</div>
						</div>

						<div v-if="details.description" class="modal-section">
							<p class="status-label">What happened</p>
							<p class="text-[13px] text-[#17181B] dark:text-white/90 leading-relaxed whitespace-pre-line mt-1">{{ details.description }}</p>
						</div>

						<!-- Investigation and resolution are the record of what was
						     done about it, so they stay distinct sections rather than
						     more fields in the grid above. -->
						<div v-if="details.cause_of_grievance || details.status === 'Investigated' || details.status === 'Resolved'" class="modal-section">
							<p class="status-label flex items-center gap-1.5">
								<span class="material-symbols-outlined !text-[16px]">search_insights</span>
								Investigation
							</p>
							<p class="text-[13px] leading-relaxed whitespace-pre-line mt-1" :class="details.cause_of_grievance ? 'text-[#17181B] dark:text-white/90' : 'text-[#656A72] dark:text-white/55'">
								{{ details.cause_of_grievance || 'Nothing recorded yet.' }}
							</p>
						</div>

						<div v-if="details.resolution_detail || details.resolved_by || details.resolution_date || details.status === 'Resolved'" class="modal-section">
							<p class="status-label flex items-center gap-1.5">
								<span class="material-symbols-outlined !text-[16px]">check_circle</span>
								Resolution
							</p>
							<div class="grid grid-cols-2 gap-x-6 gap-y-4 mt-1">
								<div>
									<p class="text-[12px] text-[#656A72] dark:text-white/55">Resolved by</p>
									<p class="text-[14px] font-semibold mt-0.5" :class="details.resolved_by ? 'text-[#17181B] dark:text-white' : 'text-[#656A72] dark:text-white/55'">{{ details.resolved_by || '—' }}</p>
								</div>
								<div>
									<p class="text-[12px] text-[#656A72] dark:text-white/55">Resolution date</p>
									<p class="text-[14px] font-semibold mt-0.5 tabular-nums" :class="details.resolution_date ? 'text-[#17181B] dark:text-white' : 'text-[#656A72] dark:text-white/55'">{{ formatDate(details.resolution_date) }}</p>
								</div>
							</div>
							<p v-if="details.resolution_detail" class="text-[13px] text-[#17181B] dark:text-white/90 leading-relaxed whitespace-pre-line mt-3">{{ details.resolution_detail }}</p>
						</div>
					</template>
				</div>

				<footer class="modal-footer justify-end">
					<button class="btn-secondary" @click="show = false">Close</button>
					<button v-if="permissions.can_edit && details" class="btn-primary" @click="handleEdit">Edit issue</button>
				</footer>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue';
import { Dialog, call } from 'frappe-ui';
import { getErrorMessage } from '@/utils';
import RowActions from '@/components/RowActions.vue';

const show = defineModel();
const emit = defineEmits(['edit', 'delete', 'changeStatus']);

const props = defineProps({
  issueId: {
    type: String,
    default: null
  }
});

const loading = ref(false);
const error = ref('');
const details = ref(null);
const showMenu = ref(false);

const permissions = ref({
  can_edit: false,
  can_delete: false,
  can_create: false,
  can_submit: false
});

const toggleMenu = () => {
  showMenu.value = !showMenu.value;
};

const closeMenu = () => {
  showMenu.value = false;
};

const fetchPermissions = async () => {
  try {
    const editPerm = await call('arijentek_core.api.issues.can_edit_employee_grievance');
    permissions.value.can_edit = !!editPerm;
    
    const deletePerm = await call('arijentek_core.api.issues.can_delete_employee_grievance');
    permissions.value.can_delete = !!deletePerm;

    const createPerm = await call('arijentek_core.api.issues.can_create_employee_grievance');
    permissions.value.can_create = !!createPerm;

    const submitPerm = await call('arijentek_core.api.issues.can_submit_employee_grievance');
    permissions.value.can_submit = !!submitPerm;
  } catch (err) {
    console.error("Failed to fetch permissions in view_issue:", err);
  }
};

const fetchDetails = async () => {
  if (!props.issueId) return;
  loading.value = true;
  error.value = '';
  try {
    const res = await call('arijentek_core.api.issues.get_issues', { id: props.issueId });
    if (res && res.length > 0) {
      details.value = res[0];
    } else {
      error.value = 'Issue not found';
    }
  } catch (err) {
    console.error("Failed to fetch issue details:", err);
    error.value = getErrorMessage(err, 'Failed to load issue details');
  } finally {
    loading.value = false;
  }
};

watch(show, async (newVal) => {
  if (newVal && props.issueId) {
    showMenu.value = false;
    await fetchPermissions();
    await fetchDetails();
  }
});

const handleEdit = () => {
  showMenu.value = false;
  show.value = false;
  emit('edit', details.value);
};

const handleDelete = () => {
  showMenu.value = false;
  show.value = false;
  emit('delete', details.value);
};

const handleAction = (targetStatus) => {
  showMenu.value = false;
  show.value = false;
  emit('changeStatus', { issue: details.value, targetStatus });
};

onMounted(() => {
  document.addEventListener('click', closeMenu);
});

onUnmounted(() => {
  document.removeEventListener('click', closeMenu);
});

/* ---- presentation helpers -------------------------------------------- */

/* The same four tags the list uses, so a status reads identically in both
   places: Open still needs action, Investigated is in hand, Resolved is done,
   Invalid was closed without one. */
function statusTag(status) {
	if (status === 'Open') return 'tag-red'
	if (status === 'Investigated') return 'tag-amber'
	if (status === 'Resolved') return 'tag-emerald'
	return 'tag-neutral'
}

function initials(name) {
	if (!name) return '?'
	return String(name)
		.split(/[\s@._-]+/)
		.filter(Boolean)
		.slice(0, 2)
		.map((p) => p[0].toUpperCase())
		.join('')
}

function formatDate(dateStr) {
	if (!dateStr) return '—'
	/* Parsed as local midnight: a bare 'YYYY-MM-DD' is read as UTC, which
	   names the previous day east of UTC. */
	const d = new Date(String(dateStr) + 'T00:00:00')
	if (isNaN(d.getTime())) return String(dateStr)
	return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}
</script>
