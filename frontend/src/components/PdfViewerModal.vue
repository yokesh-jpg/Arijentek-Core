<template>
	<Transition name="fade">
		<div
			v-if="activeReport"
			class="fixed inset-0 z-[99999] flex items-center justify-center p-2 sm:p-4 bg-[#0B0B0E]/75 backdrop-blur-sm overflow-hidden"
			@click.self="close"
			@keydown.esc="close"
			role="dialog"
			aria-modal="true"
			:aria-label="activeReport.title"
		>
			<div class="modal-panel w-[96vw] max-w-[1280px] h-[92vh] flex flex-col overflow-hidden shadow-2xl">
				<!-- Header -->
				<header class="modal-header justify-between shrink-0">
					<div class="flex items-center gap-3 min-w-0">
						<div class="w-9 h-9 rounded-xl bg-accent/10 text-accent grid place-items-center shrink-0">
							<span class="material-symbols-outlined !text-[20px]">picture_as_pdf</span>
						</div>
						<div class="min-w-0">
							<h2 class="modal-title truncate">{{ activeReport.title }}</h2>
							<p class="text-[12px] text-[#656A72] dark:text-white/60 truncate">
								Generated {{ formatTime(activeReport.completedAt || activeReport.startedAt) }}
							</p>
						</div>
					</div>

					<div class="flex items-center gap-2 shrink-0">
						<button
							type="button"
							class="btn-secondary !py-1.5 !px-3 text-xs"
							@click="openInNewTab"
							title="Open in new browser tab"
						>
							<span class="material-symbols-outlined !text-[16px]">open_in_new</span>
							<span class="hidden sm:inline">New tab</span>
						</button>
						<button
							type="button"
							class="btn-primary !py-1.5 !px-3 text-xs"
							@click="download"
							title="Download PDF"
						>
							<span class="material-symbols-outlined !text-[16px]">download</span>
							<span class="hidden sm:inline">Download</span>
						</button>
						<button
							type="button"
							class="btn-icon-ghost shrink-0 ml-1"
							aria-label="Close"
							@click="close"
						>
							<span class="material-symbols-outlined !text-[18px]">close</span>
						</button>
					</div>
				</header>

				<!-- PDF Embed Body -->
				<div class="flex-1 bg-[#262626] dark:bg-[#1a1a1a] relative overflow-hidden">
					<iframe
						v-if="activeReport.blobUrl"
						:src="activeReport.blobUrl"
						class="w-full h-full border-0"
						title="PDF Viewer"
					></iframe>
					<div v-else class="absolute inset-0 grid place-items-center text-white/70 text-sm">
						Loading PDF…
					</div>
				</div>
			</div>
		</div>
	</Transition>
</template>

<script setup>
import { computed } from 'vue'
import { useReportNotificationsStore } from '@/stores/reportNotifications.js'

const store = useReportNotificationsStore()
const activeReport = computed(() => store.activeViewerReport)

function close() {
	store.closeViewer()
}

function download() {
	if (activeReport.value) {
		store.downloadPdf(activeReport.value)
	}
}

function openInNewTab() {
	if (activeReport.value && activeReport.value.blobUrl) {
		window.open(activeReport.value.blobUrl, '_blank')
	}
}

function formatTime(date) {
	if (!date) return ''
	const d = new Date(date)
	return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
	transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
	opacity: 0;
}
</style>

