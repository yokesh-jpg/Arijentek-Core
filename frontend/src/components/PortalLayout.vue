<template>
	<div class="portal-shell font-sans text-gray-900 dark:text-gray-100">
		<!-- ===== MOBILE DRAWER (TELEPORTED, SLIDING FROM LEFT, MATCHING ZEVAR_UI) ===== -->
		<Teleport to="body">
			<div
				v-if="mobileDrawerOpen"
				class="fixed inset-0 bg-[#0B0B0E]/70 backdrop-blur-sm z-[60] lg:hidden transition-opacity duration-300"
				@click="mobileDrawerOpen = false"
			></div>
			<div
				class="fixed top-0 left-0 h-full w-80 max-w-[85vw] bg-[#0F0F11] border-r border-white/10 z-[61] transform transition-transform duration-300 ease-in-out lg:hidden flex flex-col text-white shadow-2xl"
				:class="mobileDrawerOpen ? 'translate-x-0' : '-translate-x-full'"
			>
				<!-- Drawer Header -->
				<div class="p-4 border-b border-white/10 flex items-center justify-between shrink-0">
					<div class="flex items-center gap-3">
						<img
							:src="asset('images/gemora-gem.png')"
							alt="Gemora 360"
							class="h-8 w-auto"
						/>
						<div>
							<h1 class="text-base font-semibold text-white leading-tight">Zevar</h1>
							<p class="text-xs text-white/50">Employee Portal</p>
						</div>
					</div>
					<button
						@click="mobileDrawerOpen = false"
						class="p-2 hover:bg-white/10 rounded-full transition-colors text-white/60 hover:text-white"
						aria-label="Close menu"
					>
						<span class="material-symbols-outlined text-[20px]">close</span>
					</button>
				</div>

				<!-- Search in Drawer -->
				<div class="p-3 border-b border-white/5">
					<div class="relative">
						<span class="material-symbols-outlined absolute left-3.5 top-1/2 -translate-y-1/2 text-white/40 text-[18px]">search</span>
						<input
							v-model="drawerSearchQuery"
							class="w-full bg-white/5 border border-white/10 rounded-full py-2 pl-10 pr-4 text-xs text-white placeholder:text-white/30 focus:border-accent outline-none transition-all"
							placeholder="Search pages..."
							type="text"
						/>
					</div>
				</div>

				<!-- Navigation in Drawer -->
				<nav class="flex-1 p-4 space-y-4 overflow-y-auto no-scrollbar">
					<div v-for="group in filteredDrawerNavGroups" :key="group.label" class="space-y-1.5">
						<p class="px-2 text-xs font-semibold tracking-[0.14em] text-[#8A8A9E] uppercase">
							{{ group.label }}
						</p>
						<router-link
							v-for="item in group.items"
							:key="item.to"
							:to="item.to"
							custom
							v-slot="{ href, navigate, isActive, isExactActive }"
						>
							<a
								:href="item.isExternal ? item.to : href"
								@click="(e) => onNav(e, item, navigate)"
								class="flex items-center gap-3 h-10 px-3.5 rounded-full transition-colors duration-150"
								:class="[
									(item.to === '/' ? isExactActive : isActive)
										? 'bg-accent text-white font-semibold shadow-md'
										: 'text-[#C5C5D2] hover:text-white hover:bg-white/[0.06]'
								]"
							>
								<NavIcon :name="item.icon" class="w-[18px] h-[18px] shrink-0" />
								<span class="text-sm font-medium truncate">{{ renderLabel(item.label) }}</span>
							</a>
						</router-link>
					</div>
				</nav>

				<!-- Drawer Bottom Actions -->
				<div class="p-4 border-t border-white/10 space-y-2 shrink-0 bg-white/[0.02]">

					<button
						@click="forceRefresh"
						class="w-full py-2 px-3 rounded-lg text-white/50 hover:text-white hover:bg-white/5 text-xs flex items-center justify-center gap-2 transition-colors"
					>
						<svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.75">
							<path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
						</svg>
						<span>Force Refresh</span>
					</button>
				</div>
			</div>
		</Teleport>

		<!-- ===== DESKTOP SIDEBAR (RAIL) ===== -->
		<aside
			class="hidden lg:flex portal-rail flex-col shrink-0 overflow-hidden select-none z-30 transition-[width,min-width] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]"
			:class="visuallyCollapsed ? 'w-[80px] min-w-[80px] items-center' : 'w-[256px] min-w-[256px]'"
			@mouseenter="onHoverEnter"
			@mouseleave="onHoverLeave"
		>
			<!-- Top Header: Brand Lockup (matching zevar_ui - no top toggle; collapse via hover) -->
			<div
				class="flex items-center h-16 shrink-0 transition-all duration-300 w-full"
				:class="visuallyCollapsed ? 'px-0 justify-center mb-2' : 'px-4 justify-start gap-3 mb-2'"
			>
				<!-- Brand lockup (shown when expanded) -->
				<router-link
					v-show="!visuallyCollapsed"
					to="/"
					class="flex items-center overflow-hidden outline-none group min-w-0 flex-1"
					title="Gemora 360 · Staff Hub"
				>
					<span class="flex flex-col items-start min-w-0">
						<img
							:src="asset('images/gemora-logo-full.png')"
							alt="Gemora 360"
							class="h-[54px] w-auto -ml-1 transition-transform duration-200 group-hover:scale-105"
						/>
						<span class="-mt-[3px] ml-[8px] inline-flex items-center gap-1.5 h-4 px-2 rounded-full bg-white/[0.06] border border-white/[0.08] text-[10px] font-medium text-white/70 whitespace-nowrap">
							<span class="w-1.5 h-1.5 rounded-full bg-accent-light"></span>Employee Portal
						</span>
					</span>
				</router-link>

				<!-- Collapsed View: Centered Gem Icon Only -->
				<div v-show="visuallyCollapsed" class="w-full flex flex-col items-center gap-2 pt-2">
					<router-link
						to="/"
						class="flex items-center justify-center outline-none group"
						title="Gemora 360 · Staff Hub"
					>
						<img
							:src="asset('images/gemora-gem.png')"
							alt="Gemora 360"
							class="h-[32px] w-auto transition-transform duration-200 group-hover:scale-105"
						/>
					</router-link>
				</div>
			</div>

			<!-- Grouped nav -->
			<nav
				class="flex-1 pb-3 space-y-5 overflow-y-auto overflow-x-hidden no-scrollbar w-full"
			>
				<div v-for="group in navGroups" :key="group.label" class="space-y-2.5">
					<div
						class="px-2 flex items-center overflow-hidden transition-all duration-200 ease-[cubic-bezier(0.16,1,0.3,1)]"
						:class="visuallyCollapsed ? 'opacity-0 h-0' : 'opacity-100 h-6 delay-100'"
					>
						<span
							class="text-xs font-semibold tracking-[0.14em] text-[#8A8A9E] whitespace-nowrap uppercase"
							>{{ group.label }}</span
						>
					</div>

					<router-link
						v-for="item in group.items"
						:key="item.to"
						:to="item.to"
						custom
						v-slot="{ href, navigate, isActive, isExactActive }"
					>
						<a
							:href="item.isExternal ? item.to : href"
							@click="(e) => onNav(e, item, navigate)"
							class="flex items-center h-10 rounded-full transition-colors duration-150 group relative"
							:class="[
								(item.to === '/' ? isExactActive : isActive)
									? 'bg-accent text-white font-semibold shadow-[0_6px_16px_-6px_rgb(var(--accent-rgb)/0.9)]'
									: 'text-[#C5C5D2] hover:text-white hover:bg-white/[0.06]',
								visuallyCollapsed ? 'justify-center w-10 mx-auto rounded-[14px]' : 'gap-3 px-3.5',
							]"
						>
							<NavIcon
								:name="item.icon"
								class="w-[18px] h-[18px] shrink-0 pointer-events-none transition-opacity duration-150"
								:class="(item.to === '/' ? isExactActive : isActive) ? 'opacity-100' : 'opacity-70 group-hover:opacity-100'"
							/>
							<span
								class="min-w-0 overflow-hidden transition-all duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] pointer-events-none"
								:class="visuallyCollapsed ? 'opacity-0 w-0 grow-0' : 'opacity-100 w-auto flex-1 delay-100'"
							>
								<span class="text-sm tracking-[-0.005em] block truncate">{{
									renderLabel(item.label)
								}}</span>
							</span>

							<!-- Collapsed hover tooltip — the only way to read a rail icon -->
							<span
								v-if="visuallyCollapsed"
								class="absolute left-full ml-3 px-2.5 py-1.5 bg-[#1B1B24] text-white text-xs font-medium rounded-[12px] shadow-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50 border border-white/10"
								>{{ renderLabel(item.label) }}</span
							>
						</a>
					</router-link>
				</div>
			</nav>

			<!-- Bottom utilities: collapse toggle, then Force Refresh on its own raised card (matching /pos) -->
			<div class="shrink-0 w-full px-4 pb-4 pt-2 space-y-1.5 mt-auto">
				<!-- Collapse / Expand Button -->
				<button
					@click="toggleCollapse"
					class="w-full h-9 flex items-center rounded-full text-[#8A8A9C] hover:text-white hover:bg-white/[0.06] transition-colors duration-150"
					:class="visuallyCollapsed ? 'justify-center' : 'gap-3.5 px-4'"
					:aria-label="sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
					:title="visuallyCollapsed ? (sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar') : ''"
				>
					<svg
						class="w-5 h-5 shrink-0 transition-transform duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]"
						:class="sidebarCollapsed ? 'rotate-180' : ''"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						stroke-width="1.75"
					>
						<path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
					</svg>
					<span
						class="text-[13px] overflow-hidden whitespace-nowrap transition-all duration-200 ease-[cubic-bezier(0.16,1,0.3,1)]"
						:class="visuallyCollapsed ? 'opacity-0 w-0' : 'opacity-100 w-auto delay-100'"
					>
						{{ sidebarCollapsed ? 'Expand' : 'Collapse' }}
					</span>
				</button>

				<!-- Force Refresh Button -->
				<button
					@click="forceRefresh"
					class="w-full h-[48px] flex items-center rounded-[16px] bg-white/[0.045] hover:bg-white/[0.08] border border-white/[0.06] text-[#C5C5D2] hover:text-white transition-colors duration-150"
					:class="visuallyCollapsed ? 'justify-center' : 'gap-3.5 px-4'"
					:title="visuallyCollapsed ? 'Force Refresh' : ''"
				>
					<svg class="w-[18px] h-[18px] shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.75">
						<path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
					</svg>
					<span
						class="text-[13px] overflow-hidden whitespace-nowrap transition-all duration-200 ease-[cubic-bezier(0.16,1,0.3,1)]"
						:class="visuallyCollapsed ? 'opacity-0 w-0' : 'opacity-100 w-auto delay-100'"
					>
						Force Refresh
					</span>
				</button>
			</div>
		</aside>

		<!-- ===== FLOATING CONTENT PANEL ===== -->
		<div class="portal-panel">
			<header
				class="portal-bar h-16 lg:h-[72px] shrink-0 flex items-center gap-2.5 lg:gap-3 px-3 sm:px-4 lg:px-7 border-b border-[#ECECF1] dark:border-white/[0.08]"
			>
				<!-- Mobile: Hamburger Menu Button (matching zevar_ui) -->
				<button
					@click="mobileDrawerOpen = true"
					class="lg:hidden p-1.5 -ml-1 rounded-lg hover:bg-black/5 dark:hover:bg-white/10 text-[#5C6169] dark:text-white/80 transition-colors flex items-center justify-center shrink-0"
					aria-label="Open menu"
				>
					<span class="material-symbols-outlined text-[24px]">menu</span>
				</button>

				<!-- Page identity: the rail shows where you are, this names it -->
				<h1
					class="text-base font-semibold tracking-[-0.01em] text-[#17181B] dark:text-white truncate lg:hidden"
				>
					{{ pageTitle }}
				</h1>

				<!-- Breadcrumb trail, the POS's own pattern for this bar: the
				     group the page sits in, then the page. It fills the space
				     the search box left behind with something that says where
				     you are rather than with nothing. -->
				<div class="hidden lg:flex items-center bg-[#F5F5F8] dark:bg-surface-3 rounded-full p-1 gap-0.5 shrink-0">
					<button type="button" class="history-btn" title="Go back (Alt + Left)" aria-label="Go back" @click="goBack">
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M15 19l-7-7 7-7" /></svg>
					</button>
					<button type="button" class="history-btn" title="Go forward (Alt + Right)" aria-label="Go forward" @click="router.forward()">
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M9 5l7 7-7 7" /></svg>
					</button>
					<div class="h-4 w-px bg-[#E2E2E8] dark:bg-white/10 my-auto" aria-hidden="true"></div>
					<button type="button" class="history-btn hover:!text-accent dark:hover:!text-accent-light" title="Dashboard" aria-label="Go to dashboard" @click="router.push('/')">
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" /></svg>
					</button>
				</div>

				<nav
					class="hidden lg:flex items-center gap-1.5 text-[13px] font-medium truncate"
					aria-label="Breadcrumb"
				>
					<template v-for="(crumb, i) in breadcrumbs" :key="crumb.label">
						<span v-if="i > 0" class="text-[#C9CBD2] dark:text-white/20" aria-hidden="true">/</span>
						<span
							:class="
								i === breadcrumbs.length - 1
									? 'text-[#17181B] dark:text-white font-semibold truncate'
									: 'text-[#5C6169] dark:text-white/60 truncate'
							"
							:aria-current="i === breadcrumbs.length - 1 ? 'page' : undefined"
							>{{ crumb.label }}</span
						>
					</template>
				</nav>

				<div class="ml-auto flex items-center gap-1.5 shrink-0">
					<button
						class="w-9 h-9 grid place-items-center rounded-full text-[#5C6169] dark:text-white/85 hover:bg-accent/[0.06] dark:hover:bg-white/5 transition-colors"
						aria-label="Notifications"
					>
						<span class="material-symbols-outlined !text-[20px] icon-loading-guard"
							>notifications</span
						>
					</button>
					<div class="w-px h-6 bg-[#ECECF1] dark:bg-white/10 mx-1.5"></div>

					<div class="relative">
						<button
							@click="userMenuOpen = !userMenuOpen"
							class="flex items-center gap-2 p-1 pr-2.5 rounded-full bg-[#F5F5F8] dark:bg-surface-3 hover:bg-[#EFEFF3] dark:hover:bg-white/[0.08] transition-colors"
							:aria-expanded="userMenuOpen"
							aria-haspopup="menu"
							:aria-label="'Account menu for ' + (auth.user?.full_name || 'you')"
						>
							<img
								v-if="userAvatar"
								:src="userAvatar"
								class="w-7 h-7 rounded-full object-cover shrink-0"
								alt=""
							/>
							<span
								v-else
								class="w-7 h-7 rounded-full bg-accent text-white grid place-items-center text-xs font-semibold shrink-0"
								>{{ userInitials }}</span
							>
							<span class="hidden sm:block text-[13px] font-semibold text-[#17181B] dark:text-white truncate max-w-[100px]">{{
								(auth.user?.full_name || 'Account').split(' ')[0]
							}}</span>
							<svg class="w-4 h-4 text-[#656A72] dark:text-white/50 transition-transform duration-200" :class="{ 'rotate-180': userMenuOpen }" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M19 9l-7 7-7-7" /></svg>
						</button>

						<template v-if="userMenuOpen">
							<div class="fixed inset-0 z-40" @click="userMenuOpen = false"></div>
							<div
								class="absolute right-0 top-full mt-2 w-[268px] z-50 rounded-[16px] bg-white dark:bg-surface-2 border border-[#ECECF1] dark:border-white/10 shadow-[0_24px_60px_-20px_rgba(0,0,0,0.35)] py-1.5 overflow-hidden"
							>
								<!-- Identity -->
								<div class="flex items-center gap-3 px-3.5 py-3">
									<img
										v-if="userAvatar"
										:src="userAvatar"
										class="w-10 h-10 rounded-full object-cover shrink-0"
										alt=""
									/>
									<span
										v-else
										class="w-10 h-10 rounded-full bg-accent text-white grid place-items-center text-[13px] font-semibold shrink-0"
										>{{ userInitials }}</span
									>
									<span class="min-w-0">
										<span class="block text-[13px] font-semibold text-[#17181B] dark:text-white truncate">
											{{ auth.user?.full_name || 'Signed in' }}
										</span>
										<span class="block text-xs text-[#5C6169] dark:text-white/65 truncate">
											{{ employeeStore.employee?.designation || 'Staff' }}
										</span>
									</span>
								</div>

								<div class="menu-divider"></div>

								<!-- Display -->
								<p class="menu-label">Display</p>
								<button @click="toggleDarkMode" class="menu-row">
									<span class="material-symbols-outlined !text-[18px] menu-icon">{{
										isDark ? 'light_mode' : 'dark_mode'
									}}</span>
									<span class="min-w-0">
										<span class="block text-[13px] font-medium leading-tight">Switch visual theme</span>
										<!-- The sublabel names the state you are IN, not the one the
										     click moves to - the icon already shows the destination. -->
										<span class="block text-xs text-[#5C6169] dark:text-white/60 mt-0.5 leading-tight">
											{{ isDark ? 'Dark mode' : 'Light mode' }}
										</span>
									</span>
								</button>
								<button @click="toggleLargeText" class="menu-row" :aria-pressed="largeText">
									<!-- "Aa" rather than an icon: the control is about type size,
									     and the glyph shows it directly. -->
									<span class="w-[18px] shrink-0 mt-0.5 text-center text-[13px] font-semibold text-[#5C6169] dark:text-white/65">Aa</span>
									<span class="min-w-0 flex-1">
										<span class="block text-[13px] font-medium leading-tight">Large text mode</span>
										<span class="block text-xs text-[#5C6169] dark:text-white/60 mt-0.5 leading-tight">
											Easier to read across the shop floor
										</span>
									</span>
									<span
										class="shrink-0 mt-0.5 w-9 h-5 rounded-full transition-colors relative"
										:class="largeText ? 'bg-accent' : 'bg-black/[0.12] dark:bg-white/20'"
									>
										<span
											class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform"
											:class="largeText ? 'translate-x-4' : ''"
										></span>
									</span>
								</button>

								<div class="menu-divider"></div>

								<!-- Account -->
								<p class="menu-label">Account</p>
								<button @click="goMenu('/attendance')" class="menu-row">
									<span class="material-symbols-outlined !text-[18px] menu-icon">badge</span>
									<span class="min-w-0">
										<span class="block text-[13px] font-medium leading-tight">My attendance</span>
										<span class="block text-xs text-[#5C6169] dark:text-white/60 mt-0.5 leading-tight">
											Your shifts, hours and records
										</span>
									</span>
								</button>
								<button v-if="canSeeSettings" @click="goMenu('/settings')" class="menu-row">
									<span class="material-symbols-outlined !text-[18px] menu-icon">tune</span>
									<span class="min-w-0">
										<span class="block text-[13px] font-medium leading-tight">HR settings</span>
										<span class="block text-xs text-[#5C6169] dark:text-white/60 mt-0.5 leading-tight">
											Attendance and timesheet rules
										</span>
									</span>
								</button>
								<button @click="openPasswordDialog" class="menu-row">
									<span class="material-symbols-outlined !text-[18px] menu-icon">lock_reset</span>
									<span class="min-w-0">
										<span class="block text-[13px] font-medium leading-tight">Change password</span>
										<span class="block text-xs text-[#5C6169] dark:text-white/60 mt-0.5 leading-tight">
											Update your sign-in password
										</span>
									</span>
								</button>

								<div class="menu-divider"></div>

								<!-- Sign out -->
								<button
									@click="auth.logout()"
									class="menu-row !text-red-600 dark:text-red-400 dark:!text-red-400 hover:!bg-red-500/[0.07]"
								>
									<span class="material-symbols-outlined !text-[18px] shrink-0 icon-loading-guard">logout</span>
									<span class="text-[13px] font-medium leading-tight">Log out</span>
								</button>
							</div>
						</template>
					</div>
				</div>
			</header>

			<ChangePasswordDialog v-model="passwordDialogOpen" />

			<main
				class="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-4 sm:p-5 lg:p-8 lg:pt-5"
			>
				<slot />
			</main>

			<!-- ===== Phone bottom bar =====
			     Four destinations you reach for mid-shift, plus More for the rest.
			     Eleven items do not fit a thumb row, and a bar that scrolls
			     sideways hides exactly the things people cannot find. -->
			<nav
				class="lg:hidden shrink-0 border-t border-[#ECECF1] dark:border-white/[0.08] bg-white/95 dark:bg-surface-2/95 backdrop-blur-xl pb-[env(safe-area-inset-bottom,0px)]"
			>
				<div class="grid grid-cols-5 h-[72px]">
					<router-link
						v-for="item in phoneNavItems"
						:key="item.to"
						:to="item.to"
						custom
						v-slot="{ href, navigate, isActive, isExactActive }"
					>
						<a
							:href="href"
							@click="navigate"
							class="phone-nav-item"
							:class="(item.to === '/' ? isExactActive : isActive) ? 'phone-nav-item-active' : ''"
						>
							<span class="phone-nav-pill">
								<NavIcon :name="item.icon" class="w-[22px] h-[22px]" />
							</span>
							<span class="phone-nav-label">{{ renderLabel(item.shortLabel) }}</span>
						</a>
					</router-link>

					<button
						@click="mobileDrawerOpen = true"
						class="phone-nav-item"
						:class="isOnMoreRoute ? 'phone-nav-item-active' : ''"
					>
						<span class="phone-nav-pill">
							<span class="material-symbols-outlined !text-[22px] icon-loading-guard"
								>more_horiz</span
							>
						</span>
						<span class="phone-nav-label">More</span>
					</button>
				</div>
			</nav>
		</div>
	</div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import NavIcon from './NavIcon.vue'
import ChangePasswordDialog from './ChangePasswordDialog.vue'
import { useAuthStore } from '@/stores/auth'
import { useEmployeeStore } from '@/stores/employee'
import { useTeamStore } from '@/stores/team'
import { useAttendanceStore } from '@/stores/attendance'
import { usePayrollStore } from '@/stores/payroll'
import { useTasksStore } from '@/stores/tasks'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const employeeStore = useEmployeeStore()
const teamStore = useTeamStore()
const attendanceStore = useAttendanceStore()
const payrollStore = usePayrollStore()
const tasksStore = useTasksStore()

const sidebarCollapsed = ref(false)
const isHovering = ref(false)
let leaveTimer = null
const visuallyCollapsed = computed(() => sidebarCollapsed.value && !isHovering.value)

const onHoverEnter = () => {
	if (leaveTimer) {
		clearTimeout(leaveTimer)
		leaveTimer = null
	}
	if (sidebarCollapsed.value) isHovering.value = true
}

const onHoverLeave = () => {
	if (leaveTimer) clearTimeout(leaveTimer)
	leaveTimer = setTimeout(() => {
		isHovering.value = false
		leaveTimer = null
	}, 150)
}

function toggleCollapse() {
	sidebarCollapsed.value = !sidebarCollapsed.value
	isHovering.value = false
	if (leaveTimer) {
		clearTimeout(leaveTimer)
		leaveTimer = null
	}
}

onUnmounted(() => {
	if (leaveTimer) clearTimeout(leaveTimer)
})

const userMenuOpen = ref(false)
const passwordDialogOpen = ref(false)
const mobileDrawerOpen = ref(false)
const drawerSearchQuery = ref('')

const filteredDrawerNavGroups = computed(() => {
	const query = drawerSearchQuery.value.trim().toLowerCase()
	if (!query) return navGroups.value
	return navGroups.value
		.map((g) => ({
			label: g.label,
			items: g.items.filter((i) =>
				renderLabel(i.label).toLowerCase().includes(query)
			),
		}))
		.filter((g) => g.items.length)
})

/* The menu closes first: leaving it open behind a modal gives two layers the
   same dismiss target. */
function openPasswordDialog() {
	userMenuOpen.value = false
	passwordDialogOpen.value = true
}

/* Large text mode. The class goes on <html> so the rules in index.css can
   reach the teleported dialogs and menus too, which live outside <main>. */
const largeText = ref(false)
function toggleLargeText() {
	largeText.value = !largeText.value
	document.documentElement.classList.toggle('text-large', largeText.value)
	localStorage.setItem('portal_text_large', largeText.value ? '1' : '0')
}

/* The POS header's history controls. With nothing to go back to (a page
   opened directly), Back goes to the dashboard rather than doing nothing. */
function goBack() {
	if (window.history.length > 1) router.back()
	else router.push('/')
}

/* Force Refresh (POS sidebar): drop any cached app files and service
   workers, then reload, so a stale build cannot survive it. */
async function forceRefresh() {
	try {
		if ('caches' in window) {
			const keys = await caches.keys()
			await Promise.all(keys.map((k) => caches.delete(k)))
		}
		if (navigator.serviceWorker) {
			const regs = await navigator.serviceWorker.getRegistrations()
			await Promise.all(regs.map((r) => r.unregister()))
		}
	} catch {
		/* a failed clean-up must not stop the reload */
	}
	window.location.reload()
}

/* Close the menu before navigating, or it stays open over the new page. */
function goMenu(path) {
	userMenuOpen.value = false
	router.push(path)
}
const isDark = ref(false)
const canCreateReports = ref(false)
const canAccessSettings = ref(
	Boolean(
		auth.user &&
		(auth.user.user === 'Administrator' ||
		 (auth.user.roles || []).includes('HR Manager') ||
		 (auth.user.roles || []).includes('System Manager'))
	)
)

// Vite serves this app under BASE_URL (/employee-portal/), so a root-relative
// "/images/…" would 404 in the build.
const asset = (p) => `${import.meta.env.BASE_URL}${p}`

/* initialsOf still serves the user avatar; the manager pair went with the
   "Reports to" card. */
const initialsOf = (name) =>
	(name || '')
		.split(' ')
		.filter(Boolean)
		.map((n) => n[0])
		.join('')
		.substring(0, 2)
		.toUpperCase()
const userInitials = computed(() => initialsOf(auth.user?.full_name) || 'U')
const userAvatar = computed(
	() => employeeStore.employee?.image || auth.user?.user_image || null
)

// Grouped the way the work actually splits: what you do on shift, what you
// are owed, and everything you only open occasionally.
const baseNavItems = [
	{ to: '/', icon: 'dashboard', label: 'Dashboard', group: 'My work' },
	{ to: '/tasks', icon: 'task_alt', label: 'Tasks', group: 'My work' },
	{ to: '/attendance', icon: 'calendar_today', label: 'Attendance', group: 'My work' },
	{ to: '/roster', icon: 'schedule', label: 'Roster', group: 'My work' },
	{ to: '/leave', icon: 'beach_access', label: 'Leave', group: 'My work' },
	{ to: '/payroll', icon: 'account_balance_wallet', label: 'Payroll', group: 'Pay' },
	{ to: '/expense', icon: 'payments', label: 'Expense', group: 'Pay' },
	{ to: '/issues', icon: 'support_agent', label: 'Issues', group: 'Workspace' },
	{ to: '/team', icon: 'groups', label: 'Team & Permissions', group: 'Workspace' },
	{ to: '/reports', icon: 'analytics', label: 'Reports', group: 'Workspace' },
	{ to: '/settings', icon: 'settings', label: 'Settings', group: 'Workspace' },
]

const navItems = computed(() => {
	const items = baseNavItems.filter((item) => {
		if (item.to === '/team')
			return (
				teamStore.readEmployeePermissionResource.data ||
				teamStore.readUsersPermissionResource.data
			)
		if (item.to === '/reports') return canCreateReports.value
		if (item.to === '/settings') return canAccessSettings.value
		return true
	})
	// UX change by developer: removed /desk route from portal navigation.
	// Do not re-add /desk here; it was removed intentionally to simplify the employee portal experience.
	return items
})

/* The four a staff member reaches for mid-shift. Everything else is behind
   More, which opens the same drawer as the rail — so nothing is unreachable,
   it just is not competing for a thumb. */
const PHONE_NAV = [
	{ to: '/', icon: 'dashboard', label: 'Dashboard', shortLabel: 'Home' },
	{ to: '/attendance', icon: 'calendar_today', label: 'Attendance', shortLabel: 'Attendance' },
	{ to: '/tasks', icon: 'task_alt', label: 'Tasks', shortLabel: 'Tasks' },
	{ to: '/leave', icon: 'beach_access', label: 'Leave', shortLabel: 'Leave' },
]
/* Reuses the sidebar's own permission filter rather than asking again, so
   the menu row and the nav item can never disagree about who may see it. */
const canSeeSettings = computed(() => navItems.value.some((i) => i.to === '/settings'))

const phoneNavItems = computed(() =>
	PHONE_NAV.filter((p) => navItems.value.some((i) => i.to === p.to))
)
const isOnMoreRoute = computed(
	() => !PHONE_NAV.some((p) => (p.to === '/' ? route.path === '/' : route.path.startsWith(p.to)))
)

const navGroups = computed(() =>
	['My work', 'Pay', 'Workspace']
		.map((label) => ({ label, items: navItems.value.filter((i) => i.group === label) }))
		.filter((g) => g.items.length)
)

const currentNavItem = computed(() =>
	navItems.value.find((i) => (i.to === '/' ? route.path === '/' : route.path.startsWith(i.to)))
)

const pageTitle = computed(() => renderLabel(currentNavItem.value?.label) || 'Staff Hub')

/* Group then page, e.g. "My work / Roster". One crumb when the page sits
   outside a group, rather than an empty first segment and a stray slash. */
const breadcrumbs = computed(() => {
	const item = currentNavItem.value
	if (!item) return [{ label: 'Staff Hub' }]
	const label = renderLabel(item.label)
	return item.group ? [{ label: item.group }, { label }] : [{ label }]
})

function onNav(e, item, navigate) {
	if (item.isExternal) return
	navigate(e)
	mobileDrawerOpen.value = false
}

/** Frappe translations when present; the literal otherwise. */
function renderLabel(label) {
	if (!label) return ''
	return window.__ ? window.__(label) : label
}

function toggleDarkMode() {
	isDark.value = !isDark.value
	document.documentElement.classList.toggle('dark', isDark.value)
	localStorage.setItem('portal_theme', isDark.value ? 'dark' : 'light')
}

onMounted(async () => {
	await employeeStore.init()

	try {
		const res = await fetch('/api/method/arijentek_core.api.dashboard.get_all_portal_permissions')
		const json = await res.json()
		if (json.message) {
			const perms = json.message
			attendanceStore.loadPermissions(perms.attendance)
			payrollStore.loadPermissions(perms.payroll)
			tasksStore.loadPermissions(perms.tasks)
			teamStore.loadPermissions(perms.team)
			if (perms.reports) canCreateReports.value = Boolean(perms.reports.can_create_reports)
			if (perms.hr_settings) canAccessSettings.value = Boolean(perms.hr_settings.can_read_hr_settings)
		}
	} catch (err) {
		console.error('Failed to load global portal permissions:', err)
	}

	if (!canCreateReports.value) {
		try {
			const repRes = await fetch('/api/method/arijentek_core.api.reports.can_create_reports')
			canCreateReports.value = Boolean((await repRes.json()).message)
		} catch (e) {
			console.warn('Failed to check report permission', e)
		}
	}

	if (!canAccessSettings.value) {
		try {
			const setRes = await fetch('/api/method/arijentek_core.api.hr_settings.can_read_hr_settings')
			canAccessSettings.value = Boolean((await setRes.json()).message)
		} catch (e) {
			console.warn('Failed to check hr settings permission', e)
		}
	}

	isDark.value = localStorage.getItem('portal_theme') === 'dark'
	document.documentElement.classList.toggle('dark', isDark.value)
	largeText.value = localStorage.getItem('portal_text_large') === '1'
	document.documentElement.classList.toggle('text-large', largeText.value)
})
</script>

<!-- Unscoped on purpose: these rules key off `.dark` on <html>, and inside a
     scoped block Vue rewrites the selector so the dark variant never matches.
     Every class name below is unique to this shell. -->
<style>
/* ===== Dark shell holding a floating light content panel =====
   Same numbers as the POS AppShell (#0B0B11 / #0F0F11 backdrop, 1rem inset,
   26px radius) so the add-on reads as part of the same product. */
.portal-shell {
	display: flex;
	height: 100dvh;
	width: 100%;
	overflow: hidden;
	background: #0b0b11;
}
.dark .portal-shell {
	background: #0f0f11;
}

.portal-panel {
	flex: 1 1 0%;
	display: flex;
	flex-direction: column;
	min-width: 0;
	min-height: 0;
	overflow: hidden;
	background: #fafafc;
}
.dark .portal-panel {
	background: #18181b;
}

/* The inset only earns its space once the rail is beside it. Below lg the rail
   is a drawer, so a floating panel would just be a wasted 32px frame. */
@media (min-width: 1024px) {
	.portal-panel {
		margin: 1rem 1rem 1rem 0;
		border-radius: 26px;
		box-shadow: 0 24px 60px -20px rgba(0, 0, 0, 0.55);
	}
	.dark .portal-panel {
		box-shadow:
			0 0 0 1px rgba(255, 255, 255, 0.06),
			0 24px 60px -20px rgba(0, 0, 0, 0.6);
	}
}

/* Rail sits directly on the shell backdrop — no border, the panel inset is
   what separates them. */
.portal-rail {
	background: transparent;
}
@media (max-width: 1023px) {
	.portal-rail {
		background: #0f0f11;
	}
}

.portal-panel > main::-webkit-scrollbar {
	width: 8px;
}
.portal-panel > main::-webkit-scrollbar-track {
	background: transparent;
}
.portal-panel > main::-webkit-scrollbar-thumb {
	background: rgba(11, 11, 12, 0.15);
	border-radius: 4px;
}
.dark .portal-panel > main::-webkit-scrollbar-thumb {
	background: rgba(255, 255, 255, 0.14);
}

.portal-rail .no-scrollbar::-webkit-scrollbar {
	display: none;
}
.portal-rail .no-scrollbar {
	scrollbar-width: none;
}
</style>
