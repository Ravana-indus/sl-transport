frappe.provide('public_transport.notifications');

public_transport.notifications.NotificationHandler = class NotificationHandler {
    constructor() {
        this.initializeHandlers();
        this.setupServiceWorker();
    }
    
    initializeHandlers() {
        frappe.realtime.on('service_alert', (data) => {
            this.handleServiceAlert(data);
        });
        
        frappe.realtime.on('route_deviation', (data) => {
            this.handleRouteDeviation(data);
        });
        
        // Track notification interactions
        document.addEventListener('notificationclick', (event) => {
            this.trackNotificationInteraction(event.notification);
        });
    }
    
    async setupServiceWorker() {
        if ('serviceWorker' in navigator) {
            try {
                const registration = await navigator.serviceWorker.register(
                    '/assets/public_transport/js/notification-worker.js'
                );
                
                // Register with push service
                const permission = await Notification.requestPermission();
                if (permission === 'granted') {
                    const subscription = await registration.pushManager.subscribe({
                        userVisibleOnly: true,
                        applicationServerKey: this.getVapidPublicKey()
                    });
                    
                    await this.registerDevice(subscription);
                }
            } catch (error) {
                console.error('Service Worker registration failed:', error);
            }
        }
    }
    
    async registerDevice(subscription) {
        const device_id = await this.getDeviceId();
        
        return frappe.call({
            method: 'public_transport.public_transport.api.register_device',
            args: {
                device_id: device_id,
                token: JSON.stringify(subscription),
                platform: this.getPlatform(),
                app_version: this.getAppVersion()
            }
        });
    }
    
    handleServiceAlert(data) {
        if (!('Notification' in window) || Notification.permission !== 'granted') {
            return;
        }
        
        const notification = new Notification(data.title, {
            body: data.message,
            icon: '/assets/public_transport/images/alert-icon.png',
            tag: `service-alert-${data.alert_id}`,
            data: {
                type: 'service_alert',
                id: data.alert_id
            }
        });
        
        this.trackNotification('service_alert', 'sent', 'App Notification');
        
        notification.addEventListener('show', () => {
            this.trackNotification('service_alert', 'delivered', 'App Notification');
        });
        
        notification.addEventListener('click', () => {
            this.trackNotification('service_alert', 'opened', 'App Notification');
            this.handleNotificationClick(notification);
        });
    }
    
    handleRouteDeviation(data) {
        if (!('Notification' in window) || Notification.permission !== 'granted') {
            return;
        }
        
        const notification = new Notification('Route Deviation Detected', {
            body: data.message,
            icon: '/assets/public_transport/images/deviation-icon.png',
            tag: `deviation-${data.deviation_id}`,
            data: {
                type: 'route_deviation',
                id: data.deviation_id
            }
        });
        
        this.trackNotification('route_deviation', 'sent', 'App Notification');
        
        notification.addEventListener('show', () => {
            this.trackNotification('route_deviation', 'delivered', 'App Notification');
        });
        
        notification.addEventListener('click', () => {
            this.trackNotification('route_deviation', 'opened', 'App Notification');
            this.handleNotificationClick(notification);
        });
    }
    
    handleNotificationClick(notification) {
        const data = notification.data;
        
        switch (data.type) {
            case 'service_alert':
                frappe.set_route('service-alerts', { alert: data.id });
                break;
                
            case 'route_deviation':
                frappe.set_route('track-bus', { deviation: data.id });
                break;
        }
    }
    
    trackNotification(type, event, channel) {
        frappe.call({
            method: 'public_transport.public_transport.utils.notification_analytics.update_notification_metrics',
            args: {
                notification_type: type,
                event_type: event,
                channel: channel
            }
        });
    }
    
    trackNotificationInteraction(notification) {
        const data = notification.data;
        this.trackNotification(data.type, 'action_click', 'App Notification');
    }
    
    async getDeviceId() {
        // Generate or retrieve persistent device ID
        let deviceId = localStorage.getItem('device_id');
        if (!deviceId) {
            deviceId = 'dev_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('device_id', deviceId);
        }
        return deviceId;
    }
    
    getPlatform() {
        if (/Android/i.test(navigator.userAgent)) {
            return 'Android';
        }
        if (/iPhone|iPad|iPod/i.test(navigator.userAgent)) {
            return 'iOS';
        }
        return 'Web';
    }
    
    getAppVersion() {
        return frappe.boot.public_transport_version || '1.0.0';
    }
    
    getVapidPublicKey() {
        return frappe.boot.public_transport_vapid_key;
    }
};

// Initialize notification handler when document is ready
$(document).ready(() => {
    if (frappe.boot.public_transport_notifications_enabled) {
        window.notificationHandler = new public_transport.notifications.NotificationHandler();
    }
});