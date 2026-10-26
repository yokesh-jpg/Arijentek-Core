<template>
	<!-- Same shell as the app behind it: graphite backdrop, one floating light
	     panel. Signing in should look like the place you are signing in to. -->
	<div class="login-shell">
		<div class="w-full max-w-[400px] flex flex-col items-center">
			<img
				:src="asset('images/gemora-logo-full.png')"
				alt="Gemora 360"
				class="h-[74px] w-auto mb-1"
			/>
			<p class="text-[13px] text-white/45 mb-6">Staff Hub</p>

			<div
				class="w-full rounded-[22px] bg-white dark:bg-surface-1 border border-black/[0.07] dark:border-white/10 shadow-[0_28px_70px_-24px_rgba(0,0,0,.55)] p-6 sm:p-7"
			>
				<h1
					class="text-xl font-semibold tracking-[-0.015em] text-[#17181B] dark:text-white"
				>
					Sign in
				</h1>
				<p class="text-[13px] text-[#5C6169] dark:text-white/65 mt-1 mb-6">
					Use your Zevar account to continue.
				</p>

				<form @submit.prevent="handleLogin" class="space-y-4">
					<div>
						<label for="login-email" class="field-label">Email</label>
						<div class="relative">
							<span
								class="material-symbols-outlined !text-[18px] absolute left-3.5 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/60 pointer-events-none"
								>alternate_email</span
							>
							<input
								id="login-email"
								v-model="email"
								type="email"
								autocomplete="username"
								required
								placeholder="you@zevar.com"
								class="field-input !pl-10"
							/>
						</div>
					</div>

					<div>
						<div class="flex items-baseline justify-between gap-3">
							<label for="login-password" class="field-label">Password</label>
							<!-- Not wired to anything yet — see the note in README. -->
							<a
								href="#"
								class="text-xs font-medium text-accent dark:text-accent-light hover:underline mb-1.5"
								>Forgot password?</a
							>
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
	</div>
</template>

<script setup>
import { ref } from 'vue'
import { createResource } from 'frappe-ui'

const email = ref('')
const password = ref('')
const showPassword = ref(false)
const loading = ref(false)
const errorMsg = ref('')

// Vite serves this app under BASE_URL, so a root-relative path would 404.
const asset = (p) => `${import.meta.env.BASE_URL}${p}`

const loginResource = createResource({
	url: 'login',
	makeParams() {
		return { usr: email.value, pwd: password.value }
	},
	onSuccess() {
		window.location.reload()
	},
	onError(err) {
		loading.value = false
		errorMsg.value = err?.messages?.[0] || 'Invalid credentials'
	},
})

function handleLogin() {
	errorMsg.value = ''
	loading.value = true
	loginResource.submit()
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
