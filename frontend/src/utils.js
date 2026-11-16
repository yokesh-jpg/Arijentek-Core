export function getErrorMessage(err, defaultMsg = "An error occurred.") {
    let errMsg = defaultMsg;

    if (!err) {
        return errMsg;
    }

    // Direct object returned from API payload (e.g. { success: false, message: "..." })
    if (typeof err === "object" && !(err instanceof Error)) {
        if (err.message && typeof err.message === "string") return err.message;
        if (err.message && typeof err.message === "object" && err.message.message) return err.message.message;
    }

    if (err._server_messages) {
        try {
            const msgs = JSON.parse(err._server_messages);
            if (msgs && msgs.length > 0) {
                let msgObj = msgs[0];
                try {
                    const parsed = JSON.parse(msgObj);
                    if (parsed && parsed.message) {
                        msgObj = parsed.message;
                    }
                } catch (e) {
                }
                if (typeof msgObj === 'string') {
                    errMsg = msgObj;
                }
            }
        } catch (e) {
        }
    } else if (err.messages && Array.isArray(err.messages) && err.messages.length > 0) {
        const msg = err.messages[0];
        if (typeof msg === 'object' && msg !== null) {
            if (msg.message && typeof msg.message === 'string') {
                errMsg = msg.message;
            } else if (msg.msg && typeof msg.msg === 'string') {
                errMsg = msg.msg;
            } else if (Array.isArray(msg)) {
                if (Array.isArray(msg[0])) {
                    errMsg = msg.slice(1).map(row => `${row[1]} on ${row[0]}`).join(", ");
                } else {
                    errMsg = msg.join(", ");
                }
            } else {
                try {
                    errMsg = JSON.stringify(msg);
                } catch (_) {}
            }
        } else {
            errMsg = String(msg);
        }
    } else if (err.responseJSON) {
        const r = err.responseJSON;
        if (r.message && typeof r.message === "string") errMsg = r.message;
        else if (r.message && typeof r.message === "object" && r.message.message) errMsg = r.message.message;
        else if (r.exc) errMsg = r.exc;
        else if (r._server_messages) {
            try {
                const msgs = JSON.parse(r._server_messages);
                if (msgs && msgs.length > 0) errMsg = msgs[0];
            } catch (e) {}
        }
    } else if (err.response && err.response.data) {
        const r = err.response.data;
        if (r.message && typeof r.message === "string") errMsg = r.message;
        else if (r.message && typeof r.message === "object" && r.message.message) errMsg = r.message.message;
        else if (r.exc) errMsg = r.exc;
        else if (r._server_messages) {
            try {
                const msgs = JSON.parse(r._server_messages);
                if (msgs && msgs.length > 0) errMsg = msgs[0];
            } catch (e) {}
        }
    } else if (err.exc) {
        errMsg = err.exc;
    } else if (err.exc_type && err.exception) {
        errMsg = `${err.exc_type}: ${err.exception}`;
    } else if (err.message && typeof err.message === 'string' && !err.message.startsWith("/api/method/")) {
        errMsg = err.message;
    } else if (typeof err === 'string' && !err.startsWith("/api/method/")) {
        errMsg = err;
    }

    if (typeof errMsg === 'string') {
        errMsg = errMsg.replace(/<[^>]*>/g, "").trim();

        // Catch frappe-ui's unhandled JSON parse failure or leaked API URLs
        if (
            errMsg.startsWith("/api/") ||
            errMsg.startsWith("api.") ||
            errMsg.includes("/api/method/") ||
            errMsg.includes(".api.") ||
            errMsg.includes("exc_type") ||
            errMsg.includes("Cannot read properties of undefined") ||
            errMsg.includes("Broken pipe")
        ) {
            errMsg = defaultMsg && defaultMsg !== "An error occurred."
                ? defaultMsg
                : "The record may already exist or the server encountered an unexpected error.";
        }
    }

    return errMsg;
}

export const showErrorMessage = getErrorMessage;

export function stripHtml(html) {
    if (!html) return '';
    if (typeof html !== 'string') return String(html);
    if (!html.includes('<') && !html.includes('&')) return html.trim();
    if (typeof DOMParser !== 'undefined') {
        try {
            const doc = new DOMParser().parseFromString(html, 'text/html');
            const scripts = doc.querySelectorAll('script, style');
            scripts.forEach(s => s.remove());
            return (doc.body.textContent || '').replace(/\s+/g, ' ').trim();
        } catch (e) {
            // fallback
        }
    }
    return html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
               .replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, '')
               .replace(/<[^>]*>/g, '')
               .replace(/&nbsp;/g, ' ')
               .replace(/&amp;/g, '&')
               .replace(/&lt;/g, '<')
               .replace(/&gt;/g, '>')
               .replace(/&quot;/g, '"')
               .replace(/&#39;/g, "'")
               .replace(/\s+/g, ' ')
               .trim();
}
