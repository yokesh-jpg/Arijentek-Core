<template>
	<div class="relative" :class="block ? 'w-full' : ''">
		<button
			ref="triggerEl"
			type="button"
			:id="id"
			:disabled="disabled"
			:aria-label="ariaLabel"
			:aria-expanded="open"
			aria-haspopup="listbox"
			class="flex items-center gap-2 text-left disabled:opacity-40 disabled:cursor-not-allowed"
			:class="[triggerClass || 'field-input !pr-9', open ? '!border-accent/40' : '', block ? 'w-full' : '']"
			@click="toggle"
			@keydown.down.prevent="openMenu"
		>
			<span class="flex-1 truncate" :class="selectedLabel ? '' : 'text-[#656A72] dark:text-white/60'">
				{{ selectedLabel || placeholder }}
			</span>
			<span class="material-symbols-outlined !text-[18px] text-[#656A72] dark:text-white/60 shrink-0">expand_more</span>
		</button>

		<!-- Teleported and fixed, like the date picker: these sit inside
		     dialogs and table cards that clip their overflow, where an
		     absolute menu is cut in half. A native select's own popup never
		     had that problem, which is partly why they survived this long. -->
		<Teleport to="body">
			<div
				v-if="open"
				ref="menuEl"
				role="listbox"
				:aria-label="ariaLabel || 'Options'"
				class="filter-menu select-menu-pop pointer-events-auto fixed z-[200]"
				:style="menuStyle"
				@pointerdown.stop
				@mousedown.stop
			>
				<button
					v-for="(opt, i) in normalised"
					:key="i"
					type="button"
					role="option"
					:aria-selected="opt.value === modelValue"
					class="filter-option"
					:class="{ 'is-active': opt.value === modelValue }"
					@click="pick(opt)"
				>
					<span class="truncate">{{ opt.label }}</span>
				</button>
				<p v-if="!normalised.length" class="px-2.5 py-2 text-[13px] text-[#656A72] dark:text-white/55">
					Nothing to choose from
				</p>
			</div>
		</Teleport>
	</div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { placePopover } from '@/composables/placePopover'

const props = defineProps({
	modelValue: { type: [String, Number, Boolean, null], default: '' },
	/* Strings, numbers, or {label, value} — the shapes the native selects
	   this replaces were already written with. */
	options: { type: Array, default: () => [] },
	placeholder: { type: String, default: 'Select…' },
	disabled: { type: Boolean, default: false },
	block: { type: Boolean, default: true },
	/* A caller that had its own control styling keeps it. */
	triggerClass: { type: String, default: '' },
	id: { type: String, default: '' },
	ariaLabel: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue', 'change'])

const open = ref(false)
const triggerEl = ref(null)
const menuEl = ref(null)
const menuStyle = ref({})

const normalised = computed(() =>
	(props.options || []).map((o) =>
		o !== null && typeof o === 'object' ? { label: o.label ?? o.name ?? String(o.value ?? ''), value: o.value ?? o.name ?? o.label } : { label: String(o), value: o }
	)
)

const selectedLabel = computed(() => {
	const hit = normalised.value.find((o) => o.value === props.modelValue)
	if (hit) return hit.label
	return props.modelValue === '' || props.modelValue === null || props.modelValue === undefined ? '' : String(props.modelValue)
})

/* Shared with SearchableDropdown and DateRangePicker so every menu is placed,
   flipped and zoom-corrected the same way. */
function place() {
	menuStyle.value = placePopover(triggerEl.value, menuEl.value)
}

function onDocDown(e) {
	if (triggerEl.value?.contains(e.target) || menuEl.value?.contains(e.target)) return
	close()
}
function onKey(e) {
	if (e.key === 'Escape') close()
}

function openMenu() {
	if (props.disabled) return
	open.value = true
}
function close() {
	open.value = false
}
function toggle() {
	open.value ? close() : openMenu()
}

watch(open, async (isOpen) => {
	if (isOpen) {
		await nextTick()
		place()
		await nextTick()
		place()
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

function pick(opt) {
	emit('update:modelValue', opt.value)
	emit('change', opt.value)
	close()
}
</script>
