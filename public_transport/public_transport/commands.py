import frappe
from datetime import datetime, timedelta

def process_agent_payouts():
    """Process agent commission payouts based on frequency settings"""
    from public_transport.public_transport.doctype.booking_agent_settings.booking_agent_settings import (
        process_daily_payouts,
        process_weekly_payouts,
        process_monthly_payouts
    )
    
    # Get current day info
    today = datetime.now()
    is_month_end = (today + timedelta(days=1)).day == 1
    is_week_end = today.weekday() == 6  # Sunday
    
    # Process payouts based on schedule
    process_daily_payouts()
    if is_week_end:
        process_weekly_payouts()
    if is_month_end:
        process_monthly_payouts()

def send_trip_reminders():
    """Send reminders for tomorrow's trips"""
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow_start = tomorrow.replace(hour=0, minute=0, second=0)
    tomorrow_end = tomorrow.replace(hour=23, minute=59, second=59)
    
    # Get all tomorrow's bookings
    bookings = frappe.get_all(
        "Booking",
        filters={
            "booking_status": "Confirmed",
            "bus_trip": ["in", frappe.db.sql("""
                SELECT name FROM `tabBus Trip`
                WHERE departure_time BETWEEN %s AND %s
            """, (tomorrow_start, tomorrow_end))]
        },
        fields=["name", "passenger_name", "passenger_contact", "bus_trip"]
    )
    
    for booking in bookings:
        try:
            frappe.get_doc({
                "doctype": "SMS Log",
                "message": f"Reminder: Your trip {booking.bus_trip} is scheduled for tomorrow",
                "phone": booking.passenger_contact,
                "status": "Queued"
            }).insert()
        except Exception as e:
            frappe.log_error(f"Failed to send reminder for booking {booking.name}: {str(e)}")

def cleanup_expired_seat_locks():
    """Remove expired seat locks from cache"""
    from public_transport.public_transport.utils.realtime_sync import release_seat_lock
    
    # Get all keys starting with seat_lock:
    keys = frappe.cache().get_keys("seat_lock:*")
    for key in keys:
        if not frappe.cache().exists(key):
            # Key has expired, extract trip and seat info
            _, trip_id, seat_id = key.split(":")
            release_seat_lock(trip_id, seat_id)

def cleanup_gps_logs():
    """Remove GPS logs older than 30 days"""
    cutoff_date = frappe.utils.add_days(None, -30)
    frappe.db.delete(
        "GPS Location Log",
        {
            "timestamp": ["<", cutoff_date]
        }
    )
    frappe.db.commit()