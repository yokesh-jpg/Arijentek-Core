<template>
	<Transition name="fade">
		<div
			v-if="show"
			class="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-[#0B0B0E]/70 backdrop-blur-sm overflow-hidden"
			@click.self="$emit('close')"
			@keydown.esc="$emit('close')"
			role="dialog"
			aria-modal="true"
			:aria-label="title"
		>
			<div class="modal-panel max-h-[94vh] flex flex-col" :class="extraWide ? 'max-w-[96vw] 2xl:max-w-[1460px]' : wide ? 'max-w-[1200px]' : 'max-w-[980px]'">
				<header class="modal-header">
					<div class="min-w-0">
						<!-- The icon tile that led every one of these headers repeated
						     the title in picture form and carried nothing else. -->
						<h2 class="modal-title truncate">{{ title }}</h2>
						<p v-if="subtitle" class="text-[12px] text-[#656A72] dark:text-white/60">{{ subtitle }}</p>
					</div>
					<button @click="$emit('close')" class="btn-icon-ghost shrink-0" aria-label="Close">
						<span class="material-symbols-outlined !text-[18px]">close</span>
					</button>
				</header>

				<!-- Filters sit directly on the panel. A tinted strip here was a
				     second surface between the header rule and the table. -->
				<div v-if="$slots.filters" class="px-5 py-4 border-b border-black/[0.06] dark:border-white/[0.08] shrink-0">
					<slot name="filters" />
				</div>

				<div v-if="$slots.legend" class="px-5 py-2.5 border-b border-black/[0.06] dark:border-white/[0.08] shrink-0 flex flex-wrap items-center gap-x-4 gap-y-1.5">
					<slot name="legend" />
				</div>

				<!-- The min-height keeps a short report from collapsing to a sliver
				     on desktop, but on a phone it stopped the body shrinking and
				     pushed the export buttons off the bottom of the screen. -->
				<div class="flex-1 overflow-auto relative sm:min-h-[320px] table-scroll">
					<div v-if="loading" class="absolute inset-0 z-10 grid place-items-center bg-white/75 dark:bg-surface-1/75 backdrop-blur-[2px]">
						<div class="flex flex-col items-center gap-3">
							<span class="w-5 h-5 rounded-full border-2 border-black/10 dark:border-white/15 border-t-accent animate-spin"></span>
							<span class="text-[13px] text-[#5C6169] dark:text-white/65">Loading report…</span>
						</div>
					</div>

					<div v-if="empty && !loading" class="empty-state !py-20">
						<span class="material-symbols-outlined !text-[28px] text-[#C4C7CC] dark:text-white/25">{{ emptyIcon }}</span>
						<p class="empty-state-text">{{ emptyTitle }}</p>
						<p v-if="emptyText" class="text-[12px] text-[#656A72] dark:text-white/55 max-w-sm">{{ emptyText }}</p>
						<slot name="empty-action" />
					</div>

					<slot v-else />
				</div>

				<footer class="modal-footer justify-between">
					<!-- The row count is the one thing worth stating here: it tells you
					     what the export will contain before you trigger it. -->
					<p class="text-[12px] text-[#656A72] dark:text-white/60 tabular-nums">
						{{ count }} {{ count === 1 ? unit : unitPlural }}
					</p>
					<div class="flex items-center gap-2">
						<slot name="actions" />
						<button class="btn-secondary" @click="$emit('close')">Close</button>
						<button class="btn-secondary" :disabled="!count" @click="$emit('export-excel')">
							<span class="material-symbols-outlined !text-[18px]">table_view</span>
							<span class="hidden sm:inline">Excel</span>
						</button>
						<!-- Export was a red button. Red is the destructive colour
						     everywhere else in this app; downloading a report is the
						     opposite of destructive. -->
						<button class="btn-primary" :disabled="!count" @click="$emit('export-pdf')">
							<span class="material-symbols-outlined !text-[18px]">picture_as_pdf</span>
							<span class="hidden sm:inline">PDF</span>
						</button>
					</div>
				</footer>
			</div>
		</div>
	</Transition>
</template>

<script setup>
/* All 22 report dialogs were the same shell written out 22 times - overlay,
   header with an icon tile, filter strip, loading overlay, table, empty state,
   footer with a record count and two export buttons. They had drifted apart in
   padding, header casing, empty-state wording and button colour. One shell so
   they cannot drift again; each report supplies only its filters and body. */
defineProps({
	show: { type: Boolean, default: false },
	title: { type: String, required: true },
	subtitle: { type: String, default: '' },
	loading: { type: Boolean, default: false },
	empty: { type: Boolean, default: false },
	emptyIcon: { type: String, default: 'inbox' },
	emptyTitle: { type: String, default: 'Nothing to show' },
	emptyText: { type: String, default: '' },
	/* Drives the footer line and disables both exports at zero. */
	count: { type: Number, default: 0 },
	unit: { type: String, default: 'record' },
	unitPlural: { type: String, default: 'records' },
	wide: { type: Boolean, default: false },
	extraWide: { type: Boolean, default: false },
})

defineEmits(['close', 'export-excel', 'export-pdf'])
</script>
