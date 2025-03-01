import frappe
from frappe.model.document import Document
from datetime import datetime
from geopy.distance import geodesic

class RouteDeviation(Document):
    def validate(self):
        self.validate_dates()
        self.validate_stops()
        self.update_affected_trips()
        
    def validate_dates(self):
        if self.end_time <= self.start_time:
            frappe.throw("End time must be after start time")
            
        if self.start_time < frappe.utils.now_datetime():
            frappe.throw("Start time cannot be in the past")
    
    def validate_stops(self):
        """Ensure alternate stops form a valid route"""
        if len(self.alternate_stops) < 2:
            frappe.throw("Must specify at least two stops for the alternate route")
            
        # Validate stop sequence
        for i, stop in enumerate(self.alternate_stops):
            stop.sequence = i + 1
            
        # Calculate distances and times
        self.calculate_alternate_metrics()
    
    def calculate_alternate_metrics(self):
        """Calculate distances and times for alternate route"""
        total_distance = 0
        total_time = 0
        
        for i in range(len(self.alternate_stops) - 1):
            current = frappe.get_doc("Bus Stop", self.alternate_stops[i].stop)
            next_stop = frappe.get_doc("Bus Stop", self.alternate_stops[i + 1].stop)
            
            distance = geodesic(
                (current.latitude, current.longitude),
                (next_stop.latitude, next_stop.longitude)
            ).kilometers
            
            self.alternate_stops[i].distance_from_previous = distance if i > 0 else 0
            total_distance += distance
            
            # Estimate time (assume slower speed due to deviation)
            time_minutes = (distance / 25) * 60  # Assume 25 km/h average speed
            self.alternate_stops[i].estimated_time_from_previous = round(time_minutes)
            total_time += time_minutes
    
    def update_affected_trips(self):
        """Find and update trips affected by the deviation"""
        if self.is_new():
            self.affected_trips = []
            
        affected = frappe.get_all(
            "Bus Trip",
            filters={
                "route": self.route,
                "departure_time": ["between", (self.start_time, self.end_time)],
                "docstatus": 1
            },
            fields=["name", "arrival_time"]
        )
        
        existing_trips = {trip.trip for trip in self.affected_trips}
        
        for trip in affected:
            if trip.name not in existing_trips:
                # Calculate new ETA
                original_eta = trip.arrival_time
                delay = self.calculate_trip_delay()
                new_eta = frappe.utils.add_to_date(original_eta, minutes=delay)
                
                self.append("affected_trips", {
                    "trip": trip.name,
                    "original_eta": original_eta.time(),
                    "new_eta": new_eta.time(),
                    "delay_minutes": delay,
                    "passengers_notified": 0
                })
    
    def calculate_trip_delay(self):
        """Calculate estimated delay for trips"""
        original_route = frappe.get_doc("Route", self.route)
        
        # Calculate difference in total time
        original_time = sum(
            stop.estimated_time_from_previous or 0 
            for stop in original_route.stops
        )
        
        alternate_time = sum(
            stop.estimated_time_from_previous or 0 
            for stop in self.alternate_stops
        )
        
        return max(0, alternate_time - original_time)
    
    def after_insert(self):
        self.notify_affected_parties()
    
    def notify_affected_parties(self):
        """Notify passengers and operators about the deviation"""
        if self.notification_sent:
            return
            
        for affected_trip in self.affected_trips:
            # Notify passengers
            bookings = frappe.get_all(
                "Booking",
                filters={
                    "bus_trip": affected_trip.trip,
                    "booking_status": "Confirmed"
                },
                fields=["name", "passenger_name", "passenger_contact"]
            )
            
            for booking in bookings:
                self.send_passenger_notification(
                    booking,
                    affected_trip.delay_minutes
                )
                affected_trip.passengers_notified += 1
            
            # Notify bus operator
            trip = frappe.get_doc("Bus Trip", affected_trip.trip)
            self.send_operator_notification(trip)
        
        self.notification_sent = 1
        self.save()
    
    def send_passenger_notification(self, booking, delay):
        """Send SMS notification to passenger"""
        message = (
            f"Dear {booking.passenger_name}, your trip {booking.name} will be "
            f"delayed by approximately {delay} minutes due to {self.reason.lower()}. "
            f"The bus will follow an alternate route. We apologize for any inconvenience."
        )
        
        frappe.get_doc({
            "doctype": "SMS Log",
            "message": message,
            "phone": booking.passenger_contact,
            "status": "Queued"
        }).insert()
    
    def send_operator_notification(self, trip):
        """Notify bus operator about deviation"""
        message = (
            f"Route deviation activated for trip {trip.name} due to {self.reason}. "
            f"Please follow alternate route as provided. "
            f"Deviation active from {self.start_time.strftime('%H:%M')} "
            f"to {self.end_time.strftime('%H:%M')}."
        )
        
        frappe.get_doc({
            "doctype": "SMS Log",
            "message": message,
            "phone": frappe.db.get_value("User", trip.bus_operator, "mobile_no"),
            "status": "Queued"
        }).insert()