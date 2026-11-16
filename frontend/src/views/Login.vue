<template>
	<!-- Same shell as the app behind it: graphite backdrop, one floating light
	     panel. Signing in should look like the place you are signing in to. -->
	<div class="login-shell">
		<div class="w-full max-w-[400px] flex flex-col items-center">
			<img
				:src="asset('images/arijentek-logo.svg')"
				alt="Arijentek"
				class="h-16 w-16 rounded-2xl object-contain border border-white/10 shadow-lg mb-2"
			/>
			<h2 class="text-lg font-bold text-white tracking-wide">Arijentek</h2>
			<p class="text-[13px] text-white/45 mb-6">Employee Portal</p>

			<div
				class="w-full rounded-[22px] bg-white dark:bg-surface-1 border border-black/[0.07] dark:border-white/10 shadow-[0_28px_70px_-24px_rgba(0,0,0,.55)] p-6 sm:p-7"
			>
				<h1
					class="text-xl font-semibold tracking-[-0.015em] text-[#17181B] dark:text-white"
				>
					Sign in
				</h1>
				<p class="text-[13px] text-[#5C6169] dark:text-white/65 mt-1 mb-6">
					Use your Arijentek account to continue.
				</p>

				<form @submit.prevent="handleLogin" class="space-y-4">
					<div>
						<label for="login-username" class="field-label">Username or Email</label>
						<div class="relative">
							<span
								class="material-symbols-outlined !text-[18px] absolute left-3.5 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/60 pointer-events-none"
								>person</span
							>
							<input
								id="login-username"
								v-model="usernameOrEmail"
								type="text"
								autocomplete="username"
								required
								placeholder="Username or email"
								class="field-input !pl-10"
							/>
						</div>
					</div>

					<div>
						<div class="flex items-baseline justify-between gap-3">
							<label for="login-password" class="field-label">Password</label>
							<button
								type="button"
								@click="openForgotPassword"
								class="text-xs font-medium text-accent dark:text-accent-light hover:underline mb-1.5 cursor-pointer bg-transparent border-none p-0"
							>
								Forgot password?
							</button>
						</div>
						<div class="relative">
							<span
								class="material-symbols-outlined !text-[18px] absolute left-3.5 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/60 pointer-events-none"
								>lock</span
							>
							<input
								id="login-password"
								v-model="password"
								:type="showPassword ? 'text' : 'password'"
								autocomplete="current-password"
								required
								placeholder="••••••••"
								class="field-input !pl-10 !pr-11"
							/>
							<button
								type="button"
								@click="showPassword = !showPassword"
								tabindex="-1"
								class="absolute right-1.5 top-1/2 -translate-y-1/2 w-8 h-8 grid place-items-center rounded-full text-[#656A72] dark:text-white/60 hover:text-[#17181B] dark:hover:text-white hover:bg-black/[0.05] dark:hover:bg-white/[0.08] transition-colors"
								:aria-label="showPassword ? 'Hide password' : 'Show password'"
							>
								<span class="material-symbols-outlined !text-[18px]">{{
									showPassword ? 'visibility_off' : 'visibility'
								}}</span>
							</button>
						</div>
					</div>

					<div
						v-if="errorMsg"
						class="flex items-start gap-2.5 p-3 rounded-[12px] bg-red-500/[0.08] border border-red-500/20"
						role="alert"
					>
						<span class="material-symbols-outlined !text-[18px] text-red-600 dark:text-red-400 shrink-0"
							>error</span
						>
						<p class="text-[13px] text-red-700 dark:text-red-300 leading-snug">
							{{ errorMsg }}
						</p>
					</div>

					<button type="submit" :disabled="loading" class="btn-primary w-full !h-12">
						<span
							v-if="loading"
							class="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin"
						></span>
						<template v-else>Sign in</template>
					</button>
				</form>
			</div>

			<p class="text-xs text-white/30 mt-6 text-center">
				Authorised access only · v4.2.0
			</p>
		</div>

		<!-- Forgot Password Dialog -->
		<Dialog v-model="showForgotPassword" :options="{ size: 'md' }">
			<template #body>
				<div class="modal-panel p-6 space-y-4">
					<div class="flex items-start justify-between gap-3">
						<div>
							<h3 class="text-base font-semibold text-[#17181B] dark:text-white">Reset Password</h3>
							<p class="text-xs text-[#5C6169] dark:text-white/60 mt-1">
								Enter your registered email address and we'll send you instructions to reset your password.
							</p>
						</div>
						<button @click="showForgotPassword = false" class="btn-icon-ghost shrink-0" aria-label="Close">
							<span class="material-symbols-outlined !text-[18px]">close</span>
						</button>
					</div>

					<div v-if="resetSuccess" class="p-3.5 rounded-xl bg-green-500/10 border border-green-500/20 text-xs text-green-700 dark:text-green-300">
						If an active account exists for this email, password reset instructions have been sent. Please check your inbox.
					</div>

					<div v-else class="space-y-3">
						<div v-if="resetError" class="p-2.5 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-600 dark:text-red-400">
							{{ resetError }}
						</div>
						<div>
							<label class="field-label">Email or Username</label>
							<input
								v-model="resetEmail"
								type="text"
								placeholder="you@example.com"
								class="field-input mt-1"
								:disabled="resetLoading"
								@keydown.enter.prevent="handleResetPassword"
							/>
						</div>
					</div>

					<div class="flex items-center justify-end gap-2 pt-2">
						<button type="button" class="btn-secondary" @click="showForgotPassword = false">
							{{ resetSuccess ? 'Close' : 'Cancel' }}
						</button>
						<button
							v-if="!resetSuccess"
							type="button"
							class="btn-primary flex items-center gap-1.5"
							:disabled="resetLoading || !resetEmail.trim()"
							@click="handleResetPassword"
						>
							<span v-if="resetLoading" class="material-symbols-outlined !text-[16px] animate-spin">progress_activity</span>
							{{ resetLoading ? 'Sending…' : 'Send Instructions' }}
						</button>
					</div>
				</div>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import { ref } from 'vue'
import { Dialog, createResource, call } from 'frappe-ui'
import { getErrorMessage } from '@/utils.js'
import { notify } from '@/utils/feedback.js'

const usernameOrEmail = ref('')
const password = ref('')
const showPassword = ref(false)
const loading = ref(false)
const errorMsg = ref('')

const showForgotPassword = ref(false)
const resetEmail = ref('')
const resetLoading = ref(false)
const resetSuccess = ref(false)
const resetError = ref('')

function openForgotPassword() {
	resetEmail.value = usernameOrEmail.value || ''
	resetSuccess.value = false
	resetError.value = ''
	showForgotPassword.value = true
}

async function handleResetPassword() {
	const user = resetEmail.value.trim()
	if (!user) return
	resetLoading.value = true
	resetError.value = ''
	try {
		await call('frappe.core.doctype.user.user.reset_password', { user })
		resetSuccess.value = true
		notify('Password reset instructions sent', 'success')
	} catch (err) {
		resetError.value = getErrorMessage(err, 'Could not send reset instructions. Please try again.')
	} finally {
		resetLoading.value = false
	}
}

// Vite serves this app under BASE_URL, so a root-relative path would 404.
const asset = (p) => `${import.meta.env.BASE_URL}${p}`

const loginResource = createResource({
	url: 'arijentek_core.api.auth.login',
	makeParams() {
		let usr = (usernameOrEmail.value || '').trim()
		if (usr.toLowerCase() === 'admin@example.com') {
			usr = 'Administrator'
		}
		return { usr, pwd: password.value }
	},
	onSuccess(data) {
		if (data && data.success === false) {
			loading.value = false
			errorMsg.value = data.message || 'Invalid login credentials'
			return
		}
		try {
			const usr = (usernameOrEmail.value || '').trim()
			const syncPayload = { action: 'new_login', user: usr, timestamp: Date.now() }
			localStorage.setItem('portal_session_sync', JSON.stringify(syncPayload))
			if (usr) {
				localStorage.setItem('portal_active_user', usr)
			}
			if (typeof BroadcastChannel !== 'undefined') {
				const ch = new BroadcastChannel('portal_session_sync_channel')
				ch.postMessage(syncPayload)
				ch.close()
			}
		} catch (e) {}
		window.location.reload()
	},
	onError(err) {
		loading.value = false
		errorMsg.value = getErrorMessage(err, 'Invalid login credentials. Please check your username and password.')
	},
})

async function handleLogin() {
	errorMsg.value = ''
	loading.value = true
	try {
		await loginResource.submit()
	} catch (e) {
		// Handled in onError callback
	}
}
</script>

<style scoped>
/* The backdrop is the same graphite in both themes — it is the shell, not a
   surface — so this needs no dark variant. */
.login-shell {
	min-height: 100dvh;
	width: 100%;
	display: grid;
	place-items: center;
	padding: 24px 16px;
	background: #0b0b11;
}
</style>
