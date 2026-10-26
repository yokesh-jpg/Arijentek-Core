<template>
	<div class="flex flex-col gap-4 tab-fill">
		<!-- The POS list toolbar (Purchases): search and the add button in one
		     glass card above the table. -->
		<div class="glass-card !p-3 flex flex-col sm:flex-row sm:items-center gap-2">
			<div class="relative flex-1 min-w-0">
				<span class="material-symbols-outlined !text-[18px] absolute left-3 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/60 pointer-events-none">search</span>
				<input
					:value="search"
					@input="$emit('update:search', $event.target.value)"
					type="text"
					:placeholder="placeholder"
					class="field-input !pl-9"
				/>
			</div>
			<button v-if="canAdd" @click="$emit('add')" class="btn-primary shrink-0">
				<span class="material-symbols-outlined !text-[18px]">add</span>
				{{ addLabel }}
			</button>
		</div>

		<div class="table-card">
			<div v-if="!rows.length" class="empty-state">
				<span class="material-symbols-outlined !text-[28px] text-[#C4C7CC] dark:text-white/25">inbox</span>
				<p class="empty-state-text">{{ search ? `No ${noun} match “${search}”.` : emptyText }}</p>
			</div>

			<template v-else>
				<!-- Below sm the extra columns cannot fit, so each record becomes a
				     row of label/value pairs instead of a sideways scroll. -->
				<ul class="sm:hidden divide-y divide-black/[0.05] dark:divide-white/[0.06]">
					<li v-for="row in pg.rows" :key="row.name" class="px-4 py-3.5 flex items-start justify-between gap-3">
						<div class="min-w-0" :class="clickable && 'cursor-pointer'" @click="clickable && $emit('view', row.name)">
							<p class="text-[14px] font-semibold text-[#17181B] dark:text-white leading-snug">{{ row[titleKey] || row.name }}</p>
							<p v-if="showId && row[titleKey] !== row.name" class="text-[12px] text-[#656A72] dark:text-white/55 mt-0.5">{{ row.name }}</p>
							<p v-for="c in columns" :key="c.key" class="text-[12px] text-[#5C6169] dark:text-white/65 mt-1">
								<span class="text-[#656A72] dark:text-white/50">{{ c.label }}: </span>{{ row[c.key] || c.fallback || '—' }}
							</p>
						</div>
						<div class="shrink-0" @click.stop>
							<RowActions :actions="rowActions(row)" />
						</div>
					</li>
				</ul>

				<div class="hidden sm:block overflow-x-auto table-scroll">
					<table class="w-full">
						<thead>
							<tr class="border-b border-black/[0.07] dark:border-white/10">
								<th class="table-th">{{ titleLabel }}</th>
								<th v-for="c in columns" :key="c.key" class="table-th">{{ c.label }}</th>
								<th class="table-th !text-right">Actions</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="row in pg.rows"
								:key="row.name"
								@click="clickable && $emit('view', row.name)"
								class="border-b last:border-0 border-black/[0.05] dark:border-white/[0.06] hover:bg-black/[0.02] dark:hover:bg-white/[0.04] transition-colors"
								:class="clickable && 'cursor-pointer'"
							>
								<td class="table-td-strong">
									<span class="block">{{ row[titleKey] || row.name }}</span>
									<span v-if="showId && row[titleKey] !== row.name" class="block text-[12px] font-normal text-[#656A72] dark:text-white/55">{{ row.name }}</span>
								</td>
								<td v-for="c in columns" :key="c.key" class="table-td">
									<span :class="!row[c.key] && 'text-[#656A72] dark:text-white/50'">{{ row[c.key] || c.fallback || '—' }}</span>
								</td>
								<td class="table-td !text-right" @click.stop>
									<RowActions :actions="rowActions(row)" />
								</td>
							</tr>
						</tbody>
					</table>
				</div>
			</template>
			<TablePager v-if="pg.total > 0" v-model:page="pg.page" v-model:page-size="pg.size" :total="pg.total" />
		</div>
	</div>
</template>

<script setup>
import TablePager from '@/components/TablePager.vue'
import { usePager } from '@/composables/usePager.js'
/* Seven of the Team & Permissions tabs are the same content type: a named
   reference record with an optional detail column or two. They were seven
   hand-written copies that had drifted apart - different header casing, row
   padding and empty-state wording on each. One component so they cannot. */
import RowActions from '@/components/RowActions.vue'

const props = defineProps({
	rows: { type: Array, default: () => [] },
	search: { type: String, default: '' },
	placeholder: { type: String, default: 'Search' },
	/* The field holding the human-readable name; falls back to `name`. */
	titleKey: { type: String, default: 'name' },
	titleLabel: { type: String, default: 'Name' },
	/* Extra columns as [{ label, key, fallback }]. */
	columns: { type: Array, default: () => [] },
	/* The plural noun used in the "nothing matched" line. */
	noun: { type: String, default: 'records' },
	emptyText: { type: String, default: 'Nothing here yet.' },
	addLabel: { type: String, default: 'Add' },
	showId: { type: Boolean, default: false },
	clickable: { type: Boolean, default: false },
	canAdd: { type: Boolean, default: false },
	canEdit: { type: Boolean, default: false },
	canDelete: { type: Boolean, default: false },
})

const emit = defineEmits(['update:search', 'add', 'edit', 'delete', 'view'])

function rowActions(row) {
	const name = row[props.titleKey] || row.name
	return [
		{ label: 'View', icon: 'visibility', show: props.clickable, onClick: () => emit('view', row.name) },
		{ label: 'Edit', icon: 'edit', show: props.canEdit, onClick: () => emit('edit', row.name) },
		{ divider: true },
		{
			label: 'Delete',
			icon: 'delete',
			danger: true,
			show: props.canDelete,
			onClick: () => emit('delete', row.name, name),
		},
	]
}

/* Client-side paging for the list(s) above (TablePager). */
const pg = usePager(() => props.rows)
</script>
