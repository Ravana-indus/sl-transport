import frappe
from frappe.model.document import Document
from geopy.distance import geodesic

class Route(Document):
    def validate(self):
        self.validate_stops()
        self.calculate_route_metrics()
    
    def validate_stops(self):
        """Validate route stops sequence and constraints"""
        if not self.stops:
            frappe.throw("Route must have at least two stops")
            
        # Sort stops by sequence
        self.stops.sort(key=lambda x: x.sequence)
        
        # Validate sequence numbers
        sequences = [stop.sequence for stop in self.stops]
        if len(set(sequences)) != len(sequences):
            frappe.throw("Stop sequence numbers must be unique")
            
        # Validate pickup/dropoff constraints
        if self.stops[0].is_dropoff_only:
            frappe.throw("First stop cannot be dropoff only")
        if self.stops[-1].is_pickup_only:
            frappe.throw("Last stop cannot be pickup only")
            
        # Update sequence numbers to be continuous
        for i, stop in enumerate(self.stops, 1):
            stop.sequence = i
    
    def calculate_route_metrics(self):
        """Calculate total distance and estimated time"""
        total_distance = 0
        total_time = 0
        
        for i in range(len(self.stops) - 1):
            current_stop = frappe.get_doc("Bus Stop", self.stops[i].stop)
            next_stop = frappe.get_doc("Bus Stop", self.stops[i + 1].stop)
            
            # Calculate distance between stops
            distance = geodesic(
                (current_stop.latitude, current_stop.longitude),
                (next_stop.latitude, next_stop.longitude)
            ).kilometers
            
            self.stops[i].distance_from_previous = distance if i > 0 else 0
            total_distance += distance
            
            # Estimate time based on route type and distance
            speed = self.get_average_speed()
            time_minutes = (distance / speed) * 60
            
            # Add stop time
            time_minutes += self.get_stop_time()
            
            self.stops[i].estimated_time_from_previous = round(time_minutes)
            total_time += time_minutes
        
        self.distance = round(total_distance, 2)
        self.estimated_time = round(total_time)
        
        # For circular routes, add return to start
        if self.is_circular:
            first_stop = frappe.get_doc("Bus Stop", self.stops[0].stop)
            last_stop = frappe.get_doc("Bus Stop", self.stops[-1].stop)
            
            return_distance = geodesic(
                (last_stop.latitude, last_stop.longitude),
                (first_stop.latitude, first_stop.longitude)
            ).kilometers
            
            self.distance += return_distance
            self.estimated_time += round((return_distance / self.get_average_speed()) * 60)
    
    def get_average_speed(self):
        """Get average speed based on route type"""
        speeds = {
            "Urban": 20,      # km/h
            "Suburban": 35,
            "Highway": 60,
            "Express": 70
        }
        return speeds.get(self.route_type, 30)
    
    def get_stop_time(self):
        """Get average stop time in minutes"""
        times = {
            "Urban": 2,       # minutes
            "Suburban": 1,
            "Highway": 3,
            "Express": 5
        }
        return times.get(self.route_type, 2)
    
    def on_update(self):
        """Update all bus trips using this route"""
        trips = frappe.get_all(
            "Bus Trip",
            filters={"route": self.route_number},
            fields=["name"]
        )
        
        for trip in trips:
            try:
                trip_doc = frappe.get_doc("Bus Trip", trip.name)
                if trip_doc.docstatus == 1:  # If submitted
                    continue
                trip_doc.save()
            except Exception as e:
                frappe.log_error(f"Failed to update trip {trip.name}: {str(e)}")