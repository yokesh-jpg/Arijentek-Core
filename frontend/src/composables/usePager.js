import { computed, reactive, unref, watch } from 'vue'

/* Client-side paging for a list that already sits in memory, feeding
   TablePager. `source` returns the full (filtered) array, or a ref to it.

     const pg = usePager(() => filteredRows)
     <tr v-for="row in pg.rows">
     <TablePager v-model:page="pg.page" v-model:page-size="pg.size" :total="pg.total" />

   A filter that shrinks the list below the current page drops back to the
   last page that still has rows, rather than showing an empty one. */
export function usePager(source, size = 10) {
	const all = computed(() => unref(source()) || [])
	const state = reactive({
		page: 1,
		size,
		total: computed(() => all.value.length),
		rows: computed(() => {
			const n = Number(state.size) || size
			const start = (state.page - 1) * n
			return all.value.slice(start, start + n)
		}),
	})
	watch(
		() => [state.total, state.size],
		() => {
			const last = Math.max(1, Math.ceil(state.total / (Number(state.size) || size)))
			if (state.page > last) state.page = last
		},
	)
	return state
}
