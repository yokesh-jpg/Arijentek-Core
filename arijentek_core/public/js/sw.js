self.addEventListener('push', function(event) {
    event.waitUntil(
        (async () => {
            let shouldShow = true;
            try {
                // Verify user is still logged in before showing the notification
                const res = await fetch('/api/method/frappe.auth.get_logged_user');
                if (res.ok) {
                    const data = await res.json();
                    if (data.message === 'Guest') {
                        shouldShow = false;
                        // User logged out, unsubscribe to prevent future ghosts
                        const registration = await self.registration;
                        const subscription = await registration.pushManager.getSubscription();
                        if (subscription) {
                            await subscription.unsubscribe();
                        }
                    }
                } else if (res.status === 401 || res.status === 403) {
                    shouldShow = false;
                }
            } catch (e) {
                // Network error, assume we can still show it (e.g. offline queue)
                console.warn('Could not verify session for push notification:', e);
            }

            if (shouldShow && event.data) {
                try {
                    const data = event.data.json();
                    const title = data.title || 'New Notification';
                    const options = {
                        body: data.body || '',
                        icon: data.icon || '/assets/arijentek_core/images/portal-icon.svg',
                        badge: data.icon || '/assets/arijentek_core/images/portal-icon.svg',
                        data: {
                            url: data.url || '/'
                        }
                    };
                    
                    await self.registration.showNotification(title, options);
                } catch (e) {
                    console.error('Error parsing push data', e);
                }
            }
        })()
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    if (event.notification.data && event.notification.data.url) {
        event.waitUntil(clients.openWindow(event.notification.data.url));
    }
});
