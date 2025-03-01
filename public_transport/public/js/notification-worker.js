const CACHE_VERSION = 'v1';
const CACHE_NAME = `public-transport-${CACHE_VERSION}`;

// Assets to cache for offline access
const CACHED_ASSETS = [
    '/assets/public_transport/js/notification_handlers.js',
    '/assets/public_transport/css/tracking.css',
    '/assets/public_transport/images/alert-icon.png',
    '/assets/public_transport/images/deviation-icon.png',
    '/assets/public_transport/images/bus-icon.svg',
    '/assets/public_transport/images/bus-stop-icon.svg',
    '/assets/public_transport/images/bus-stop-icon-alt.svg'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(CACHED_ASSETS))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames
                        .filter((name) => name.startsWith('public-transport-') && name !== CACHE_NAME)
                        .map((name) => caches.delete(name))
                );
            })
            .then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    // Network-first strategy for API calls
    if (event.request.url.includes('/api/')) {
        event.respondWith(
            fetch(event.request)
                .catch(() => caches.match(event.request))
        );
    }
    // Cache-first strategy for static assets
    else {
        event.respondWith(
            caches.match(event.request)
                .then((response) => response || fetch(event.request))
        );
    }
});

self.addEventListener('push', (event) => {
    const data = event.data.json();
    const options = {
        body: data.message,
        icon: data.icon || '/assets/public_transport/images/alert-icon.png',
        badge: '/assets/public_transport/images/notification-badge.png',
        tag: data.tag,
        data: data.data,
        actions: getPushActions(data.type)
    };

    event.waitUntil(
        self.registration.showNotification(data.title, options)
            .then(() => trackNotificationDelivery(data))
    );
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    
    const urlToOpen = getNotificationUrl(event.notification.data);
    
    event.waitUntil(
        self.clients.matchAll({ type: 'window' })
            .then((clientList) => {
                // If we have a client window open, focus it
                for (const client of clientList) {
                    if (client.url === urlToOpen && 'focus' in client) {
                        return client.focus();
                    }
                }
                // If no window is open, open a new one
                if (self.clients.openWindow) {
                    return self.clients.openWindow(urlToOpen);
                }
            })
            .then(() => trackNotificationInteraction(event.notification.data))
    );
});

function getPushActions(type) {
    switch (type) {
        case 'service_alert':
            return [
                {
                    action: 'view_details',
                    title: 'View Details'
                },
                {
                    action: 'dismiss',
                    title: 'Dismiss'
                }
            ];
        case 'route_deviation':
            return [
                {
                    action: 'track_bus',
                    title: 'Track Bus'
                },
                {
                    action: 'view_route',
                    title: 'View Route'
                }
            ];
        default:
            return [];
    }
}

function getNotificationUrl(data) {
    const baseUrl = self.registration.scope;
    switch (data.type) {
        case 'service_alert':
            return `${baseUrl}service_alerts?alert=${data.id}`;
        case 'route_deviation':
            return `${baseUrl}track_bus?deviation=${data.id}`;
        default:
            return baseUrl;
    }
}

async function trackNotificationDelivery(data) {
    try {
        await fetch('/api/method/public_transport.public_transport.utils.notification_analytics.update_notification_metrics', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                notification_type: data.type,
                event_type: 'delivered',
                channel: 'App Notification'
            })
        });
    } catch (error) {
        console.error('Failed to track notification delivery:', error);
    }
}

async function trackNotificationInteraction(data) {
    try {
        await fetch('/api/method/public_transport.public_transport.utils.notification_analytics.update_notification_metrics', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                notification_type: data.type,
                event_type: 'action_click',
                channel: 'App Notification'
            })
        });
    } catch (error) {
        console.error('Failed to track notification interaction:', error);
    }
}