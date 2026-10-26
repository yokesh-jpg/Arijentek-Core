<template>
	<!-- One field, one value: "09-10-2026 17:30". It opens a single panel
	     with the calendar on the left and hour / minute columns on the right,
	     instead of two separate controls side by side. -->
	<DateField
		:model-value="datePart"
		:display="label"
		:placeholder="placeholder"
		:min="minDate"
		:max="maxDate"
		:disabled="disabled"
		:invalid="invalid"
		:input-class="inputClass"
		:id="id"
		:aria-label="ariaLabel || 'Date and time'"
		:close-on-pick="false"
		icon="event"
		with-time
		:time="timeText"
		@update:model-value="onDate"
		@update:time="onTime"
	>
		<template #side>
			<div class="w-[148px] shrink-0 flex flex-col border-l border-black/[0.06] dark:border-white/[0.08] pl-3">
				<div class="grid grid-cols-2 gap-1 mb-1">
					<p class="h-7 grid place-items-center text-xs font-medium text-[#656A72] dark:text-white/55">Hour</p>
					<p class="h-7 grid place-items-center text-xs font-medium text-[#656A72] dark:text-white/55">Min</p>
				</div>
				<div class="grid grid-cols-2 gap-1 flex-1 min-h-0">
					<div ref="hourList" class="max-h-[276px] overflow-y-auto pr-0.5 space-y-0.5">
						<button
							v-for="h in hours"
							:key="h"
							type="button"
							:data-sel="h === selHour ? '1' : null"
							class="w-full h-8 rounded-[10px] text-[13px] tabular-nums transition-colors"
							:class="h === selHour ? 'bg-accent text-white font-semibold' : 'text-[#17181B] dark:text-white hover:bg-accent/[0.08]'"
							@click="setTime(h, selMinute ?? 0)"
						>
							{{ pad(h) }}
						</button>
					</div>
					<div ref="minList" class="max-h-[276px] overflow-y-auto pr-0.5 space-y-0.5">
						<button
							v-for="m in minutes"
							:key="m"
							type="button"
							:data-sel="m === selMinute ? '1' : null"
							class="w-full h-8 rounded-[10px] text-[13px] tabular-nums transition-colors"
							:class="m === selMinute ? 'bg-accent text-white font-semibold' : 'text-[#17181B] dark:text-white hover:bg-accent/[0.08]'"
							@click="setTime(selHour ?? 9, m)"
						>
							{{ pad(m) }}
						</button>
					</div>
				</div>
			</div>
		</template>
	</DateField>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import DateField from './DateField.vue'

const props = defineProps({
	/* 'YYYY-MM-DDTHH:MM', the same string a native datetime-local holds.
	   Frappe hands back 'YYYY-MM-DD HH:MM:SS', so a space is accepted too. */
	modelValue: { type: String, default: '' },
	placeholder: { type: String, default: 'Select date and time' },
	/* Kept so existing call sites still compile; the single field uses
	   `placeholder`. */
	datePlaceholder: { type: String, default: '' },
	timePlaceholder: { type: String, default: '' },
	step: { type: Number, default: 5 },
	minDate: { type: String, default: '' },
	maxDate: { type: String, default: '' },
	disabled: { type: Boolean, default: false },
	invalid: { type: Boolean, default: false },
	/* Passed through to the trigger, as on DateField. */
	inputClass: { type: String, default: '' },
	id: { type: String, default: '' },
	ariaLabel: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue', 'change'])

const pad = (n) => String(n).padStart(2, '0')

const split = computed(() => {
	const s = (props.modelValue || '').trim()
	const m = /^(\d{4}-\d{2}-\d{2})[T ](\d{2}):(\d{2})/.exec(s)
	if (m) return { date: m[1], h: Number(m[2]), m: Number(m[3]) }
	if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return { date: s, h: null, m: null }
	return { date: '', h: null, m: null }
})
const datePart = computed(() => split.value.date)
const selHour = computed(() => split.value.h)
const selMinute = computed(() => split.value.m)

const hours = Array.from({ length: 24 }, (_, i) => i)
const minutes = computed(() => {
	const out = []
	for (let m = 0; m < 60; m += props.step) out.push(m)
	if (selMinute.value != null && !out.includes(selMinute.value)) out.push(selMinute.value)
	return out.sort((a, b) => a - b)
})

const label = computed(() => {
	if (!datePart.value) return ''
	// DD-MM-YYYY HH:MM, the order the field is typed in.
	const [y, mo, d] = datePart.value.split('-')
	const date = `${d}-${mo}-${y}`
	return selHour.value == null ? date : `${date} ${pad(selHour.value)}:${pad(selMinute.value ?? 0)}`
})

function todayLocal() {
	const n = new Date()
	return [n.getFullYear(), pad(n.getMonth() + 1), pad(n.getDate())].join('-')
}

function commit(date, h, m) {
	// Half a datetime is not a datetime; clearing the date clears the value.
	const value = date ? `${date}T${pad(h ?? 0)}:${pad(m ?? 0)}` : ''
	emit('update:modelValue', value)
	emit('change', value)
}

function onDate(d) {
	commit(d, selHour.value, selMinute.value)
}
/* Typed into the field's HH:MM part. */
const timeText = computed(() => (selHour.value == null ? '' : `${pad(selHour.value)}:${pad(selMinute.value ?? 0)}`))
function onTime(t, typedDate) {
	const [h, m] = t.split(':').map(Number)
	commit(typedDate || datePart.value || todayLocal(), h, m)
}
function setTime(h, m) {
	// A time with no date yet defaults to today, so picking a time first
	// still produces a value.
	commit(datePart.value || todayLocal(), h, m)
}

/* Bring the selected hour and minute into view when the panel opens. */
const hourList = ref(null)
const minList = ref(null)
watch([hourList, minList], async () => {
	await nextTick()
	for (const el of [hourList.value, minList.value]) {
		const sel = el?.querySelector('[data-sel="1"]')
		if (sel) el.scrollTop = sel.offsetTop - el.clientHeight / 2 + sel.offsetHeight / 2
	}
})
</script>
