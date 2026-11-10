import { createApp } from "vue";
import { createPinia } from "pinia";
import { setConfig, frappeRequest, resourcesPlugin } from "frappe-ui";
import { safeFrappeRequest } from "./utils/safeFrappeRequest";
import { VueQueryPlugin } from "@tanstack/vue-query";
import App from "./App.vue";
import router from "./router";
import "./index.css";

// Handle chunk load errors (asset mismatch after redeploy/long idle)
window.addEventListener(
	"error",
	(e) => {
		const errors = ["Failed to fetch dynamically imported module", "Importing a module script failed"];
		if (errors.some((err) => e.message?.includes(err))) {
			const lastReload = sessionStorage.getItem("last_chunk_error_reload");
			const now = Date.now();
			if (!lastReload || now - parseInt(lastReload, 10) > 10000) {
				sessionStorage.setItem("last_chunk_error_reload", now.toString());
				window.location.reload();
			}
		}
	},
	true
);

const pinia = createPinia();
const app = createApp(App);

// Register safe resource fetcher to guard createResource calls against raw HTML/TypeError crashes
setConfig("resourceFetcher", safeFrappeRequest);

// Global Vue Runtime Error Boundary
app.config.errorHandler = (err, instance, info) => {
	console.error("[Global Vue Error Boundary Intercepted]:", err, info);
};

// Global Unhandled Async Promise Rejection Shield
window.addEventListener("unhandledrejection", (event) => {
	console.warn("[Global Unhandled Rejection Shielded]:", event.reason);
	event.preventDefault();
});

app.use(pinia);
app.use(router);
app.use(resourcesPlugin);
app.use(VueQueryPlugin, {
	queryClientConfig: {
		defaultOptions: {
			queries: {
				staleTime: 1000 * 60 * 5, // 5 mins fresh cache
				gcTime: 1000 * 60 * 15,   // 15 mins inactive retention
				refetchOnWindowFocus: false,
			},
		},
	},
});

router.isReady().then(() => {
	app.mount("#app");
});

import { initializeWebPush } from "../notification/webPush";

// Web Push Registration - only for authenticated sessions
if (typeof window !== "undefined" && window.frappe_user && window.frappe_user !== "Guest") {
	initializeWebPush(frappeRequest);
}
