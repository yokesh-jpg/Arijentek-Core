export function getErrorMessage(err, defaultMsg = "An error occurred.") {
    let errMsg = defaultMsg;

    if (!err) {
        return errMsg;
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
        if (Array.isArray(msg)) {
            if (Array.isArray(msg[0])) {
                errMsg = msg.slice(1).map(row => `${row[1]} on ${row[0]}`).join(", ");
            } else {
                errMsg = msg.join(", ");
            }
        } else {
            errMsg = String(msg);
        }
    } else if (err.exc) {
        errMsg = err.exc;
    } else if (err.exc_type && err.exception) {
        errMsg = `${err.exc_type}: ${err.exception}`;
    } else if (err.responseJSON) {
        const r = err.responseJSON;
        if (r.exc) errMsg = r.exc;
        else if (r.message) errMsg = r.message;
        else if (r._server_messages) {
            try {
                const msgs = JSON.parse(r._server_messages);
                if (msgs && msgs.length > 0) errMsg = msgs[0];
            } catch (e) {}
        }
    } else if (err.response && err.response.data) {
        const r = err.response.data;
        if (r.exc) errMsg = r.exc;
        else if (r.message) errMsg = r.message;
        else if (r._server_messages) {
            try {
                const msgs = JSON.parse(r._server_messages);
                if (msgs && msgs.length > 0) errMsg = msgs[0];
            } catch (e) {}
        }
    } else if (err.message) {
        errMsg = err.message;
    } else if (typeof err === 'string') {
        errMsg = err;
    }

    if (typeof errMsg === 'string') {
        errMsg = errMsg.replace(/<[^>]*>/g, "").trim();

        // Catch frappe-ui's unhandled JSON parse failure: "Cannot read properties of undefined (reading 'exc_type')"
        if (errMsg.includes("exc_type") || errMsg.includes("Cannot read properties of undefined") || errMsg.includes("Broken pipe")) {
            errMsg = defaultMsg && defaultMsg !== "An error occurred."
                ? defaultMsg
                : "The record may already exist or the server encountered an unexpected error.";
        }
    }

    return errMsg;
}
