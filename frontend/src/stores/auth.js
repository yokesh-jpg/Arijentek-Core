import { defineStore } from "pinia";
import { createResource, frappeRequest } from "frappe-ui";
import { ref, watch } from "vue";
import { unsubscribeWebPush } from "../../notification/webPush";

function clearClientCookies() {
	if (typeof document === "undefined") return;
	const cookies = document.cookie.split(";");
	const paths = ["/", "/employee-portal", "/api"];
	for (const cookie of cookies) {
		const eqPos = cookie.indexOf("=");
		const name = eqPos > -1 ? cookie.substr(0, eqPos).trim() : cookie.trim();
		if (!name) continue;
		for (const p of paths) {
			document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=${p};`;
			if (typeof window !== "undefined" && window.location?.hostname) {
				document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=${p}; domain=${window.location.hostname};`;
			}
		}
	}
}

function clearClientSession() {
	try {
		if (typeof sessionStorage !== "undefined") {
			sessionStorage.clear();
		}
	} catch (e) {
		console.warn("Failed to clear sessionStorage:", e);
	}

	try {
		if (typeof localStorage !== "undefined") {
			// Retain visual preferences (theme, text size)
			const preservedTheme = localStorage.getItem("portal_theme");
			const preservedText = localStorage.getItem("portal_text_large");

			const keysToRemove = [];
			for (let i = 0; i < localStorage.length; i++) {
				const key = localStorage.key(i);
				if (key && key !== "portal_theme" && key !== "portal_text_large") {
					keysToRemove.push(key);
				}
			}
			keysToRemove.forEach((k) => localStorage.removeItem(k));

			if (preservedTheme) localStorage.setItem("portal_theme", preservedTheme);
			if (preservedText) localStorage.setItem("portal_text_large", preservedText);
		}
	} catch (e) {
		console.warn("Failed to clear localStorage:", e);
	}

	if (typeof window !== "undefined") {
		window.frappe_user = "Guest";
		window.user = null;
		clearClientCookies();
	}
}

function broadcastAuthSync(payload) {
	try {
		if (typeof localStorage !== "undefined") {
			localStorage.setItem("portal_session_sync", JSON.stringify(payload));
		}
	} catch (e) {}
	try {
		if (typeof BroadcastChannel !== "undefined") {
			const ch = new BroadcastChannel("portal_session_sync_channel");
			ch.postMessage(payload);
			ch.close();
		}
	} catch (e) {}
}

export const useAuthStore = defineStore("auth", () => {
	const user = ref(null);
	const isLoggedIn = ref(false);
	const ready = ref(false);

	function handleCrossTabSync(payload) {
		if (!payload || !payload.action) return;

		if (payload.action === "logout") {
			if (isLoggedIn.value) {
				user.value = null;
				isLoggedIn.value = false;
				ready.value = false;
				clearClientSession();
				if (typeof window !== "undefined") {
					window.location.href = "/employee-portal/login";
				}
			}
		} else if (payload.action === "login" || payload.action === "new_login") {
			const currentUserId = user.value?.user || user.value?.email;
			if (currentUserId) {
				if (payload.user && payload.user.toLowerCase() !== currentUserId.toLowerCase()) {
					console.warn("Different user login detected in sibling tab. Resetting session.");
					user.value = null;
					isLoggedIn.value = false;
					ready.value = false;
					clearClientSession();
					if (typeof window !== "undefined") {
						window.location.href = "/employee-portal/login";
					}
				} else if (payload.action === "new_login") {
					fetch("/api/method/arijentek_core.api.user_info.get_user_info")
						.then((r) => r.json())
						.then((res) => {
							const newUser = res?.message?.user || res?.message;
							if (
								!newUser ||
								newUser === "Guest" ||
								(typeof newUser === "string" && newUser.toLowerCase() !== currentUserId.toLowerCase())
							) {
								user.value = null;
								isLoggedIn.value = false;
								ready.value = false;
								clearClientSession();
								if (typeof window !== "undefined") {
									window.location.href = "/employee-portal/login";
								}
							}
						})
						.catch(() => {});
				}
			}
		}
	}

	let syncListenersAttached = false;
	function setupCrossTabSync() {
		if (typeof window === "undefined" || syncListenersAttached) return;
		syncListenersAttached = true;

		window.addEventListener("storage", (e) => {
			if (e.key === "portal_session_sync" && e.newValue) {
				try {
					const data = JSON.parse(e.newValue);
					handleCrossTabSync(data);
				} catch (_) {}
			} else if (e.key === "portal_active_user") {
				const newActiveUser = e.newValue;
				const currentUserId = user.value?.user || user.value?.email;
				if (!newActiveUser && isLoggedIn.value) {
					handleCrossTabSync({ action: "logout" });
				} else if (
					newActiveUser &&
					currentUserId &&
					newActiveUser.toLowerCase() !== currentUserId.toLowerCase()
				) {
					handleCrossTabSync({ action: "login", user: newActiveUser });
				}
			}
		});

		if (typeof BroadcastChannel !== "undefined") {
			try {
				const syncChannel = new BroadcastChannel("portal_session_sync_channel");
				syncChannel.onmessage = (event) => {
					handleCrossTabSync(event.data);
				};
			} catch (_) {}
		}

		if (typeof document !== "undefined") {
			document.addEventListener("visibilitychange", () => {
				if (!document.hidden && isLoggedIn.value) {
					try {
						const activeUser = localStorage.getItem("portal_active_user");
						const currentUserId = user.value?.user || user.value?.email;
						if (!activeUser) {
							handleCrossTabSync({ action: "logout" });
						} else if (
							currentUserId &&
							activeUser.toLowerCase() !== currentUserId.toLowerCase()
						) {
							handleCrossTabSync({ action: "login", user: activeUser });
						}
					} catch (_) {}
				}
			});
		}
	}

	setupCrossTabSync();

	const userResource = createResource({
		url: "arijentek_core.api.user_info.get_user_info",
		method: "GET",
		auto: true,
		cache: false,
		onSuccess(data) {
			if (!data || data === "Guest" || data?.user === "Guest") {
				user.value = null;
				isLoggedIn.value = false;
				try {
					localStorage.removeItem("portal_active_user");
				} catch (e) {}
			} else {
				const canonicalUser =
					typeof data === "string" ? data : data.user || data.name || data.email;
				user.value =
					typeof data === "string" ? { full_name: data, email: data, user: data } : data;
				isLoggedIn.value = true;
				if (canonicalUser) {
					try {
						const prevActiveUser = localStorage.getItem("portal_active_user");
						localStorage.setItem("portal_active_user", canonicalUser);
						if (
							prevActiveUser &&
							prevActiveUser.toLowerCase() !== canonicalUser.toLowerCase()
						) {
							broadcastAuthSync({
								action: "login",
								user: canonicalUser,
								timestamp: Date.now(),
							});
						}
					} catch (e) {}
				}
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
		method: "POST",
		onSuccess() {
			user.value = null;
			isLoggedIn.value = false;
			ready.value = false;
			clearClientSession();
			if (typeof window !== "undefined") {
				window.location.href = "/employee-portal/login";
			}
		},
		onError() {
			user.value = null;
			isLoggedIn.value = false;
			ready.value = false;
			clearClientSession();
			if (typeof window !== "undefined") {
				window.location.href = "/employee-portal/login";
			}
		},
	});

	async function logout() {
		try {
			await unsubscribeWebPush(frappeRequest);
		} catch (err) {
			console.error("Failed to unsubscribe push:", err);
		}

		broadcastAuthSync({ action: "logout", timestamp: Date.now() });
		try {
			localStorage.removeItem("portal_active_user");
		} catch (e) {}

		try {
			await fetch("/api/method/logout", {
				method: "POST",
				headers: {
					"X-Frappe-CSRF-Token": window.csrf_token || "",
				},
			});
		} catch (err) {
			console.warn("Server logout request failed, continuing cleanup:", err);
		}

		try {
			await fetch("/api/method/arijentek_core.api.auth.logout", {
				method: "POST",
				headers: {
					"X-Frappe-CSRF-Token": window.csrf_token || "",
				},
			});
		} catch (e) {
			// Fallback attempt ignored
		}

		user.value = null;
		isLoggedIn.value = false;
		ready.value = false;
		clearClientSession();

		if (typeof window !== "undefined") {
			window.location.href = "/employee-portal/login";
		}
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
