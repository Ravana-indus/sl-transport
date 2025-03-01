import frappe
from frappe.utils import now_datetime, add_to_date

def get_context(context):
    context.no_cache = 1
    
    # Get all active trips (departed but not arrived)
    context.active_trips = frappe.get_all(
        "Bus Trip",
        filters={
            "departure_time": ["<=", now_datetime()],
            "arrival_time": [">", now_datetime()],
            "docstatus": 1
        },
        fields=["name", "route", "departure_time", "bus"],
        order_by="departure_time desc"
    )
    
    # Add estimated arrival for each trip
    for trip in context.active_trips:
        trip.departure_time = trip.departure_time.strftime("%H:%M")
        
        # Get latest location
        latest_location = frappe.get_all(
            "GPS Location Log",
            filters={"bus": trip.bus},
            fields=["latitude", "longitude", "timestamp"],
            order_by="timestamp desc",
            limit=1
        )
        
        if latest_location:
            trip.current_location = latest_location[0]
    
    return context