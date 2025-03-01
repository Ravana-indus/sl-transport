import frappe
from frappe import _
from frappe.utils import now_datetime
import json

@frappe.whitelist()
def process_payment(booking_id, payment_details):
    """Handle external payment gateway integration"""
    try:
        details = json.loads(payment_details)
        booking = frappe.get_doc("Booking", booking_id)
        
        payment = frappe.get_doc({
            "doctype": "Payment",
            "booking": booking_id,
            "payment_type": details.get("payment_type"),
            "amount": details.get("amount"),
            "payment_time": now_datetime(),
            "transaction_status": "Success"
        })
        payment.insert()
        payment.submit()
        
        return {"status": "success", "payment_id": payment.name}
    except Exception as e:
        frappe.log_error(f"Payment processing failed: {str(e)}")
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def update_gps_location(bus_id, latitude, longitude, timestamp=None):
    """Handle GPS tracking updates"""
    try:
        if not timestamp:
            timestamp = now_datetime()
            
        frappe.get_doc({
            "doctype": "GPS Location Log",
            "bus": bus_id,
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": timestamp
        }).insert()
        
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def generate_ticket(booking_id):
    """Generate ticket for printing"""
    try:
        booking = frappe.get_doc("Booking", booking_id)
        ticket_data = {
            "booking_id": booking.name,
            "passenger": booking.passenger_name,
            "trip": booking.bus_trip,
            "seats": [seat.seat_id for seat in booking.selected_seats],
            "departure": frappe.db.get_value("Bus Trip", booking.bus_trip, "departure_time"),
            "route": booking.route
        }
        return {"status": "success", "ticket_data": ticket_data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def send_notification(booking_id, notification_type):
    """Send SMS/notifications to passengers"""
    try:
        booking = frappe.get_doc("Booking", booking_id)
        
        if notification_type == "booking_confirmation":
            message = f"Booking confirmed for {booking.passenger_name}. Booking ID: {booking.name}"
        elif notification_type == "trip_reminder":
            message = f"Reminder: Your trip {booking.bus_trip} is scheduled for tomorrow"
        else:
            frappe.throw(_("Invalid notification type"))
            
        # TODO: Integrate with actual SMS gateway
        frappe.get_doc({
            "doctype": "SMS Log",
            "message": message,
            "phone": booking.passenger_contact,
            "status": "Queued"
        }).insert()
        
        return {"status": "success", "message": "Notification queued"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@frappe.whitelist(allow_guest=True)
def get_seat_map(trip_id):
    """Get seat map for a specific trip"""
    try:
        trip = frappe.get_doc("Bus Trip", trip_id)
        if not trip.long_trip_limited_seat:
            frappe.throw(_("This trip does not have a seat map"))
            
        seats = []
        for seat in trip.seat_map_layout:
            seats.append({
                "seat_id": seat.seat_id,
                "status": seat.status,
                "price": seat.price,
                "row": seat.row_identifier,
                "column": seat.column_identifier,
                "side": seat.side
            })
        
        return seats
    except Exception as e:
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def create_booking(trip_id, seats):
    """Create a new booking for selected seats"""
    try:
        if isinstance(seats, str):
            seats = json.loads(seats)
            
        # Create booking
        booking = frappe.get_doc({
            "doctype": "Booking",
            "bus_trip": trip_id,
            "selected_seats": seats,
            "user_role": "Regular User",
            "booking_status": "Pending",
            "booking_time": now_datetime()
        })
        
        if frappe.session.user != "Guest":
            user = frappe.get_doc("User", frappe.session.user)
            booking.passenger_name = user.full_name
            booking.passenger_contact = user.mobile_no
            
        booking.insert()
        
        return {
            "status": "success",
            "booking_id": booking.name
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def get_bus_location(trip_id):
    """Get current bus location and ETA for a trip"""
    try:
        trip = frappe.get_doc("Bus Trip", trip_id)
        
        # Get latest location for the bus
        latest_location = frappe.get_all(
            "GPS Location Log",
            filters={"bus": trip.bus},
            fields=["latitude", "longitude", "timestamp"],
            order_by="timestamp desc",
            limit=1
        )
        
        if not latest_location:
            return {
                "status": "error",
                "message": "No location data available for this bus"
            }
            
        # Calculate ETA if we have destination coordinates
        eta = None
        if hasattr(trip, 'destination_coordinates'):
            from ..utils.gps_tracking import calculate_eta
            eta = calculate_eta(latest_location[0], trip.destination_coordinates)
            
        return {
            "status": "success",
            "location": latest_location[0],
            "eta": eta
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@frappe.whitelist()
def get_trip_eta(trip_id):
    """Calculate and return ETA for a trip"""
    try:
        trip = frappe.get_doc("Bus Trip", trip_id)
        latest_location = frappe.get_all(
            "GPS Location Log",
            filters={"bus": trip.bus},
            fields=["latitude", "longitude", "timestamp"],
            order_by="timestamp desc",
            limit=1
        )
        
        if not latest_location:
            return {
                "status": "error",
                "message": "No location data available"
            }
            
        from geopy.distance import geodesic
        from datetime import timedelta
        
        # Parse destination coordinates
        dest_coords = trip.destination_coordinates.split(',')
        current_pos = (latest_location[0].latitude, latest_location[0].longitude)
        destination = (float(dest_coords[0]), float(dest_coords[1]))
        
        # Calculate distance and estimated time
        distance = geodesic(current_pos, destination).kilometers
        avg_speed = 40  # assumed average speed in km/h
        
        # Add traffic factor based on time of day
        current_hour = frappe.utils.now_datetime().hour
        if 7 <= current_hour <= 9 or 16 <= current_hour <= 19:  # Rush hours
            avg_speed *= 0.7  # Reduce speed by 30% during rush hours
        
        travel_time = distance / avg_speed
        eta = frappe.utils.now_datetime() + timedelta(hours=travel_time)
        
        return {
            "status": "success",
            "eta": eta,
            "distance_remaining": round(distance, 2)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@frappe.whitelist()
def get_route_data(bus_id):
    """Get route and stop data for bus tracking"""
    try:
        # Get current trip for the bus
        current_trip = frappe.get_all(
            "Bus Trip",
            filters={
                "bus": bus_id,
                "departure_time": ["<=", frappe.utils.now_datetime()],
                "arrival_time": [">", frappe.utils.now_datetime()],
                "docstatus": 1
            },
            fields=["name", "route"],
            limit=1
        )
        
        if not current_trip:
            return {
                "status": "error",
                "message": "No active trip found for this bus"
            }
            
        route = frappe.get_doc("Route", current_trip[0].route)
        stops = []
        coordinates = []
        
        for stop_entry in route.stops:
            stop = frappe.get_doc("Bus Stop", stop_entry.stop)
            coordinates.append({
                "lat": stop.latitude,
                "lng": stop.longitude
            })
            
            stops.append({
                "name": stop.name,
                "stop_name": stop.stop_name,
                "latitude": stop.latitude,
                "longitude": stop.longitude,
                "address": stop.address,
                "sequence": stop_entry.sequence,
                "facilities": [
                    {
                        "facility_type": f.facility_type,
                        "status": f.status
                    } for f in stop.facilities
                ] if stop.facilities else []
            })
        
        # Calculate ETAs for upcoming stops
        current_location = get_bus_location(bus_id)
        if current_location.get("status") == "success":
            location = current_location["location"]
            update_stop_etas(stops, location)
        
        return {
            "status": "success",
            "route": {
                "name": route.name,
                "route_number": route.route_number,
                "coordinates": coordinates
            },
            "stops": stops
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def update_stop_etas(stops, current_location):
    """Calculate ETAs for each upcoming stop"""
    from geopy.distance import geodesic
    from datetime import timedelta
    
    current_pos = (current_location["latitude"], current_location["longitude"])
    
    # Find closest stop to determine which stops are upcoming
    distances = [(i, geodesic(current_pos, (stop["latitude"], stop["longitude"])).kilometers)
                for i, stop in enumerate(stops)]
    closest_idx = min(distances, key=lambda x: x[1])[0]
    
    # Update ETAs for upcoming stops
    avg_speed = 30  # km/h
    cumulative_distance = 0
    
    for i in range(closest_idx, len(stops)):
        if i > closest_idx:
            # Calculate distance from previous stop
            prev_pos = (stops[i-1]["latitude"], stops[i-1]["longitude"])
            curr_pos = (stops[i]["latitude"], stops[i]["longitude"])
            segment_distance = geodesic(prev_pos, curr_pos).kilometers
            cumulative_distance += segment_distance
        else:
            # For first upcoming stop, use distance from current position
            cumulative_distance = distances[i][1]
        
        # Calculate ETA
        travel_time = (cumulative_distance / avg_speed) * 60  # minutes
        eta = frappe.utils.now_datetime() + timedelta(minutes=travel_time)
        stops[i]["eta"] = eta.strftime("%H:%M")

@frappe.whitelist()
def toggle_alert_subscription(alert_id):
    """Toggle user's subscription to a service alert"""
    try:
        if not frappe.session.user or frappe.session.user == 'Guest':
            frappe.throw("Please log in to subscribe to alerts")
        
        key = f"alert_subscribers:{alert_id}"
        redis = frappe.cache()
        subscribers = redis.get_value(key) or []
        
        if frappe.session.user in subscribers:
            subscribers.remove(frappe.session.user)
            subscribed = False
        else:
            subscribers.append(frappe.session.user)
            subscribed = True
            
        redis.set_value(key, subscribers)
        
        return {
            "status": "success",
            "subscribed": subscribed
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@frappe.whitelist()
def get_alert_share_data(alert_id):
    """Get formatted data for sharing a service alert"""
    try:
        alert = frappe.get_doc("Service Alert", alert_id)
        
        title = f"Service Alert: {alert.alert_type}"
        text = f"{alert.severity} Alert - {alert.alert_message}"
        url = f"{frappe.utils.get_url()}/service_alerts?alert={alert_id}"
        
        return {
            "status": "success",
            "title": title,
            "text": text,
            "url": url
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@frappe.whitelist()
def get_active_alerts(route=None):
    """Get active alerts, optionally filtered by route"""
    try:
        filters = {
            "status": "Active",
            "end_time": [">", frappe.utils.now_datetime()]
        }
        
        if route:
            # Get alerts affecting this route
            alerts = frappe.get_all(
                "Service Alert",
                filters=filters,
                fields=[
                    "name", "alert_type", "severity",
                    "alert_message", "affected_areas",
                    "action_required"
                ]
            )
            
            # Filter to only alerts affecting this route
            route_alerts = []
            for alert in alerts:
                alert_doc = frappe.get_doc("Service Alert", alert.name)
                if any(r.route == route for r in alert_doc.affected_routes):
                    route_alerts.append(alert)
            
            return {
                "status": "success",
                "alerts": route_alerts
            }
        
        else:
            # Return all active alerts
            alerts = frappe.get_all(
                "Service Alert",
                filters=filters,
                fields=[
                    "name", "alert_type", "severity",
                    "alert_message", "affected_areas",
                    "action_required"
                ]
            )
            
            return {
                "status": "success",
                "alerts": alerts
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@frappe.whitelist()
def register_device(device_id: str, token: str, platform: str, app_version: str = None) -> dict:
    """Register a device for push notifications"""
    try:
        if not frappe.session.user or frappe.session.user == "Guest":
            frappe.throw("Authentication required")
            
        # Check for existing device
        existing = frappe.get_all(
            "Push Notification Device",
            filters={"device_id": device_id},
            fields=["name", "token"]
        )
        
        if existing:
            # Update existing device
            device = frappe.get_doc("Push Notification Device", existing[0].name)
            device.token = token
            device.platform = platform
            device.app_version = app_version
            device.last_active = frappe.utils.now_datetime()
            device.save()
        else:
            # Create new device registration
            device = frappe.get_doc({
                "doctype": "Push Notification Device",
                "user": frappe.session.user,
                "device_id": device_id,
                "token": token,
                "platform": platform,
                "app_version": app_version,
                "last_active": frappe.utils.now_datetime()
            })
            device.insert()
            
        return {
            "status": "success",
            "message": "Device registered successfully"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@frappe.whitelist()
def update_notification_preferences(device_id: str, enabled: bool = True) -> dict:
    """Update notification preferences for a device"""
    try:
        if not frappe.session.user or frappe.session.user == "Guest":
            frappe.throw("Authentication required")
            
        device = frappe.get_all(
            "Push Notification Device",
            filters={
                "device_id": device_id,
                "user": frappe.session.user
            },
            fields=["name"]
        )
        
        if not device:
            frappe.throw("Device not found")
            
        doc = frappe.get_doc("Push Notification Device", device[0].name)
        doc.enabled = enabled
        doc.save()
        
        return {
            "status": "success",
            "message": "Preferences updated successfully"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@frappe.whitelist()
def send_test_notification(device_id: str) -> dict:
    """Send a test notification to verify device setup"""
    try:
        if not frappe.session.user or frappe.session.user == "Guest":
            frappe.throw("Authentication required")
            
        device = frappe.get_all(
            "Push Notification Device",
            filters={
                "device_id": device_id,
                "user": frappe.session.user
            },
            fields=["token"]
        )
        
        if not device:
            frappe.throw("Device not found")
            
        from .utils.push_notifications import PushNotificationManager
        
        notification_manager = PushNotificationManager()
        notification_data = {
            "title": "Test Notification",
            "body": "This is a test notification to verify your device setup.",
            "data": {
                "type": "test",
                "timestamp": str(frappe.utils.now_datetime())
            }
        }
        
        notification_manager._send_notification(
            notification_data,
            [frappe.session.user]
        )
        
        return {
            "status": "success",
            "message": "Test notification sent"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }