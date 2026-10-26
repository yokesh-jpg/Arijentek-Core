/**
 * Shared Web Push module for zevar_ui (POS) and employee_portal.
 *
 * Two ways in:
 *  - initializeWebPush(frappeRequest): load-time wiring. By default (legacy
 *    behavior, used by the portal) it also creates a subscription, which can
 *    trigger the browser permission prompt without a user gesture. Pass
 *    { optIn: true } (zevar_ui) to only RE-SYNC an existing subscription to
 *    the logged-in user — new subscriptions then happen exclusively through
 *    subscribeWebPushPrompt(), called from the bell's explicit
 *    "Enable browser notifications" button.
 *  - subscribeWebPushPrompt(frappeRequest): user-gesture flow — asks
 *    permission, subscribes, and remembers the opt-in.
 */

const OPT_IN_KEY = 'arijentek.push_opt_in'

export function initializeWebPush(frappeRequest, { optIn = false } = {}) {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;
    window.addEventListener('load', async () => {
        try {
            const registration = await navigator.serviceWorker.register('/assets/arijentek_core/js/sw.js');
            let subscription = await registration.pushManager.getSubscription();

            const userOptedIn = localStorage.getItem(OPT_IN_KEY) === '1';
            if (!subscription && !optIn) {
                subscription = await subscribeWebPush(frappeRequest, registration);
            }
            // When optIn mode: only (re)subscribe if this browser previously
            // opted in — otherwise leave permission untouched.
            if (!subscription && optIn && userOptedIn) {
                subscription = await subscribeWebPush(frappeRequest, registration);
            }

            if (subscription) {
                await syncSubscription(frappeRequest, subscription);
            }
        } catch (error) {
            console.error('Service Worker or Push Error:', error);
        }
    });
}

async function subscribeWebPush(frappeRequest, registration) {
    let subscription = await registration.pushManager.getSubscription();
    if (subscription) return subscription;

    const response = await frappeRequest({
        url: '/api/method/arijentek_core.api.web_push.get_vapid_public_key',
        method: 'GET'
    });
    if (!response) return null;

    const urlBase64ToUint8Array = (base64String) => {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding).replace(/\-/g, '+').replace(/_/g, '/');
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    };

    return registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(response)
    });
}

async function syncSubscription(frappeRequest, subscription) {
    // Always sync on login/load so the endpoint is re-bound to the current
    // user (Jane logging into a browser Gaara was using, etc.).
    const subJSON = subscription.toJSON();
    await frappeRequest({
        url: '/api/method/arijentek_core.api.web_push.subscribe',
        method: 'POST',
        params: {
            endpoint: subJSON.endpoint,
            auth_key: subJSON.keys.auth,
            p256dh_key: subJSON.keys.p256dh
        }
    });
}

export async function subscribeWebPushPrompt(frappeRequest) {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        throw new Error('This browser does not support push notifications.');
    }
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') {
        throw new Error('Browser notifications were blocked. Allow them in the browser site settings, then retry.');
    }
    const registration = await navigator.serviceWorker.register('/assets/arijentek_core/js/sw.js');
    const subscription = await subscribeWebPush(frappeRequest, registration);
    if (subscription) {
        await syncSubscription(frappeRequest, subscription);
        localStorage.setItem(OPT_IN_KEY, '1');
    }
    return Boolean(subscription);
}

export async function unsubscribeWebPush(frappeRequest) {
    localStorage.removeItem(OPT_IN_KEY);
    if ('serviceWorker' in navigator && 'PushManager' in window) {
        try {
            const registration = await navigator.serviceWorker.register('/assets/arijentek_core/js/sw.js');
            if (registration) {
                const subscription = await registration.pushManager.getSubscription();
                if (subscription) {
                    const subJSON = subscription.toJSON();

                    await frappeRequest({
                        url: '/api/method/arijentek_core.api.web_push.unsubscribe',
                        method: 'POST',
                        params: {
                            endpoint: subJSON.endpoint
                        }
                    });

                    await subscription.unsubscribe();
                }
            }
        } catch (error) {
            console.error('Error unsubscribing from Web Push:', error);
        }
    }
}
