import { defineStore } from "pinia";
import { createResource } from "frappe-ui";
import { ref } from "vue";

/*
 * Brand store — the client never hardcodes a company/brand label.
 * The display name always comes from the backend (get_company_name) and is
 * cached in localStorage so the shell renders without a flash on revisits.
 * Logout clears localStorage, so the cache never outlives a session.
 */

const COMPANY_NAME_CACHE_KEY = "portal_company_name";

function readCachedCompanyName() {
	try {
		if (typeof localStorage !== "undefined") return localStorage.getItem(COMPANY_NAME_CACHE_KEY) || "";
	} catch (e) {
		console.warn("Failed to read cached company name:", e);
	}
	return "";
}

export const useBrandStore = defineStore("brand", () => {
	const companyName = ref(readCachedCompanyName());

	const companyResource = createResource({
		url: "arijentek_core.api.common_functions.get_company_name",
		onSuccess(data) {
			const name = data?.company_name || "";
			if (!name) return;
			companyName.value = name;
			try {
				localStorage.setItem(COMPANY_NAME_CACHE_KEY, name);
			} catch (e) {}
		},
		onError(err) {
			console.warn("Company name fetch failed:", err);
		},
	});

	function fetchCompanyName() {
		if (!companyName.value) {
			companyResource.fetch();
		}
	}

	return { companyName, fetchCompanyName };
});
