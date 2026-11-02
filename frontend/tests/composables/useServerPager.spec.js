import { describe, it, expect } from "vitest";
import { useServerPager } from "@/composables/useServerPager";

/* The pager must start in the loading state (the first paint is a pending
   fetch, so DataTable must not flash its empty state) and must settle that
   state on success, on failure, and when a stale fetch is dropped. */
describe("useServerPager", () => {
	it("starts loading before the first fetch", () => {
		const pager = useServerPager(async () => ({ rows: [], total: 0 }));
		expect(pager.state.loading).toBe(true);
		expect(pager.state.rows).toEqual([]);
	});

	it("can opt out of the initial loading state", () => {
		const pager = useServerPager(async () => ({ rows: [], total: 0 }), { initialLoading: false });
		expect(pager.state.loading).toBe(false);
	});

	it("clears loading and stores rows/total after a successful fetch", async () => {
		const pager = useServerPager(async () => ({ rows: [{ name: "ATT-0001" }], total: 1 }));
		await pager.fetchPage();
		expect(pager.state.loading).toBe(false);
		expect(pager.state.rows).toEqual([{ name: "ATT-0001" }]);
		expect(pager.state.total).toBe(1);
	});

	it("clears loading when the fetch rejects", async () => {
		const pager = useServerPager(async () => {
			throw new Error("network down");
		});
		await expect(pager.fetchPage()).rejects.toThrow("network down");
		expect(pager.state.loading).toBe(false);
	});

	it("drops a stale fetch when a newer one started", async () => {
		let resolveFirst;
		let calls = 0;
		const pager = useServerPager(() => {
			calls += 1;
			if (calls === 1) return new Promise((resolve) => (resolveFirst = resolve));
			return Promise.resolve({ rows: [{ name: "ATT-0002" }], total: 2 });
		});

		const first = pager.fetchPage();
		const second = pager.fetchPage();
		await second;
		resolveFirst({ rows: [{ name: "ATT-0001" }], total: 99 });
		await first;

		expect(pager.state.rows).toEqual([{ name: "ATT-0002" }]);
		expect(pager.state.total).toBe(2);
		expect(pager.state.loading).toBe(false);
	});
});
