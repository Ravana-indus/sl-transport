import frappe
from frappe import _

def get_context(context):
    context.no_cache = 1
    
    # Get available trips for today and future
    context.trips = frappe.get_all(
        "Bus Trip",
        filters={
            "departure_time": [">", frappe.utils.now_datetime()],
            "docstatus": 1
        },
        fields=["name", "route", "bus_type", "departure_time", "arrival_time"],
        order_by="departure_time asc"
    )
    
    # Add available seats count for each trip
    for trip in context.trips:
        trip.available_seats = len(frappe.get_all(
            "Seat Map",
            filters={
                "parent": trip.name,
                "status": "Available"
            }
        ))
        
    return context