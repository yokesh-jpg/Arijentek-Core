import { reactive, computed, watch, onUnmounted } from 'vue'

/**
 * Standardized Server-Side Infinite Scroll & Load More Pager.
 *
 * @param {Function} fetchFn - Async function (page, pageSize) => Promise<{ items: Array, total: number, hasMore?: boolean, extra?: any }>
 * @param {Object} options - Configuration options
 * @param {number} [options.pageSize=50] - Number of records per batch
 * @param {string} [options.itemKey='id'] - Optional key used to deduplicate items when appending
 * @param {boolean} [options.initialLoading=true] - Initial loading state
 */
export function useInfiniteServerPager(fetchFn, { pageSize = 50, itemKey = 'employee', initialLoading = false } = {}) {
	let seq = 0
	let observer = null

	const state = reactive({
		page: 1,
		pageSize,
		total: 0,
		items: [],
		loadingInitial: initialLoading,
		loadingMore: false,
		hasMore: false,
		extra: null,
		error: null,
	})

	const isLoading = computed(() => state.loadingInitial || state.loadingMore)

	async function resetAndFetch() {
		const mySeq = ++seq
		state.page = 1
		state.loadingInitial = true
		state.loadingMore = false
		state.error = null

		try {
			const res = await fetchFn(1, state.pageSize)
			if (mySeq !== seq) return // Newer fetch started

			state.items = res?.items || []
			state.total = Number(res?.total) || (res?.items?.length || 0)
			state.hasMore = res?.hasMore !== undefined ? Boolean(res.hasMore) : state.items.length < state.total
			state.extra = res?.extra || null
		} catch (err) {
			if (mySeq === seq) {
				state.error = err
				console.error('[useInfiniteServerPager] Initial fetch error:', err)
			}
		} finally {
			if (mySeq === seq) {
				state.loadingInitial = false
			}
		}
	}

	async function loadMore() {
		if (state.loadingInitial || state.loadingMore || !state.hasMore) return

		const mySeq = ++seq
		state.loadingMore = true
		state.error = null
		const nextPage = state.page + 1

		try {
			const res = await fetchFn(nextPage, state.pageSize)
			if (mySeq !== seq) return

			const newItems = res?.items || []
			if (newItems.length > 0) {
				if (itemKey) {
					const existingKeys = new Set(state.items.map((it) => it[itemKey]))
					for (const item of newItems) {
						if (!existingKeys.has(item[itemKey])) {
							state.items.push(item)
							existingKeys.add(item[itemKey])
						}
					}
				} else {
					state.items.push(...newItems)
				}
				state.page = nextPage
			}

			if (res?.total !== undefined) {
				state.total = Number(res.total)
			}
			state.hasMore = res?.hasMore !== undefined ? Boolean(res.hasMore) : state.items.length < state.total
			if (res?.extra) state.extra = res.extra
		} catch (err) {
			if (mySeq === seq) {
				state.error = err
				console.error('[useInfiniteServerPager] Load more error:', err)
			}
		} finally {
			if (mySeq === seq) {
				state.loadingMore = false
			}
		}
	}

	function cleanupObserver() {
		if (observer) {
			observer.disconnect()
			observer = null
		}
	}

	function attachObserver(sentinelRef, scrollContainerRef = null) {
		cleanupObserver()
		if (typeof window === 'undefined' || !window.IntersectionObserver) return

		const target = sentinelRef?.value?.$el || sentinelRef?.value || sentinelRef
		if (!target) return

		const root = scrollContainerRef?.value?.$el || scrollContainerRef?.value || scrollContainerRef || null

		observer = new IntersectionObserver(
			(entries) => {
				const entry = entries[0]
				if (entry && entry.isIntersecting && state.hasMore && !state.loadingInitial && !state.loadingMore) {
					loadMore()
				}
			},
			{
				root,
				rootMargin: '200px', // Pre-fetch 200px before scrolling to bottom
				threshold: 0.05,
			}
		)

		observer.observe(target)
	}

	onUnmounted(() => {
		cleanupObserver()
	})

	return {
		state,
		isLoading,
		resetAndFetch,
		loadMore,
		attachObserver,
		cleanupObserver,
	}
}

