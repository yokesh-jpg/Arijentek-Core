<template>
	<Teleport to="body">
		<div
			v-if="modelValue"
			class="fixed inset-0 z-[120] flex items-center justify-center bg-[#0B0B0E]/70 backdrop-blur-sm p-4"
			@click="close"
		>
			<div class="modal-panel max-w-md" @click.stop>
				<header class="flex items-start justify-between gap-3 px-5 py-4 border-b border-black/[0.07] dark:border-white/10 shrink-0">
					<div class="min-w-0">
						<h2 class="modal-title">Change password</h2>
						<p class="text-[13px] text-[#5C6169] dark:text-white/65">
							You will stay signed in on this device.
						</p>
					</div>
					<button class="btn-icon-ghost shrink-0" aria-label="Close" @click="close">
						<span class="material-symbols-outlined !text-[18px]">close</span>
					</button>
				</header>

				<form class="flex-1 overflow-y-auto px-6 py-5 space-y-4" @submit.prevent="submit">
					<div>
						<label for="cp-current" class="field-label">Current password</label>
						<div class="relative">
							<input
								id="cp-current"
								v-model="current"
								:type="show.current ? 'text' : 'password'"
								autocomplete="current-password"
								class="field-input !pr-11"
								:class="error ? '!border-red-400 dark:!border-red-500/60' : ''"
							/>
							<button type="button" tabindex="-1" class="reveal-btn" :aria-label="show.current ? 'Hide password' : 'Show password'" @click="show.current = !show.current">
								<span class="material-symbols-outlined !text-[18px]">{{ show.current ? 'visibility_off' : 'visibility' }}</span>
							</button>
						</div>
					</div>

					<div>
						<label for="cp-new" class="field-label">New password</label>
						<div class="relative">
							<input
								id="cp-new"
								v-model="next"
								:type="show.next ? 'text' : 'password'"
								autocomplete="new-password"
								class="field-input !pr-11"
							/>
							<button type="button" tabindex="-1" class="reveal-btn" :aria-label="show.next ? 'Hide password' : 'Show password'" @click="show.next = !show.next">
								<span class="material-symbols-outlined !text-[18px]">{{ show.next ? 'visibility_off' : 'visibility' }}</span>
							</button>
						</div>
						<!-- Stated up front rather than only after a rejected submit. -->
						<p class="text-xs text-[#5C6169] dark:text-white/60 mt-1.5">At least 8 characters.</p>
					</div>

					<div>
						<label for="cp-confirm" class="field-label">Confirm new password</label>
						<input
							id="cp-confirm"
							v-model="confirm"
							:type="show.next ? 'text' : 'password'"
							autocomplete="new-password"
							class="field-input"
							:class="mismatch ? '!border-red-400 dark:!border-red-500/60' : ''"
						/>
						<p v-if="mismatch" class="text-xs text-red-600 dark:text-red-400 mt-1.5">
							The two new passwords do not match.
						</p>
					</div>

					<div v-if="error" class="inset-panel flex items-start gap-2.5 !border-red-500/25">
						<span class="material-symbols-outlined !text-[18px] text-red-500 dark:text-red-400 shrink-0">error</span>
						<p class="text-[13px] text-red-700 dark:text-red-300">{{ error }}</p>
					</div>

					<div v-if="done" class="inset-panel flex items-start gap-2.5 !border-green-500/25">
						<span class="material-symbols-outlined !text-[18px] text-green-700 dark:text-green-400 shrink-0">check_circle</span>
						<p class="text-[13px] text-green-700 dark:text-green-300">Password updated.</p>
					</div>
				</form>

				<footer class="px-5 py-4 border-t border-black/[0.07] dark:border-white/10 shrink-0 flex items-center justify-end gap-2">
					<button class="btn-secondary" @click="close">Cancel</button>
					<button class="btn-primary" :disabled="!canSubmit || saving" @click="submit">
						<span v-if="saving" class="material-symbols-outlined !text-[18px] animate-spin">progress_activity</span>
						Update password
					</button>
				</footer>
			</div>
		</div>
	</Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { call } from 'frappe-ui'

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue'])

const current = ref('')
const next = ref('')
const confirm = ref('')
const show = ref({ current: false, next: false })
const error = ref('')
const done = ref(false)
const saving = ref(false)

/* Only flagged once something has been typed, so the field is not red the
   moment it is focused. */
const mismatch = computed(() => Boolean(confirm.value) && next.value !== confirm.value)

const canSubmit = computed(
	() => Boolean(current.value) && next.value.length >= 8 && next.value === confirm.value,
)

/* Nothing is kept between openings - a password left in a field is a password
   on screen for whoever opens the menu next. */
watch(
	() => props.modelValue,
	(open) => {
		if (!open) return
		current.value = ''
		next.value = ''
		confirm.value = ''
		show.value = { current: false, next: false }
		error.value = ''
		done.value = false
		saving.value = false
	},
)

function close() {
	emit('update:modelValue', false)
}

async function submit() {
	if (!canSubmit.value || saving.value) return
	saving.value = true
	error.value = ''
	done.value = false
	try {
		const res = await call('arijentek_core.api.settings.change_own_password', {
			current_password: current.value,
			new_password: next.value,
		})
		if (res && res.success === false) {
			error.value = res.error || 'Could not update the password.'
			return
		}
		done.value = true
		/* Long enough to read the confirmation, short enough not to sit there. */
		setTimeout(close, 1200)
	} catch (e) {
		error.value = e?.message || 'Could not update the password.'
	} finally {
		saving.value = false
	}
}
</script>
