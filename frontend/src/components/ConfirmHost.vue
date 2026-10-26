<template>
	<!-- The POS's AppConfirmDialog: large targets, an accent (or red) top edge,
	     Cancel and the action side by side. Replaces the browser's confirm(). -->
	<Teleport to="body">
		<div
			v-if="state"
			class="confirm-scrim pointer-events-auto fixed inset-0 z-[999999] flex items-center justify-center bg-black/60 p-4"
			data-dismissable-layer=""
			@pointerdown.stop
			@mousedown.stop
			@touchstart.stop
			@click.self="cancel"
		>
			<div
				ref="panel"
				role="alertdialog"
				aria-modal="true"
				:aria-labelledby="'confirm-title'"
				:aria-describedby="'confirm-message'"
				class="pointer-events-auto bg-white dark:bg-surface-2 rounded-2xl shadow-2xl max-w-md w-full p-6 border-t-4"
				:class="state.danger ? 'border-red-500' : 'border-accent'"
				@keydown.esc.stop="cancel"
			>
				<h3 id="confirm-title" class="text-xl font-semibold text-[#17181B] dark:text-white mb-2">{{ state.title }}</h3>
				<p id="confirm-message" class="text-base text-[#5C6169] dark:text-white/60 mb-6 whitespace-pre-line">{{ state.message }}</p>
				<div class="flex gap-3">
					<button
						ref="cancelBtn"
						type="button"
						class="pointer-events-auto flex-1 py-3.5 rounded-xl border-2 border-black/[0.12] dark:border-white/[0.08] text-[#2D3138] dark:text-white/80 font-semibold text-base hover:bg-black/[0.03] dark:hover:bg-surface-3 transition cursor-pointer"
						@click="cancel"
					>
						{{ state.cancelText || 'Cancel' }}
					</button>
					<button
						type="button"
						class="pointer-events-auto flex-1 py-3.5 rounded-xl text-white font-semibold text-base transition cursor-pointer"
						:class="state.danger ? 'bg-red-500 hover:bg-red-600' : 'bg-accent hover:bg-accent-hover'"
						@click="ok"
					>
						{{ state.confirmText || 'Confirm' }}
					</button>
				</div>
			</div>
		</div>
	</Teleport>
</template>

<script setup>
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import { useFeedbackStore } from '@/stores/feedback.js'

const feedback = useFeedbackStore()
const state = computed(() => feedback.confirmState)
const cancelBtn = ref(null)

let prevBodyPointerEvents = null

function onKeyDown(e) {
	if (!state.value) return
	if (e.key === 'Escape') {
		e.stopPropagation()
		e.preventDefault()
		cancel(e)
	}
}

/* Focus lands on Cancel - the safe choice - so Enter on a stray keypress
   does not delete anything, and Esc works without reaching for the mouse. */
watch(state, async (s) => {
	if (!s) {
		window.removeEventListener('keydown', onKeyDown, { capture: true })
		if (prevBodyPointerEvents !== null) {
			document.body.style.pointerEvents = prevBodyPointerEvents
			prevBodyPointerEvents = null
		}
		return
	}
	window.addEventListener('keydown', onKeyDown, { capture: true })
	prevBodyPointerEvents = document.body.style.pointerEvents
	if (document.body.style.pointerEvents === 'none') {
		document.body.style.pointerEvents = 'auto'
	}
	await nextTick()
	cancelBtn.value?.focus()
})

onUnmounted(() => {
	window.removeEventListener('keydown', onKeyDown, { capture: true })
	if (prevBodyPointerEvents !== null) {
		document.body.style.pointerEvents = prevBodyPointerEvents
		prevBodyPointerEvents = null
	}
})

function ok(e) {
	if (e) {
		e.stopPropagation?.()
		e.preventDefault?.()
	}
	feedback._resolveConfirm(true)
}
function cancel(e) {
	if (e) {
		e.stopPropagation?.()
		e.preventDefault?.()
	}
	feedback._resolveConfirm(false)
}
</script>
