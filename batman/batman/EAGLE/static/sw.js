
self.addEventListener('push', function(event) {
    const options = {
        body: event.data ? event.data.text() : 'New notification from Eagle Task Manager',
        icon: '/static/icon-192x192.png',
        badge: '/static/badge-72x72.png',
        vibrate: [200, 100, 200],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: 1
        },
        actions: [
            {
                action: 'explore',
                title: 'View',
                icon: '/static/checkmark.png'
            },
            {
                action: 'close',
                title: 'Close',
                icon: '/static/xmark.png'
            }
        ]
    };

    event.waitUntil(
        self.registration.showNotification('Eagle Task Manager', options)
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();

    if (event.action === 'explore') {
        event.waitUntil(
            clients.openWindow('/')
        );
    }
});
