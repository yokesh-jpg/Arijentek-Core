<template>
	<!-- The POS's ToastNotification: bottom-right glass cards with a tinted
	     icon, a title and the message. Replaces the browser's alert(). -->
	<Teleport to="body">
		<TransitionGroup
			tag="div"
			aria-live="polite"
			class="fixed bottom-5 right-5 z-[999999] flex flex-col-reverse items-end gap-2.5 pointer-events-none w-[360px] max-w-[calc(100vw-2.5rem)]"
			enter-active-class="transition-all duration-300 ease-out"
			enter-from-class="opacity-0 translate-x-6"
			enter-to-class="opacity-100 translate-x-0"
			leave-active-class="transition-all duration-200 ease-in"
			leave-from-class="opacity-100 translate-x-0"
			leave-to-class="opacity-0 translate-x-6"
			move-class="transition-transform duration-300"
		>
			<div
				v-for="t in feedback.toasts"
				:key="t.id"
				:role="t.type === 'error' ? 'alert' : 'status'"
				class="toast-card pointer-events-auto w-full rounded-2xl p-3.5"
			>
				<div class="flex items-start gap-3">
					<div class="w-8 h-8 rounded-full flex items-center justify-center shrink-0" :class="TONES[t.type] || TONES.info">
						<span
							v-if="t.type === 'loading'"
							class="material-symbols-outlined !text-[20px] animate-spin text-accent dark:text-accent-light shrink-0"
							aria-hidden="true"
						>progress_activity</span>
						<svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" :d="ICONS[t.type] || ICONS.info" />
						</svg>
					</div>
					<div class="flex-1 min-w-0 pt-0.5">
						<div class="text-sm font-semibold leading-snug text-[#17181B] dark:text-white">{{ t.title || TITLES[t.type] }}</div>
						<p v-if="t.message" class="mt-0.5 text-[13px] leading-snug text-[#5C6169] dark:text-white/60 break-words">{{ t.message }}</p>

						<!-- Proper animated loading progress bar for loading toasts -->
						<div v-if="t.type === 'loading'" class="mt-2.5 w-full bg-accent/15 dark:bg-white/10 rounded-full h-1.5 overflow-hidden">
							<div class="h-full bg-accent dark:bg-accent-light rounded-full animate-indeterminate"></div>
						</div>

						<button
							v-if="t.action"
							type="button"
							class="mt-2 text-xs font-semibold px-2.5 py-1 rounded-lg bg-accent text-white hover:bg-accent-hover transition-colors inline-flex items-center gap-1 cursor-pointer pointer-events-auto"
							@click="t.action.onClick(); feedback.dismiss(t.id)"
						>
							<span v-if="t.action.icon" class="material-symbols-outlined !text-[14px]">{{ t.action.icon }}</span>
							<span>{{ t.action.label }}</span>
						</button>
					</div>
					<button
						type="button"
						class="shrink-0 w-7 h-7 -mr-1 -mt-0.5 flex items-center justify-center rounded-full text-[#656A72] hover:text-[#17181B] dark:text-white/55 dark:hover:text-white hover:bg-[#F5F5F8] dark:hover:bg-surface-3 transition-colors"
						aria-label="Dismiss notice"
						@click="feedback.dismiss(t.id)"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				</div>
			</div>
		</TransitionGroup>
	</Teleport>
</template>

<script setup>
import { useFeedbackStore } from '@/stores/feedback.js'

const feedback = useFeedbackStore()

const TITLES = { loading: 'Generating PDF…', success: 'Action completed', error: 'Action restricted', warning: 'Attention needed', info: 'Notice' }
/* green-*, not emerald-*: emerald is remapped to the accent in this app. */
const TONES = {
	loading: 'bg-accent/10 text-accent dark:bg-accent-soft/15 dark:text-accent-light',
	success: 'bg-green-500/[0.12] text-green-600 dark:bg-green-400/15 dark:text-green-400',
	error: 'bg-red-500/10 text-red-600 dark:bg-red-400/15 dark:text-red-400',
	warning: 'bg-amber-500/[0.12] text-amber-600 dark:bg-amber-400/15 dark:text-amber-400',
	info: 'bg-accent/10 text-accent dark:bg-accent-soft/15 dark:text-accent-light',
}
const ICONS = {
	success: 'M5 13l4 4L19 7',
	error: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z',
	warning: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z',
	info: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
}
</script>

<style scoped>
@keyframes indeterminate {
	0% {
		transform: translateX(-100%) scaleX(0.2);
	}
	50% {
		transform: translateX(35%) scaleX(0.7);
	}
	100% {
		transform: translateX(200%) scaleX(0.2);
	}
}
.animate-indeterminate {
	width: 50%;
	animation: indeterminate 1.5s infinite ease-in-out;
	transform-origin: 0% 50%;
}
</style>
