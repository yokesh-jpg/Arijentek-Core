<template>
	<div class="max-w-3xl mx-auto space-y-5">
		<div>
			<h1 class="page-title">HR settings</h1>
			<p class="page-subtitle">Rules that apply to attendance and timesheets for everyone.</p>
		</div>

		<div class="table-card divide-y divide-black/[0.06] dark:divide-white/[0.07]">
			<div class="p-5">
				<div class="flex items-center justify-between gap-4">
					<div>
						<h3 class="text-[14px] font-semibold text-[#17181B] dark:text-white">Timesheet automation</h3>
						<p class="text-[13px] text-[#5C6169] dark:text-white/65 mt-1 max-w-prose">
							Automatically create and update timesheets when employees clock in and clock out.
						</p>
					</div>
					<div>
						<label class="relative inline-flex items-center cursor-pointer">
							<input 
								type="checkbox" 
								v-model="timesheetWithClockin" 
								@change="toggleTimesheetAutomation"
								:disabled="loadingTimesheet || initialLoading"
								class="sr-only peer" 
							/>
							<div class="w-11 h-6 rounded-full bg-black/[0.12] dark:bg-white/20 peer-focus-visible:ring-2 peer-focus-visible:ring-accent/40 peer-checked:bg-accent after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:h-5 after:w-5 after:rounded-full after:bg-white after:shadow-sm after:transition-transform peer-checked:after:translate-x-full transition-colors"
								:class="{'opacity-50 cursor-not-allowed': loadingTimesheet || initialLoading}">
							</div>
						</label>
					</div>
				</div>
			</div>

			<div class="p-5">
				<div class="flex items-center justify-between gap-4">
					<div>
						<h3 class="text-[14px] font-semibold text-[#17181B] dark:text-white">Mark present on clock-out</h3>
						<p class="text-[13px] text-[#5C6169] dark:text-white/65 mt-1 max-w-prose">
							Automatically mark employee attendance status as Present when clocking out.
						</p>
					</div>
					<div>
						<label class="relative inline-flex items-center cursor-pointer">
							<input 
								type="checkbox" 
								v-model="markPresentOnClockOut" 
								@change="toggleMarkPresentOnClockOut"
								:disabled="loadingMarkPresent || initialLoading"
								class="sr-only peer" 
							/>
							<div class="w-11 h-6 rounded-full bg-black/[0.12] dark:bg-white/20 peer-focus-visible:ring-2 peer-focus-visible:ring-accent/40 peer-checked:bg-accent after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:h-5 after:w-5 after:rounded-full after:bg-white after:shadow-sm after:transition-transform peer-checked:after:translate-x-full transition-colors"
								:class="{'opacity-50 cursor-not-allowed': loadingMarkPresent || initialLoading}">
							</div>
						</label>
					</div>
				</div>
			</div>

			<div class="p-5">
				<div class="flex items-center justify-between gap-4">
					<div>
						<h3 class="text-[14px] font-semibold text-[#17181B] dark:text-white">Disable auto attendance</h3>
						<p class="text-[13px] text-[#5C6169] dark:text-white/65 mt-1 max-w-prose">
							Disable automatic attendance creation from clock-in/out logs.
						</p>
					</div>
					<div>
						<label class="relative inline-flex items-center cursor-pointer">
							<input 
								type="checkbox" 
								v-model="disableAutoAttendance" 
								@change="toggleDisableAutoAttendance"
								:disabled="loadingDisableAutoAttendance || initialLoading"
								class="sr-only peer" 
							/>
							<div class="w-11 h-6 rounded-full bg-black/[0.12] dark:bg-white/20 peer-focus-visible:ring-2 peer-focus-visible:ring-accent/40 peer-checked:bg-accent after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:h-5 after:w-5 after:rounded-full after:bg-white after:shadow-sm after:transition-transform peer-checked:after:translate-x-full transition-colors"
								:class="{'opacity-50 cursor-not-allowed': loadingDisableAutoAttendance || initialLoading}">
							</div>
						</label>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { createResource } from 'frappe-ui'
import { notify } from '@/utils/feedback.js'
import { getErrorMessage } from '@/utils'

const router = useRouter()

const timesheetWithClockin = ref(false)
const markPresentOnClockOut = ref(false)
const disableAutoAttendance = ref(false)
const initialLoading = ref(true)
const loadingTimesheet = ref(false)
const loadingMarkPresent = ref(false)
const loadingDisableAutoAttendance = ref(false)

const getSettingsResource = createResource({
	url: 'arijentek_core.api.hr_settings.get_hr_settings',
	auto: false,
	onSuccess(data) {
		if (data) {
			if (data.timesheet_with_clockin !== undefined) {
				timesheetWithClockin.value = Boolean(data.timesheet_with_clockin)
			}
			if (data.mark_present_on_clock_out !== undefined) {
				markPresentOnClockOut.value = Boolean(data.mark_present_on_clock_out)
			}
			if (data.disable_auto_attendance !== undefined) {
				disableAutoAttendance.value = Boolean(data.disable_auto_attendance)
			}
		}
	}
})

const updateSettingsResource = createResource({
	url: 'arijentek_core.api.hr_settings.update_timesheet_automation',
	auto: false,
})

const updateMarkPresentResource = createResource({
	url: 'arijentek_core.api.hr_settings.update_mark_present_on_clock_out',
	auto: false,
})

const updateDisableAutoAttendanceResource = createResource({
	url: 'arijentek_core.api.hr_settings.update_disable_auto_attendance',
	auto: false,
})

const toggleTimesheetAutomation = async () => {
	loadingTimesheet.value = true
	const newVal = timesheetWithClockin.value
	try {
		await updateSettingsResource.submit({
			timesheet_with_clockin: newVal ? 1 : 0
		})
		notify(newVal ? 'Timesheet automation enabled' : 'Timesheet automation disabled')
	} catch (error) {
		console.error('Failed to update timesheet settings', error)
		timesheetWithClockin.value = !newVal
		notify(getErrorMessage(error, 'Failed to update timesheet settings'))
	} finally {
		loadingTimesheet.value = false
	}
}

const toggleMarkPresentOnClockOut = async () => {
	loadingMarkPresent.value = true
	const newVal = markPresentOnClockOut.value
	try {
		await updateMarkPresentResource.submit({
			mark_present_on_clock_out: newVal ? 1 : 0
		})
		notify(newVal ? 'Mark present on clock-out enabled' : 'Mark present on clock-out disabled')
	} catch (error) {
		console.error('Failed to update mark present settings', error)
		markPresentOnClockOut.value = !newVal
		notify(getErrorMessage(error, 'Failed to update mark present settings'))
	} finally {
		loadingMarkPresent.value = false
	}
}

const toggleDisableAutoAttendance = async () => {
	loadingDisableAutoAttendance.value = true
	const newVal = disableAutoAttendance.value
	try {
		await updateDisableAutoAttendanceResource.submit({
			disable_auto_attendance: newVal ? 1 : 0
		})
		notify(newVal ? 'Auto attendance disabled' : 'Auto attendance enabled')
	} catch (error) {
		console.error('Failed to update auto attendance settings', error)
		disableAutoAttendance.value = !newVal
		notify(getErrorMessage(error, 'Failed to update auto attendance settings'))
	} finally {
		loadingDisableAutoAttendance.value = false
	}
}

onMounted(async () => {
	initialLoading.value = true
	try {
		await getSettingsResource.fetch()
	} catch (error) {
		console.error('Error fetching settings on mount:', error)
		notify('You do not have permission to access HR Settings')
		router.push('/')
	} finally {
		initialLoading.value = false
	}
})
</script>
