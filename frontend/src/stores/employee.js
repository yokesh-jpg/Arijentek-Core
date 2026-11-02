import { defineStore } from "pinia";
import { createResource } from "frappe-ui";
import { ref, watch } from "vue";



export const useEmployeeStore = defineStore("employee", () => {
	const isGuest = typeof window !== "undefined" && (!window.frappe_user || window.frappe_user === "Guest");
	const employee = ref(null);
	const ready = ref(isGuest);

	const employeeResource = createResource({
		url: "arijentek_core.api.attendance.get_current_employee",
		auto: !isGuest,
		onSuccess(data) {
			if (data) {
				employee.value = data;
			} else {
				employee.value = null;
			}
			ready.value = true;
		},
		onError(err) {
			console.error("Employee fetch error:", err);
			employee.value = null;
			ready.value = true;
		},
	});

	function init() {
		if (typeof window !== "undefined" && (!window.frappe_user || window.frappe_user === "Guest")) {
			employee.value = null;
			ready.value = true;
			return Promise.resolve();
		}
		if (ready.value) {
			return Promise.resolve();
		}
		return new Promise((resolve) => {
			const unwatch = watch(ready, (val) => {
				if (val) {
					unwatch();
					resolve();
				}
			});
		});
	}

	function refresh() {
		employeeResource.fetch();
	}

	return {
		employee,
		ready,
		init,
		refresh,
	};
});
