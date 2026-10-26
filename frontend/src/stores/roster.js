import { notify, ask } from '@/utils/feedback.js'
import { defineStore } from "pinia";
import { createResource } from "frappe-ui";
import { ref, computed, shallowRef } from "vue";

export const useRosterStore = defineStore("roster", () => {
	const weeklySchedule = ref([]);
	const weeklySummary = ref(null);
	const weeklyNotes = ref([]); // swap requests and manager notes for the week
	const loading = ref(false);
	const error = ref(null);
	const currentWeekStart = ref(null); // "YYYY-MM-DD"

	// Monthly view state
	const monthlyCalendar = ref([]);
	const monthlySummary = ref(null);
	const monthlyLoading = ref(false);
	const monthlyYear = ref(new Date().getFullYear());
	const monthlyMonth = ref(new Date().getMonth()); // 0-indexed

	const weeklyRosterResource = createResource({
		url: "arijentek_core.api.roster.get_weekly_roster",
		auto: false,
		onSuccess(data) {
			weeklySchedule.value = data?.schedule ?? [];
			weeklySummary.value = data?.summary || null;
			weeklyNotes.value = data?.notes ?? [];
		},
		onError(err) {
			console.error("Weekly roster fetch error:", err);
			error.value = err;
		},
	});

	const monthlyRosterResource = createResource({
		url: "arijentek_core.api.roster.get_monthly_roster",
		auto: false,
		onSuccess(data) {
			monthlyCalendar.value = data?.calendar ?? [];
			monthlySummary.value = data?.summary || null;
		},
		onError(err) {
			console.error("Monthly roster fetch error:", err);
		},
	});

	// Shift Request state
	const shiftRequests = ref([]);
	const shiftRequestLoading = ref(false);
	const approverInfo = ref(null); // { name, message }
	const shiftApprovers = ref([]);
	const defaultShiftApprover = ref(null);
	const showRequestModal = ref(false);
	const editingRequestId = ref(null);
	const shiftTypes = ref([]);
	const submissionError = ref(null);
	const submitting = ref(false);
	const cancelingId = ref(null);

	// Add Roster state
	const showAddRosterModal = ref(false);
	const addRosterSubmitting = ref(false);
	const addRosterError = ref(null);
	const currentEmployeeId = ref(null);
	const frequencyOptions = ref([]);
	const addRosterForm = ref({
		employee: "",
		shift_type: "",
		start_date: "",
		end_date: "",
		shift_location: "",
		schedule_enabled: false,
		repeat_on_days: [],
		frequency: "Every Week",
	});

	// Shift Matrix state
	const shiftMatrix = ref({ employees: [], days: [] });
	const shiftMatrixLoading = ref(false);
	const shiftMatrixMonth = ref(new Date().getMonth() + 1);
	const shiftMatrixYear = ref(new Date().getFullYear());
	const shiftMatrixFilters = ref({ department: "", designation: "" });
	
	// Bulk Assign state
	const showBulkAssignModal = ref(false);
	const bulkAssignSubmitting = ref(false);
	const bulkAssignError = ref(null);
	const bulkAssignResult = ref(null);
	
	const deptDesignationList = ref({ departments: [], designations: [] });

	// Employee and shift location dropdowns for Add Roster
	const addRosterEmployees = ref([]);
	const shiftLocations = ref([]);

	const shiftRequestsResource = createResource({
		url: "arijentek_core.api.roster.get_shift_requests",
		auto: false,
		onSuccess(data) {
			shiftRequests.value = data ?? [];
		},
		onError(err) {
			console.error("Shift requests fetch error:", err);
		},
	});

	const createRequestResource = createResource({
		url: "arijentek_core.api.roster.create_shift_request",
		onSuccess() {
			shiftRequestsResource.fetch();
		},
	});

	const updateRequestResource = createResource({
		url: "arijentek_core.api.roster.update_shift_request",
		onSuccess() {
			shiftRequestsResource.fetch();
		},
	});

	const cancelRequestResource = createResource({
		url: "arijentek_core.api.roster.cancel_shift_request",
		onSuccess() {
			shiftRequestsResource.fetch();
		},
	});

	const updateRequestStatusResource = createResource({
		url: "arijentek_core.api.roster.update_shift_request_status",
		onSuccess() {
			shiftRequestsResource.fetch();
		},
	});

	const checkShiftConflictResource = createResource({ url: "arijentek_core.api.roster.check_shift_conflict" });


	const shiftApproversResource = createResource({
		url: "arijentek_core.api.roster.get_shift_request_approvers",
		auto: false,
		onSuccess(data) {
			shiftApprovers.value = data?.approvers ?? [];
			defaultShiftApprover.value = data?.default_approver ?? null;
		},
		onError(err) {
			console.error("Shift approvers fetch error:", err);
		},
	});

	const approverResource = createResource({
		url: "hrms.api.get_shift_request_approvers",
		auto: false,
		onSuccess(data) {
			if (data && data.length > 0) {
				approverInfo.value = { name: data[0].full_name, user: data[0].name };
			} else {
				approverInfo.value = null;
			}
		},
	});

	const shiftTypesResource = createResource({
		url: "arijentek_core.api.roster.get_shift_types",
		auto: false,
		onSuccess(data) {
			shiftTypes.value = data ?? [];
		},
		onError(err) {
			console.error("Shift types fetch error:", err);
		},
	});

	// Add Roster permission check
	const canAddRosterResource = createResource({
		url: "arijentek_core.api.roster.can_add_roster",
		auto: false,
	});

	// Delete Roster permission check
	const canDeleteRosterResource = createResource({
		url: "arijentek_core.api.roster.can_delete_roster",
		auto: false,
	});

	// Edit Roster permission check
	const canEditRosterResource = createResource({
		url: "arijentek_core.api.roster.can_edit_roster",
		auto: false,
	});

	// Manage Shift Location permission check
	const canManageShiftLocationResource = createResource({
		url: "arijentek_core.api.roster.can_manage_shift_location",
		auto: false,
	});

	const isShiftApproverResource = createResource({
		url: "arijentek_core.api.roster.is_shift_approver",
		auto: false,
	});

	// ---------------------------------------------------------------------------
	// Permission resources — Shift Request
	// ---------------------------------------------------------------------------
	const canReadShiftRequestResource = createResource({
		url: "arijentek_core.api.roster.can_read_shift_request",
		auto: false,
	});
	const canCreateShiftRequestResource = createResource({
		url: "arijentek_core.api.roster.can_create_shift_request",
		auto: false,
	});
	const canEditShiftRequestResource = createResource({
		url: "arijentek_core.api.roster.can_edit_shift_request",
		auto: false,
	});
	const canDeleteShiftRequestResource = createResource({
		url: "arijentek_core.api.roster.can_delete_shift_request",
		auto: false,
	});
	const canSubmitShiftRequestResource = createResource({
		url: "arijentek_core.api.roster.can_submit_shift_request",
		auto: false,
	});

	// ---------------------------------------------------------------------------
	// Permission resources — Shift Assignment
	// ---------------------------------------------------------------------------
	const canReadShiftAssignmentResource = createResource({
		url: "arijentek_core.api.roster.can_read_shift_assignment",
		auto: false,
	});
	const canCreateShiftAssignmentResource = createResource({
		url: "arijentek_core.api.roster.can_create_shift_assignment",
		auto: false,
	});
	const canEditShiftAssignmentResource = createResource({
		url: "arijentek_core.api.roster.can_edit_shift_assignment",
		auto: false,
	});
	const canDeleteShiftAssignmentResource = createResource({
		url: "arijentek_core.api.roster.can_delete_shift_assignment",
		auto: false,
	});
	const canSubmitShiftAssignmentResource = createResource({
		url: "arijentek_core.api.roster.can_submit_shift_assignment",
		auto: false,
	});

	// ---------------------------------------------------------------------------
	// Permission resources — Shift Location
	// ---------------------------------------------------------------------------
	const canReadShiftLocationResource = createResource({
		url: "arijentek_core.api.roster.can_read_shift_location",
		auto: false,
	});
	const canCreateShiftLocationResource = createResource({
		url: "arijentek_core.api.roster.can_create_shift_location",
		auto: false,
	});
	const canEditShiftLocationResource = createResource({
		url: "arijentek_core.api.roster.can_edit_shift_location",
		auto: false,
	});
	const canDeleteShiftLocationResource = createResource({
		url: "arijentek_core.api.roster.can_delete_shift_location",
		auto: false,
	});
	const canSubmitShiftLocationResource = createResource({
		url: "arijentek_core.api.roster.can_submit_shift_location",
		auto: false,
	});

	// ---------------------------------------------------------------------------
	// Permission resources — Shift Type
	// ---------------------------------------------------------------------------
	const canReadShiftTypeResource = createResource({
		url: "arijentek_core.api.roster.can_read_shift_type",
		auto: false,
	});
	const canCreateShiftTypeResource = createResource({
		url: "arijentek_core.api.roster.can_create_shift_type",
		auto: false,
	});
	const canEditShiftTypeResource = createResource({
		url: "arijentek_core.api.roster.can_edit_shift_type",
		auto: false,
	});
	const canDeleteShiftTypeResource = createResource({
		url: "arijentek_core.api.roster.can_delete_shift_type",
		auto: false,
	});
	const canSubmitShiftTypeResource = createResource({
		url: "arijentek_core.api.roster.can_submit_shift_type",
		auto: false,
	});

	const allowMultipleShiftsResource = createResource({
		url: "arijentek_core.api.roster.allow_multiple_shifts",
		auto: false,
	});

	// Frequency options resource for Schedule Settings
	const frequencyOptionsResource = createResource({
		url: "arijentek_core.api.roster.get_frequency_options",
		auto: false,
		onSuccess(data) {
			frequencyOptions.value = data ?? [];
		},
		onError(err) {
			console.error("Frequency options fetch error:", err);
		},
	});

	// Shift locations resource for Add Roster dropdown
	const shiftLocationsResource = createResource({
		url: "arijentek_core.api.roster.get_shift_locations",
		auto: false,
		onSuccess(data) {
			shiftLocations.value = data ?? [];
		},
		onError(err) {
			console.error("Shift locations fetch error:", err);
		},
	});

	// Employee list resource for Add Roster dropdown
	const employeeListResource = createResource({
		url: "arijentek_core.api.roster.get_employee_list",
		auto: false,
		onSuccess(data) {
			addRosterEmployees.value = data ?? [];
		},
		onError(err) {
			console.error("Employee list fetch error:", err);
		},
	});

	const deptDesignationResource = createResource({
		url: "arijentek_core.api.roster.get_departments_and_designations",
		auto: false,
		onSuccess(data) {
			deptDesignationList.value = data ?? { departments: [], designations: [] };
		},
	});

	const shiftMatrixResource = createResource({
		url: "arijentek_core.api.roster.get_shift_matrix",
		auto: false,
		onSuccess(data) {
			shiftMatrix.value = data ?? { employees: [], days: [] };
		},
	});

	const bulkAddRosterResource = createResource({
		url: "arijentek_core.api.roster.bulk_add_roster",
		auto: false,
	});

	const addRosterResource = createResource({
		url: "arijentek_core.api.roster.add_roster",
		onSuccess() {
			// Refresh shift requests and weekly roster after adding
			if (currentEmployeeId.value) {
				fetchShiftRequests(currentEmployeeId.value);
				if (currentWeekStart.value) {
					fetchWeekly(currentEmployeeId.value, currentWeekStart.value);
				}
			}
		},
	});

	const deleteRosterResource = createResource({
		url: "arijentek_core.api.roster.delete_roster",
		onSuccess() {
			// Refresh shift requests and weekly roster after deleting
			if (currentEmployeeId.value) {
				fetchShiftRequests(currentEmployeeId.value);
				if (currentWeekStart.value) {
					fetchWeekly(currentEmployeeId.value, currentWeekStart.value);
				}
				fetchMonthly(currentEmployeeId.value, monthlyYear.value, monthlyMonth.value);
			}
		},
	});


	// Computed stats
	const workingDays = computed(() => weeklySummary.value?.total_working_days ?? 0);
	const hoursWorked = computed(() => Number(weeklySummary.value?.total_hours ?? 0));
	const targetHours = computed(() => Number(weeklySummary.value?.target_hours ?? 0));
	const remainingHours = computed(
		() => Math.max(0, Number((targetHours.value - hoursWorked.value).toFixed(1)))
	);

	const monthlyWorkingDays = computed(() => monthlySummary.value?.total_working_days ?? 0);
	const monthlyHoursWorked = computed(() => Number(monthlySummary.value?.total_hours ?? 0));
	const monthlyTargetHours = computed(() => Number(monthlySummary.value?.target_hours ?? 0));
	const monthlyRemainingHours = computed(
		() => Math.max(0, Number((monthlyTargetHours.value - monthlyHoursWorked.value).toFixed(1)))
	);

	// Actions
	async function fetchWeekly(employeeId, weekStartStr) {
		if (!employeeId) return;
		loading.value = true;
		error.value = null;
		try {
			await weeklyRosterResource.submit({
				employee_id: employeeId,
				start_date: weekStartStr,
			});
			currentWeekStart.value = weekStartStr;
		} finally {
			loading.value = false;
		}
	}



	async function fetchMonthly(employeeId, year, month) {
		if (!employeeId) return;
		monthlyLoading.value = true;
		try {
			await monthlyRosterResource.submit({
				employee_id: employeeId,
				year: year,
				month: month,
			});
			monthlyYear.value = year;
			monthlyMonth.value = month;
		} finally {
			monthlyLoading.value = false;
		}
	}

	async function fetchShiftRequests(employeeId) {
		shiftRequestLoading.value = true;
		try {
			await shiftRequestsResource.submit(employeeId ? { employee_id: employeeId } : {});
		} finally {
			shiftRequestLoading.value = false;
		}
	}

	async function fetchShiftApprovers() {
		try {
			await shiftApproversResource.fetch();
		} catch (err) {
			console.error("Failed to fetch shift approvers", err);
		}
	}

	async function fetchApprover(employeeId) {
		if (!employeeId) {
			approverInfo.value = null;
			return;
		}
		try {
			await approverResource.submit({ employee: employeeId });
		} catch (err) {
			approverInfo.value = null;
		}
	}

	async function fetchShiftTypes() {
		try {
			await shiftTypesResource.fetch();
		} catch {
			shiftTypes.value = [];
		}
	}

	async function fetchShiftLocations() {
		try {
			await shiftLocationsResource.fetch();
		} catch {
			shiftLocations.value = [];
		}
	}

	async function fetchAddRosterEmployees() {
		try {
			await employeeListResource.fetch();
		} catch {
			addRosterEmployees.value = [];
		}
	}

	async function checkCanAddRoster() {
		await canAddRosterResource.fetch();
		return canAddRosterResource.data;
	}

	async function checkCanDeleteRoster() {
		await canDeleteRosterResource.fetch();
		return canDeleteRosterResource.data;
	}

	async function checkCanEditRoster() {
		await canEditRosterResource.fetch();
		return canEditRosterResource.data;
	}

	async function checkCanManageShiftLocation() {
		await canManageShiftLocationResource.fetch();
		return canManageShiftLocationResource.data;
	}


	async function checkIsShiftApprover() {
		await isShiftApproverResource.fetch();
		return isShiftApproverResource.data;
	}

	async function checkAllowMultipleShifts() {
		await allowMultipleShiftsResource.fetch();
		return allowMultipleShiftsResource.data;
	}

	// ---------------------------------------------------------------------------
	// Permission check actions — Shift Request
	// ---------------------------------------------------------------------------
	async function checkCanReadShiftRequest() {
		await canReadShiftRequestResource.fetch();
		return canReadShiftRequestResource.data;
	}
	async function checkCanCreateShiftRequest() {
		await canCreateShiftRequestResource.fetch();
		return canCreateShiftRequestResource.data;
	}
	async function checkCanEditShiftRequest() {
		await canEditShiftRequestResource.fetch();
		return canEditShiftRequestResource.data;
	}
	async function checkCanDeleteShiftRequest() {
		await canDeleteShiftRequestResource.fetch();
		return canDeleteShiftRequestResource.data;
	}
	async function checkCanSubmitShiftRequest() {
		await canSubmitShiftRequestResource.fetch();
		return canSubmitShiftRequestResource.data;
	}

	// ---------------------------------------------------------------------------
	// Permission check actions — Shift Assignment
	// ---------------------------------------------------------------------------
	async function checkCanReadShiftAssignment() {
		await canReadShiftAssignmentResource.fetch();
		return canReadShiftAssignmentResource.data;
	}
	async function checkCanCreateShiftAssignment() {
		await canCreateShiftAssignmentResource.fetch();
		return canCreateShiftAssignmentResource.data;
	}
	async function checkCanEditShiftAssignment() {
		await canEditShiftAssignmentResource.fetch();
		return canEditShiftAssignmentResource.data;
	}
	async function checkCanDeleteShiftAssignment() {
		await canDeleteShiftAssignmentResource.fetch();
		return canDeleteShiftAssignmentResource.data;
	}
	async function checkCanSubmitShiftAssignment() {
		await canSubmitShiftAssignmentResource.fetch();
		return canSubmitShiftAssignmentResource.data;
	}

	// ---------------------------------------------------------------------------
	// Permission check actions — Shift Location
	// ---------------------------------------------------------------------------
	async function checkCanReadShiftLocation() {
		await canReadShiftLocationResource.fetch();
		return canReadShiftLocationResource.data;
	}
	async function checkCanCreateShiftLocation() {
		await canCreateShiftLocationResource.fetch();
		return canCreateShiftLocationResource.data;
	}
	async function checkCanEditShiftLocation() {
		await canEditShiftLocationResource.fetch();
		return canEditShiftLocationResource.data;
	}
	async function checkCanDeleteShiftLocation() {
		await canDeleteShiftLocationResource.fetch();
		return canDeleteShiftLocationResource.data;
	}
	async function checkCanSubmitShiftLocation() {
		await canSubmitShiftLocationResource.fetch();
		return canSubmitShiftLocationResource.data;
	}

	// ---------------------------------------------------------------------------
	// Permission check actions — Shift Type
	// ---------------------------------------------------------------------------
	async function checkCanReadShiftType() {
		await canReadShiftTypeResource.fetch();
		return canReadShiftTypeResource.data;
	}
	async function checkCanCreateShiftType() {
		await canCreateShiftTypeResource.fetch();
		return canCreateShiftTypeResource.data;
	}
	async function checkCanEditShiftType() {
		await canEditShiftTypeResource.fetch();
		return canEditShiftTypeResource.data;
	}
	async function checkCanDeleteShiftType() {
		await canDeleteShiftTypeResource.fetch();
		return canDeleteShiftTypeResource.data;
	}
	async function checkCanSubmitShiftType() {
		await canSubmitShiftTypeResource.fetch();
		return canSubmitShiftTypeResource.data;
	}

	async function openRequestModal(editId = null) {
		editingRequestId.value = editId;
		showRequestModal.value = true;
		submissionError.value = null;
	}

	async function closeRequestModal() {
		showRequestModal.value = false;
		editingRequestId.value = null;
		submissionError.value = null;
	}

	// Add Roster actions
	async function openAddRosterModal(employeeId) {
		currentEmployeeId.value = employeeId;
		addRosterForm.value = {
			employee: employeeId,
			shift_type: "",
			start_date: "",
			end_date: "",
			shift_location: "",
			schedule_enabled: false,
			repeat_on_days: [],
			frequency: "Every Week",
		};
		showAddRosterModal.value = true;
		addRosterError.value = null;
		// Fetch dropdown data
		if (shiftTypes.value.length === 0) {
			await fetchShiftTypes();
		}
		if (shiftLocations.value.length === 0) {
			await fetchShiftLocations();
		}
		if (addRosterEmployees.value.length === 0) {
			await fetchAddRosterEmployees();
		}
		if (frequencyOptions.value.length === 0) {
			await fetchFrequencyOptions();
		}
	}

	function closeAddRosterModal() {
		showAddRosterModal.value = false;
		addRosterForm.value = { employee: "", shift_type: "", start_date: "", end_date: "", shift_location: "", schedule_enabled: false, repeat_on_days: [], frequency: "Every Week" };
		addRosterError.value = null;
	}

	async function fetchFrequencyOptions() {
		try {
			await frequencyOptionsResource.fetch();
		} catch (err) {
			console.error("Failed to fetch frequency options", err);
		}
	}

	async function submitAddRoster(formData) {
		addRosterError.value = null;
		addRosterSubmitting.value = true;
		try {
			const payload = {
				employee: formData.employee,
				shift_type: formData.shift_type,
				start_date: formData.start_date,
				end_date: formData.end_date || null,
				shift_location: formData.shift_location || null,
				assignment_name: formData.assignment_name || null,
			};
			if (formData.schedule_enabled) {
				payload.schedule_enabled = 1;
				payload.repeat_on_days = JSON.stringify(formData.repeat_on_days || []);
				payload.frequency = formData.frequency || "Every Week";
			}
			let result = await addRosterResource.submit(payload);
			if (result && result.success === false) {
				addRosterError.value = result.message;
				return;
			}
			closeAddRosterModal();
		} catch (err) {
			if (err && err._server_messages) {
				try {
					const msgs = JSON.parse(err._server_messages);
					if (msgs && msgs.length > 0) {
						addRosterError.value = msgs[0].replace(/<[^>]*>/g, "").trim();
						return;
					}
				} catch {}
			}
			if (err && err.exc && typeof err.exc === "string") {
				const lines = err.exc.trim().split('\n');
				const lastLine = lines[lines.length - 1].trim();
				if (lastLine) {
					const parts = lastLine.split(': ');
					addRosterError.value = parts.length > 1 ? parts[1] : lastLine;
				} else {
					addRosterError.value = "Failed to create shift assignment";
				}
			} else if (err && err.message) {
				addRosterError.value = err.message;
			} else {
				addRosterError.value = "Failed to create shift assignment";
			}
		} finally {
			addRosterSubmitting.value = false;
		}
	}
	
	async function fetchDeptDesignations() {
		try {
			await deptDesignationResource.fetch();
		} catch (e) {
			deptDesignationList.value = { departments: [], designations: [] };
		}
	}
	
	// Assignment List state

	async function fetchShiftMatrix(month, year, department, designation, employee) {
		if (!month || !year) return;
		shiftMatrixLoading.value = true;
		shiftMatrixMonth.value = month;
		shiftMatrixYear.value = year;
		shiftMatrixFilters.value = { department, designation, employee };
		try {
			await shiftMatrixResource.submit({ month, year, department, designation, employee });
		} finally {
			shiftMatrixLoading.value = false;
		}
	}
	
	async function submitBulkAssign(employee_ids, shift_type, start_date, end_date = null, shift_location = null, schedule_enabled = false, repeat_on_days = [], frequency = "Every Week") {
		bulkAssignSubmitting.value = true;
		bulkAssignError.value = null;
		bulkAssignResult.value = null;
		try {
			let payload = {
				employee_ids: JSON.stringify(employee_ids),
				shift_type,
				start_date,
				end_date,
				shift_location
			};
			if (schedule_enabled) {
				payload.schedule_enabled = 1;
				payload.repeat_on_days = JSON.stringify(repeat_on_days);
				payload.frequency = frequency;
			}
			let result = await bulkAddRosterResource.submit(payload);
			if (result && result.success === false) {
				bulkAssignError.value = result.message;
				return false;
			}
			bulkAssignResult.value = result;
			// refresh the matrix
			await fetchShiftMatrix(shiftMatrixMonth.value, shiftMatrixYear.value, shiftMatrixFilters.value.department, shiftMatrixFilters.value.designation);
			return true;
		} catch (err) {
			bulkAssignError.value = err.message || "Failed to bulk assign shifts";
			return false;
		} finally {
			bulkAssignSubmitting.value = false;
		}
	}

	async function deleteRoster(assignmentName, deleteDate = null) {
		try {
			const payload = { assignment_name: assignmentName };
			if (deleteDate) {
				payload.delete_date = deleteDate;
			}
			let result = await deleteRosterResource.submit(payload);
			if (result && result.success === false) {
				return { success: false, message: result.message };
			}
			return { success: true };
		} catch (err) {
			console.error("Delete roster assignment error:", err);
			let errMsg = "Failed to delete roster assignment";
			if (err && err._server_messages) {
				try {
					const msgs = JSON.parse(err._server_messages);
					if (msgs && msgs.length > 0) {
						errMsg = msgs[0].replace(/<[^>]*>/g, "").trim();
					}
				} catch {}
			} else if (err && err.message) {
				errMsg = err.message;
			}
			return { success: false, message: errMsg };
		}
	}


	async function submitRequest(data) {
		submissionError.value = null;
		submitting.value = true;
		try {
			let result;
			if (editingRequestId.value) {
				result = await updateRequestResource.submit({
					name: editingRequestId.value,
					shift_type: data.shift_type,
					from_date: data.from_date,
					to_date: data.to_date || null,
				});
			} else {
				result = await createRequestResource.submit(data);
			}
			// Backend may return {success: false, message: ...} for validation errors
			if (result && result.success === false) {
				submissionError.value = result.message;
				return;
			}
			closeRequestModal();
		} catch (err) {
			// Backend _server_messages (clean messages from frappe.throw / DocType validation)
			if (err && err._server_messages) {
				try {
					const msgs = JSON.parse(err._server_messages);
					if (msgs && msgs.length > 0) {
						// Strip HTML tags from server message
						submissionError.value = msgs[0].replace(/<[^>]*>/g, "").trim();
						return;
					}
				} catch {}
			}
			// frappe 500 errors: err.exc has the raw traceback, clean message is the last line
			if (err && err.exc && typeof err.exc === "string") {
				const lines = err.exc.trim().split('\n');
				const lastLine = lines[lines.length - 1].trim();
				// "OverlappingShiftRequestError: ..." or "msgprint: ..." — extract the message
				if (lastLine) {
					const parts = lastLine.split(': ');
					submissionError.value = parts.length > 1 ? parts[1] : lastLine;
				} else {
					submissionError.value = "Failed to submit request";
				}
			} else if (err && err.message) {
				submissionError.value = err.message;
			} else if (err && typeof err === "string") {
				submissionError.value = err;
			} else {
				submissionError.value = "Failed to submit request";
			}
		} finally {
			submitting.value = false;
		}
	}

	async function handleCancelRequest(name) {
		if (await ask("Cancel this shift request?")) {
			cancelingId.value = name;
			try {
				const result = await cancelRequestResource.submit({ name });
				if (result && result.success === false) {
					notify(result.message);
				}
			} finally {
				cancelingId.value = null;
			}
		}
	}

	async function updateRequestStatus(name, status) {
		try {
			await updateRequestStatusResource.submit({ name, status });
		} catch (err) {
			console.error("Failed to update request status:", err);
			throw err;
		}
	}

	async function checkShiftConflict(employees, startDate, endDate, excludeAssignment = null, scheduleEnabled = false, repeatOnDays = []) {
		try {
			const payload = {
				employees: JSON.stringify(employees),
				start_date: startDate,
				end_date: endDate || startDate,
				exclude_assignment: excludeAssignment
			};
			if (scheduleEnabled) {
				payload.schedule_enabled = 1;
				payload.repeat_on_days = JSON.stringify(repeatOnDays);
			}
			const res = await checkShiftConflictResource.submit(payload);
			return res;
		} catch (err) {
			console.error("Failed to check shift conflict:", err);
			return { has_conflict: true, message: "Error validating shift assignment (network or server error). Please try again." }; 
		}
	}

	return {
		weeklySchedule,
		weeklySummary,
		weeklyNotes,
		loading,
		error,
		currentWeekStart,
		workingDays,
		hoursWorked,
		targetHours,
		remainingHours,
		fetchWeekly,

		// Monthly view
		monthlyCalendar,
		monthlySummary,
		monthlyWorkingDays,
		monthlyHoursWorked,
		monthlyTargetHours,
		monthlyRemainingHours,
		monthlyLoading,
		monthlyYear,
		monthlyMonth,
		fetchMonthly,

		// Shift request state
		shiftRequests,
		shiftRequestLoading,
		approverInfo,
		showRequestModal,
		editingRequestId,
		shiftTypes,
		submissionError,
		submitting,
		cancelingId,
		fetchShiftRequests,
		fetchShiftApprovers,
		shiftApprovers,
		defaultShiftApprover,
		fetchApprover,
		fetchShiftTypes,
		checkCanAddRoster,
		checkCanManageShiftLocation,
		checkIsShiftApprover,
		checkAllowMultipleShifts,
		openRequestModal,
		closeRequestModal,
		submitRequest,
		handleCancelRequest,
		updateRequestStatus,

		// Add Roster state
		showAddRosterModal,
		addRosterSubmitting,
		addRosterError,
		addRosterForm,
		addRosterEmployees,
		shiftLocations,
		frequencyOptions,
		openAddRosterModal,
		closeAddRosterModal,
		submitAddRoster,
		fetchFrequencyOptions,
		deleteRoster,
		fetchShiftLocations,
		fetchAddRosterEmployees,
		checkCanDeleteRoster,
		checkCanEditRoster,
		checkShiftConflict,
		
		// Matrix and Bulk Assign state
		shiftMatrix,
		shiftMatrixLoading,
		shiftMatrixMonth,
		shiftMatrixYear,
		shiftMatrixFilters,
		showBulkAssignModal,
		bulkAssignSubmitting,
		bulkAssignError,
		bulkAssignResult,
		deptDesignationList,
		fetchDeptDesignations,
		fetchShiftMatrix,
		submitBulkAssign,

		// Shift Request permissions
		checkCanReadShiftRequest,
		checkCanCreateShiftRequest,
		checkCanEditShiftRequest,
		checkCanDeleteShiftRequest,
		checkCanSubmitShiftRequest,

		// Shift Assignment permissions
		checkCanReadShiftAssignment,
		checkCanCreateShiftAssignment,
		checkCanEditShiftAssignment,
		checkCanDeleteShiftAssignment,
		checkCanSubmitShiftAssignment,

		// Shift Location permissions
		checkCanReadShiftLocation,
		checkCanCreateShiftLocation,
		checkCanEditShiftLocation,
		checkCanDeleteShiftLocation,
		checkCanSubmitShiftLocation,

		// Shift Type permissions
		checkCanReadShiftType,
		checkCanCreateShiftType,
		checkCanEditShiftType,
		checkCanDeleteShiftType,
		checkCanSubmitShiftType,
	};
});
