<template>
	<div class="relative">
		<!-- Typeable. It reads DD-MM-YYYY at rest and while typing, and its
		     mask refuses a day the month does not have
		     and a month past 12. The calendar still opens alongside it. -->
		<div
			ref="triggerEl"
			class="flex items-center gap-2"
			:class="[ inputClass || DEFAULT_TRIGGER, open || focused ? OPEN_CLASS : '', showInvalid ? '!border-red-400 dark:!border-red-500/60' : '', disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-text', ]"
			@click="onWrapClick"
		>
			<input
				ref="inputEl"
				:id="id"
				type="text"
				inputmode="numeric"
				autocomplete="off"
				:size="withTime ? 16 : 12"
				:disabled="disabled"
				:aria-label="ariaLabel || 'Date'"
				:aria-invalid="showInvalid"
				:placeholder="focused ? (withTime ? 'DD-MM-YYYY HH:MM' : 'DD-MM-YYYY') : placeholder"
				:value="inputText"
				class="flex-1 min-w-0 w-full p-0 m-0 bg-transparent border-0 shadow-none outline-none ring-0 focus:ring-0 focus:outline-none tabular-nums truncate placeholder:text-[#656A72] dark:placeholder:text-white/60 disabled:cursor-not-allowed"
				style="font: inherit; color: inherit; letter-spacing: inherit"
				@focus="onFocus"
				@blur="onBlur"
				@input="onInput"
				@keydown="onKeydown"
				@beforeinput="onBeforeInput"
				@click="onInputClick"
			/>
			<button
				type="button"
				tabindex="-1"
				:disabled="disabled"
				:aria-label="open ? 'Close calendar' : 'Open calendar'"
				:aria-expanded="open"
				aria-haspopup="dialog"
				class="material-symbols-outlined !text-[18px] leading-none text-[#656A72] dark:text-white/60 hover:text-accent shrink-0 disabled:cursor-not-allowed"
				@click.stop="onIconClick"
			>{{ icon }}</button>
		</div>

		<!-- Fixed, not absolute: these sit inside dialogs and table cards that
		     clip their overflow, where an absolute popover is cut in half.

		     pointer-events-auto is load-bearing, not redundant. frappe-ui's
		     Dialog makes the background inert with an inline
		     `pointer-events: none` on <body>, and this panel is teleported to
		     <body>, so it inherits that and every click passes straight
		     through it: the calendar paints, the click lands on whatever is
		     underneath, and the outside-click handler then closes it. The
		     symptom is "the date will not change" plus a stray control being
		     toggled somewhere else on the form.

		     @pointerdown.stop / @mousedown.stop are the second half of the
		     same problem. frappe-ui's Dialog is a Reka dismissable layer: it
		     closes when a pointerdown lands outside its content, and a panel
		     teleported to <body> is outside. Without these, picking a date
		     shut the whole form. Our own outside-click handler listens on
		     document in the CAPTURE phase, so it still runs and clicking away
		     from the calendar still closes it. -->
		<Teleport to="body">
			<div
				v-if="open"
				ref="popEl"
				data-lt-zoom
				role="dialog"
				:aria-label="ariaLabel || 'Choose a date'"
				class="pointer-events-auto fixed z-[200] p-3 rounded-[16px] bg-white dark:bg-surface-1 border border-black/[0.07] dark:border-white/10 shadow-[0_28px_70px_-24px_rgba(0,0,0,.45)]"
				:class="$slots.side ? 'flex gap-3' : 'w-[292px]'"
				:style="popStyle"
				@keydown.esc.stop="close"
				@pointerdown.stop
				@mousedown.stop
			>
				<div class="w-[266px] shrink-0">
				<div class="flex items-center justify-between gap-2 mb-2">
					<div class="flex items-center gap-1 min-w-0">
						<div class="relative">
							<SelectField v-model="viewMonth" :options="monthOptions" :block="false" :trigger-class="CAL_SELECT" aria-label="Month" />
						</div>
						<div class="relative">
							<SelectField v-model="viewYear" :options="yearSelectOptions" :block="false" :trigger-class="CAL_SELECT" aria-label="Year" />
						</div>
					</div>
					<div class="flex items-center gap-0.5 shrink-0">
						<button type="button" :class="ICON_BTN" aria-label="Previous month" @click="step(-1)">
							<span class="material-symbols-outlined !text-[18px]">chevron_left</span>
						</button>
						<button type="button" :class="ICON_BTN" aria-label="Next month" @click="step(1)">
							<span class="material-symbols-outlined !text-[18px]">chevron_right</span>
						</button>
					</div>
				</div>

				<div class="grid grid-cols-7 gap-0.5 mb-1">
					<div v-for="d in SHORT_WEEKDAYS" :key="d" class="h-7 grid place-items-center text-xs font-medium text-[#656A72] dark:text-white/55">
						{{ d }}
					</div>
				</div>

				<div class="grid grid-cols-7 gap-0.5">
					<button
						v-for="day in days"
						:key="day.date"
						type="button"
						:disabled="day.disabled"
						class="h-9 rounded-[10px] text-[13px] tabular-nums transition-colors"
						:class="dayClass(day)"
						:aria-current="day.isToday ? 'date' : undefined"
						:aria-pressed="day.date === modelValue"
						@click="pick(day)"
					>
						{{ day.num }}
					</button>
				</div>

				<div class="flex items-center justify-between gap-2 mt-2 pt-2 border-t border-black/[0.06] dark:border-white/[0.08]">
					<button type="button" class="h-8 px-2.5 rounded-[12px] text-xs font-medium text-[#5C6169] dark:text-white/65 hover:text-accent hover:bg-accent/[0.08] transition-colors" @click="clear">
						Clear
					</button>
					<button type="button" class="h-8 px-2.5 rounded-[12px] text-xs font-medium text-accent dark:text-accent-light hover:bg-accent/[0.08] transition-colors" @click="pickToday">
						Today
					</button>
				</div>
				</div>
				<!-- A combined field (DateTimeField) puts its time columns here, so
				     date and time are picked in one panel. -->
				<slot name="side" />
			</div>
		</Teleport>
	</div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import SelectField from './SelectField.vue'

/* Style hooks. The Zevar POS copy of this file swaps these for inlined
   classes, since the POS has no .field-input / .cal-select / .btn-icon-ghost. */
const DEFAULT_TRIGGER = 'field-input'
const CAL_SELECT = 'cal-select !h-8 !text-xs'
const ICON_BTN = 'btn-icon-ghost !w-8 !h-8'
const OPEN_CLASS = 'bg-white dark:bg-white/[0.09] !border-accent/40'

const props = defineProps({
	modelValue: { type: String, default: '' },
	placeholder: { type: String, default: 'Select a date' },
	min: { type: String, default: '' },
	max: { type: String, default: '' },
	disabled: { type: Boolean, default: false },
	/* The forms flagged a bad value by swapping the input's border colour.
	   The border lives on the trigger here, so it comes in as a flag. */
	invalid: { type: Boolean, default: false },
	id: { type: String, default: '' },
	ariaLabel: { type: String, default: '' },
	/* Overrides the trigger text (a combined date-and-time label). */
	display: { type: String, default: '' },
	icon: { type: String, default: 'calendar_today' },
	/* Keep the panel open after a day is picked, for a time still to choose. */
	closeOnPick: { type: Boolean, default: true },
	/* The trigger's look. Each POS form styled its native date input its own
	   way, so the replacement takes that same class string. */
	inputClass: { type: String, default: '' },
	/* Date-and-time mode (DateTimeField): the typed text grows an HH:MM part,
	   edited the same way, and changes to it come out as update:time. */
	withTime: { type: Boolean, default: false },
	time: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue', 'change', 'update:time'])

const MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
const SHORT_WEEKDAYS = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']

/* Local calendar date. toISOString() converts to UTC first, so east of UTC it
   names the previous day. */
const ymd = (d) => [d.getFullYear(), String(d.getMonth() + 1).padStart(2, '0'), String(d.getDate()).padStart(2, '0')].join('-')
/* A 'YYYY-MM-DD' string parsed as local midnight rather than as UTC. */
const parse = (s) => (/^\d{4}-\d{2}-\d{2}$/.test(s || '') ? new Date(s + 'T00:00:00') : null)

const todayKey = ymd(new Date())

const open = ref(false)
const inputEl = ref(null)
const triggerEl = ref(null)
const popEl = ref(null)
const popStyle = ref({})

const anchor = computed(() => parse(props.modelValue) || parse(props.min) || new Date())
const viewYear = ref(anchor.value.getFullYear())
const viewMonth = ref(anchor.value.getMonth())

const yearOptions = computed(() => {
	const base = viewYear.value
	const minBound = props.min ? Number(props.min.slice(0, 4)) : base - 8
	const maxBound = props.max ? Number(props.max.slice(0, 4)) : base + 8
	const start = Math.min(minBound, base)
	const end = Math.max(maxBound, base)
	const out = []
	for (let y = props.min ? Math.max(minBound, start) : start; y <= (props.max ? Math.min(maxBound, end) : end); y++) out.push(y)
	return out
})

const monthOptions = MONTH_NAMES.map((m, i) => ({ label: m, value: i }))
const yearSelectOptions = computed(() => yearOptions.value.map((y) => ({ label: String(y), value: y })))

/* DD-MM-YYYY at rest too, the same order the field is typed in, so the
   text does not change shape when the field is clicked. */
const displayValue = computed(() => {
	const d = parse(props.modelValue)
	if (!d) return ''
	return [String(d.getDate()).padStart(2, '0'), String(d.getMonth() + 1).padStart(2, '0'), d.getFullYear()].join('-')
})

/* Six weeks, always — a grid that changes height makes the popover jump as you
   page through the months. */
const days = computed(() => {
	const first = new Date(viewYear.value, viewMonth.value, 1)
	const start = new Date(first)
	start.setDate(1 - first.getDay())
	const out = []
	for (let i = 0; i < 42; i++) {
		const d = new Date(start)
		d.setDate(start.getDate() + i)
		const key = ymd(d)
		out.push({
			date: key,
			num: d.getDate(),
			inMonth: d.getMonth() === viewMonth.value,
			isToday: key === todayKey,
			/* Boolean(), not the bare expression: with no min/max this evaluates
			   to '', and Vue treats an empty string on a boolean attribute as
			   true - which disabled every day in the grid. */
			disabled: Boolean((props.min && key < props.min) || (props.max && key > props.max)),
		})
	}
	return out
})

function dayClass(day) {
	if (day.date === props.modelValue) return 'bg-accent text-white font-semibold'
	if (day.disabled) return 'text-[#C4C7CC] dark:text-white/15 cursor-not-allowed'
	if (!day.inMonth) return 'text-[#C4C7CC] dark:text-white/20 hover:bg-black/[0.03] dark:hover:bg-white/[0.06]'
	if (day.isToday) return 'text-accent dark:text-accent-light font-semibold ring-1 ring-inset ring-accent/40 hover:bg-accent/[0.08]'
	return 'text-[#17181B] dark:text-white hover:bg-accent/[0.08]'
}

/* Measured, not assumed. The height was hard-coded at 340 while the panel
   actually renders 373, so the "is there room below?" test was wrong by 33px
   every time: on a short window it flipped above and landed 33px too low over
   the form, and on a tall one it decided there was room and hung off the
   bottom of the screen. popEl is already in the DOM when this runs (the
   watcher awaits nextTick), so its real box is available. */
const GAP = 6
const EDGE = 8

function place() {
	const t = triggerEl.value
	if (!t) return
	const r = t.getBoundingClientRect()
	const p = popEl.value?.getBoundingClientRect()
	const W = p?.width || 292
	const H = p?.height || 373

	const roomBelow = window.innerHeight - r.bottom - GAP - EDGE
	const roomAbove = r.top - GAP - EDGE

	let top
	if (H <= roomBelow) top = r.bottom + GAP
	else if (H <= roomAbove) top = r.top - GAP - H
	/* Fits neither way - on a short window the panel is taller than the space
	   above or below the field. Pin it to whichever side has more room and let
	   it run to the viewport edge rather than hang off the screen. */
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

function onDocDown(e) {
	if (triggerEl.value?.contains(e.target) || popEl.value?.contains(e.target)) return
	/* The month and year pickers in this calendar's own header are SelectFields,
	   and they teleport their list to <body> too. With no DOM relationship back
	   to the panel, choosing a month counted as a click outside and shut the
	   calendar before the new month could render. */
	if (e.target instanceof Element && e.target.closest('.select-menu-pop')) return
	close()
}
function onKey(e) {
	if (e.key === 'Escape') close()
}

function openPicker() {
	if (props.disabled) return
	const d = parse(props.modelValue) || parse(props.min) || new Date()
	viewYear.value = d.getFullYear()
	viewMonth.value = d.getMonth()
	open.value = true
}
function close() {
	open.value = false
}

watch(open, async (isOpen) => {
	if (isOpen) {
		await nextTick()
		place()
		document.addEventListener('mousedown', onDocDown, true)
		document.addEventListener('keydown', onKey, true)
		window.addEventListener('resize', place)
		// Capture phase: the popover has to follow a trigger inside a dialog
		// body that scrolls, not just the page.
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

/* ===== Typing =====
   The field takes digits only and lays them out as DD-MM-YYYY. Each digit is
   checked as it lands, so a day the month does not have (31-04, 30-02), a
   month past 12, or a 29-02 outside a leap year can never be typed at all.
   A complete date is committed straight away; a half-typed one is not, and
   leaving the field puts the last good date back. */
const focused = ref(false)
const editText = ref('')
/* Complete and well-formed, but outside min / max. */
const outOfRange = ref(false)
const showInvalid = computed(() => props.invalid || outOfRange.value)

const pad2 = (n) => String(n).padStart(2, '0')
const onlyDigits = (s) => String(s || '').replace(/\D/g, '')
const toDMY = (s) => {
	const d = parse(s)
	return d ? `${pad2(d.getDate())}-${pad2(d.getMonth() + 1)}-${d.getFullYear()}` : ''
}
/* Without a year yet, February is allowed 29 so 29-02 can still be typed;
   the last year digit then decides. */
const daysIn = (month, year) => (year ? new Date(year, month, 0).getDate() : month === 2 ? 29 : [4, 6, 9, 11].includes(month) ? 30 : 31)

/* Reads whatever is in the box, character by character, into day / month /
   year. People type dates loosely, so:
   - a day of 4-9 or a month of 2-9 can only be one digit, and is padded
     ("5" -> "05-"), rather than refused;
   - "-", "/", "." or a space ends a one-digit day or month ("5/3" -> "05-03-");
   - anything that would make the date impossible is dropped, along with
     everything typed after it.
   A part that is complete gets its dash straight away ("27-"), so it is clear
   the field wants the next part. */
function readParts(raw) {
	const p = ['', '', '']
	let at = 0
	let used = 0
	const dayOk = (d) => d >= 1 && d <= 31
	const monthOk = (m) => m >= 1 && m <= 12 && Number(p[0]) <= daysIn(m)
	for (const ch of String(raw || '')) {
		used++
		if (/[-/. ]/.test(ch)) {
			// Only a lone digit can be closed off early; '0' alone is no day.
			if (at < 2 && p[at].length === 1 && p[at] !== '0') {
				const v = '0' + p[at]
				if (at === 0 ? !dayOk(+v) : !monthOk(+v)) break
				p[at] = v
				at++
			}
			continue
		}
		if (!/\d/.test(ch)) continue
		if (at === 0) {
			if (!p[0]) {
				if (ch > '3') { p[0] = '0' + ch; at = 1 } else p[0] = ch
			} else {
				if (!dayOk(+(p[0] + ch))) break
				p[0] += ch
				at = 1
			}
		} else if (at === 1) {
			if (!p[1]) {
				if (ch > '1') {
					if (!monthOk(+ch)) break
					p[1] = '0' + ch
					at = 2
				} else p[1] = ch
			} else {
				if (!monthOk(+(p[1] + ch))) break
				p[1] += ch
				at = 2
			}
		} else {
			if (!p[2] && ch === '0') break
			if (p[2].length === 3 && Number(p[0]) > daysIn(+p[1], +(p[2] + ch))) break
			p[2] += ch
			if (p[2].length === 4) break
		}
	}
	const text = p[0] + (at >= 1 ? '-' + p[1] : '') + (at >= 2 ? '-' + p[2] : '')
	/* rest: whatever was typed after a finished year (a pasted time). */
	return { day: p[0], month: at >= 1 ? p[1] : '', year: at >= 2 ? p[2] : '', text, rest: p[2].length === 4 ? String(raw || '').slice(used) : '' }
}

const inputText = computed(() => (focused.value ? editText.value : props.modelValue ? props.display || displayValue.value : ''))

/* ===== Part-by-part editing =====
   Once the field holds a whole date it behaves like the browser's own date
   box: day, month and year (and hour and minute, in date-and-time mode) are
   separate parts. Clicking selects the part under the pointer, digits replace
   only that part and then move on to the next, ← / → move between parts, and
   ↑ / ↓ step the selected part by one. An empty or half-typed date is still
   typed straight through (readParts). */
const SEGS = [[0, 2], [3, 2], [6, 4], [11, 2], [14, 2]] // [start, length]
const segMode = ref(false)
const seg = ref(0)
let segBuf = ''

const lastSeg = () => (props.withTime ? 4 : 2)
const timeOrMidnight = () => (/^\d{2}:\d{2}$/.test(props.time) ? props.time : '00:00')
const fullText = (v) => {
	const d = toDMY(v)
	return d && props.withTime ? `${d} ${timeOrMidnight()}` : d
}
const isWhole = (s) => (props.withTime ? /^\d{2}-\d{2}-\d{4} \d{2}:\d{2}$/ : /^\d{2}-\d{2}-\d{4}$/).test(s)

function selectSeg(i, keepBuf = false) {
	seg.value = i
	if (!keepBuf) segBuf = ''
	nextTick(() => {
		const el = inputEl.value
		if (!el || document.activeElement !== el) return
		el.setSelectionRange(SEGS[i][0], SEGS[i][0] + SEGS[i][1])
	})
}

/* The text as parts. A year being typed shows zero-padded ("0002") so every
   part keeps its place. */
function partsNow() {
	const [date, time = ''] = editText.value.split(' ')
	const [d, m, y] = date.split('-')
	const [hh = '00', mm = '00'] = time.split(':')
	return { day: Number(d), month: Number(m), yText: y, hh, mm }
}

/* Writes the parts back, and commits the date when it is whole and allowed. */
function setParts(day, month, yText, { save = true, hh, mm } = {}) {
	const cur = props.withTime ? partsNow() : {}
	const h = hh ?? cur.hh
	const mi = mm ?? cur.mm
	editText.value = `${pad2(day)}-${pad2(month)}-${yText}` + (props.withTime ? ` ${h}:${mi}` : '')
	if (inputEl.value) inputEl.value.value = editText.value
	viewMonth.value = month - 1
	if (!save) return
	viewYear.value = Number(yText)
	const iso = `${yText}-${pad2(month)}-${pad2(day)}`
	outOfRange.value = Boolean((props.min && iso < props.min) || (props.max && iso > props.max))
	if (!outOfRange.value && iso !== props.modelValue) commit(iso)
}
function setTime(h, mi) {
	const { day, month, yText } = partsNow()
	setParts(day, month, yText, { save: false, hh: pad2(h), mm: pad2(mi) })
	const t = `${pad2(h)}:${pad2(mi)}`
	/* The typed date goes along with it: typed in one go, the time arrives
	   before the parent has taken in the new date. */
	const iso = /^[1-9]\d{3}$/.test(yText) ? `${yText}-${pad2(month)}-${pad2(day)}` : ''
	if (t !== props.time || (iso && iso !== props.modelValue)) emit('update:time', t, iso)
}

/* One digit typed into a two-digit part running min..max. A first digit too
   big to have a second is the whole value ("5" -> 05); a second digit that
   overshoots starts the part again from that digit. `wait` is a leading
   digit that is not a value yet (a 0 where the part starts at 1). */
function twoDigit(ch, max, min) {
	segBuf += ch
	const v = Number(segBuf)
	if (segBuf.length === 1) return v * 10 > max ? { v, done: true } : { v, done: false, wait: v < min }
	if (v >= min && v <= max) return { v, done: true }
	segBuf = ''
	return twoDigit(ch, max, min)
}

function typeIntoSeg(ch) {
	const { day, month, yText, hh, mm } = partsNow()
	const yearKnown = /^[1-9]\d{3}$/.test(yText) ? Number(yText) : 0

	if (seg.value === 0) {
		const r = twoDigit(ch, daysIn(month, yearKnown), 1)
		if (r.wait) return selectSeg(0, true)
		setParts(r.v, month, yText)
		return r.done ? selectSeg(1) : selectSeg(0, true)
	}

	if (seg.value === 1) {
		const before = segBuf
		const r = twoDigit(ch, 12, 1)
		if (r.wait) return selectSeg(1, true)
		if (day > daysIn(r.v, yearKnown)) {
			// e.g. day 31 and month 4: refuse the digit, keep what was there.
			segBuf = before
			return selectSeg(1, true)
		}
		setParts(day, r.v, yText)
		return r.done ? selectSeg(2) : selectSeg(1, true)
	}

	if (seg.value === 2) {
		// Year: digits build up, and the date is saved once there are four.
		if (!segBuf && ch === '0') return selectSeg(2)
		segBuf += ch
		if (segBuf.length < 4) {
			setParts(day, month, segBuf.padStart(4, '0'), { save: false })
			return selectSeg(2, true)
		}
		if (day > daysIn(month, Number(segBuf))) {
			// 29-02 in a year that is not a leap year: keep the old year.
			segBuf = ''
			setParts(day, month, fullText(props.modelValue).slice(6, 10) || yText, { save: false })
			return selectSeg(2)
		}
		setParts(day, month, segBuf)
		return props.withTime ? selectSeg(3) : selectSeg(2)
	}

	if (seg.value === 3) {
		const r = twoDigit(ch, 23, 0)
		setTime(r.v, Number(mm))
		return r.done ? selectSeg(4) : selectSeg(3, true)
	}

	const r = twoDigit(ch, 59, 0)
	setTime(Number(hh), r.v)
	return r.done ? selectSeg(4) : selectSeg(4, true)
}

function stepSeg(delta) {
	const { day: d0, month: m0, yText, hh, mm } = partsNow()
	if (seg.value === 3) {
		setTime((Number(hh) + delta + 24) % 24, Number(mm))
		return selectSeg(3)
	}
	if (seg.value === 4) {
		setTime(Number(hh), (Number(mm) + delta + 60) % 60)
		return selectSeg(4)
	}
	let day = d0
	let month = m0
	let year = Number(yText)
	if (seg.value === 0) {
		const max = daysIn(month, year)
		day = ((day - 1 + delta + max) % max) + 1
	} else if (seg.value === 1) {
		month = ((month - 1 + delta + 12) % 12) + 1
		day = Math.min(day, daysIn(month, year))
	} else {
		year = Math.max(1, year + delta)
		day = Math.min(day, daysIn(month, year))
	}
	setParts(day, month, String(year).padStart(4, '0'))
	selectSeg(seg.value)
}

function onKeydown(e) {
	if (e.key === 'Enter') {
		e.preventDefault()
		return onEnter()
	}
	if (e.key === 'Tab') return close()
	if (e.ctrlKey || e.metaKey || e.altKey) return

	if (!segMode.value) {
		if (e.key === 'ArrowDown' && !open.value) {
			e.preventDefault()
			openPicker()
		}
		return
	}

	if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
		e.preventDefault()
		return selectSeg(Math.max(0, Math.min(lastSeg(), seg.value + (e.key === 'ArrowLeft' ? -1 : 1))))
	}
	if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
		e.preventDefault()
		if (!isWhole(editText.value)) return
		return stepSeg(e.key === 'ArrowUp' ? 1 : -1)
	}
}

/* Typed characters, in part-by-part mode or straight after a finished year. */
function feed(chars) {
	for (const ch of chars || '') {
		if (/\d/.test(ch)) typeIntoSeg(ch)
		else if (/[-/.: ]/.test(ch)) selectSeg(Math.min(lastSeg(), seg.value + 1))
	}
}

/* Text going in or coming out is handled here rather than on keydown:
   on-screen keyboards, phones and paste insert text without a key event,
   but every one of them fires beforeinput. */
function onBeforeInput(e) {
	const el = inputEl.value
	if (!segMode.value || !el) return
	const allSelected = el.value.length > 0 && el.selectionStart === 0 && el.selectionEnd === el.value.length
	const type = e.inputType || ''

	if (type.startsWith('delete')) {
		e.preventDefault()
		if (allSelected) {
			segMode.value = false
			editText.value = ''
			el.value = ''
			if (props.modelValue) commit('')
			return
		}
		// Undo the last digit typed into this part, else step back a part.
		if (segBuf) {
			segBuf = segBuf.slice(0, -1)
			return selectSeg(seg.value, true)
		}
		return selectSeg(Math.max(0, seg.value - 1))
	}
	if (!type.startsWith('insert')) return
	/* Select-all then type starts the date over, typed straight through. */
	if (allSelected) {
		segMode.value = false
		return
	}
	e.preventDefault()
	feed(e.data)
}

/* Which part is under the pointer. Measured from the click's x against the
   text's own glyph widths, not from the caret, which on the click that
   focuses the field is not placed yet when this runs. */
let measureCtx = null
function segAtX(clientX) {
	const el = inputEl.value
	measureCtx = measureCtx || document.createElement('canvas').getContext('2d')
	const cs = getComputedStyle(el)
	measureCtx.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`
	const x = clientX - el.getBoundingClientRect().left + el.scrollLeft
	const w = (n) => measureCtx.measureText(editText.value.slice(0, n)).width
	// The split between two parts is the middle of the separator between them.
	let i = 0
	for (const at of [2, 5, 10, 13]) if (x >= (w(at) + w(at + 1)) / 2) i++
	return Math.min(i, lastSeg())
}
function onInputClick(e) {
	if (!segMode.value || !inputEl.value) return
	if (e && e.clientX) return selectSeg(segAtX(e.clientX))
	const pos = inputEl.value.selectionStart ?? 0
	let i = 0
	SEGS.forEach(([s], k) => { if (pos >= s) i = k })
	selectSeg(Math.min(i, lastSeg()))
}

function onFocus() {
	focused.value = true
	editText.value = fullText(props.modelValue)
	outOfRange.value = false
	segMode.value = isWhole(editText.value)
	if (segMode.value) selectSeg(0)
	if (!open.value) openPicker()
}
function onBlur() {
	focused.value = false
	segMode.value = false
	segBuf = ''
	editText.value = fullText(props.modelValue)
	outOfRange.value = false
}
function onInput(e) {
	const before = editText.value
	let parts = readParts(e.target.value)
	/* Backspace over the dash after a finished part would only have it put
	   straight back; take the digit before it too. */
	if (e.inputType && e.inputType.startsWith('delete') && parts.text === before) {
		parts = readParts(onlyDigits(before).slice(0, -1).replace(/^(\d{2})(\d{1,2})/, '$1-$2').replace(/^(\d{2}-\d{2})(\d)/, '$1-$2'))
		if (parts.text === before) parts = readParts('')
	}
	editText.value = parts.text
	e.target.value = parts.text
	outOfRange.value = false

	if (parts.month.length === 2) viewMonth.value = Number(parts.month) - 1
	if (parts.year.length === 4) {
		viewYear.value = Number(parts.year)
		const iso = `${parts.year}-${parts.month}-${parts.day}`
		if ((props.min && iso < props.min) || (props.max && iso > props.max)) outOfRange.value = true
		else if (iso !== props.modelValue) commit(iso)
		// A whole date: from here on, edit it part by part.
		segMode.value = true
		if (props.withTime) {
			// The time follows on: keep the one already set, and carry on into
			// it with anything typed or pasted past the year.
			editText.value = `${parts.text} ${timeOrMidnight()}`
			e.target.value = editText.value
			selectSeg(3)
			feed(parts.rest)
		} else selectSeg(2)
	} else if (!parts.text && props.modelValue) {
		commit('')
	}
}
function onEnter() {
	close()
	inputEl.value?.blur()
}
function onWrapClick() {
	if (props.disabled) return
	if (document.activeElement !== inputEl.value) inputEl.value?.focus()
	else if (!open.value) openPicker()
}
function onIconClick() {
	if (props.disabled) return
	if (open.value) return close()
	inputEl.value?.focus()
	if (!open.value) openPicker()
}

function pick(day) {
	if (day.disabled) return
	commit(day.date)
	editText.value = fullText(day.date)
	outOfRange.value = false
	if (props.closeOnPick) close()
}
function pickToday() {
	if ((props.min && todayKey < props.min) || (props.max && todayKey > props.max)) return
	const d = new Date()
	viewYear.value = d.getFullYear()
	viewMonth.value = d.getMonth()
	commit(todayKey)
	editText.value = fullText(todayKey)
	close()
}
function clear() {
	commit('')
	editText.value = ''
	close()
}

function step(n) {
	let m = viewMonth.value + n
	let y = viewYear.value
	if (m < 0) {
		m = 11
		y--
	} else if (m > 11) {
		m = 0
		y++
	}
	viewMonth.value = m
	viewYear.value = y
}
</script>
