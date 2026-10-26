import { defineStore } from "pinia";
import { createResource, frappeRequest } from "frappe-ui";
import { ref, watch } from "vue";
import { unsubscribeWebPush } from "../../notification/webPush";

export const useAuthStore = defineStore("auth", () => {
	const user = ref(null);
	const isLoggedIn = ref(false);
	const ready = ref(false);

	const userResource = createResource({
		url: "arijentek_core.api.user_info.get_user_info",
		method: "GET",
		auto: true,
		cache: false,
		onSuccess(data) {
			if (!data || data === "Guest" || data?.user === "Guest") {
				user.value = null;
				isLoggedIn.value = false;
			} else if (typeof data === "string") {
				user.value = { full_name: data, email: data };
				isLoggedIn.value = true;
			} else {
				user.value = data;
				isLoggedIn.value = true;
			}
			ready.value = true;
		},
		onError(err) {
			console.error("Auth Error:", err);
			user.value = null;
			isLoggedIn.value = false;
			ready.value = true;
		},
	});

	const logoutResource = createResource({
		url: "logout",
		onSuccess() {
			user.value = null;
			isLoggedIn.value = false;
			window.location.reload();
		},
	});

	async function logout() {
		try {
			await unsubscribeWebPush(frappeRequest);
		} catch (err) {
			console.error("Failed to unsubscribe push", err);
		}
		logoutResource.submit();
	}

	function init() {
		return new Promise((resolve) => {
			if (ready.value) {
				resolve();
			} else {
				const unwatch = watch(ready, (val) => {
					if (val) {
						unwatch();
						resolve();
					}
				});
			}
		});
	}

	return {
		user,
		isLoggedIn,
		ready,
		userResource,
		logout,
		init,
	};
});
