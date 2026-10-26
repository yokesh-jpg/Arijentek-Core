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
				v-for="(row, idx) in rows"
				:key="idx"
				class="border-b last:border-0 border-black/[0.05] dark:border-white/[0.06] hover:bg-black/[0.02] dark:hover:bg-white/[0.04] transition-colors"
			>
				<td
					v-for="col in columns"
					:key="col.fieldname"
					class="table-td whitespace-nowrap"
					:class="isNumeric(col) && '!text-right tabular-nums'"
				>
					<span v-if="isStatus(col) && !isBlank(row[col.fieldname])" class="premium-tag" :class="statusTag(row[col.fieldname])">
						{{ row[col.fieldname] }}
					</span>
					<span v-else :class="isBlank(row[col.fieldname]) && 'text-[#656A72] dark:text-white/50'">
						{{ isBlank(row[col.fieldname]) ? '—' : row[col.fieldname] }}
					</span>
				</td>
			</tr>
		</tbody>
	</table>
</template>

<script setup>
/* The report tables were eleven copies of the same markup at four different
   header casings and three row paddings. */
defineProps({
	columns: { type: Array, default: () => [] },
	rows: { type: Array, default: () => [] },
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
