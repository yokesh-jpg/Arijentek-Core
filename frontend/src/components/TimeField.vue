<template>
	<div class="relative">
		<button
			ref="triggerEl"
			type="button"
			:id="id"
			:disabled="disabled"
			:aria-label="ariaLabel"
			:aria-expanded="open"
			aria-haspopup="dialog"
			class="field-input flex items-center gap-2 text-left disabled:opacity-40 disabled:cursor-not-allowed"
			:class="[ open ? 'bg-white dark:bg-white/[0.09] !border-accent/40' : '', invalid ? '!border-red-400 dark:!border-red-500/60' : '', ]"
			@click="toggle"
			@keydown.down.prevent="openPicker"
		>
			<span class="flex-1 truncate tabular-nums" :class="modelValue ? '' : 'text-[#656A72] dark:text-white/60'">
				{{ modelValue ? displayValue : placeholder }}
			</span>
			<span class="material-symbols-outlined !text-[18px] text-[#656A72] dark:text-white/60 shrink-0">schedule</span>
		</button>

		<!-- Fixed and teleported for the same reason as the date popover: these
		     sit inside dialogs and table cards that clip their overflow. -->
		<Teleport to="body">
			<div
				v-if="open"
				ref="popEl"
				data-lt-zoom
				role="dialog"
				:aria-label="ariaLabel || 'Choose a time'"
				class="pointer-events-auto fixed z-[200] w-[196px] rounded-[16px] bg-white dark:bg-surface-1 border border-black/[0.07] dark:border-white/10 shadow-[0_28px_70px_-24px_rgba(0,0,0,.45)] overflow-hidden"
				:style="popStyle"
				@pointerdown.stop
				@mousedown.stop
			>
				<div class="grid grid-cols-2 divide-x divide-black/[0.06] dark:divide-white/[0.08]">
					<div>
						<p class="h-8 grid place-items-center text-xs font-medium text-[#656A72] dark:text-white/55 border-b border-black/[0.06] dark:border-white/[0.08]">
							Hour
						</p>
						<div ref="hourList" class="h-[196px] overflow-y-auto no-scrollbar p-1.5 space-y-0.5">
							<button
								v-for="h in hours"
								:key="h"
								type="button"
								:data-sel="h === selHour ? '1' : null"
								class="w-full h-9 rounded-[10px] text-[13px] tabular-nums transition-colors"
								:class="h === selHour ? 'bg-accent text-white font-semibold' : 'text-[#17181B] dark:text-white hover:bg-accent/[0.08]'"
								@click="setHour(h)"
							>
								{{ pad(h) }}
							</button>
						</div>
					</div>
					<div>
						<p class="h-8 grid place-items-center text-xs font-medium text-[#656A72] dark:text-white/55 border-b border-black/[0.06] dark:border-white/[0.08]">
							Minute
						</p>
						<div ref="minList" class="h-[196px] overflow-y-auto no-scrollbar p-1.5 space-y-0.5">
							<button
								v-for="m in minutes"
								:key="m"
								type="button"
								:data-sel="m === selMinute ? '1' : null"
								class="w-full h-9 rounded-[10px] text-[13px] tabular-nums transition-colors"
								:class="m === selMinute ? 'bg-accent text-white font-semibold' : 'text-[#17181B] dark:text-white hover:bg-accent/[0.08]'"
								@click="setMinute(m)"
							>
								{{ pad(m) }}
							</button>
						</div>
					</div>
				</div>

				<div class="flex items-center justify-between gap-2 px-2 py-2 border-t border-black/[0.06] dark:border-white/[0.08]">
					<button
						type="button"
						class="h-8 px-2.5 rounded-[12px] text-xs font-medium text-[#5C6169] dark:text-white/65 hover:text-accent hover:bg-accent/[0.08] transition-colors"
						@click="clear"
					>
						Clear
					</button>
					<button
						type="button"
						class="h-8 px-2.5 rounded-[12px] text-xs font-medium text-accent dark:text-accent-light hover:bg-accent/[0.08] transition-colors"
						@click="setNow"
					>
						Now
					</button>
				</div>
			</div>
		</Teleport>
	</div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'

const props = defineProps({
	/* 'HH:MM', the same string a native <input type="time"> holds. */
	modelValue: { type: String, default: '' },
	placeholder: { type: String, default: 'Select a time' },
	/* Minutes between options. A value off the step is still offered, so an
	   existing 09:07 does not silently become 09:05. */
	step: { type: Number, default: 5 },
	disabled: { type: Boolean, default: false },
	invalid: { type: Boolean, default: false },
	id: { type: String, default: '' },
	ariaLabel: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue', 'change'])

const pad = (n) => String(n).padStart(2, '0')
const parse = (s) => {
	const m = /^(\d{1,2}):(\d{2})/.exec(s || '')
	if (!m) return null
	const h = Number(m[1])
	const mi = Number(m[2])
	if (h > 23 || mi > 59) return null
	return { h, m: mi }
}

const open = ref(false)
const triggerEl = ref(null)
const popEl = ref(null)
const hourList = ref(null)
const minList = ref(null)
const popStyle = ref({})

const parsed = computed(() => parse(props.modelValue))
const selHour = computed(() => parsed.value?.h ?? null)
const selMinute = computed(() => parsed.value?.m ?? null)

const displayValue = computed(() => (parsed.value ? `${pad(parsed.value.h)}:${pad(parsed.value.m)}` : ''))

const hours = Array.from({ length: 24 }, (_, i) => i)

const minutes = computed(() => {
	const step = props.step > 0 && props.step <= 30 ? props.step : 5
	const out = []
	for (let m = 0; m < 60; m += step) out.push(m)
	const cur = selMinute.value
	if (cur !== null && !out.includes(cur)) out.push(cur)
	return out.sort((a, b) => a - b)
})

function place() {
	const t = triggerEl.value
	if (!t) return
	const r = t.getBoundingClientRect()
	/* Measured rather than hard-coded - see the note on DateField.place().
	   A guessed height makes the flip decision wrong in both directions. */
	const p = popEl.value?.getBoundingClientRect()
	const W = p?.width || 196
	const H = p?.height || 280

	const GAP = 6
	const EDGE = 8
	const roomBelow = window.innerHeight - r.bottom - GAP - EDGE
	const roomAbove = r.top - GAP - EDGE

	let top
	if (H <= roomBelow) top = r.bottom + GAP
	else if (H <= roomAbove) top = r.top - GAP - H
	else if (roomBelow >= roomAbove) top = r.bottom + GAP
	else top = Math.max(EDGE, window.innerHeight - EDGE - H)

	top = Math.max(EDGE, Math.min(top, window.innerHeight - EDGE - H))
	const left = Math.max(EDGE, Math.min(r.left, window.innerWidth - W - EDGE))
	{
		// Large text mode zooms the panel; fixed offsets are in its own units.
		const z = parseFloat(getComputedStyle(popEl.value || document.body).zoom) || 1
		popStyle.value = { top: `${top / z}px`, left: `${left / z}px` }
	}
}

function scrollToSelected() {
	for (const list of [hourList.value, minList.value]) {
		const el = list?.querySelector('[data-sel]')
		if (el) list.scrollTop = el.offsetTop - list.clientHeight / 2 + el.offsetHeight / 2
	}
}

function onDocDown(e) {
	if (triggerEl.value?.contains(e.target) || popEl.value?.contains(e.target)) return
	/* A teleported menu opened from inside this panel has no DOM link back to
	   it - see the note on DateField.onDocDown. */
	if (e.target instanceof Element && e.target.closest('.select-menu-pop')) return
	close()
}
function onKey(e) {
	if (e.key === 'Escape') close()
}

function openPicker() {
	if (props.disabled) return
	open.value = true
}
function close() {
	open.value = false
}
function toggle() {
	open.value ? close() : openPicker()
}

watch(open, async (isOpen) => {
	if (isOpen) {
		await nextTick()
		place()
		scrollToSelected()
		document.addEventListener('mousedown', onDocDown, true)
		document.addEventListener('keydown', onKey, true)
		window.addEventListener('resize', place)
		window.addEventListener('scroll', place, true)
	} else {
		document.removeEventListener('mousedown', onDocDown, true)
		document.removeEventListener('keydown', onKey, true)
		window.removeEventListener('resize', place)
		window.removeEventListener('scroll', place, true)
	}
})

onBeforeUnmount(() => {
	document.removeEventListener('mousedown', onDocDown, true)
	document.removeEventListener('keydown', onKey, true)
	window.removeEventListener('resize', place)
	window.removeEventListener('scroll', place, true)
})

function commit(value) {
	emit('update:modelValue', value)
	emit('change', value)
}

/* Picking an hour on an empty field should give you a usable time rather than
   nothing, so the other half falls back to zero. The popover stays open until
   both halves have been chosen once. */
function setHour(h) {
	commit(`${pad(h)}:${pad(selMinute.value ?? 0)}`)
}
function setMinute(m) {
	commit(`${pad(selHour.value ?? 0)}:${pad(m)}`)
	close()
}
function setNow() {
	const d = new Date()
	const step = props.step > 0 ? props.step : 5
	const m = Math.round(d.getMinutes() / step) * step
	const carry = m === 60
	commit(`${pad((d.getHours() + (carry ? 1 : 0)) % 24)}:${pad(carry ? 0 : m)}`)
	close()
}
function clear() {
	commit('')
	close()
}
</script>
