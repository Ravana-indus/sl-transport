import frappe
from frappe.realtime import get_redis_server
from frappe.utils import now_datetime
import json

def handle_gps_update(data):
    """Handle real-time GPS updates from devices"""
    try:
        # Validate data
        required_fields = ['bus_id', 'latitude', 'longitude', 'timestamp']
        if not all(field in data for field in required_fields):
            return {'status': 'error', 'message': 'Missing required fields'}

        # Create GPS log entry
        log_entry = frappe.get_doc({
            'doctype': 'GPS Location Log',
            'bus': data['bus_id'],
            'latitude': data['latitude'],
            'longitude': data['longitude'],
            'timestamp': data.get('timestamp') or now_datetime()
        })
        log_entry.insert()

        # Notify subscribed clients
        notify_tracking_clients(data['bus_id'], {
            'location': {
                'lat': data['latitude'],
                'lng': data['longitude'],
                'timestamp': str(log_entry.timestamp)
            }
        })

        return {'status': 'success'}
    except Exception as e:
        frappe.log_error(f"GPS Update Failed: {str(e)}")
        return {'status': 'error', 'message': str(e)}

def notify_tracking_clients(bus_id, data):
    """Notify clients tracking specific bus"""
    frappe.publish_realtime(
        f'bus_location_{bus_id}',
        data,
        after_commit=True
    )

def subscribe_to_bus(bus_id, user=None):
    """Subscribe user to bus location updates"""
    if not user:
        user = frappe.session.user
    
    redis = get_redis_server()
    key = f'bus_tracking:{bus_id}:subscribers'
    redis.sadd(key, user)

def unsubscribe_from_bus(bus_id, user=None):
    """Unsubscribe user from bus location updates"""
    if not user:
        user = frappe.session.user
        
    redis = get_redis_server()
    key = f'bus_tracking:{bus_id}:subscribers'
    redis.srem(key, user)

def get_active_subscribers(bus_id):
    """Get list of users tracking a bus"""
    redis = get_redis_server()
    key = f'bus_tracking:{bus_id}:subscribers'
    return list(redis.smembers(key))

def cleanup_subscriptions():
    """Remove stale subscriptions"""
    redis = get_redis_server()
    pattern = 'bus_tracking:*:subscribers'
    keys = redis.keys(pattern)
    
    for key in keys:
        bus_id = key.split(':')[1]
        # Check if bus has any active trips
        active_trips = frappe.get_all(
            'Bus Trip',
            filters={
                'bus': bus_id,
                'departure_time': ['<=', now_datetime()],
                'arrival_time': ['>', now_datetime()],
                'docstatus': 1
            },
            limit=1
        )
        
        if not active_trips:
            # No active trips, remove all subscribers
            redis.delete(key)