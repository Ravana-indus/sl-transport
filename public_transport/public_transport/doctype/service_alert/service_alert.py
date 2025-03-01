import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from .notification_manager import ServiceAlertNotificationManager

class ServiceAlert(Document):
    def validate(self):
        self.validate_dates()
        self.validate_affected_routes()
        
    def validate_dates(self):
        if self.end_time <= self.start_time:
            frappe.throw("End time must be after start time")
        
        if self.start_time < now_datetime() and self.is_new():
            frappe.throw("Start time cannot be in the past for new alerts")
    
    def validate_affected_routes(self):
        if self.affected_routes:
            # Ensure all routes are active
            for route in self.affected_routes:
                route_status = frappe.db.get_value("Route", route.route, "status")
                if route_status != "Active":
                    frappe.throw(f"Route {route.route} is not active")
    
    def on_submit(self):
        if self.status == "Draft":
            self.status = "Active"
        self.notify_affected_parties()
        self.publish_realtime_update()
    
    def on_update(self):
        if not self.is_new() and self.has_value_changed("alert_message"):
            self.publish_realtime_update(update_type="update")
    
    def on_update_after_submit(self):
        if self.has_value_changed("status"):
            if self.status == "Resolved":
                self.publish_realtime_update(update_type="resolve")
        else:
            self.publish_realtime_update(update_type="update")
    
    def notify_affected_parties(self):
        """Send notifications through configured channels"""
        if self.notification_sent:
            return
            
        notification_manager = ServiceAlertNotificationManager(self)
        notification_manager.notify_all_channels()
        
        self.notification_sent = 1
        self.db_set('notification_sent', 1, update_modified=False)
    
    def publish_realtime_update(self, update_type="new"):
        """Publish realtime update for websocket clients"""
        if update_type == "new":
            data = self.get_alert_data()
        elif update_type == "update":
            data = self.get_alert_data()
        else:  # resolve
            data = {"alert_id": self.name}
            
        frappe.publish_realtime(
            'service_alert_update',
            {
                "type": update_type,
                "alert": data
            }
        )
    
    def get_alert_data(self):
        """Get formatted alert data for realtime updates"""
        return {
            "name": self.name,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "alert_message": self.alert_message,
            "affected_areas": self.affected_areas,
            "action_required": self.action_required,
            "start_time": self.start_time.strftime("%H:%M"),
            "end_time": self.end_time.strftime("%H:%M")
        }