import frappe
from geopy.distance import geodesic
from datetime import datetime, timedelta

def check_route_deviation(bus_id, current_position):
    """Check if bus has deviated from planned route"""
    try:
        # Get current trip
        current_trip = get_active_trip(bus_id)
        if not current_trip:
            return None
            
        # Get route and calculate expected position
        route = frappe.get_doc("Route", current_trip.route)
        expected_position = calculate_expected_position(current_trip, route)
        
        if not expected_position:
            return None
            
        # Calculate distance from expected position
        actual_pos = (current_position["latitude"], current_position["longitude"])
        expected_pos = (expected_position["latitude"], expected_position["longitude"])
        
        deviation_distance = geodesic(actual_pos, expected_pos).kilometers
        
        # If deviation is significant (more than 500m)
        if deviation_distance > 0.5:
            return handle_deviation(current_trip, route, current_position, deviation_distance)
            
        return None
        
    except Exception as e:
        frappe.log_error(f"Deviation check failed: {str(e)}")
        return None

def get_active_trip(bus_id):
    """Get currently active trip for bus"""
    trips = frappe.get_all(
        "Bus Trip",
        filters={
            "bus": bus_id,
            "departure_time": ["<=", frappe.utils.now_datetime()],
            "arrival_time": [">", frappe.utils.now_datetime()],
            "docstatus": 1
        },
        fields=["name", "route", "departure_time"],
        limit=1
    )
    
    return frappe.get_doc("Bus Trip", trips[0].name) if trips else None

def calculate_expected_position(trip, route):
    """Calculate where the bus should be based on schedule"""
    try:
        # Calculate time elapsed since departure
        elapsed = (frappe.utils.now_datetime() - trip.departure_time).total_seconds() / 3600  # hours
        
        # Calculate total route time
        total_time = sum(stop.estimated_time_from_previous or 0 for stop in route.stops) / 60  # hours
        
        if total_time == 0:
            return None
            
        # Calculate progress through route (0-1)
        progress = min(elapsed / total_time, 1)
        
        # Find expected position by interpolating between stops
        return interpolate_position(route.stops, progress)
        
    except Exception as e:
        frappe.log_error(f"Position calculation failed: {str(e)}")
        return None

def interpolate_position(stops, progress):
    """Interpolate position between stops based on progress"""
    if not stops or len(stops) < 2:
        return None
        
    # Calculate cumulative distances
    total_distance = 0
    distances = []
    
    for i in range(len(stops) - 1):
        current = frappe.get_doc("Bus Stop", stops[i].stop)
        next_stop = frappe.get_doc("Bus Stop", stops[i + 1].stop)
        
        distance = geodesic(
            (current.latitude, current.longitude),
            (next_stop.latitude, next_stop.longitude)
        ).kilometers
        
        total_distance += distance
        distances.append(distance)
    
    if total_distance == 0:
        return None
    
    # Find segment where bus should be
    target_distance = total_distance * progress
    current_distance = 0
    
    for i in range(len(distances)):
        if current_distance + distances[i] >= target_distance:
            # Interpolate between these stops
            segment_progress = (target_distance - current_distance) / distances[i]
            
            current = frappe.get_doc("Bus Stop", stops[i].stop)
            next_stop = frappe.get_doc("Bus Stop", stops[i + 1].stop)
            
            return {
                "latitude": current.latitude + (next_stop.latitude - current.latitude) * segment_progress,
                "longitude": current.longitude + (next_stop.longitude - current.longitude) * segment_progress
            }
            
        current_distance += distances[i]
    
    # If we're at the end, return last stop
    last_stop = frappe.get_doc("Bus Stop", stops[-1].stop)
    return {
        "latitude": last_stop.latitude,
        "longitude": last_stop.longitude
    }

def handle_deviation(trip, route, current_position, deviation_distance):
    """Handle detected route deviation"""
    try:
        # Check for existing active deviation
        existing = frappe.get_all(
            "Route Deviation",
            filters={
                "route": route.name,
                "status": "Active",
                "start_time": ["<=", frappe.utils.now_datetime()],
                "end_time": [">", frappe.utils.now_datetime()]
            },
            limit=1
        )
        
        if existing:
            return None
        
        # Find nearest stops for alternate route
        nearest_stops = find_nearest_stops(current_position)
        
        # Create deviation record
        deviation = frappe.get_doc({
            "doctype": "Route Deviation",
            "route": route.name,
            "start_time": frappe.utils.now_datetime(),
            "end_time": frappe.utils.add_to_date(None, hours=1),
            "reason": "Traffic",
            "description": f"Automatic deviation detection: {deviation_distance:.2f}km off route",
            "status": "Active"
        })
        
        # Add stops to deviation
        sequence = 1
        for stop in nearest_stops:
            deviation.append("alternate_stops", {
                "stop": stop.name,
                "sequence": sequence
            })
            sequence += 1
        
        deviation.insert()
        
        # Create service alert for the deviation
        create_deviation_alert(deviation, trip, route)
        
        # Send notifications
        notify_deviation(deviation, trip)
        
        return deviation
        
    except Exception as e:
        frappe.log_error(f"Deviation handling failed: {str(e)}")
        return None

def create_deviation_alert(deviation, trip, route):
    """Create service alert for route deviation"""
    try:
        alert = frappe.get_doc({
            "doctype": "Service Alert",
            "alert_type": "Route Deviation",
            "severity": "High",
            "start_time": deviation.start_time,
            "end_time": deviation.end_time,
            "affected_routes": [{"route": route.name}],
            "affected_areas": route.route_name,
            "alert_message": (
                f"Bus {trip.bus} has deviated from the planned route. "
                f"Alternative route in effect. Expect delays."
            ),
            "action_required": (
                "Please check the app for real-time location updates "
                "and revised arrival times."
            ),
            "notification_channels": "All Channels",
            "status": "Active"
        })
        
        alert.insert()
        alert.submit()
        
    except Exception as e:
        frappe.log_error(f"Deviation alert creation failed: {str(e)}")

def notify_deviation(deviation, trip):
    """Send notifications for route deviation"""
    try:
        from ..utils.push_notifications import PushNotificationManager
        
        # Initialize notification manager
        push_manager = PushNotificationManager()
        
        # Send notification to operator
        push_manager.send_deviation_notification(deviation, trip.bus)
        
        # Get affected bookings
        bookings = frappe.get_all(
            "Booking",
            filters={
                "bus_trip": trip.name,
                "booking_status": "Confirmed"
            },
            fields=["name", "passenger_name", "passenger_contact"]
        )
        
        # Send SMS to passengers
        for booking in bookings:
            frappe.get_doc({
                "doctype": "SMS Log",
                "message": (
                    f"Dear {booking.passenger_name}, your bus has deviated "
                    f"from the planned route due to traffic conditions. "
                    f"New ETA will be calculated shortly. "
                    f"Please check the app for real-time updates."
                ),
                "phone": booking.passenger_contact,
                "status": "Queued"
            }).insert()
            
    except Exception as e:
        frappe.log_error(f"Deviation notification failed: {str(e)}")

def calculate_new_eta(deviation, trip):
    """Calculate new ETA based on deviation route"""
    try:
        total_distance = 0
        total_time = 0
        
        # Calculate distance and time for alternate route
        for i in range(len(deviation.alternate_stops) - 1):
            current = frappe.get_doc("Bus Stop", deviation.alternate_stops[i].stop)
            next_stop = frappe.get_doc("Bus Stop", deviation.alternate_stops[i + 1].stop)
            
            distance = geodesic(
                (current.latitude, current.longitude),
                (next_stop.latitude, next_stop.longitude)
            ).kilometers
            
            total_distance += distance
            
            # Estimate time (assume slower speed due to deviation)
            time_minutes = (distance / 20) * 60  # Assume 20 km/h average speed
            total_time += time_minutes
        
        # Update trip ETA
        new_eta = frappe.utils.add_to_date(
            frappe.utils.now_datetime(),
            minutes=int(total_time)
        )
        
        frappe.db.set_value("Bus Trip", trip.name, "estimated_arrival", new_eta)
        
        return new_eta
        
    except Exception as e:
        frappe.log_error(f"ETA calculation failed: {str(e)}")
        return None

def find_nearest_stops(position):
    """Find nearest stops to create alternate route"""
    stops = frappe.get_all(
        "Bus Stop",
        fields=["name", "latitude", "longitude"],
        filters={"is_active": 1}
    )
    
    # Calculate distances
    for stop in stops:
        stop.distance = geodesic(
            (position["latitude"], position["longitude"]),
            (stop.latitude, stop.longitude)
        ).kilometers
    
    # Sort by distance and return closest 3 stops
    stops.sort(key=lambda x: x.distance)
    return stops[:3]