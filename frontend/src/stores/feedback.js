import { defineStore } from 'pinia'
import { ref } from 'vue'

/* The POS's feedback store (zevar_ui_design_bundle/src/stores/feedback.js),
   trimmed to what the Staff Hub uses: an in-app confirm dialog in place of the
   browser's confirm(), and toasts in place of alert(). Rendered by
   ConfirmHost.vue and ToastHost.vue, mounted once in App.vue. */
export const useFeedbackStore = defineStore('feedback', () => {
	const confirmState = ref(null)
	const toasts = ref([])
	let nextId = 0

	function confirm({ title = 'Please confirm', message = '', confirmText = 'Confirm', cancelText = 'Cancel', danger = false } = {}) {
		return new Promise((resolve) => {
			/* A second request while one is open answers the first "no", so a
			   caller is never left waiting on a dialog that was replaced. */
			if (confirmState.value) confirmState.value.resolve(false)
			confirmState.value = { title, message, confirmText, cancelText, danger, resolve }
		})
	}

	function _resolveConfirm(value) {
		const s = confirmState.value
		confirmState.value = null
		if (s) s.resolve(value)
	}

	const DURATION = { success: 4500, error: 8000, warning: 6000, info: 5000 }

	function show(type, message, title = '') {
		const id = ++nextId
		toasts.value.unshift({ id, type, title, message: typeof message === 'string' ? message : message?.message || JSON.stringify(message) })
		if (toasts.value.length > 3) toasts.value.pop()
		setTimeout(() => dismiss(id), DURATION[type] || 5000)
		return id
	}

	function dismiss(id) {
		toasts.value = toasts.value.filter((t) => t.id !== id)
	}

	return { confirmState, confirm, _resolveConfirm, toasts, show, dismiss }
})
