<template>
	<div class="tab-strip relative">
		<!-- Below sm: one button that names the current tab, opening a menu of
		     all of them. Team has twelve tabs; on a phone only four fit, so a
		     scrolling strip means guessing that it scrolls and then swiping
		     eight times. This is one tap. -->
		<div class="sm:hidden">
			<button
				ref="trigger"
				type="button"
				class="tab-switch"
				:aria-expanded="open"
				aria-haspopup="menu"
				@click.stop="open = !open"
			>
				<span class="tab-switch-label truncate">{{ activeLabel || 'Select a tab' }}</span>
				<span class="material-symbols-outlined !text-[18px] shrink-0 text-[#5C6169] dark:text-white/60 transition-transform" :class="{ 'rotate-180': open }">expand_more</span>
				<span v-if="items.length > 1" class="ml-auto shrink-0 text-xs font-medium text-[#5C6169] dark:text-white/55 tabular-nums">
					{{ activeIndex + 1 }}/{{ items.length }}
				</span>
			</button>

			<div v-if="open" ref="menu" class="tab-menu" role="menu">
				<button
					v-for="item in items"
					:key="item.i"
					type="button"
					role="menuitem"
					class="tab-menu-row"
					:class="{ 'tab-menu-row-active': item.active }"
					@click="pick(item.i)"
				>
					<span class="truncate">{{ item.label }}</span>
					<span v-if="item.active" class="material-symbols-outlined !text-[16px] ml-auto shrink-0">check</span>
				</button>
			</div>
		</div>

		<!-- sm and up: the strip as before, but the scrolling is now visible.
		     The arrows sit over the ends and carry the fade themselves, so the
		     strip keeps its full width and its bottom border runs unbroken. -->
		<div class="hidden sm:block relative">
			<div ref="strip" class="tab-bar" @scroll.passive="measure">
				<slot />
			</div>

			<button
				v-show="canLeft"
				type="button"
				class="tab-nudge left-0 tab-nudge-left"
				aria-label="Scroll tabs left"
				@click="nudge(-1)"
			>
				<span class="material-symbols-outlined !text-[20px]">chevron_left</span>
			</button>
			<button
				v-show="canRight"
				type="button"
				class="tab-nudge right-0 tab-nudge-right"
				aria-label="Scroll tabs right"
				@click="nudge(1)"
			>
				<span class="material-symbols-outlined !text-[20px]">chevron_right</span>
			</button>
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'

/* The tabs stay in the parent's markup. Each page guards its tabs with its own
   permission checks and click handlers, and lifting all of that into props
   would mean rewriting seven views to gain nothing. The buttons in the slot
   are the source of truth: this component reads their labels and active state
   from the DOM and, for the phone menu, clicks the real button. */
const strip = ref(null)
const menu = ref(null)
const trigger = ref(null)

const canLeft = ref(false)
const canRight = ref(false)
const open = ref(false)
const items = ref([])
const activeLabel = ref('')
const activeIndex = ref(0)

function tabEls() {
	if (!strip.value) return []
	return [...strip.value.querySelectorAll('.tab-item')]
}

function readTabs() {
	const els = tabEls()
	items.value = els.map((el, i) => ({
		i,
		label: (el.querySelector('.tab-label') || el).textContent.trim(),
		active: el.classList.contains('tab-item-active'),
	}))
	const active = items.value.find((t) => t.active)
	activeLabel.value = active ? active.label : items.value[0]?.label || ''
	activeIndex.value = active ? active.i : 0
}

function measure() {
	const el = strip.value
	if (!el) return
	/* A 1px tolerance: sub-pixel layout can leave scrollWidth a hair over
	   clientWidth on a strip that actually fits, which would strand an arrow
	   on screen with nothing to scroll to. */
	canLeft.value = el.scrollLeft > 1
	canRight.value = el.scrollLeft < el.scrollWidth - el.clientWidth - 1
}

function nudge(dir) {
	const el = strip.value
	if (!el) return
	el.scrollBy({ left: dir * Math.max(160, el.clientWidth * 0.7), behavior: 'smooth' })
}

/* Landing on a page whose selected tab is scrolled out of sight is the thing
   that makes the strip feel broken, so the active tab is pulled into view
   whenever it changes. */
function revealActive() {
	const el = strip.value
	if (!el) return
	const active = el.querySelector('.tab-item-active')
	if (!active) return
	/* Measured from the strip's own edge, and kept clear of the 36px arrow
	   that sits over each end - offsetLeft alone counted from the wrapper,
	   which left the first tab parked a few pixels under the left arrow. The first
	   tab scrolls the strip fully home, so no arrow shows at all. */
	const CLEAR = 40
	/* offsetLeft, not getBoundingClientRect: rects come back scaled by the
	   large-text zoom while scrollLeft does not. Both offsets share the
	   wrapper as their offsetParent, so the difference is the tab's position
	   inside the strip's scroll area. */
	const left = active.offsetLeft - el.offsetLeft - el.clientLeft
	const right = left + active.offsetWidth
	if (active === el.querySelector('.tab-item')) el.scrollTo({ left: 0, behavior: 'smooth' })
	else if (left - CLEAR < el.scrollLeft) el.scrollTo({ left: Math.max(0, left - CLEAR), behavior: 'smooth' })
	else if (right + CLEAR > el.scrollLeft + el.clientWidth) el.scrollTo({ left: right - el.clientWidth + CLEAR, behavior: 'smooth' })
}

function pick(i) {
	const el = tabEls()[i]
	open.value = false
	if (el) el.click()
}

function refresh() {
	readTabs()
	measure()
	revealActive()
}

let ro
let mo
function onDocClick(e) {
	if (!open.value) return
	if (menu.value?.contains(e.target) || trigger.value?.contains(e.target)) return
	open.value = false
}
function onKey(e) {
	if (e.key === 'Escape') open.value = false
}

onMounted(async () => {
	await nextTick()
	refresh()

	if (typeof ResizeObserver !== 'undefined') {
		ro = new ResizeObserver(() => {
			measure()
			revealActive()
		})
		if (strip.value) ro.observe(strip.value)
	}

	/* The parent swaps tab-item-active and may add or remove tabs as
	   permissions resolve, so watch the strip rather than taking one reading
	   at mount. */
	mo = new MutationObserver(() => refresh())
	if (strip.value) mo.observe(strip.value, { subtree: true, childList: true, attributes: true, attributeFilter: ['class'] })

	window.addEventListener('click', onDocClick)
	window.addEventListener('keydown', onKey)
})

onUnmounted(() => {
	ro?.disconnect()
	mo?.disconnect()
	window.removeEventListener('click', onDocClick)
	window.removeEventListener('keydown', onKey)
})
</script>
