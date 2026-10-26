<template>
	<div ref="containerRef" class="relative inline-block shrink-0" :class="wrapperWidthClass">
		<!-- Trigger Button -->
		<button
			ref="triggerRef"
			type="button"
			role="combobox"
			:aria-expanded="isOpen"
			:aria-haspopup="true"
			:disabled="disabled"
			@click="toggleOpen"
			@keydown="handleTriggerKeydown"
			:class="[
				'w-full flex items-center justify-between gap-2 transition-all cursor-pointer outline-none select-none',
				triggerBaseClass,
				triggerStateClass,
				disabled ? 'opacity-50 cursor-not-allowed pointer-events-none' : '',
				triggerClass,
			]"
		>
			<!-- Left side icon (if any) or content -->
			<div class="flex items-center gap-1.5 min-w-0 flex-1 text-left">
				<span
					v-if="selectedOption?.icon"
					class="material-symbols-outlined !text-[16px] shrink-0 text-accent dark:text-accent-soft"
				>
					{{ selectedOption.icon }}
				</span>
				<span
					class="truncate whitespace-nowrap"
					:class="[
						hasActiveValue ? 'font-semibold' : 'font-medium',
						variant === 'pill' && hasActiveValue
							? 'text-white'
							: 'text-[#17181B] dark:text-white',
					]"
					:title="displayLabel"
				>
					{{ displayLabel }}
				</span>
			</div>

			<!-- Right side: Clear icon and Chevron -->
			<div class="flex items-center gap-1 shrink-0">
				<!-- Clear button (if clearable and has active value) -->
				<span
					v-if="clearable && hasActiveValue && !disabled"
					role="button"
					tabindex="0"
					title="Clear selection"
					class="w-4 h-4 rounded-full flex items-center justify-center hover:bg-black/10 dark:hover:bg-white/10 transition-colors cursor-pointer"
					@click.stop="clearSelection"
					@keydown.enter.stop="clearSelection"
				>
					<span class="material-symbols-outlined !text-[12px] opacity-75">close</span>
				</span>

				<!-- Chevron -->
				<span
					class="material-symbols-outlined !text-[16px] transition-transform duration-200 pointer-events-none"
					:class="[
						isOpen ? 'rotate-180' : '',
						variant === 'pill' && hasActiveValue
							? 'text-white/80'
							: 'text-[#9AA0A8] dark:text-white/50',
					]"
				>
					expand_more
				</span>
			</div>
		</button>

		<!-- Popover Menu -->
		<Teleport :to="'body'" :disabled="!teleport">
			<div
				v-if="isOpen"
				ref="menuRef"
				role="listbox"
				@click.stop
				:class="[
					'filter-menu shadow-xl',
					teleport
						? 'fixed z-[99999]'
						: ['absolute z-[300] min-w-full min-w-[170px]', dropup ? 'bottom-full mb-1.5' : 'top-full mt-1.5', menuAlignmentClass],
					menuClass,
				]"
				:style="teleport ? teleportStyle : {}"
			>
			<!-- Custom Header Slot (e.g. Price Min/Max inputs, date pickers) -->
			<slot name="header"></slot>

			<!-- Embedded Search Bar (if searchable) -->
			<div
				v-if="effectiveSearchable"
				class="p-1.5 border-b border-[#ECECF1] dark:border-white/[0.08] sticky top-0 bg-white/95 dark:bg-surface-1/95 backdrop-blur-md z-10"
			>
				<div class="relative">
					<span
						class="material-symbols-outlined !text-[16px] absolute left-2.5 top-1/2 -translate-y-1/2 text-[#9AA0A8] pointer-events-none"
					>
						search
					</span>
					<input
						ref="searchInputRef"
						v-model="searchQuery"
						type="text"
						:placeholder="searchPlaceholder"
						class="w-full h-8 pl-8 pr-2.5 rounded-lg bg-[#F5F5F8] dark:bg-surface-3 border border-transparent text-xs text-[#17181B] dark:text-white placeholder-[#9AA0A8] dark:placeholder-white/40 outline-none focus:border-accent focus:bg-white dark:focus:bg-surface-2 transition-all"
						@keydown="handleSearchKeydown"
					/>
				</div>
			</div>

			<!-- Options List -->
			<div class="max-h-60 overflow-y-auto custom-scrollbar py-1 space-y-0.5">
				<button
					v-for="(option, index) in filteredOptions"
					:key="String(option.value)"
					type="button"
					role="option"
					:aria-selected="isSelected(option)"
					class="filter-option"
					:class="{
						'is-active': isSelected(option),
						'bg-black/[0.04] dark:bg-white/[0.06]': index === highlightedIndex,
					}"
					@click.stop="selectOption(option)"
					@mouseenter="highlightedIndex = index"
				>
					<div class="flex items-center gap-2 min-w-0 flex-1 text-left">
						<span
							v-if="option.icon"
							class="material-symbols-outlined !text-[16px] shrink-0"
							:class="isSelected(option) ? 'text-accent dark:text-accent-soft' : 'text-[#9AA0A8]'"
						>
							{{ option.icon }}
						</span>
						<div class="min-w-0 flex-1">
							<span class="truncate block">{{ option.label }}</span>
							<span
								v-if="option.description"
								class="text-[10px] text-[#9AA0A8] dark:text-white/40 block truncate"
							>
								{{ option.description }}
							</span>
						</div>
					</div>

					<!-- Badge if option has one -->
					<span
						v-if="option.badge"
						class="text-[10px] font-semibold px-1.5 py-0.2 rounded-full bg-black/[0.06] dark:bg-white/[0.1] text-[#5C6169] dark:text-white/70 shrink-0 ml-1.5"
					>
						{{ option.badge }}
					</span>
				</button>

				<!-- Empty Results Message -->
				<p
					v-if="filteredOptions.length === 0"
					class="px-3 py-3 text-center text-xs text-[#9AA0A8] dark:text-white/45"
				>
					No results found
				</p>
			</div>
		</div>
		</Teleport>
	</div>
</template>

<script setup>
import { Teleport, computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
	modelValue: {
		type: [String, Number, Boolean, Object, null],
		default: null,
	},
	options: {
		type: Array,
		default: () => [],
	},
	/** 'pill' for filter bars and headers, 'input' for forms and toolbars */
	variant: {
		type: String,
		default: 'pill',
		validator: (v) => ['pill', 'input'].includes(v),
	},
	placeholder: {
		type: String,
		default: 'Select...',
	},
	/** 'auto' shows search if > 6 options; true forces search; false hides it */
	searchable: {
		type: [Boolean, String],
		default: 'auto',
	},
	searchPlaceholder: {
		type: String,
		default: 'Search...',
	},
	labelKey: {
		type: String,
		default: null,
	},
	valueKey: {
		type: String,
		default: null,
	},
	showAllOption: {
		type: Boolean,
		default: false,
	},
	allOptionLabel: {
		type: String,
		default: 'All',
	},
	allOptionValue: {
		type: [String, Number, null],
		default: '',
	},
	clearable: {
		type: Boolean,
		default: false,
	},
	disabled: {
		type: Boolean,
		default: false,
	},
	/** Placement: 'auto', 'start', 'end' */
	align: {
		type: String,
		default: 'start',
		validator: (v) => ['start', 'end'].includes(v),
	},
	triggerClass: {
		type: String,
		default: '',
	},
	menuClass: {
		type: String,
		default: '',
	},
	fullWidth: {
		type: Boolean,
		default: false,
	},
	teleport: {
		type: Boolean,
		default: false,
	},
	active: {
		type: Boolean,
		default: null,
	},
	selectedLabel: {
		type: String,
		default: null,
	},
	showAllLabelInTrigger: {
		type: Boolean,
		default: false,
	},
})

const emit = defineEmits(['update:modelValue', 'change', 'select', 'clear'])

const instanceId = Symbol('UnifiedDropdown')

function handleOtherDropdownOpened(e) {
	if (e.detail?.id !== instanceId && isOpen.value) {
		closeMenu()
	}
}

const containerRef = ref(null)
const triggerRef = ref(null)
const menuRef = ref(null)
const searchInputRef = ref(null)

const isOpen = ref(false)
const dropup = ref(false)
const searchQuery = ref('')
const highlightedIndex = ref(-1)

// Width styling
const wrapperWidthClass = computed(() => (props.fullWidth ? 'w-full' : ''))

// Variant-specific trigger styling
const triggerBaseClass = computed(() => {
	if (props.variant === 'pill') {
		return 'rounded-full text-xs font-medium px-3.5 py-2 border whitespace-nowrap'
	}
	// 'input' variant
	return 'h-10 px-3.5 rounded-xl border text-xs sm:text-sm font-medium'
})

const triggerStateClass = computed(() => {
	if (props.variant === 'pill') {
		if (hasActiveValue.value) {
			return 'bg-accent text-white border-accent shadow-xs'
		}
		if (isOpen.value) {
			return 'bg-white dark:bg-surface-2 border-accent/40 ring-2 ring-accent/20 text-[#17181B] dark:text-white shadow-xs'
		}
		return 'bg-[#F5F5F8] dark:bg-surface-3 text-[#5C6169] dark:text-white/70 border-transparent hover:bg-[#EFEFF3] dark:hover:bg-white/10'
	}
	// 'input' variant
	if (isOpen.value || hasActiveValue.value) {
		return 'bg-white dark:bg-surface-2 border-accent text-[#17181B] dark:text-white ring-2 ring-accent/15'
	}
	return 'bg-[#F5F5F8] dark:bg-surface-3 text-[#17181B] dark:text-white border-[#ECECF1] dark:border-white/[0.08] hover:border-accent/40'
})

const menuAlignmentClass = computed(() => {
	return props.align === 'end' ? 'right-0' : 'left-0'
})

// Options normalization
const normalizedOptions = computed(() => {
	const list = []

	if (props.showAllOption) {
		list.push({
			label: props.allOptionLabel,
			value: props.allOptionValue,
			isAll: true,
		})
	}

	if (!Array.isArray(props.options)) return list

	for (const opt of props.options) {
		if (typeof opt === 'object' && opt !== null) {
			const label = props.labelKey
				? opt[props.labelKey]
				: opt.label !== undefined
				? opt.label
				: opt.name !== undefined
				? opt.name
				: opt.title !== undefined
				? opt.title
				: String(opt.value ?? '')

			const value = props.valueKey
				? opt[props.valueKey]
				: opt.value !== undefined
				? opt.value
				: opt.name !== undefined
				? opt.name
				: opt.id !== undefined
				? opt.id
				: label

			list.push({
				label: String(label ?? ''),
				value,
				icon: opt.icon,
				description: opt.description,
				badge: opt.badge,
				isAll: Boolean(opt.isAll),
				original: opt,
			})
		} else {
			list.push({
				label: String(opt ?? ''),
				value: opt,
				original: opt,
			})
		}
	}

	return list
})

// Active value checks
const hasActiveValue = computed(() => {
	if (props.active !== null) {
		return props.active
	}
	if (props.modelValue === null || props.modelValue === undefined || props.modelValue === '') {
		return false
	}
	if (props.showAllOption && props.modelValue === props.allOptionValue) {
		return false
	}
	return true
})

const selectedOption = computed(() => {
	return (
		normalizedOptions.value.find(
			(o) =>
				o.value === props.modelValue ||
				String(o.value) === String(props.modelValue)
		) || null
	)
})

const displayLabel = computed(() => {
	if (props.selectedLabel) return props.selectedLabel
	if (selectedOption.value) {
		if (!selectedOption.value.isAll || props.showAllLabelInTrigger) {
			return selectedOption.value.label
		}
	}
	if (hasActiveValue.value) return String(props.modelValue)
	return props.placeholder
})

// Search logic
const effectiveSearchable = computed(() => {
	if (props.searchable === true) return true
	if (props.searchable === false) return false
	// 'auto': enable if more than 6 options
	return normalizedOptions.value.length > 6
})

const filteredOptions = computed(() => {
	const q = searchQuery.value.trim().toLowerCase()
	if (!q) return normalizedOptions.value

	return normalizedOptions.value.filter((o) => {
		const labelMatch = o.label.toLowerCase().includes(q)
		const descMatch = o.description ? o.description.toLowerCase().includes(q) : false
		return labelMatch || descMatch
	})
})

function isSelected(opt) {
	if (opt.isAll) {
		return !hasActiveValue.value || props.modelValue === props.allOptionValue
	}
	return (
		props.modelValue === opt.value ||
		String(props.modelValue) === String(opt.value)
	)
}

function selectOption(opt) {
	emit('update:modelValue', opt.value)
	emit('change', opt.value)
	emit('select', opt.original ?? opt)
	closeMenu()
}

function clearSelection() {
	const fallback = props.showAllOption ? props.allOptionValue : null
	emit('update:modelValue', fallback)
	emit('change', fallback)
	emit('clear')
}

// Open / Close / Dropup detection
const teleportStyle = ref({})

function updateTeleportPosition() {
	if (!props.teleport || !triggerRef.value) return
	const rect = triggerRef.value.getBoundingClientRect()
	const spaceBelow = window.innerHeight - rect.bottom
	const spaceAbove = rect.top
	const isDropup = spaceBelow < 250 && spaceAbove > spaceBelow
	dropup.value = isDropup

	const menuWidth = 220
	let left = props.align === 'end' ? rect.right - menuWidth : rect.left
	if (left + menuWidth > window.innerWidth - 8) {
		left = Math.max(8, window.innerWidth - menuWidth - 8)
	}
	if (left < 8) left = 8

	teleportStyle.value = {
		position: 'fixed',
		top: isDropup ? 'auto' : `${rect.bottom + 6}px`,
		bottom: isDropup ? `${window.innerHeight - rect.top + 6}px` : 'auto',
		left: `${left}px`,
		minWidth: `${Math.max(170, rect.width)}px`,
		maxWidth: 'calc(100vw - 16px)',
		zIndex: 99999,
	}
}

function handleScrollOrResize() {
	if (isOpen.value && props.teleport) {
		updateTeleportPosition()
	}
}

function toggleOpen() {
	if (props.disabled) return
	if (isOpen.value) {
		closeMenu()
	} else {
		openMenu()
	}
}

function openMenu() {
	isOpen.value = true
	searchQuery.value = ''
	highlightedIndex.value = -1

	// Broadcast to close all other open dropdowns across the application
	window.dispatchEvent(
		new CustomEvent('zevar-dropdown-opened', { detail: { id: instanceId } })
	)

	// Viewport collision check & positioning
	nextTick(() => {
		if (props.teleport) {
			updateTeleportPosition()
		} else if (triggerRef.value) {
			const rect = triggerRef.value.getBoundingClientRect()
			const spaceBelow = window.innerHeight - rect.bottom
			const spaceAbove = rect.top
			dropup.value = spaceBelow < 240 && spaceAbove > spaceBelow
		}

		if (effectiveSearchable.value && searchInputRef.value) {
			searchInputRef.value.focus()
		}
	})
}

function closeMenu() {
	isOpen.value = false
	searchQuery.value = ''
	highlightedIndex.value = -1
}

// Keyboard navigation
function handleTriggerKeydown(e) {
	if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
		e.preventDefault()
		if (!isOpen.value) {
			openMenu()
		} else {
			moveHighlight(e.key === 'ArrowDown' ? 1 : -1)
		}
	} else if (e.key === 'Escape') {
		closeMenu()
	}
}

function handleSearchKeydown(e) {
	if (e.key === 'ArrowDown') {
		e.preventDefault()
		moveHighlight(1)
	} else if (e.key === 'ArrowUp') {
		e.preventDefault()
		moveHighlight(-1)
	} else if (e.key === 'Enter') {
		e.preventDefault()
		if (highlightedIndex.value >= 0 && filteredOptions.value[highlightedIndex.value]) {
			selectOption(filteredOptions.value[highlightedIndex.value])
		}
	} else if (e.key === 'Escape') {
		closeMenu()
	}
}

function moveHighlight(step) {
	const total = filteredOptions.value.length
	if (total === 0) return
	if (highlightedIndex.value === -1) {
		highlightedIndex.value = step === 1 ? 0 : total - 1
	} else {
		highlightedIndex.value = (highlightedIndex.value + step + total) % total
	}
}

// Click outside handling
function onDocumentClick(e) {
	if (
		containerRef.value &&
		!containerRef.value.contains(e.target) &&
		(!menuRef.value || !menuRef.value.contains(e.target))
	) {
		closeMenu()
	}
}

onMounted(() => {
	document.addEventListener('click', onDocumentClick)
	window.addEventListener('zevar-dropdown-opened', handleOtherDropdownOpened)
	window.addEventListener('close-all-dropdowns', closeMenu)
	window.addEventListener('scroll', handleScrollOrResize, true)
	window.addEventListener('resize', handleScrollOrResize)
})

onBeforeUnmount(() => {
	document.removeEventListener('click', onDocumentClick)
	window.removeEventListener('zevar-dropdown-opened', handleOtherDropdownOpened)
	window.removeEventListener('close-all-dropdowns', closeMenu)
	window.removeEventListener('scroll', handleScrollOrResize, true)
	window.removeEventListener('resize', handleScrollOrResize)
})
</script>
