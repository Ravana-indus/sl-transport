import frappe
from frappe.realtime import publish_realtime

def notify_seat_status_change(trip, seat_id, status):
    """Notify all clients about seat status changes"""
    publish_realtime('seat_status_update', {
        'trip': trip,
        'seat_id': seat_id,
        'status': status
    })

def notify_booking_confirmation(booking_id):
    """Notify relevant parties about booking confirmation"""
    booking = frappe.get_doc("Booking", booking_id)
    
    # Notify the booking agent if exists
    if booking.booking_agent:
        publish_realtime(
            'booking_confirmation',
            {'booking_id': booking_id},
            user=frappe.db.get_value('Booking Agent Settings', booking.booking_agent, 'user')
        )
    
    # Notify the bus operator
    publish_realtime(
        'booking_confirmation',
        {'booking_id': booking_id},
        user=booking.bus_operator
    )

def lock_seat(trip_id, seat_id, user):
    """Lock a seat temporarily during booking process"""
    key = f"seat_lock:{trip_id}:{seat_id}"
    if not frappe.cache().exists(key):
        frappe.cache().setex(key, 300, user)  # Lock for 5 minutes
        return True
    return False

def release_seat_lock(trip_id, seat_id):
    """Release a seat lock"""
    key = f"seat_lock:{trip_id}:{seat_id}"
    frappe.cache().delete(key)