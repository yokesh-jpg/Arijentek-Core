<template>
	<div class="table-card">
		<!-- Loading: a spinner while a page is being fetched and there are no
		     rows to show yet (stale-while-revalidate keeps old rows visible
		     while a new page loads, so the table never flashes empty). -->
		<div v-if="loading && !rows.length" class="empty-state">
			<span class="material-symbols-outlined !text-[28px] text-accent dark:text-accent-light animate-spin">progress_activity</span>
			<p class="empty-state-text">Loading…</p>
		</div>

		<!-- Empty: no rows and not loading. -->
		<div v-else-if="!rows.length" class="empty-state">
			<span class="material-symbols-outlined !text-[28px] text-[#C4C7CC] dark:text-white/25">event_busy</span>
			<p class="empty-state-text">{{ emptyText }}</p>
		</div>

		<!-- Table -->
		<div v-else class="overflow-x-auto table-scroll">
			<table class="w-full border-collapse">
				<thead class="table-head">
					<tr>
						<th
							v-for="col in visibleColumns"
							:key="col.key"
							class="table-th"
							:class="col.className"
							:style="col.align ? { textAlign: col.align } : {}"
						>
							{{ col.label }}
						</th>
						<th v-if="hasActions" class="table-th text-right">Actions</th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="row in rows"
						:key="rowKeyFn(row)"
						:class="onRowClick ? 'table-row cursor-pointer' : 'table-row'"
						@click="onRowClick && onRowClick(row)"
					>
						<td
							v-for="col in visibleColumns"
							:key="col.key"
							class="table-td"
							:class="col.className"
							:style="col.align ? { textAlign: col.align } : {}"
						>
							<!-- Per-column custom cell: `#cell-<key>` with `:row`
							     and `:col`; falls back to the raw value. -->
							<slot :name="`cell-${col.key}`" :row="row" :col="col">
								{{ row[col.key] }}
							</slot>
						</td>
						<td v-if="hasActions" class="table-td !text-right w-[104px]" @click.stop>
							<RowActions :actions="actionsFor(row)" :max-inline="1" />
						</td>
					</tr>
				</tbody>
			</table>
		</div>

		<!-- Pager: a custom pager slot, or the default TablePager. In
		     server-side paging the parent owns the page state, so the pager
		     just re-emits the change. -->
		<slot v-if="showPager" name="pager">
			<!-- TablePager emits `update:pageSize` (camelCase), so the listener
			     must match that name exactly or the size change never reaches
			     the parent. -->
			<TablePager
				:page="page"
				:page-size="pageSize"
				:total="total"
				:sizes="sizes"
				@update:page="emit('update:page', $event)"
				@update:pageSize="emit('update:page-size', $event)"
			/>
		</slot>
	</div>
</template>

<script setup>
/* One table for every list in the portal. A view declares its columns
   (labels, alignment, hidden columns), its rows, and its row actions, and
   the table renders the rest. A single action sits on the row as an icon;
   two or more fold into a More dropdown (RowActions, maxInline=1), so a
   row never shows delete one mis-click from edit. Cells that need a custom
   render (a status chip, a date + weekday) take a `#cell-<key>` slot and
   fall back to the raw value. */
import { computed } from 'vue'
import TablePager from './TablePager.vue'
import RowActions from './RowActions.vue'

const props = defineProps({
	/* [{ key, label, align?, className?, hidden? }] - the order of the
	   array is the order of the columns; `hidden` drops a column. */
	columns: { type: Array, default: () => [] },
	/* The rows for the current page. */
	rows: { type: Array, default: () => [] },
	/* A static array of actions, or a function (row) => actions so each row
	   can carry its own (e.g. permission-gated). */
	actions: { type: [Array, Function], default: null },
	/* A string key or a function (row) => key, defaulting to 'name'. */
	rowKey: { type: [String, Function], default: 'name' },
	/* Called when a row is clicked; the Actions cell stops propagation. */
	onRowClick: { type: Function, default: null },
	/* True while a page is being fetched. */
	loading: { type: Boolean, default: false },
	/* Shown when there are no rows and it is not loading. */
	emptyText: { type: String, default: 'No records.' },
	/* Show the pager (default TablePager). */
	showPager: { type: Boolean, default: true },
	/* Total number of rows (server-side paging). */
	total: { type: Number, default: 0 },
	/* Current page (server-side paging). */
	page: { type: Number, default: 1 },
	/* Rows per page (server-side paging). */
	pageSize: { type: [Number, String], default: null },
	/* Page-size options for the pager. */
	sizes: { type: Array, default: () => [10, 20, 50] },
})
const emit = defineEmits(['update:page', 'update:page-size'])

const visibleColumns = computed(() => props.columns.filter((c) => c.hidden !== true))

const hasActions = computed(() => {
	if (typeof props.actions === 'function') return true
	return Array.isArray(props.actions) && props.actions.length > 0
})

function actionsFor(row) {
	return typeof props.actions === 'function' ? props.actions(row) : props.actions || []
}

function rowKeyFn(row) {
	return typeof props.rowKey === 'function' ? props.rowKey(row) : row[props.rowKey]
}
</script>
