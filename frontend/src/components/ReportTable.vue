<template>
	<table class="w-full">
		<thead class="sticky top-0 z-[1]">
			<tr class="bg-white dark:bg-surface-1 border-b border-black/[0.07] dark:border-white/10">
				<th
					v-for="col in columns"
					:key="col.fieldname"
					class="table-th whitespace-nowrap"
					:class="isNumeric(col) && '!text-right'"
				>
					{{ col.label }}
				</th>
			</tr>
		</thead>
		<tbody>
			<tr
				v-for="(row, idx) in displayRows"
				:key="idx"
				class="border-b last:border-0 border-black/[0.05] dark:border-white/[0.06] hover:bg-black/[0.02] dark:hover:bg-white/[0.04] transition-colors"
			>
				<td
					v-for="col in columns"
					:key="col.fieldname"
					class="table-td align-top"
					:class="cellClass(col)"
				>
					<span v-if="isStatus(col) && !isBlank(row[col.fieldname])" class="premium-tag" :class="statusTag(row[col.fieldname])">
						{{ row[col.fieldname] }}
					</span>
					<span
						v-else
						:class="[isBlank(row[col.fieldname]) && 'text-[#656A72] dark:text-white/50', isLongText(col) && 'whitespace-pre-line break-words']"
					>
						{{ isBlank(row[col.fieldname]) ? '—' : row[col.fieldname] }}
					</span>
				</td>
			</tr>

			<!-- Sentinel element for IntersectionObserver -->
			<tr ref="tableSentinelRef" class="h-1">
				<td :colspan="columns.length" class="p-0 border-0"></td>
			</tr>

			<!-- Safe Load More Controls & Status Indicator -->
			<tr v-if="hasMore" class="border-t border-black/[0.06] dark:border-white/[0.07] bg-black/[0.01] dark:bg-white/[0.02]">
				<td :colspan="columns.length" class="p-4 text-center">
					<div class="flex flex-col items-center justify-center gap-1.5">
						<button
							type="button"
							@click="loadMore"
							class="btn-secondary !text-xs !py-1.5 !px-4 inline-flex items-center gap-1.5"
						>
							<span class="material-symbols-outlined !text-[16px]">expand_more</span>
							Load more ({{ remainingCount }} remaining)
						</button>
						<p class="text-[11px] text-[#5C6169] dark:text-white/50">
							Showing {{ displayRows.length }} of {{ rows.length }} records
						</p>
					</div>
				</td>
			</tr>
			<tr v-else-if="rows.length > pageSize" class="border-t border-black/[0.06] dark:border-white/[0.07]">
				<td :colspan="columns.length" class="py-2.5 px-4 text-center text-[11px] text-[#5C6169] dark:text-white/50">
					All {{ rows.length }} records loaded.
				</td>
			</tr>
		</tbody>
	</table>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'

/* The report tables were eleven copies of the same markup at four different
   header casings and three row paddings. */
const props = defineProps({
	columns: { type: Array, default: () => [] },
	rows: { type: Array, default: () => [] },
	pageSize: { type: Number, default: 50 },
})

const visibleCount = ref(props.pageSize)
const tableSentinelRef = ref(null)
let observer = null

const displayRows = computed(() => {
	const all = props.rows || []
	return all.slice(0, visibleCount.value)
})

const hasMore = computed(() => (props.rows?.length || 0) > visibleCount.value)
const remainingCount = computed(() => Math.max(0, (props.rows?.length || 0) - visibleCount.value))

function loadMore() {
	if (hasMore.value) {
		visibleCount.value += props.pageSize
	}
}

// Reset visible count when rows array changes (e.g. filters applied)
watch(
	() => props.rows,
	() => {
		visibleCount.value = props.pageSize
	}
)

function setupObserver() {
	if (observer) {
		observer.disconnect()
		observer = null
	}
	if (typeof window === 'undefined' || !window.IntersectionObserver) return
	const target = tableSentinelRef.value
	if (!target) return

	observer = new IntersectionObserver(
		(entries) => {
			const entry = entries[0]
			if (entry && entry.isIntersecting && hasMore.value) {
				loadMore()
			}
		},
		{
			rootMargin: '200px',
			threshold: 0.05,
		}
	)
	observer.observe(target)
}

watch(
	[tableSentinelRef, hasMore],
	([sentinel, more]) => {
		if (sentinel && more) {
			setupObserver()
		} else if (!more && observer) {
			observer.disconnect()
			observer = null
		}
	},
	{ flush: 'post' }
)

onUnmounted(() => {
	if (observer) {
		observer.disconnect()
		observer = null
	}
})

/* Numbers right-align so columns of figures can be compared down the column,
   and carry tabular figures so the digits line up. Frappe report columns
   declare their own fieldtype; fall back to the label when they do not. */
function isNumeric(col) {
	const t = String(col.fieldtype || '').toLowerCase()
	if (t) return ['currency', 'float', 'int', 'percent'].includes(t)
	return /amount|total|count|days|hours|rate|qty|balance|commission/i.test(col.label || '')
}

function isBlank(v) {
	return v === null || v === undefined || v === ''
}

/* Free-text columns (explanation, description, reason…) wrap in full instead
   of nowrap-stretching the whole table, and keep their stored line breaks
   (whitespace-pre-line) so the preview matches the PDF and Excel exports,
   which render the same breaks. Backends may declare a fieldtype; the name
   heuristic catches the columns that don't. */
function isLongText(col) {
	const t = String(col.fieldtype || '').toLowerCase()
	if (['small text', 'text', 'long text', 'text editor', 'code'].includes(t)) return true
	const pattern = /explanation|description|reason|remark|note|subject|justific|comment|detail/i
	return pattern.test(col.fieldname || '') || pattern.test(col.label || '')
}

function cellClass(col) {
	return [
		isLongText(col) ? 'max-w-[640px]' : 'whitespace-nowrap',
		isNumeric(col) && '!text-right tabular-nums',
	]
}

/* Each report carried its own getStatusBadgeClass with its own palette, so
   "Approved" was a different green in four places and "Open" was blue here
   and amber there. The four tags the rest of the app uses, applied once. */
function isStatus(col) {
	return /(^|_)status$/i.test(col.fieldname || '')
}

function statusTag(value) {
	const v = String(value).toLowerCase()
	if (['approved', 'resolved', 'submitted', 'completed', 'closed', 'active', 'eligible', 'present'].includes(v)) return 'tag-emerald'
	if (['rejected', 'absent', 'invalid', 'cancelled'].includes(v)) return 'tag-red'
	if (['open', 'working', 'pending', 'investigated'].includes(v)) return 'tag-amber'
	return 'tag-neutral'
}
</script>
