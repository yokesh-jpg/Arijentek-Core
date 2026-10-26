<template>
	<div :class="isModal ? 'modal-panel' : 'h-full flex flex-col'">
		<header class="flex items-start justify-between gap-3 px-5 py-4 border-b border-black/[0.07] dark:border-white/10 shrink-0">
			<div class="flex items-start gap-3 min-w-0">
				<button v-if="!isModal" @click="goBack" class="btn-icon-ghost shrink-0 -ml-1" aria-label="Back">
					<span class="material-symbols-outlined !text-[18px]">arrow_back</span>
				</button>
				<div class="min-w-0">
					<h2 class="modal-title truncate">Designation details</h2>
					<p v-if="details?.designation_name" class="text-[13px] text-[#5C6169] dark:text-white/65 truncate">{{ details.designation_name }}</p>
					<p class="text-[12px] text-[#656A72] dark:text-white/55 truncate tabular-nums">{{ designationId }}</p>
				</div>
			</div>
			<div class="flex items-center gap-1 shrink-0">
				<button v-if="details" @click="emit('edit', { name: details.name })" class="btn-icon-ghost" aria-label="Edit" title="Edit">
					<span class="material-symbols-outlined !text-[18px]">edit</span>
				</button>
				<button v-if="details" @click="emit('delete', { name: details.name })" class="btn-danger-ghost" aria-label="Delete" title="Delete">
					<span class="material-symbols-outlined !text-[18px]">delete</span>
				</button>
				<button v-if="isModal" @click="goBack" class="btn-icon-ghost" aria-label="Close">
					<span class="material-symbols-outlined !text-[18px]">close</span>
				</button>
			</div>
		</header>

		<div class="flex-1 overflow-y-auto px-6 py-5">
			<div v-if="loading" class="flex flex-col items-center justify-center py-16 gap-3">
				<span class="w-5 h-5 rounded-full border-2 border-black/10 dark:border-white/15 border-t-accent animate-spin"></span>
				<span class="text-[13px] text-[#5C6169] dark:text-white/65">Loading details…</span>
			</div>

			<div v-else-if="error" class="empty-state">
				<span class="material-symbols-outlined !text-[28px] text-red-600 dark:text-red-400">error</span>
				<p class="empty-state-text">Could not load this record</p>
				<p class="text-[12px] text-[#656A72] dark:text-white/55">{{ error }}</p>
				<button @click="fetchDetails" class="btn-secondary !h-9 mt-1">Try again</button>
			</div>

			<template v-else-if="details">
				<div class="grid grid-cols-2 gap-x-6 gap-y-5">
					<div>
						<p class="status-label">Designation</p>
						<p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ details.designation_name || '—' }}</p>
					</div>
					<div>
						<p class="status-label">ID</p>
						<p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1 tabular-nums">{{ details.name }}</p>
					</div>
				</div>

				<div class="mt-6 pt-5 border-t border-black/[0.07] dark:border-white/10">
					<p class="status-label">Description</p>
					<p class="text-[13px] leading-relaxed whitespace-pre-wrap mt-1" :class="details.description ? 'text-[#17181B] dark:text-white/90' : 'text-[#656A72] dark:text-white/55'">{{ details.description || 'No description provided.' }}</p>
				</div>
			</template>
		</div>

		<footer v-if="isModal" class="px-5 py-4 border-t border-black/[0.07] dark:border-white/10 shrink-0">
			<button class="btn-secondary w-full" @click="goBack">Close</button>
		</footer>
	</div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { call } from 'frappe-ui';

const props = defineProps({
	id: {
		type: String,
		default: ''
	},
	isModal: {
		type: Boolean,
		default: false
	}
});

const emit = defineEmits(['close', 'edit', 'delete']);

const route = useRoute();
const router = useRouter();

const designationId = ref(props.id || route.params.id);
const loading = ref(true);
const error = ref('');
const details = ref(null);

function goBack() {
	if (props.isModal) {
		emit('close');
	} else if (window.history.length > 2) {
		router.back();
	} else {
		router.push({ name: 'designations' });
	}
}

watch(() => props.id, (newVal) => {
	if (newVal) {
		designationId.value = newVal;
		fetchDetails();
	}
});

async function fetchDetails() {
	if (!designationId.value) return;
	
	loading.value = true;
	error.value = '';
	
	try {
		const data = await call('arijentek_core.api.teams_permissons.get_designation_list', { 
			designation_id: designationId.value 
		});
		
		if (!data) {
			throw new Error('No details returned');
		}
		
		details.value = data;
	} catch (err) {
		const msg = err.messages ? err.messages[0] : (err.message || 'An error occurred while fetching details');
		error.value = msg;
	} finally {
		loading.value = false;
	}
}

onMounted(() => {
	fetchDetails();
});
</script>
