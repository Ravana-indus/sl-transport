import frappe
from frappe.model.document import Document

class BusTrip(Document):
    def validate(self):
        self.validate_dates()
        if self.long_trip_limited_seat:
            self.validate_seat_map()

    def validate_dates(self):
        if self.departure_time >= self.arrival_time:
            frappe.throw("Departure time must be before arrival time")

    def validate_seat_map(self):
        if not self.seat_map_layout:
            frappe.throw("Seat map layout is required for long trips")
        
        # Validate unique seat IDs within the trip
        seat_ids = []
        for seat in self.seat_map_layout:
            if seat.seat_id in seat_ids:
                frappe.throw(f"Duplicate seat ID found: {seat.seat_id}")
            seat_ids.append(seat.seat_id)
            
        # Validate seat capacity against bus capacity
        bus_doc = frappe.get_doc("Bus", self.bus)
        if len(self.seat_map_layout) > bus_doc.capacity:
            frappe.throw(f"Seat map exceeds bus capacity of {bus_doc.capacity}")

def has_permission(doc, ptype, user):
    """Custom permission check for Bus Trip"""
    if not user:
        user = frappe.session.user

    # System Manager can do anything
    if "System Manager" in frappe.get_roles(user):
        return True

    # Check role-specific permissions
    roles = frappe.get_roles(user)
    
    if ptype == "read":
        # All roles can read bus trips
        return True
    
    elif ptype == "write":
        # Bus Operators can edit their own trips
        if "Bus Operator" in roles and doc.bus_operator == user:
            return True
        # Bus Conductors can edit trips they're assigned to
        if "Bus Conductor" in roles and doc.bus_operator == user:
            return True
            
    elif ptype == "create":
        # Only Bus Operators can create trips
        return "Bus Operator" in roles
        
    elif ptype in ["submit", "cancel", "amend"]:
        # Only Bus Operators can submit/cancel/amend their own trips
        return "Bus Operator" in roles and doc.bus_operator == user

    return False