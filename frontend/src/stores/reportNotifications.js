import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { toast } from '@/utils/feedback.js'

export const useReportNotificationsStore = defineStore('reportNotifications', () => {
	const reports = ref([])
	const activeViewerReport = ref(null)

	const unreadCount = computed(() => reports.value.filter((r) => !r.read).length)
	const isGeneratingAny = computed(() => reports.value.some((r) => r.status === 'generating'))

	async function generatePdf({ title, url, filename }) {
		const id = `rep_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`
		const cleanTitle = title || 'Report'
		const defaultFilename = filename || `${cleanTitle.replace(/\s+/g, '_')}.pdf`

		const reportItem = {
			id,
			title: cleanTitle,
			url,
			filename: defaultFilename,
			blobUrl: null,
			status: 'generating',
			startedAt: new Date(),
			completedAt: null,
			read: false,
			error: null,
		}

		reports.value.unshift(reportItem)

		// Show immediate proper loader animation while PDF generates
		// For the first 5 seconds: only display the loader animation and title, no wait warning message
		const toastId = toast.loading(
			'',
			`Generating: ${cleanTitle}`
		)

		// 5-second notice timer:
		// "while click the PDF the five seconds have load the loader animation after that needs to show that message"
		const timer = setTimeout(() => {
			if (reportItem.status === 'generating') {
				toast.update(toastId, {
					type: 'loading',
					title: `Generating: ${cleanTitle}`,
					message: 'PDF creation takes time, please wait or continue your work.',
				})
			}
		}, 5000)

		try {
			const res = await fetch(url, {
				method: 'GET',
				headers: {
					Accept: 'application/pdf, application/octet-stream, */*',
				},
			})

			clearTimeout(timer)
			toast.dismiss(toastId)

			if (!res.ok) {
				throw new Error(`Server returned HTTP ${res.status}: ${res.statusText || 'Export failed'}`)
			}

			// Try to extract filename from content-disposition header if present
			const disposition = res.headers.get('content-disposition')
			if (disposition && disposition.includes('filename=')) {
				const match = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
				if (match && match[1]) {
					reportItem.filename = match[1].replace(/['"]/g, '').trim()
				}
			}

			const blob = await res.blob()
			const pdfBlob = new Blob([blob], { type: 'application/pdf' })
			const blobUrl = URL.createObjectURL(pdfBlob)

			reportItem.blobUrl = blobUrl
			reportItem.status = 'ready'
			reportItem.completedAt = new Date()

			// In-app notification with click-to-view action
			toast.success(
				`Report "${cleanTitle}" is ready to view.`,
				'PDF Ready',
				{
					label: 'View PDF',
					icon: 'picture_as_pdf',
					onClick: () => openViewer(reportItem),
				}
			)

			return reportItem
		} catch (err) {
			clearTimeout(timer)
			toast.dismiss(toastId)
			reportItem.status = 'error'
			reportItem.error = err.message || 'Failed to generate PDF'
			toast.error(
				`Could not generate PDF for "${cleanTitle}". Please try again.`,
				'PDF Generation Failed'
			)
			throw err
		}
	}

	function openViewer(report) {
		if (!report) return
		markAsRead(report.id)
		activeViewerReport.value = report
	}

	function closeViewer() {
		activeViewerReport.value = null
	}

	function markAsRead(id) {
		const item = reports.value.find((r) => r.id === id)
		if (item) item.read = true
	}

	function markAllAsRead() {
		reports.value.forEach((r) => {
			r.read = true
		})
	}

	function downloadPdf(report) {
		if (!report || !report.blobUrl) return
		const a = document.createElement('a')
		a.href = report.blobUrl
		a.download = report.filename || `${report.title}.pdf`
		document.body.appendChild(a)
		a.click()
		document.body.removeChild(a)
	}

	function removeReport(id) {
		const idx = reports.value.findIndex((r) => r.id === id)
		if (idx !== -1) {
			const item = reports.value[idx]
			if (item.blobUrl) {
				try {
					URL.revokeObjectURL(item.blobUrl)
				} catch (_) {}
			}
			reports.value.splice(idx, 1)
		}
	}

	function clearAll() {
		reports.value.forEach((r) => {
			if (r.blobUrl) {
				try {
					URL.revokeObjectURL(r.blobUrl)
				} catch (_) {}
			}
		})
		reports.value = []
	}

	return {
		reports,
		activeViewerReport,
		unreadCount,
		isGeneratingAny,
		generatePdf,
		openViewer,
		closeViewer,
		markAsRead,
		markAllAsRead,
		downloadPdf,
		removeReport,
		clearAll,
	}
})

