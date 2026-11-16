import { useReportNotificationsStore } from '@/stores/reportNotifications.js'

export function exportReportPdf({ title, url, filename }) {
	const store = useReportNotificationsStore()
	return store.generatePdf({ title, url, filename })
}

