import { reactive, watch } from 'vue'

/* Server-side paging for a list whose rows come from the API, one page at
   a time (LIMIT x OFFSET y), feeding TablePager.

     const pager = useServerPager((page, size) => store.fetchPage(page, size))
     <tr v-for="row in pager.state.rows">
     <TablePager v-model:page="pager.state.page" v-model:page-size="pager.state.size" :total="pager.state.total" />

   `fetchFn(page, size)` must resolve to { rows, total }. While a new page
   is being fetched the previous rows stay visible (stale-while-revalidate)
   with `loading` true, so the table does not flash empty on every page
   turn. A stale fetch (one that started on an older page) is dropped when
   it resolves, so a slow page 1 can never overwrite a fresh page 2. */
export function useServerPager(fetchFn, { size = 10 } = {}) {
	let seq = 0
	const state = reactive({
		page: 1,
		size,
		total: 0,
		rows: [],
		loading: false,
	})

	async function fetchPage() {
		const mySeq = ++seq
		state.loading = true
		try {
			const res = await fetchFn(state.page, state.size)
			if (mySeq !== seq) return // a newer fetch started; drop this one
			state.rows = res?.rows || []
			state.total = Number(res?.total) || 0
		} finally {
			if (mySeq === seq) state.loading = false
		}
	}

	function nextPage() {
		if (state.page < Math.max(1, Math.ceil(state.total / state.size))) state.page++
	}

	function prevPage() {
		if (state.page > 1) state.page--
	}

	function setPageSize(v) {
		state.size = Number(v) || size
		state.page = 1
	}

	// Reset to page 1 when the total shrinks below the current page
	// (e.g. a filter was applied), so the pager never points at an empty
	// last page.
	watch(
		() => [state.total, state.size],
		() => {
			const last = Math.max(1, Math.ceil(state.total / (Number(state.size) || size)))
			if (state.page > last) state.page = last
		},
	)

	watch(
		() => [state.page, state.size],
		() => {
			fetchPage()
		},
	)

	return { state, fetchPage, nextPage, prevPage, setPageSize }
}
