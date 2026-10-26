import { defineStore } from "pinia";
import { createResource } from "frappe-ui";
import { ref, watch } from "vue";



export const useEmployeeStore = defineStore("employee", () => {
	const employee = ref(null);
	const ready = ref(false);

	const employeeResource = createResource({
		url: "arijentek_core.api.attendance.get_current_employee",
		auto: true,
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
