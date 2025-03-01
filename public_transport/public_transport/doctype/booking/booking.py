import frappe
from frappe.model.document import Document
from ..utils.realtime_sync import notify_seat_status_change, notify_booking_confirmation, lock_seat, release_seat_lock

class Booking(Document):
    def validate(self):
        self.validate_seats()
        self.set_booking_time()
        self.validate_booking_agent()

    def validate_seats(self):
        if not self.selected_seats:
            frappe.throw("At least one seat must be selected")
            
        trip = frappe.get_doc("Bus Trip", self.bus_trip)
        available_seats = {seat.seat_id: seat for seat in trip.seat_map_layout if seat.status == "Available"}
        
        for seat in self.selected_seats:
            if seat.seat_id not in available_seats:
                frappe.throw(f"Seat {seat.seat_id} is not available")
            # Try to lock the seat during booking
            if not lock_seat(self.bus_trip, seat.seat_id, frappe.session.user):
                frappe.throw(f"Seat {seat.seat_id} is currently being booked by another user")

    def set_booking_time(self):
        if self.is_new():
            self.booking_time = frappe.utils.now_datetime()

    def validate_booking_agent(self):
        if self.user_role == "Booking Agent" and not self.booking_agent:
            frappe.throw("Booking Agent must be specified for bookings made by agents")

    def on_trash(self):
        # Release any seat locks if booking is cancelled
        for seat in self.selected_seats:
            release_seat_lock(self.bus_trip, seat.seat_id)

    def on_submit(self):
        # Update seat status in the trip
        trip = frappe.get_doc("Bus Trip", self.bus_trip)
        for seat in self.selected_seats:
            for trip_seat in trip.seat_map_layout:
                if trip_seat.seat_id == seat.seat_id:
                    trip_seat.status = "Booked"
                    notify_seat_status_change(self.bus_trip, seat.seat_id, "Booked")
        trip.save()

        # Create payment record
        if self.booking_status == "Confirmed":
            self.create_payment()
            notify_booking_confirmation(self.name)

    def create_payment(self):
        # Calculate total amount from selected seats
        total_amount = sum(seat.price or 0 for seat in self.selected_seats)
        
        payment = frappe.new_doc("Payment")
        payment.update({
            "booking": self.name,
            "payment_type": self.payment_mode,
            "amount": total_amount,
            "payment_time": frappe.utils.now_datetime(),
            "transaction_status": "Success"
        })
        payment.insert()

def has_permission(doc, ptype, user):
    """Custom permission check for Booking"""
    if not user:
        user = frappe.session.user

    if "System Manager" in frappe.get_roles(user):
        return True

    roles = frappe.get_roles(user)
    
    if ptype == "read":
        # Regular users can only read their own bookings
        if "Regular User" in roles:
            return doc.passenger_contact == frappe.db.get_value("User", user, "mobile_no")
        # Booking agents can read bookings they created
        if "Booking Agent" in roles:
            return doc.booking_agent == frappe.db.get_value("Booking Agent Settings", {"user": user}, "name")
        # Bus operators and conductors can read bookings for their trips
        if "Bus Operator" in roles or "Bus Conductor" in roles:
            return doc.bus_operator == user
            
    elif ptype == "write":
        # Regular users can't modify bookings
        if "Regular User" in roles:
            return False
        # Booking agents can modify their own bookings before submission
        if "Booking Agent" in roles and not doc.docstatus == 1:
            return doc.booking_agent == frappe.db.get_value("Booking Agent Settings", {"user": user}, "name")
        # Bus operators and conductors can modify bookings for their trips
        if "Bus Operator" in roles or "Bus Conductor" in roles:
            return doc.bus_operator == user
            
    elif ptype == "create":
        # All roles except System Manager need additional validation
        if "Regular User" in roles:
            # Regular users can only create bookings for themselves
            return True
        if "Booking Agent" in roles:
            # Booking agents must be active
            return frappe.db.get_value("Booking Agent Settings", {"user": user, "status": "Active"}, "name")
        if "Bus Operator" in roles or "Bus Conductor" in roles:
            return True
            
    elif ptype in ["submit", "cancel", "amend"]:
        # Regular users can't submit/cancel/amend
        if "Regular User" in roles:
            return False
        # Others can only handle their own bookings
        if "Booking Agent" in roles:
            return doc.booking_agent == frappe.db.get_value("Booking Agent Settings", {"user": user}, "name")
        if "Bus Operator" in roles or "Bus Conductor" in roles:
            return doc.bus_operator == user
            
    return False