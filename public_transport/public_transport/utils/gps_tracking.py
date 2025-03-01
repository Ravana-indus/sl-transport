import frappe
from frappe.utils import now_datetime
from geopy.distance import geodesic
from datetime import timedelta
from .deviation_detection import check_route_deviation

def update_bus_location(bus_id, latitude, longitude):
    """Update bus location and check for deviations"""
    try:
        # Create GPS log entry
        log_entry = frappe.get_doc({
            'doctype': 'GPS Location Log',
            'bus': bus_id,
            'latitude': latitude,
            'longitude': longitude,
            'timestamp': now_datetime()
        })
        log_entry.insert()

        # Check for route deviation
        current_position = {
            'latitude': latitude,
            'longitude': longitude
        }
        deviation = check_route_deviation(bus_id, current_position)

        # Notify clients about location update and any deviation
        notify_tracking_clients(bus_id, {
            'location': current_position,
            'timestamp': str(log_entry.timestamp),
            'deviation': deviation.name if deviation else None
        })

        return {"status": "success"}
    except Exception as e:
        frappe.log_error(f"GPS Update Failed: {str(e)}")
        return {"status": "error", "message": str(e)}

def notify_delay(trip):
    """Notify passengers about trip delay"""
    bookings = frappe.get_all(
        "Booking",
        filters={
            "bus_trip": trip.name,
            "booking_status": "Confirmed"
        },
        fields=["name", "passenger_name", "passenger_contact"]
    )
    
    for booking in bookings:
        try:
            frappe.get_doc({
                "doctype": "SMS Log",
                "message": f"Dear {booking.passenger_name}, your trip {trip.route} is experiencing a delay. " \
                          f"New estimated arrival time: {trip.estimated_arrival.strftime('%H:%M')}",
                "phone": booking.passenger_contact,
                "status": "Queued"
            }).insert()
        except Exception as e:
            frappe.log_error(f"Failed to send delay notification: {str(e)}")

def get_bus_location(bus_id):
    """Get latest bus location"""
    try:
        latest_log = frappe.get_all(
            "GPS Location Log",
            filters={"bus": bus_id},
            fields=["latitude", "longitude", "timestamp"],
            order_by="timestamp desc",
            limit=1
        )
        
        if latest_log:
            return {
                "status": "success",
                "location": latest_log[0]
            }
        return {
            "status": "error",
            "message": "No location data available"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }