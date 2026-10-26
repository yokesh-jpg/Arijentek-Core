import { useFeedbackStore } from '@/stores/feedback.js'

/* Drop-in replacements for the browser's alert() and confirm(), which drew the
   OS's own grey box over the app. */

function store() {
	try {
		return useFeedbackStore()
	} catch {
		return null
	}
}

/* alert() carried no type, so read one from the wording - the same approach
   the POS's feedback.alert takes. Validation prompts ("Please select ...") are
   warnings, failures are errors, completions are successes. */
function classify(text) {
	const t = String(text).toLowerCase()
	if (/\b(fail|failed|error|could not|couldn't|cannot|can't|unable|denied|not allowed|invalid)\b/.test(t)) return 'error'
	if (/\b(success|successfully|saved|created|updated|deleted|removed|submitted|approved|rejected|cancelled|canceled|added|uploaded|assigned|completed|sent|done)\b/.test(t)) return 'success'
	if (/\b(please|required|select|enter|must|missing|choose|at least)\b/.test(t)) return 'warning'
	return 'info'
}

export function notify(message, type) {
	const text = message instanceof Error ? message.message : message
	const kind = type || classify(text)
	const s = store()
	if (s) return s.show(kind, text)
	console[kind === 'error' ? 'error' : 'log'](text)
}

export const toast = {
	success: (m, title) => store()?.show('success', m, title),
	error: (m, title) => store()?.show('error', m, title),
	warning: (m, title) => store()?.show('warning', m, title),
	info: (m, title) => store()?.show('info', m, title),
}

/* confirm() returned a boolean synchronously; this returns a Promise of one,
   so callers `await ask(...)`. A plain string is treated as the message, and
   wording about deleting, rejecting or cancelling makes the dialog a red one
   with a matching button. */
export function ask(opts) {
	const o = typeof opts === 'string' ? { message: opts } : { ...opts }
	const t = String(o.message || '').toLowerCase()
	if (o.danger === undefined) o.danger = /\b(delete|remove|reject|cancel)\b/.test(t)
	if (!o.confirmText) {
		if (/\bdelete\b/.test(t)) o.confirmText = 'Delete'
		else if (/\breject\b/.test(t)) o.confirmText = 'Reject'
		else if (/\bapprove\b/.test(t)) o.confirmText = 'Approve'
		else if (/\bremove\b/.test(t)) o.confirmText = 'Remove'
	}
	const s = store()
	if (!s) return Promise.resolve(window.confirm(o.message))
	return s.confirm(o)
}
