import { createApp } from "vue";
import { createPinia } from "pinia";
import { setConfig, frappeRequest, resourcesPlugin } from "frappe-ui";
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

setConfig("resourceFetcher", frappeRequest);

app.use(pinia);
app.use(router);
app.use(resourcesPlugin);

app.mount("#app");

import { initializeWebPush } from "../notification/webPush";

// Web Push Registration
initializeWebPush(frappeRequest);
