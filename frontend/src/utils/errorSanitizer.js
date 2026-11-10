/**
 * Universal Enterprise Error Sanitizer & Translation Engine
 *
 * Guarantees zero-leakage of raw technical runtime errors, JavaScript TypeErrors,
 * Python tracebacks, database queries, and system crash strings into the UI across
 * all retail, employee portal, and POS interfaces.
 */

export const PROHIBITED_PATTERNS = [
	// JavaScript Engine Runtime Errors
	/Cannot read properties/i,
	/reading 'exc'/i,
	/reading ['"][^'"]+['"]/i,
	/is not a function/i,
	/TypeError/i,
	/ReferenceError/i,
	/SyntaxError/i,
	/RangeError/i,
	/undefined/i,
	/null/i,
	/\[object Object\]/i,
	/object Object/i,
	/Uncaught /i,
	/call stack/i,
	/at (?:async )?[a-zA-Z0-9_$.]+\s*\(.*:\d+:\d+\)/i,

	// Python & Frappe Backend Exceptions
	/Traceback \(most recent call last\)/i,
	/frappe\.exceptions/i,
	/BrokenPipeError/i,
	/Broken pipe/i,
	/OperationalError/i,
	/IntegrityError/i,
	/ProgrammingError/i,
	/InternalError/i,
	/KeyError/i,
	/IndexError/i,
	/AttributeError/i,
	/ValueError/i,
	/NameError/i,
	/ZeroDivisionError/i,
	/pymysql/i,
	/mariadb/i,
	/MySQLdb/i,
	/1048,\s*"Column/i,
	/1062,\s*"Duplicate entry/i,
	/1054,\s*"Unknown column/i,
	/1146,\s*"Table .* doesn't exist/i,
	/SELECT\s+.*FROM/i,
	/INSERT\s+INTO/i,
	/UPDATE\s+.*SET/i,
	/DELETE\s+FROM/i,
	/apps\/[a-zA-Z0-9_\-/]+\.py/i,
	/site-packages\//i,
	/venv\//i,
	/env\/lib\/python/i,

	// Network & HTTP Infrastructure Codes
	/Failed to fetch/i,
	/NetworkError/i,
	/net::ERR_/i,
	/502 Bad Gateway/i,
	/504 Gateway Time-out/i,
	/500 Internal Server Error/i,
	/Connection refused/i,
	/ECONNREFUSED/i,
	/ETIMEDOUT/i,
	/ECONNRESET/i,
]

export function isProhibitedMessage(msg) {
	if (!msg || typeof msg !== 'string') return false
	return PROHIBITED_PATTERNS.some((pattern) => pattern.test(msg))
}

export function parseRawError(err) {
	if (!err) return { rawMessage: '', rawTitle: '', status: 0 }

	let rawMessage = ''
	let rawTitle = ''
	let status = err.status || err.statusCode || err.httpStatus || 0

	if (typeof err === 'string') {
		rawMessage = err
	} else if (err instanceof Error) {
		rawMessage = err.message || err.toString()
		rawTitle = err.name || ''
		status = err.status || status
	} else if (typeof err === 'object') {
		// Frappe server messages JSON
		if (err._server_messages) {
			try {
				const msgs = JSON.parse(err._server_messages)
				if (Array.isArray(msgs) && msgs.length > 0) {
					const parsed = typeof msgs[0] === 'string' ? JSON.parse(msgs[0]) : msgs[0]
					rawMessage = parsed.message || (typeof msgs[0] === 'string' ? msgs[0] : '')
				}
			} catch {
				rawMessage = String(err._server_messages)
			}
		}

		if (!rawMessage && Array.isArray(err.messages) && err.messages.length > 0) {
			const m = err.messages[0]
			if (typeof m === 'string') rawMessage = m
			else if (m && typeof m === 'object' && m.message) rawMessage = m.message
		}

		if (!rawMessage && err.message) {
			rawMessage = typeof err.message === 'string' ? err.message : JSON.stringify(err.message)
		}
		if (!rawMessage && err.exception) {
			rawMessage = typeof err.exception === 'string' ? err.exception : JSON.stringify(err.exception)
		}
		if (!rawMessage && err.exc) {
			rawMessage = typeof err.exc === 'string' ? err.exc : JSON.stringify(err.exc)
		}
		if (!rawMessage && err.error) {
			rawMessage = typeof err.error === 'string' ? err.error : (err.error?.message || JSON.stringify(err.error))
		}

		rawTitle = err.title || err.exception_type || err.exc_type || err.name || ''
	}

	// Strip HTML tags if present (e.g. Frappe <p>, <b>, or <html> error traces)
	if (typeof rawMessage === 'string') {
		rawMessage = rawMessage.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()
	}

	return { rawMessage, rawTitle, status }
}

export function sanitizeError(err, customTitle = '') {
	const { rawMessage, rawTitle, status } = parseRawError(err)
	const combined = `${rawTitle} ${rawMessage}`.toLowerCase()

	let title = customTitle || ''
	let message = ''
	let actionHint = 'Please try again or contact support if the issue persists.'
	let supportTeam = 'Support'
	let iconType = 'error' // 'error', 'lock', 'wifi-off', 'warning', 'info'

	// 1. Authentication & Session Expired (401)
	if (
		status === 401 ||
		combined.includes('authenticationerror') ||
		combined.includes('sessionexpired') ||
		combined.includes('not logged in') ||
		combined.includes('invalid login credentials') ||
		combined.includes('invalid credentials') ||
		combined.includes('invalid token') ||
		combined.includes('csrf') ||
		combined.includes('broken pipe') // Broken pipe during login handshake
	) {
		title = title || 'Authentication Notice'
		message = 'Invalid login credentials or session expired. Please sign in again.'
		actionHint = 'Please check your username and password, then try signing in again.'
		supportTeam = 'Security & Login Support'
		iconType = 'lock'
	}
	// 2. Permission & Access Control (403)
	else if (
		status === 403 ||
		combined.includes('permissionerror') ||
		combined.includes('not permitted') ||
		combined.includes('not authorized') ||
		combined.includes('permission denied') ||
		combined.includes('insufficient permission') ||
		combined.includes('access restricted') ||
		combined.includes('whitelist') ||
		combined.includes('only_for')
	) {
		title = title || 'Access Restricted'
		message = 'You do not have permission to access this feature or perform this action.'
		actionHint = 'Please contact your Manager or Administrator to enable access for your account.'
		supportTeam = 'Manager / Admin'
		iconType = 'lock'
	}
	// 3. Duplicate Records & Unique Constraints
	else if (
		combined.includes('duplicateentry') ||
		combined.includes('already exists') ||
		combined.includes('duplicate') ||
		combined.includes('unique constraint') ||
		combined.includes('1062')
	) {
		title = title || 'Record Already Exists'
		message = 'A record with this information (such as barcode, email, or code) already exists in the system.'
		actionHint = 'Please verify the details or use a different unique identifier.'
		supportTeam = 'Data & Records Team'
		iconType = 'warning'
	}
	// 4. Form Validation & Mandatory Fields
	else if (
		combined.includes('mandatory') ||
		combined.includes('validationerror') ||
		combined.includes('is required') ||
		combined.includes('missing required') ||
		combined.includes('cannot be empty')
	) {
		title = title || 'Required Information Missing'
		if (rawMessage.length > 5 && rawMessage.length < 120 && !isProhibitedMessage(rawMessage)) {
			message = rawMessage
		} else {
			message = 'Please ensure all required fields are accurately completed before saving.'
		}
		actionHint = 'Fill in the highlighted fields and try again.'
		supportTeam = 'Operations'
		iconType = 'warning'
	}
	// 5. Connection & Network Offline (502, 504, 500, network drop)
	else if (
		status === 502 ||
		status === 504 ||
		status === 503 ||
		status === 500 ||
		combined.includes('failed to fetch') ||
		combined.includes('networkerror') ||
		combined.includes('connection refused') ||
		combined.includes('offline') ||
		combined.includes('timeout') ||
		combined.includes('server error') ||
		combined.includes('broken pipe')
	) {
		title = title || 'Connection Notice'
		message = 'Unable to reach the server right now. The network might be temporarily slow or disconnected.'
		actionHint = 'Please check your internet or Wi-Fi connection and retry.'
		supportTeam = 'IT & Network Support'
		iconType = 'wifi-off'
	}
	// 6. Record Not Found (404)
	else if (status === 404 || combined.includes('doesnotexist') || combined.includes('not found')) {
		title = title || 'Record Not Found'
		message = 'The requested item, document, or record could not be located in the database.'
		actionHint = 'Please verify the reference number or query and search again.'
		supportTeam = 'Records Support'
		iconType = 'warning'
	}
	// 7. Payment Gateways & Terminals
	else if (
		combined.includes('terminal') ||
		combined.includes('stripe') ||
		combined.includes('square') ||
		combined.includes('card reader') ||
		combined.includes('payment gateway')
	) {
		title = title || 'Payment Terminal Notice'
		if (rawMessage.length > 5 && rawMessage.length < 140 && !isProhibitedMessage(rawMessage)) {
			message = rawMessage
		} else {
			message = 'The payment terminal or gateway encountered an issue processing the request.'
		}
		actionHint = 'Ensure the reader is powered on, paired, and ready for cards.'
		supportTeam = 'Payment Gateway Support'
		iconType = 'warning'
	}
	// 8. General Fallback with Strict Prohibited Pattern Protection
	else {
		title = title || 'Action Notice'
		// Only allow rawMessage if it is clean, short, and DOES NOT match any prohibited pattern
		if (
			rawMessage.length > 4 &&
			rawMessage.length < 130 &&
			!isProhibitedMessage(rawMessage) &&
			!isProhibitedMessage(rawTitle)
		) {
			message = rawMessage
		} else {
			message = 'The requested operation could not be completed.'
		}
		actionHint = 'Please retry or contact support if the issue persists.'
		supportTeam = 'Technical Support'
		iconType = 'error'
	}

	const technicalDetails = [
		rawTitle ? `Exception: ${rawTitle}` : null,
		rawMessage ? `Details: ${rawMessage}` : null,
		status ? `HTTP Status: ${status}` : null,
		`Timestamp: ${new Date().toLocaleString()}`,
	]
		.filter(Boolean)
		.join('\n')

	return {
		title,
		message,
		actionHint,
		supportTeam,
		iconType,
		status,
		isSanitized: true,
		technicalDetails,
	}
}

export function getSafeErrorMessage(err, defaultMsg = 'The requested operation could not be completed.') {
	try {
		const sanitized = sanitizeError(err)
		return sanitized.message || defaultMsg
	} catch {
		return defaultMsg
	}
}

export function getSafeErrorTitle(err, defaultTitle = 'Notice') {
	try {
		const sanitized = sanitizeError(err)
		return sanitized.title || defaultTitle
	} catch {
		return defaultTitle
	}
}

export function createSafeError(err, customTitle = '') {
	const sanitized = sanitizeError(err, customTitle)
	const safeErr = new Error(sanitized.message)
	safeErr.title = sanitized.title
	safeErr.status = sanitized.status
	safeErr.iconType = sanitized.iconType
	safeErr.actionHint = sanitized.actionHint
	safeErr.supportTeam = sanitized.supportTeam
	safeErr.technicalDetails = sanitized.technicalDetails
	safeErr.isSanitized = true
	safeErr.originalError = err
	return safeErr
}

export default {
	isProhibitedMessage,
	parseRawError,
	sanitizeError,
	getSafeErrorMessage,
	getSafeErrorTitle,
	createSafeError,
}

