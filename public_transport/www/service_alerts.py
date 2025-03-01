import frappe
from frappe.utils import now_datetime

def get_context(context):
    context.no_cache = 1
    
    # Get active alerts
    context.alerts = frappe.get_all(
        "Service Alert",
        filters={
            "status": "Active",
            "end_time": [">", now_datetime()]
        },
        fields=[
            "name", "alert_type", "severity", 
            "start_time", "end_time", "affected_areas",
            "alert_message", "action_required"
        ],
        order_by="severity desc, start_time desc"
    )
    
    # Group alerts by severity
    context.alerts_by_severity = {
        "Critical": [],
        "High": [],
        "Medium": [],
        "Low": []
    }
    
    for alert in context.alerts:
        # Get affected routes for each alert
        alert.routes = frappe.get_all(
            "Route",
            filters={"name": ["in", [r.route for r in alert.affected_routes]]},
            fields=["route_name", "route_number"]
        ) if alert.affected_routes else []
        
        context.alerts_by_severity[alert.severity].append(alert)
    
    return context