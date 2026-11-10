/**
 * Safe Frappe Request Wrapper for Arijentek Employee Portal
 *
 * Intercepts transport-level crashes, non-JSON HTML error responses (500, 502, 504),
 * network drops, and guards against frappe-ui's known "Cannot read properties of undefined (reading 'exc')" bug.
 */

import { frappeRequest } from 'frappe-ui'
import { createSafeError } from './errorSanitizer.js'

export async function safeFrappeRequest(options) {
	try {
		return await frappeRequest(options)
	} catch (err) {
		console.warn('[Transport Shielded API Error]:', options?.url || options, err)

		const safeErr = createSafeError(err)
		if (options?.onError && typeof options.onError === 'function') {
			try {
				options.onError(safeErr)
			} catch (_) {}
		}
		throw safeErr
	}
}

export default safeFrappeRequest

