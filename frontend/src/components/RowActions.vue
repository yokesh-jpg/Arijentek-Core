<template>
	<div class="inline-flex items-center justify-end gap-0.5">
		<!-- One or two actions do not need hiding behind a click, so they sit on
		     the row as icons. -->
		<button
			v-for="(a, i) in inlineActions"
			:key="'inline-' + i"
			type="button"
			:class="a.danger ? 'btn-danger-ghost' : 'btn-icon-ghost'"
			:disabled="a.disabled"
			:title="a.label"
			:aria-label="a.label"
			@click.stop="run(a)"
		>
			<span class="material-symbols-outlined !text-[18px]">{{ a.icon || 'more_horiz' }}</span>
		</button>

		<button
			v-if="menuActions.length"
			ref="triggerEl"
			type="button"
			class="row-actions-btn"
			:class="open && 'row-actions-btn-open'"
			:aria-expanded="open"
			aria-haspopup="menu"
			aria-label="More actions"
			@click.stop="toggle"
		>
			<span>More</span>
			<span class="material-symbols-outlined !text-[16px] transition-transform" :class="open && 'rotate-180'">expand_more</span>
		</button>

		<!-- Teleported to the body: the menu used to be absolutely positioned
		     inside the cell, so in any list that scrolls sideways it was clipped
		     by the table's own overflow, and in the last rows it had to be
		     flipped by hand with a row-index hack. -->
		<Teleport to="body">
			<div
				v-if="open"
				ref="popEl"
				data-lt-zoom
				:style="popStyle"
				class="pointer-events-auto fixed z-[200] w-48 py-1.5 bg-white dark:bg-surface-1 border border-black/[0.07] dark:border-white/10 rounded-[12px] shadow-xl text-left"
				role="menu"
				@click.stop
				@pointerdown.stop
				@mousedown.stop
				@keydown.esc.stop="close"
			>
				<template v-for="(a, i) in menuActions" :key="i">
					<div v-if="a.divider" class="menu-divider"></div>
					<button
						v-else
						type="button"
						role="menuitem"
						class="menu-row"
						:class="a.danger && '!text-red-600 dark:!text-red-400'"
						:disabled="a.disabled"
						@click="run(a)"
					>
						<span v-if="a.icon" class="material-symbols-outlined !text-[18px] shrink-0 mt-0.5" :class="!a.danger && 'menu-icon'">{{ a.icon }}</span>
						<span class="min-w-0">{{ a.label }}</span>
					</button>
				</template>
			</div>
		</Teleport>
	</div>
</template>

<script setup>
/* Every list in the Staff Hub had its own Actions column: some a bare ⋮ that
   gave no clue what it held, some a pair of icon buttons that put delete one
   mis-click from edit, and the two kinds sat on adjacent tabs of the same
   page. One labelled control for all of them, with the row's actions named
   inside rather than guessed from an icon. */
import { ref, computed, onBeforeUnmount, nextTick, watch } from 'vue'

const props = defineProps({
	/* [{ label, icon, danger, disabled, divider, onClick }] - entries whose
	   `show` is explicitly false are dropped, so callers can pass permission
	   flags straight through. */
	actions: { type: Array, default: () => [] },
	/* How many actions sit on the row before the rest fold into More.
	   Default 1: two or more actions all go behind More, so a row never
	   shows a pair of icon buttons (delete is one mis-click from edit). */
	maxInline: { type: Number, default: 1 },
})

const open = ref(false)
const triggerEl = ref(null)
const popEl = ref(null)
const popStyle = ref({})

/* `show` is evaluated per row, so the same table has rows with five actions
   and rows with two. The split below is therefore decided per row, not per
   list - one list can show icons on some rows and More on others. */
const visibleActions = computed(() => props.actions.filter((a) => a && a.show !== false && !a.divider))

/* More than maxInline actions crowd a row, so they all go behind More.
   A More holding a single item is a click in front of nothing. */
const useMenu = computed(() => visibleActions.value.length > props.maxInline)

const inlineActions = computed(() => (useMenu.value ? [] : visibleActions.value))

const menuActions = computed(() => {
	if (!useMenu.value) return []
	const wanted = props.actions.filter((a) => a && a.show !== false)
	/* A divider that ends up first or last, or next to another, is a rule with
	   nothing to separate. */
	return wanted.filter((a, i) => {
		if (!a.divider) return true
		if (i === 0 || i === wanted.length - 1) return false
		return !wanted[i - 1]?.divider
	})
})

const GAP = 6
const EDGE = 8

function place() {
	const t = triggerEl.value
	if (!t) return
	const r = t.getBoundingClientRect()
	const p = popEl.value?.getBoundingClientRect()
	const W = p?.width || 192
	const H = p?.height || 160
	const roomBelow = window.innerHeight - r.bottom - GAP - EDGE
	const roomAbove = r.top - GAP - EDGE
	let top
	if (H <= roomBelow) top = r.bottom + GAP
	else if (H <= roomAbove) top = r.top - GAP - H
	else if (roomBelow >= roomAbove) top = r.bottom + GAP
	else top = Math.max(EDGE, window.innerHeight - EDGE - H)
	top = Math.max(EDGE, Math.min(top, window.innerHeight - EDGE - H))
	/* Right-aligned to the trigger, since the Actions column is last. */
	const left = Math.max(EDGE, Math.min(r.right - W, window.innerWidth - W - EDGE))
	{
		// Large text mode zooms the panel; fixed offsets are in its own units.
		const z = parseFloat(getComputedStyle(popEl.value || document.body).zoom) || 1
		popStyle.value = { top: `${top / z}px`, left: `${left / z}px` }
	}
}

function onDocDown(e) {
	if (triggerEl.value?.contains(e.target)) return
	if (popEl.value?.contains(e.target)) return
	close()
}

function onReflow() {
	/* Scrolling the table or the page moves the row out from under a menu
	   that is fixed to the viewport, so it closes rather than detaching. */
	close()
}

function toggle() {
	open.value ? close() : openMenu()
}

async function openMenu() {
	open.value = true
	await nextTick()
	place()
	document.addEventListener('pointerdown', onDocDown, true)
	window.addEventListener('scroll', onReflow, true)
	window.addEventListener('resize', onReflow)
}

function close() {
	if (!open.value) return
	open.value = false
	document.removeEventListener('pointerdown', onDocDown, true)
	window.removeEventListener('scroll', onReflow, true)
	window.removeEventListener('resize', onReflow)
}

function run(a) {
	if (a.disabled) return
	close()
	a.onClick?.()
}

/* A row can be removed while its menu is open. */
watch(menuActions, (list) => {
	if (open.value && !list.length) close()
})

onBeforeUnmount(close)

defineExpose({ close })
</script>
