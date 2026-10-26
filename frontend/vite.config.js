import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";
import frappeui from "frappe-ui/vite";

export default defineConfig({
	base: "/assets/arijentek_core/employee-portal/",
	server: {
		port: 8081,
		strictPort: true,
		host: true,
		proxy: {
			"^/(app|api|assets|files|private)": {
				target: "http://127.0.0.1:8000",
				ws: true,
				changeOrigin: true,
				headers: {
					"X-Frappe-Site-Name": "arijentek.local",
				},
			},
		},
	},
	plugins: [
		frappeui({
			lucideIcons: true,
			frappeProxy: true,
			frappeTypes: true,
			jinjaBootData: true,
			buildConfig: false,
		}),
		vue(),
	],
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "./src"),
		},
	},
	build: {
		outDir: path.resolve(__dirname, "../arijentek_core/public/employee-portal"),
		emptyOutDir: true,
		target: "es2015",
		manifest: true,
	},
	optimizeDeps: {
		include: ["frappe-ui > feather-icons", "showdown", "engine.io-client"],
	},
	test: {
		globals: true,
		environment: "jsdom",
		setupFiles: ["./tests/setup.js"],
		include: ["tests/**/*.spec.js"],
		alias: {
			"@": path.resolve(__dirname, "./src"),
		},
	},
});
